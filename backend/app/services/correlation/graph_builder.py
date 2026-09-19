"""Graph builder and path-finding service using NetworkX for entity correlation."""

import logging
from collections import defaultdict
from typing import Final

import networkx as nx
from sqlmodel import Session, select

from app.db.models import Entity, EntityLink
from app.db.session import engine
from app.services.correlation.confidence_rules import (
    combine_confidences,
    get_link_confidence,
)

logger = logging.getLogger("correlation.graph_builder")

# Epsilon floor to prevent division by zero in inverse confidence computation
MIN_CONFIDENCE_EPSILON: Final[float] = 1e-4


class GraphBuilder:
    """Builds weighted NetworkX graphs from Entity and EntityLink database rows."""

    def __init__(self, session: Session | None = None) -> None:
        """Initialize builder with an optional active database session.

        Args:
            session: SQLModel session. If None, a new session against the global engine
                will be opened for the duration of the build call.
        """
        self.session = session

    @classmethod
    def build_for_case(
        cls,
        case_id: int,
        session: Session | None = None,
        enforce_rules: bool = True,
    ) -> nx.Graph:
        """Build an undirected, confidence-weighted entity graph for a given case.

        Loads all Entity and EntityLink records for the case, creates nodes with
        entity metadata, consolidates multiple links between the same entity pair
        using the confidence compounding rules, assigns inverse-confidence weights
        for path-finding, and labels connected components (clusters).

        Args:
            case_id: Primary key of the investigation case.
            session: Optional SQLModel session.
            enforce_rules: If True, uses the canonical confidence_rules weighting
                table for link weights.

        Returns:
            An undirected networkx.Graph instance with node and edge attributes.
        """
        builder = cls(session=session)
        return builder.build(case_id=case_id, enforce_rules=enforce_rules)

    def build(self, case_id: int, enforce_rules: bool = True) -> nx.Graph:
        """Execute graph construction for the specified case.

        Args:
            case_id: Primary key of the investigation case.
            enforce_rules: If True, uses confidence_rules weighting table.

        Returns:
            An undirected networkx.Graph instance with cluster_id attributes.
        """
        if self.session is not None:
            return self._build_with_session(
                self.session, case_id, enforce_rules=enforce_rules
            )

        with Session(engine) as session:
            return self._build_with_session(
                session, case_id, enforce_rules=enforce_rules
            )

    def _build_with_session(
        self,
        session: Session,
        case_id: int,
        enforce_rules: bool = True,
    ) -> nx.Graph:
        """Internal worker to construct graph from an active database session."""
        graph = nx.Graph()

        # 1. Load all entities for the case
        entities = list(
            session.exec(select(Entity).where(Entity.case_id == case_id)).all()
        )

        for entity in entities:
            if entity.id is not None:
                entity_type_str = (
                    entity.entity_type.value
                    if hasattr(entity.entity_type, "value")
                    else str(entity.entity_type)
                )
                graph.add_node(
                    entity.id,
                    id=entity.id,
                    entity_type=entity_type_str,
                    value=entity.value,
                    case_id=entity.case_id,
                    first_seen_at=(
                        entity.first_seen_at.isoformat()
                        if entity.first_seen_at
                        else None
                    ),
                )

        # 2. Load all entity links for the case
        links = list(
            session.exec(select(EntityLink).where(EntityLink.case_id == case_id)).all()
        )

        # Group links by canonical entity pair (min_id, max_id)
        pair_links: dict[tuple[int, int], list[EntityLink]] = defaultdict(list)
        for link in links:
            if link.entity_a_id == link.entity_b_id:
                continue  # Skip self-links if any
            u = min(link.entity_a_id, link.entity_b_id)
            v = max(link.entity_a_id, link.entity_b_id)
            pair_links[(u, v)].append(link)

        # 3. Add edges with compounded confidence and inverse weights
        for (u, v), link_list in pair_links.items():
            if u not in graph or v not in graph:
                continue

            # Calculate individual confidence weights
            weights: list[float] = []
            for lnk in link_list:
                if enforce_rules or lnk.confidence_score is None:
                    w = get_link_confidence(lnk.link_type)
                else:
                    w = float(lnk.confidence_score)
                weights.append(w)

            combined_confidence = combine_confidences(weights)

            # Determine primary link type (highest individual confidence)
            primary_link = max(
                link_list,
                key=lambda lnk: (
                    get_link_confidence(lnk.link_type)
                    if enforce_rules or lnk.confidence_score is None
                    else float(lnk.confidence_score)
                ),
            )
            primary_link_type = (
                primary_link.link_type.value
                if hasattr(primary_link.link_type, "value")
                else str(primary_link.link_type)
            )

            all_link_types = list(
                {
                    (
                        lnk.link_type.value
                        if hasattr(lnk.link_type, "value")
                        else str(lnk.link_type)
                    )
                    for lnk in link_list
                }
            )

            # Inverse confidence weight for shortest_path:
            # Minimizing (1/confidence) favors paths of high-confidence links.
            inv_confidence = 1.0 / max(combined_confidence, MIN_CONFIDENCE_EPSILON)

            graph.add_edge(
                u,
                v,
                weight=combined_confidence,
                confidence=combined_confidence,
                link_type=primary_link_type,
                link_types=all_link_types,
                inverse_confidence=inv_confidence,
                link_count=len(link_list),
            )

        # 4. Identify connected components (clusters) and assign cluster_id to each node
        if len(graph) > 0:
            # Sort components by size descending, then by min node ID for stability
            components = sorted(
                nx.connected_components(graph),
                key=lambda comp: (-len(comp), min(comp)),
            )
            for cluster_id, component in enumerate(components):
                for node_id in component:
                    graph.nodes[node_id]["cluster_id"] = cluster_id
        else:
            graph.graph["clusters"] = 0

        graph.graph["case_id"] = case_id
        return graph


def find_path(
    graph: nx.Graph,
    entity_a_id: int,
    entity_b_id: int,
) -> list[int] | None:
    """Find the most confident path connecting two entities in the correlation graph.

    Uses NetworkX's shortest_path weighted by inverse confidence (1 / confidence).
    Because shortest_path minimizes the total accumulated weight, inverting confidence
    ensures that paths composed of strong evidentiary signals (e.g., shared IMEI 0.85)
    are strictly preferred over multi-hop weak-signal paths
    (e.g., shared IP subnet 0.30).

    Args:
        graph: Undirected weighted NetworkX graph built by GraphBuilder.
        entity_a_id: Source Entity primary key ID.
        entity_b_id: Target Entity primary key ID.

    Returns:
        List of entity IDs in order from source to target, or None if no path exists.
    """
    if entity_a_id not in graph or entity_b_id not in graph:
        return None

    if entity_a_id == entity_b_id:
        return [entity_a_id]

    try:
        path: list[int] = nx.shortest_path(
            graph,
            source=entity_a_id,
            target=entity_b_id,
            weight="inverse_confidence",
        )
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None
