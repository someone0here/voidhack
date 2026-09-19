"""Ingestion service package for parsing and normalizing forensic artifacts."""

from app.services.ingestion.exceptions import IngestionError
from app.services.ingestion.models import (
    IngestionResult,
    IngestionSummary,
    LinkedEntityRef,
    ParsedRecord,
    ParserResult,
)
from app.services.ingestion.normalizer import normalize

__all__ = [
    "IngestionError",
    "IngestionResult",
    "IngestionSummary",
    "LinkedEntityRef",
    "ParsedRecord",
    "ParserResult",
    "normalize",
]
