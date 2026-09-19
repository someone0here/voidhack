"""Correlation engine: confidence-weighted entity graph building and serialization."""

from app.services.correlation.confidence_rules import (
    CONFIDENCE_CO_OCCURRENCE,
    CONFIDENCE_DEFAULT,
    CONFIDENCE_DIRECT_COMMUNICATION,
    CONFIDENCE_SHARED_IMEI,
    CONFIDENCE_SHARED_IP_SUBNET,
    CONFIDENCE_SHARED_MAC,
    CONFIDENCE_SHARED_UPI_HANDLE,
    CONFIDENCE_TRANSACTION,
    LINK_TYPE_CONFIDENCE,
    WEAK_SIGNAL_THRESHOLD,
    combine_confidences,
    compound_weak_signals,
    get_link_confidence,
)
from app.services.correlation.graph_builder import GraphBuilder, find_path
from app.services.correlation.graph_serializer import GraphSerializer, serialize_graph

__all__ = [
    # Constants
    "CONFIDENCE_SHARED_IMEI",
    "CONFIDENCE_SHARED_UPI_HANDLE",
    "CONFIDENCE_TRANSACTION",
    "CONFIDENCE_DIRECT_COMMUNICATION",
    "CONFIDENCE_SHARED_MAC",
    "CONFIDENCE_CO_OCCURRENCE",
    "CONFIDENCE_SHARED_IP_SUBNET",
    "CONFIDENCE_DEFAULT",
    "WEAK_SIGNAL_THRESHOLD",
    "LINK_TYPE_CONFIDENCE",
    # Functions
    "get_link_confidence",
    "compound_weak_signals",
    "combine_confidences",
    # Builder
    "GraphBuilder",
    "find_path",
    # Serializer
    "GraphSerializer",
    "serialize_graph",
]
