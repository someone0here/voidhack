"""Rule-based risk scoring engine for cyber fraud entity analysis.

===============================================================================
DESIGN PHILOSOPHY: RULE-BASED, NOT ML
===============================================================================
This engine is intentionally NOT machine-learning based. Every score it produces
is the direct arithmetic sum of explicitly triggered, named heuristic rules, each
backed by a documented weight (see reason_codes.py).

Why this matters for law enforcement:
  1. Traceability: An investigating officer, a defence advocate, or a High Court
     judge must be able to ask "why is this entity flagged?" and receive a plain-
     language answer traceable to a specific observable pattern in the evidence —
     not "because the model said so."

  2. Contestability: Opaque ML scores cannot be cross-examined. Every heuristic
     here is a human-readable rule that any trained forensic analyst can evaluate,
     dispute, or re-weight.

  3. Stability under review: ML models drift with retraining. This engine's output
     is deterministic given the same input data; a score computed today will be
     identical to one computed during trial, months later.

  4. Legal admissibility (Section 65B, Indian Evidence Act / BSA 2023): Electronic
     records used in criminal proceedings must demonstrate reliable, auditable
     processes. A rule-based engine whose full logic fits in one file is far easier
     to certify than a neural network whose internals are inaccessible.

The trade-off is acknowledged: rule-based systems can be gamed once their rules
are known, and they miss novel fraud patterns. This trade-off is accepted in
favour of the above guarantees. Novel patterns should prompt new named rules,
not silent model updates.

HUMAN-IN-THE-LOOP CONSTRAINT
==============================
All output from this engine carries a `recommendation` field that uses
advisory language ONLY. The engine recommends — it does not command. No string
produced by this engine should contain directive terms ("arrest", "seize",
"detain", "charge", "convict"). Investigators must exercise independent judgment.
===============================================================================
"""

import logging
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Final

import networkx as nx
from sqlmodel import Session, select

from app.db.models import Entity, EntityLink, EntityType, LinkType, RiskScore
from app.db.session import engine
from app.services.risk.reason_codes import ReasonCode

logger = logging.getLogger("risk.scoring_engine")

# ---------------------------------------------------------------------------
# Configurable Thresholds (named constants — not magic numbers)
# ---------------------------------------------------------------------------

# High-velocity routing: minimum number of distinct linked-entity hops within
# the time window to trigger the HIGH_VELOCITY_ROUTING heuristic.
VELOCITY_HOP_THRESHOLD: Final[int] = 3

# High-velocity routing: time window in minutes within which hops must occur.
VELOCITY_WINDOW_MINUTES: Final[int] = 10

# SIM-switching: minimum distinct phone-number entities linked to a single IMEI
# within the time window to trigger the SIM_SWITCHING_PATTERN heuristic.
SIM_SWITCH_PHONE_THRESHOLD: Final[int] = 3

# SIM-switching: time window in hours within which the distinct phones must
# have been first seen to trigger the SIM_SWITCHING_PATTERN heuristic.
SIM_SWITCH_WINDOW_HOURS: Final[int] = 24

# Shared flagged device: minimum existing RiskScore for a device-sharing peer
# to be considered "already flagged" and trigger SHARED_DEVICE_FLAGGED_PEER.
FLAGGED_PEER_SCORE_THRESHOLD: Final[int] = 40

# Cluster size: ratio above the case's median cluster size to trigger
# OVERSIZED_CLUSTER. E.g., 2.0 means the cluster must be ≥ 2× median.
OVERSIZED_CLUSTER_RATIO: Final[float] = 1.5

# Multi-hub: minimum number of distinct transaction senders converging on this
# entity to trigger MULTI_ACCOUNT_TRANSACTION_HUB.
HUB_SENDER_THRESHOLD: Final[int] = 3

# Score cap — no single entity can score above 100.
MAX_SCORE: Final[int] = 100

# Advisory recommendation string — always advisory, never directive.
# This is the single source of truth for output language.
INVESTIGATOR_RECOMMENDATION: Final[str] = (
    "Recommended for investigator review — "
    "do not act without independent corroboration of the evidence."
)

LOW_RISK_NOTE: Final[str] = (
    "No significant fraud indicators detected at this time. "
    "Continue routine monitoring."
)


# ---------------------------------------------------------------------------
# Output Models
# ---------------------------------------------------------------------------


@dataclass
class TriggeredRule:
    """A single heuristic rule that fired during scoring."""

    reason_code: ReasonCode
    rendered_message: str
    weight: int


@dataclass
class RiskScoreResult:
    """Full result of a risk scoring pass for one entity.

    Fields
    ------
    entity_id:
        Primary key of the scored entity.
    score:
        Aggregate risk score in [0, 100].
    triggered_rules:
        Ordered list of every heuristic that fired, with its human-readable
        rendered message. This is the audit trail.
    reason_code_strings:
        Flat list of code strings (e.g. ["HIGH_VELOCITY_ROUTING", ...])
        suitable for persisting in the RiskScore.reason_codes JSON column.
    recommendation:
        Advisory string for investigators. ALWAYS advisory. NEVER directive.
    persisted_row:
        The RiskScore database row created/updated for this result, or None
        if persistence was skipped.
    """

    entity_id: int
    score: int
    triggered_rules: list[TriggeredRule] = field(default_factory=list)
    reason_code_strings: list[str] = field(default_factory=list)
    recommendation: str = INVESTIGATOR_RECOMMENDATION
    persisted_row: RiskScore | None = None


# ---------------------------------------------------------------------------
# Scoring Engine
# ---------------------------------------------------------------------------


class RiskScoringEngine:
    """Rule-based fraud risk scoring engine.

    Scores a single entity against its correlation graph context, persisting
    the result as a RiskScore row with full reason-code audit trail.

    Every public method is deterministic given identical input. There is no
    randomness, no learned weights, and no model state.
    """

    def __init__(self, session: Session | None = None) -> None:
        """Initialise the engine with an optional database session.

        Args:
            session: Active SQLModel session. If None, a new session is opened
                per score call against the global engine.
        """
        self._session = session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score_entity(
        self,
        entity_id: int,
        graph: nx.Graph,
        persist: bool = True,
    ) -> RiskScoreResult:
        """Score a single entity against its graph context.

        Args:
            entity_id: Primary key of the entity to score.
            graph: Pre-built NetworkX correlation graph from GraphBuilder.
            persist: If True, upsert a RiskScore row into the database.

        Returns:
            RiskScoreResult with score, triggered rules, and recommendation.
        """
        if self._session is not None:
            return self._score_with_session(
                self._session, entity_id, graph, persist=persist
            )

        with Session(engine) as session:
            return self._score_with_session(session, entity_id, graph, persist=persist)

    # ------------------------------------------------------------------
    # Internal orchestration
    # ------------------------------------------------------------------

    def _score_with_session(
        self,
        session: Session,
        entity_id: int,
        graph: nx.Graph,
        persist: bool,
    ) -> RiskScoreResult:
        """Run all heuristics, accumulate score, persist if requested."""
        if entity_id not in graph:
            logger.warning(
                "Entity %d not found in graph — returning zero score.", entity_id
            )
            return RiskScoreResult(
                entity_id=entity_id,
                score=0,
                recommendation=LOW_RISK_NOTE,
            )

        entity_data = graph.nodes[entity_id]
        triggered: list[TriggeredRule] = []

        # Pull all EntityLink rows for this entity from the DB once
        links_a = list(
            session.exec(
                select(EntityLink).where(EntityLink.entity_a_id == entity_id)
            ).all()
        )
        links_b = list(
            session.exec(
                select(EntityLink).where(EntityLink.entity_b_id == entity_id)
            ).all()
        )
        all_links = links_a + links_b

        # ---- Heuristic 1: High-velocity multi-hop routing ----
        rule = self._check_high_velocity_routing(entity_id, graph, all_links, session)
        if rule:
            triggered.append(rule)

        # ---- Heuristic 2: SIM-switching pattern ----
        if entity_data.get("entity_type") in (
            EntityType.DEVICE_IMEI.value,
            EntityType.PHONE.value,
        ):
            rule = self._check_sim_switching(entity_id, graph, all_links, session)
            if rule:
                triggered.append(rule)

        # ---- Heuristic 3: Shared device with flagged peer ----
        rule = self._check_shared_device_flagged_peer(
            entity_id, graph, all_links, session
        )
        if rule:
            triggered.append(rule)

        # ---- Heuristic 4: Oversized cluster ----
        rule = self._check_oversized_cluster(entity_id, graph)
        if rule:
            triggered.append(rule)

        # ---- Heuristic 5: Multi-account transaction hub ----
        rule = self._check_transaction_hub(entity_id, all_links, session)
        if rule:
            triggered.append(rule)

        # ---- Aggregate score (weighted sum, capped at MAX_SCORE) ----
        raw_score = sum(r.weight for r in triggered)
        final_score = min(raw_score, MAX_SCORE)

        reason_code_strings = [r.reason_code.code for r in triggered]

        recommendation = (
            INVESTIGATOR_RECOMMENDATION if final_score > 0 else LOW_RISK_NOTE
        )

        result = RiskScoreResult(
            entity_id=entity_id,
            score=final_score,
            triggered_rules=triggered,
            reason_code_strings=reason_code_strings,
            recommendation=recommendation,
        )

        if persist:
            result.persisted_row = self._persist(session, entity_id, result)

        logger.info(
            "Scored entity %d: score=%d rules=%s",
            entity_id,
            final_score,
            reason_code_strings,
        )
        return result

    # ------------------------------------------------------------------
    # Heuristic implementations
    # ------------------------------------------------------------------

    def _check_high_velocity_routing(
        self,
        entity_id: int,
        graph: nx.Graph,
        all_links: list[EntityLink],
        session: Session,
    ) -> TriggeredRule | None:
        """Heuristic 1 — High-velocity multi-hop routing.

        Examines all entities reachable within 1 hop in the graph. If N or more
        of those neighbors were first seen within VELOCITY_WINDOW_MINUTES of each
        other (or the entity itself), flag rapid multi-hop layering.
        """
        if entity_id not in graph:
            return None

        # Collect first_seen_at timestamps for this entity + all its neighbors
        entity_row = session.get(Entity, entity_id)
        if entity_row is None:
            return None

        raw_ref = entity_row.first_seen_at or datetime.now(tz=UTC)
        # Normalize to naive UTC for comparison (SQLite stores naive datetimes)
        reference_ts = (
            raw_ref.replace(tzinfo=None) if raw_ref.tzinfo is not None else raw_ref
        )

        # Gather timestamps of all directly linked neighbors
        neighbor_ids = list(graph.neighbors(entity_id))
        timestamps: list[datetime] = [reference_ts]

        for nid in neighbor_ids:
            neighbor = session.get(Entity, nid)
            if neighbor and neighbor.first_seen_at:
                ts = neighbor.first_seen_at
                # Normalize to naive UTC
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                timestamps.append(ts)

        if len(timestamps) < VELOCITY_HOP_THRESHOLD + 1:
            # Not enough neighbors to form a hop chain
            return None

        # Sort and find the shortest window containing N+1 timestamps
        timestamps.sort()
        window = timedelta(minutes=VELOCITY_WINDOW_MINUTES)

        hops_in_window = 0
        for i in range(len(timestamps)):
            count = sum(1 for ts in timestamps if ts - timestamps[i] <= window)
            hops_in_window = max(hops_in_window, count - 1)

        if hops_in_window >= VELOCITY_HOP_THRESHOLD:
            rc = ReasonCode.HIGH_VELOCITY_ROUTING
            return TriggeredRule(
                reason_code=rc,
                rendered_message=rc.render(
                    n_hops=hops_in_window,
                    window_minutes=VELOCITY_WINDOW_MINUTES,
                ),
                weight=rc.weight,
            )
        return None

    def _check_sim_switching(
        self,
        entity_id: int,
        graph: nx.Graph,
        all_links: list[EntityLink],
        session: Session,
    ) -> TriggeredRule | None:
        """Heuristic 2 — SIM-switching / burner-rotation pattern.

        For IMEI entities: counts distinct PHONE-type entities linked via
        SHARED_IMEI within SIM_SWITCH_WINDOW_HOURS of each other.

        For PHONE entities: checks if a linked IMEI is itself connected to
        SIM_SWITCH_PHONE_THRESHOLD+ distinct phones.
        """
        entity_data = graph.nodes.get(entity_id, {})
        entity_type = entity_data.get("entity_type", "")

        if entity_type == EntityType.DEVICE_IMEI.value:
            return self._sim_switch_for_imei(entity_id, all_links, session)

        if entity_type == EntityType.PHONE.value:
            # Check if any IMEI this phone is linked to is itself a SIM-switcher
            for lnk in all_links:
                link_type_val = (
                    lnk.link_type.value
                    if hasattr(lnk.link_type, "value")
                    else str(lnk.link_type)
                )
                if link_type_val != LinkType.SHARED_IMEI.value:
                    continue
                peer_id = (
                    lnk.entity_b_id if lnk.entity_a_id == entity_id else lnk.entity_a_id
                )
                peer = session.get(Entity, peer_id)
                if peer is None:
                    continue
                peer_entity_type = (
                    peer.entity_type.value
                    if hasattr(peer.entity_type, "value")
                    else str(peer.entity_type)
                )
                if peer_entity_type != EntityType.DEVICE_IMEI.value:
                    continue
                # Load all links for this IMEI and check its phone count
                imei_links_a = list(
                    session.exec(
                        select(EntityLink).where(EntityLink.entity_a_id == peer_id)
                    ).all()
                )
                imei_links_b = list(
                    session.exec(
                        select(EntityLink).where(EntityLink.entity_b_id == peer_id)
                    ).all()
                )
                result = self._sim_switch_for_imei(
                    peer_id, imei_links_a + imei_links_b, session
                )
                if result is not None:
                    # Propagate: this phone is linked to a SIM-switching device
                    rc = ReasonCode.SIM_SWITCHING_PATTERN
                    return TriggeredRule(
                        reason_code=rc,
                        rendered_message=rc.render(
                            imei=peer.value,
                            n_phones=SIM_SWITCH_PHONE_THRESHOLD,
                            window_hours=SIM_SWITCH_WINDOW_HOURS,
                        ),
                        weight=rc.weight,
                    )
        return None

    def _sim_switch_for_imei(
        self,
        imei_entity_id: int,
        links: list[EntityLink],
        session: Session,
    ) -> TriggeredRule | None:
        """Check whether an IMEI entity is linked to SIM_SWITCH_PHONE_THRESHOLD+
        distinct phone numbers within SIM_SWITCH_WINDOW_HOURS."""
        imei_row = session.get(Entity, imei_entity_id)
        imei_value = imei_row.value if imei_row else str(imei_entity_id)

        phone_timestamps: list[datetime] = []
        seen_phone_ids: set[int] = set()

        for lnk in links:
            link_type_val = (
                lnk.link_type.value
                if hasattr(lnk.link_type, "value")
                else str(lnk.link_type)
            )
            if link_type_val != LinkType.SHARED_IMEI.value:
                continue

            peer_id = (
                lnk.entity_b_id
                if lnk.entity_a_id == imei_entity_id
                else lnk.entity_a_id
            )
            if peer_id in seen_phone_ids:
                continue

            peer = session.get(Entity, peer_id)
            if peer is None:
                continue
            peer_type = (
                peer.entity_type.value
                if hasattr(peer.entity_type, "value")
                else str(peer.entity_type)
            )
            if peer_type != EntityType.PHONE.value:
                continue

            seen_phone_ids.add(peer_id)
            ts = peer.first_seen_at or datetime.utcnow()
            # Normalize to naive UTC (SQLite stores naive datetimes)
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            phone_timestamps.append(ts)

        if len(phone_timestamps) < SIM_SWITCH_PHONE_THRESHOLD:
            return None

        # Check if at least SIM_SWITCH_PHONE_THRESHOLD phones appear within window
        phone_timestamps.sort()
        window = timedelta(hours=SIM_SWITCH_WINDOW_HOURS)

        for i in range(len(phone_timestamps)):
            count = sum(
                1 for ts in phone_timestamps if ts - phone_timestamps[i] <= window
            )
            if count >= SIM_SWITCH_PHONE_THRESHOLD:
                rc = ReasonCode.SIM_SWITCHING_PATTERN
                return TriggeredRule(
                    reason_code=rc,
                    rendered_message=rc.render(
                        imei=imei_value,
                        n_phones=count,
                        window_hours=SIM_SWITCH_WINDOW_HOURS,
                    ),
                    weight=rc.weight,
                )
        return None

    def _check_shared_device_flagged_peer(
        self,
        entity_id: int,
        graph: nx.Graph,
        all_links: list[EntityLink],
        session: Session,
    ) -> TriggeredRule | None:
        """Heuristic 3 — Shared device with already-flagged entity.

        If this entity shares a SHARED_IMEI or SHARED_MAC link with any peer
        that already has a RiskScore >= FLAGGED_PEER_SCORE_THRESHOLD, flag it.
        """
        device_link_types = {
            LinkType.SHARED_IMEI.value,
            LinkType.SHARED_MAC.value,
        }

        for lnk in all_links:
            link_type_val = (
                lnk.link_type.value
                if hasattr(lnk.link_type, "value")
                else str(lnk.link_type)
            )
            if link_type_val not in device_link_types:
                continue

            peer_id = (
                lnk.entity_b_id if lnk.entity_a_id == entity_id else lnk.entity_a_id
            )

            # Look for existing RiskScore rows for the peer
            peer_scores = list(
                session.exec(
                    select(RiskScore).where(RiskScore.entity_id == peer_id)
                ).all()
            )
            if not peer_scores:
                continue

            latest_score = max(ps.score for ps in peer_scores)
            if latest_score >= FLAGGED_PEER_SCORE_THRESHOLD:
                rc = ReasonCode.SHARED_DEVICE_FLAGGED_PEER
                return TriggeredRule(
                    reason_code=rc,
                    rendered_message=rc.render(
                        peer_id=peer_id,
                        peer_score=latest_score,
                    ),
                    weight=rc.weight,
                )
        return None

    def _check_oversized_cluster(
        self,
        entity_id: int,
        graph: nx.Graph,
    ) -> TriggeredRule | None:
        """Heuristic 4 — Membership in an unusually large connected cluster.

        Compares the size of this entity's cluster against the median cluster
        size across the full case graph. If it is OVERSIZED_CLUSTER_RATIO×
        or more above the median, flag it.
        """
        if entity_id not in graph:
            return None

        # Collect all connected component sizes
        components = list(nx.connected_components(graph))
        if len(components) == 0:
            return None

        cluster_sizes = [len(c) for c in components]
        median_size = statistics.median(cluster_sizes)

        if median_size == 0:
            return None

        # Find this entity's cluster size
        entity_cluster_size = 0
        for comp in components:
            if entity_id in comp:
                entity_cluster_size = len(comp)
                break

        if entity_cluster_size == 0:
            return None

        ratio = entity_cluster_size / median_size
        if ratio >= OVERSIZED_CLUSTER_RATIO:
            rc = ReasonCode.OVERSIZED_CLUSTER
            return TriggeredRule(
                reason_code=rc,
                rendered_message=rc.render(
                    cluster_size=entity_cluster_size,
                    median_size=median_size,
                    ratio=ratio,
                ),
                weight=rc.weight,
            )
        return None

    def _check_transaction_hub(
        self,
        entity_id: int,
        all_links: list[EntityLink],
        session: Session,
    ) -> TriggeredRule | None:
        """Heuristic 5 — Multi-account transaction hub / mule aggregator.

        Counts distinct sender entities that have a TRANSACTION link pointing
        to this entity. If HUB_SENDER_THRESHOLD or more distinct senders
        converge here, flag as a probable aggregation node.
        """
        transaction_type_val = LinkType.TRANSACTION.value
        sender_ids: set[int] = set()

        for lnk in all_links:
            link_type_val = (
                lnk.link_type.value
                if hasattr(lnk.link_type, "value")
                else str(lnk.link_type)
            )
            if link_type_val != transaction_type_val:
                continue

            # This entity is the receiver — entity_b_id >= entity_a_id by
            # normalizer convention, but either direction is possible.
            # We count peers as "senders" if they link to this entity.
            peer_id = (
                lnk.entity_b_id if lnk.entity_a_id == entity_id else lnk.entity_a_id
            )
            sender_ids.add(peer_id)

        if len(sender_ids) >= HUB_SENDER_THRESHOLD:
            rc = ReasonCode.MULTI_ACCOUNT_TRANSACTION_HUB
            return TriggeredRule(
                reason_code=rc,
                rendered_message=rc.render(n_senders=len(sender_ids)),
                weight=rc.weight,
            )
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist(
        self,
        session: Session,
        entity_id: int,
        result: RiskScoreResult,
    ) -> RiskScore:
        """Upsert a RiskScore row for the scored entity.

        Existing rows for the same entity are left in place (audit history).
        A new row is always inserted so the full scoring history is preserved.
        """
        row = RiskScore(
            entity_id=entity_id,
            score=result.score,
            reason_codes=result.reason_code_strings,
            computed_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
