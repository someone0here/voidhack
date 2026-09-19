from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.db.models import LinkType


class EntityLinkBase(BaseModel):
    case_id: int
    entity_a_id: int
    entity_b_id: int
    link_type: LinkType
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Deterministic correlation confidence between 0.0 and 1.0",
    )
    source_evidence_file_id: int


class EntityLinkCreate(EntityLinkBase):
    pass


def get_confidence_label(confidence_score: float) -> str:
    """Derive human-readable confidence label without redundant storage.

    Criteria:
      - Strong: >= 0.8
      - Medium: >= 0.5 and < 0.8
      - Weak:   < 0.5
    """
    if confidence_score >= 0.8:
        return "Strong"
    if confidence_score >= 0.5:
        return "Medium"
    return "Weak"


class EntityLinkRead(EntityLinkBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def confidence_label(self) -> str:
        """Derive human-readable confidence label without redundant storage."""
        return get_confidence_label(self.confidence_score)
