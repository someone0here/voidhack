"""Graph serializer: converts NetworkX correlation graphs to JSON for the frontend."""

from typing import Any

import networkx as nx
from pydantic import BaseModel

from app.schemas.entity_link import get_confidence_label


class SerializedNode(BaseModel):
    """Frontend-ready representation of an entity graph node."""

    id: int
    entity_type: str
    value: str
    cluster_id: int


class SerializedEdge(BaseModel):
    """Frontend-ready representation of a correlation graph edge."""

    source: int
    target: int
    confidence: float
    link_type: str
    confidence_label: str


class SerializedGraph(BaseModel):
    """Complete serialized correlation graph envelope."""

    nodes: list[SerializedNode]
    edges: list[SerializedEdge]


def serialize_graph(graph: nx.Graph) -> dict[str, list[dict[str, Any]]]:
    """Convert a NetworkX correlation graph into a clean JSON shape for the frontend.

    Outputs:
        {
            "nodes": [{"id": int, "entity_type": str, "value": str,
                       "cluster_id": int}, ...],
            "edges": [{"source": int, "target": int, "confidence": float,
                       "link_type": str, "confidence_label": str}, ...]
        }

    Reuses Phase 1's schema layer confidence_label derivation logic directly from
    app.schemas.entity_link.get_confidence_label without duplicating thresholds.

    Args:
        graph: NetworkX graph constructed by GraphBuilder.

    Returns:
        Dictionary with 'nodes' and 'edges' lists.
    """
    nodes: list[dict[str, Any]] = []
    for node_id, data in graph.nodes(data=True):
        nodes.append(
            {
                "id": int(node_id),
                "entity_type": str(data.get("entity_type", "")),
                "value": str(data.get("value", "")),
                "cluster_id": int(data.get("cluster_id", 0)),
            }
        )
    nodes.sort(key=lambda n: n["id"])

    edges: list[dict[str, Any]] = []
    for u, v, data in graph.edges(data=True):
        confidence = round(float(data.get("confidence", data.get("weight", 0.0))), 4)
        link_type = data.get("link_type", "")
        if hasattr(link_type, "value"):
            link_type = link_type.value

        confidence_label = get_confidence_label(confidence)

        edges.append(
            {
                "source": int(u),
                "target": int(v),
                "confidence": confidence,
                "link_type": str(link_type),
                "confidence_label": confidence_label,
            }
        )
    edges.sort(
        key=lambda e: (min(e["source"], e["target"]), max(e["source"], e["target"]))
    )

    return {
        "nodes": nodes,
        "edges": edges,
    }


class GraphSerializer:
    """Namespace container for graph serialization utilities."""

    @staticmethod
    def serialize(graph: nx.Graph) -> dict[str, list[dict[str, Any]]]:
        """Serialize a NetworkX graph into clean JSON."""
        return serialize_graph(graph)
