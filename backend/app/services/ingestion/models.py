"""Intermediate data structures and summaries for the ingestion pipeline."""

from dataclasses import dataclass, field
from typing import Any

from app.db.models import CustodyLogEntry, Entity, EntityLink, EntityType, LinkType


@dataclass
class LinkedEntityRef:
    """Reference to an entity linked within the same evidence record."""

    entity_type: EntityType
    value: str
    link_type: LinkType = LinkType.CO_OCCURRENCE
    confidence_score: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_type": self.entity_type.value,
            "value": self.value,
            "link_type": self.link_type.value,
            "confidence_score": self.confidence_score,
        }


@dataclass
class ParsedRecord:
    """Common intermediate shape emitted by all artifact parsers."""

    entity_type: EntityType
    value: str
    linked_entities: list[LinkedEntityRef] = field(default_factory=list)
    source_row_ref: str | int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "entity_type": self.entity_type.value,
            "value": self.value,
            "linked_entities": [link.to_dict() for link in self.linked_entities],
            "source_row_ref": self.source_row_ref,
        }


@dataclass
class ParserResult:
    """Raw parsing result containing intermediate parsed records and row metrics."""

    records: list[ParsedRecord] = field(default_factory=list)
    rows_processed: int = 0
    rows_skipped: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class IngestionSummary:
    """Per-file ingestion summary metrics."""

    rows_processed: int
    rows_skipped: int
    entities_created: int
    entity_links_created: int = 0
    skipped_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "rows_processed": self.rows_processed,
            "rows_skipped": self.rows_skipped,
            "entities_created": self.entities_created,
            "entity_links_created": self.entity_links_created,
            "skipped_reasons": self.skipped_reasons,
        }


@dataclass
class IngestionResult:
    """Final normalized result containing summary, persisted entities, and links."""

    summary: IngestionSummary
    entities: list[Entity] = field(default_factory=list)
    entity_links: list[EntityLink] = field(default_factory=list)
    custody_log: CustodyLogEntry | None = None
