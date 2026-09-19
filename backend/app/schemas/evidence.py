from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import SourceType


class EvidenceFileBase(BaseModel):
    original_filename: str
    source_type: SourceType


class EvidenceFileCreate(EvidenceFileBase):
    case_id: int
    file_hash: str


class EvidenceFileRead(EvidenceFileBase):
    id: int
    case_id: int
    file_hash: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustodyLogEntryBase(BaseModel):
    evidence_file_id: int
    file_hash: str
    previous_hash: str | None = None
    chained_hash: str | None = None
    handling_note: str


class CustodyLogEntryCreate(CustodyLogEntryBase):
    pass


class CustodyLogEntryRead(CustodyLogEntryBase):
    id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
