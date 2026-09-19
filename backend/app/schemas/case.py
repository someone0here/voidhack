from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CaseBase(BaseModel):
    name: str
    status: str = "active"


class CaseCreate(CaseBase):
    pass


class CaseUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class CaseRead(CaseBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
