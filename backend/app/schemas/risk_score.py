from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RiskScoreBase(BaseModel):
    entity_id: int
    score: int = Field(ge=0, le=100, description="Fraud risk score between 0 and 100")
    reason_codes: list[str] = Field(default_factory=list)


class RiskScoreCreate(RiskScoreBase):
    pass


class RiskScoreRead(RiskScoreBase):
    id: int
    computed_at: datetime

    model_config = ConfigDict(from_attributes=True)
