from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import EntityType


class EntityBase(BaseModel):
    case_id: int
    entity_type: EntityType
    value: str


class EntityCreate(EntityBase):
    pass


class EntityRead(EntityBase):
    id: int
    first_seen_at: datetime

    model_config = ConfigDict(from_attributes=True)
