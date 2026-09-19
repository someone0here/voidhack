"""Reason code registry for the rule-based risk scoring engine.

Each ReasonCode entry carries:
  - code:     A stable snake_case identifier (safe to store in DB, safe to display).
  - template: A human-readable interpolable string explaining the triggered rule.
  - weight:   Severity contribution toward the 0-100 aggregate risk score.

Design principle
----------------
Every score emitted by the system MUST be traceable to one or more entries from
this registry. "No score without an explanation" is a hard invariant enforced in
RiskScoringEngine — a score of 0 is valid, but a non-zero score with an empty
reason list is a bug.

Weights are additive and capped at 100 in the scoring engine. They are not ML
outputs: each weight reflects deliberate operational judgement about the severity
of the corresponding fraud pattern, documented inline.
"""

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ReasonCodeDef:
    """Definition of a single risk reason code."""

    code: str
    template: str
    weight: int  # Raw contribution toward 0–100 score


class ReasonCode(Enum):
    """Registry of all reason codes emitted by the risk scoring engine.

    Weight rationale
    ----------------
    HIGH_VELOCITY_ROUTING (45):
        Rapid multi-hop fund movement through unrelated accounts within a tight
        time window is a hallmark of layering in money laundering. N hops in
        under 10 minutes is practically impossible in legitimate retail banking.
        Assigned 45 to make it nearly certain to reach "high risk" when combined
        with any secondary signal.

    SIM_SWITCHING_PATTERN (40):
        A single physical device (IMEI) cycling through 3+ distinct registered
        phone numbers in a short window is a classic SIM-swap / burner-rotation
        tactic used by fraud syndicates to evade CDR-based identity correlation.
        Assigned 40 as it is strong standalone evidence of deliberate obfuscation.

    SHARED_DEVICE_FLAGGED_PEER (35):
        An entity sharing a device or MAC address with an already-scored high-risk
        entity inherits significant operational suspicion. Device sharing in fraud
        networks typically implies confederate actors using the same physical
        hardware for coordination. Assigned 35 because it is conditional on an
        existing score, making it a corroborating escalator rather than a primary
        signal.

    OVERSIZED_CLUSTER (20):
        Membership in a connected entity cluster significantly larger than the
        case's median cluster size indicates the entity is embedded in a broad
        syndicate network. Alone this is insufficient for attribution, but in
        combination with other signals it materially raises operational concern.
        Assigned 20 to reflect its role as a contextual amplifier.

    MULTI_ACCOUNT_TRANSACTION_HUB (30):
        An account that is the intersection point for transactions from 3 or more
        distinct sender accounts is exhibiting classic aggregator/mule-hub
        behaviour. This pattern is strongly associated with cash pooling prior to
        withdrawal or layering. Assigned 30 as a moderately strong primary signal.
    """

    HIGH_VELOCITY_ROUTING = ReasonCodeDef(
        code="HIGH_VELOCITY_ROUTING",
        template=(
            "High-velocity multi-hop routing detected: {n_hops} linked entity hops "
            "observed within {window_minutes} minutes, indicating rapid fund layering."
        ),
        weight=45,
    )

    SIM_SWITCHING_PATTERN = ReasonCodeDef(
        code="SIM_SWITCHING_PATTERN",
        template=(
            "SIM-switching / burner-rotation pattern: same device (IMEI {imei}) "
            "linked to {n_phones} distinct phone numbers within {window_hours}h, "
            "consistent with deliberate CDR identity obfuscation."
        ),
        weight=40,
    )

    SHARED_DEVICE_FLAGGED_PEER = ReasonCodeDef(
        code="SHARED_DEVICE_FLAGGED_PEER",
        template=(
            "Shared device with already-flagged entity: this entity shares a "
            "device or MAC with entity {peer_id} (risk score {peer_score}), "
            "indicating confederate device usage."
        ),
        weight=35,
    )

    OVERSIZED_CLUSTER = ReasonCodeDef(
        code="OVERSIZED_CLUSTER",
        template=(
            "Embedded in oversized syndicate cluster: cluster contains {cluster_size} "
            "entities vs. case median of {median_size:.1f}, indicating broad network "
            "membership ({ratio:.1f}x above median)."
        ),
        weight=20,
    )

    MULTI_ACCOUNT_TRANSACTION_HUB = ReasonCodeDef(
        code="MULTI_ACCOUNT_TRANSACTION_HUB",
        template=(
            "Multi-account transaction hub: this entity receives transactions from "
            "{n_senders} distinct sender accounts, consistent with mule aggregation "
            "or cash-pooling prior to layering."
        ),
        weight=30,
    )

    @property
    def code(self) -> str:
        """Stable snake_case code string."""
        return self.value.code

    @property
    def template(self) -> str:
        """Human-readable template string for the reason narrative."""
        return self.value.template

    @property
    def weight(self) -> int:
        """Severity weight contribution to the 0–100 aggregate score."""
        return self.value.weight

    def render(self, **kwargs: object) -> str:
        """Render the human-readable reason string with interpolated values.

        Args:
            **kwargs: Template variable substitutions.

        Returns:
            Fully interpolated reason string.
        """
        return self.template.format(**kwargs)
