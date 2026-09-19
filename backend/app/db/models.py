from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class SourceType(str, Enum):
    """Supported source evidentiary artifact formats."""

    CDR = "cdr"
    IPDR = "ipdr"
    BANK_UPI = "bank_upi"
    EMAIL = "email"
    ANDROID_LOG = "android_log"


class EntityType(str, Enum):
    """Normalized cross-case entity types."""

    PHONE = "phone"
    ACCOUNT = "account"
    DEVICE_IMEI = "device_imei"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    EMAIL_ADDRESS = "email_address"


class LinkType(str, Enum):
    """Correlation link signal categories."""

    SHARED_IMEI = "shared_imei"
    SHARED_UPI_HANDLE = "shared_upi_handle"
    SHARED_MAC = "shared_mac"
    SHARED_IP_SUBNET = "shared_ip_subnet"
    CO_OCCURRENCE = "co_occurrence"
    DIRECT_COMMUNICATION = "direct_communication"
    TRANSACTION = "transaction"


class CaseStatus(str, Enum):
    """Lifecycle status for an investigation case."""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Case(SQLModel, table=True):
    """Law enforcement investigation case envelope."""

    __tablename__ = "case"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default=CaseStatus.ACTIVE.value, index=True)

    # Relationships
    evidence_files: list["EvidenceFile"] = Relationship(
        back_populates="case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    entities: list["Entity"] = Relationship(
        back_populates="case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    entity_links: list["EntityLink"] = Relationship(
        back_populates="case",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class EvidenceFile(SQLModel, table=True):
    """Raw uploaded investigation artifact record."""

    __tablename__ = "evidence_file"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    original_filename: str
    source_type: SourceType = Field(index=True)
    file_hash: str = Field(index=True)  # SHA-256
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Case | None = Relationship(back_populates="evidence_files")
    custody_logs: list["CustodyLogEntry"] = Relationship(
        back_populates="evidence_file",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    entity_links: list["EntityLink"] = Relationship(
        back_populates="source_evidence_file"
    )


class Entity(SQLModel, table=True):
    """Extracted and normalized investigative identifier."""

    __tablename__ = "entity"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    entity_type: EntityType = Field(index=True)
    value: str = Field(index=True)
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Case | None = Relationship(back_populates="entities")
    risk_scores: list["RiskScore"] = Relationship(
        back_populates="entity",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class EntityLink(SQLModel, table=True):
    """Correlated connection between two extracted entities."""

    __tablename__ = "entity_link"

    id: int | None = Field(default=None, primary_key=True)
    case_id: int = Field(foreign_key="case.id", index=True)
    entity_a_id: int = Field(foreign_key="entity.id", index=True)
    entity_b_id: int = Field(foreign_key="entity.id", index=True)
    link_type: LinkType = Field(index=True)
    confidence_score: float = Field(ge=0.0, le=1.0)
    source_evidence_file_id: int = Field(foreign_key="evidence_file.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    case: Case | None = Relationship(back_populates="entity_links")
    entity_a: Entity | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[EntityLink.entity_a_id]"}
    )
    entity_b: Entity | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[EntityLink.entity_b_id]"}
    )
    source_evidence_file: EvidenceFile | None = Relationship(
        back_populates="entity_links"
    )


class RiskScore(SQLModel, table=True):
    """Calculated operational fraud risk score for an entity."""

    __tablename__ = "risk_score"

    id: int | None = Field(default=None, primary_key=True)
    entity_id: int = Field(foreign_key="entity.id", index=True)
    score: int = Field(ge=0, le=100)
    reason_codes: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    entity: Entity | None = Relationship(back_populates="risk_scores")


class CustodyLogEntry(SQLModel, table=True):
    """Chain of custody audit ledger entry for evidentiary integrity."""

    __tablename__ = "custody_log_entry"

    id: int | None = Field(default=None, primary_key=True)
    evidence_file_id: int = Field(foreign_key="evidence_file.id", index=True)
    file_hash: str = Field(index=True)
    previous_hash: str | None = Field(default=None)
    chained_hash: str | None = Field(default=None, index=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    handling_note: str

    # Relationships
    evidence_file: EvidenceFile | None = Relationship(back_populates="custody_logs")
