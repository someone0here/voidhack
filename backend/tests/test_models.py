import sqlite3
from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import (
    Case,
    CaseStatus,
    CustodyLogEntry,
    Entity,
    EntityLink,
    EntityType,
    EvidenceFile,
    LinkType,
    RiskScore,
    SourceType,
)
from app.schemas.entity_link import EntityLinkCreate, EntityLinkRead


@pytest.fixture(name="db_session")
def db_session_fixture():
    """Create an isolated in-memory SQLite database with foreign keys enabled."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    SQLModel.metadata.drop_all(engine)


def test_tables_create_without_error(db_session: Session):
    """Verify all expected evidentiary and operational tables exist in DB."""
    inspector = inspect(db_session.bind)
    table_names = inspector.get_table_names()

    expected_tables = {
        "case",
        "evidence_file",
        "entity",
        "entity_link",
        "risk_score",
        "custody_log_entry",
    }
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' was not created."


def test_foreign_key_enforcement(db_session: Session):
    """Verify that foreign key constraints prevent orphan records."""
    # Attempt inserting an EvidenceFile pointing to non-existent Case ID 999
    orphan_file = EvidenceFile(
        case_id=999,
        original_filename="cdr_dump.csv",
        source_type=SourceType.CDR,
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    db_session.add(orphan_file)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Attempt inserting an EntityLink pointing to non-existent entities
    case = Case(name="Operation Hawk Eye", status=CaseStatus.ACTIVE.value)
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    valid_file = EvidenceFile(
        case_id=case.id,
        original_filename="cdr_dump.csv",
        source_type=SourceType.CDR,
        file_hash="abc123hash",
    )
    db_session.add(valid_file)
    db_session.commit()
    db_session.refresh(valid_file)

    orphan_link = EntityLink(
        case_id=case.id,
        entity_a_id=999,  # Invalid
        entity_b_id=998,  # Invalid
        link_type=LinkType.SHARED_IMEI,
        confidence_score=0.9,
        source_evidence_file_id=valid_file.id,
    )
    db_session.add(orphan_link)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_valid_relationships_and_navigation(db_session: Session):
    """Verify valid entities, links, risk scores, and custody chain navigation."""
    # 1. Create Case
    case = Case(name="Operation Vanguard", status=CaseStatus.ACTIVE.value)
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)

    # 2. Add Evidence File
    evidence = EvidenceFile(
        case_id=case.id,
        original_filename="bank_transactions.xlsx",
        source_type=SourceType.BANK_UPI,
        file_hash="d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2",
    )
    db_session.add(evidence)
    db_session.commit()
    db_session.refresh(evidence)

    # 3. Add Custody Log
    custody = CustodyLogEntry(
        evidence_file_id=evidence.id,
        file_hash=evidence.file_hash,
        previous_hash=None,
        handling_note="Initial upload and hash verification by forensic intake",
    )
    db_session.add(custody)
    db_session.commit()

    # 4. Add Entities
    entity_a = Entity(
        case_id=case.id,
        entity_type=EntityType.PHONE,
        value="+919876543210",
    )
    entity_b = Entity(
        case_id=case.id,
        entity_type=EntityType.ACCOUNT,
        value="mule_payee@upi",
    )
    db_session.add_all([entity_a, entity_b])
    db_session.commit()
    db_session.refresh(entity_a)
    db_session.refresh(entity_b)

    # 5. Add Link
    link = EntityLink(
        case_id=case.id,
        entity_a_id=entity_a.id,
        entity_b_id=entity_b.id,
        link_type=LinkType.SHARED_UPI_HANDLE,
        confidence_score=0.88,
        source_evidence_file_id=evidence.id,
    )
    db_session.add(link)

    # 6. Add Risk Score
    risk = RiskScore(
        entity_id=entity_a.id,
        score=85,
        reason_codes=["HIGH_VELOCITY_TXN", "MULTI_SIM_LINKED", "MULE_ASSOCIATION"],
    )
    db_session.add(risk)
    db_session.commit()

    # Verify relationship queries
    loaded_case = db_session.exec(select(Case).where(Case.id == case.id)).one()
    assert len(loaded_case.evidence_files) == 1
    assert len(loaded_case.entities) == 2
    assert len(loaded_case.entity_links) == 1

    loaded_evidence = loaded_case.evidence_files[0]
    assert len(loaded_evidence.custody_logs) == 1
    assert loaded_evidence.custody_logs[0].handling_note.startswith("Initial upload")

    loaded_risk = db_session.exec(
        select(RiskScore).where(RiskScore.entity_id == entity_a.id)
    ).one()
    assert loaded_risk.score == 85
    assert "MULE_ASSOCIATION" in loaded_risk.reason_codes


def test_confidence_score_schema_validation():
    """Verify confidence_score is strictly constrained to [0.0, 1.0] at schema level."""
    # Valid values
    valid_low = EntityLinkCreate(
        case_id=1,
        entity_a_id=1,
        entity_b_id=2,
        link_type=LinkType.SHARED_IP_SUBNET,
        confidence_score=0.0,
        source_evidence_file_id=1,
    )
    assert valid_low.confidence_score == 0.0

    valid_high = EntityLinkCreate(
        case_id=1,
        entity_a_id=1,
        entity_b_id=2,
        link_type=LinkType.SHARED_MAC,
        confidence_score=1.0,
        source_evidence_file_id=1,
    )
    assert valid_high.confidence_score == 1.0

    # Below lower bound (0.0)
    with pytest.raises(ValidationError):
        EntityLinkCreate(
            case_id=1,
            entity_a_id=1,
            entity_b_id=2,
            link_type=LinkType.SHARED_IMEI,
            confidence_score=-0.05,
            source_evidence_file_id=1,
        )

    # Above upper bound (1.0)
    with pytest.raises(ValidationError):
        EntityLinkCreate(
            case_id=1,
            entity_a_id=1,
            entity_b_id=2,
            link_type=LinkType.SHARED_IMEI,
            confidence_score=1.05,
            source_evidence_file_id=1,
        )


def test_derived_confidence_labels():
    """Verify EntityLinkRead computes human-readable Strong/Medium/Weak labels."""
    now = datetime.utcnow()

    link_strong = EntityLinkRead(
        id=1,
        case_id=1,
        entity_a_id=10,
        entity_b_id=20,
        link_type=LinkType.SHARED_IMEI,
        confidence_score=0.85,
        source_evidence_file_id=5,
        created_at=now,
    )
    assert link_strong.confidence_label == "Strong"

    link_medium = EntityLinkRead(
        id=2,
        case_id=1,
        entity_a_id=10,
        entity_b_id=20,
        link_type=LinkType.SHARED_IP_SUBNET,
        confidence_score=0.65,
        source_evidence_file_id=5,
        created_at=now,
    )
    assert link_medium.confidence_label == "Medium"

    link_weak = EntityLinkRead(
        id=3,
        case_id=1,
        entity_a_id=10,
        entity_b_id=20,
        link_type=LinkType.SHARED_IP_SUBNET,
        confidence_score=0.35,
        source_evidence_file_id=5,
        created_at=now,
    )
    assert link_weak.confidence_label == "Weak"
