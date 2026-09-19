import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import (
    Case,
    CaseStatus,
    Entity,
    EntityLink,
    EntityType,
    EvidenceFile,
    SourceType,
)
from app.services.ingestion.exceptions import (
    CorruptedFileError,
    EmptyFileError,
    IngestionError,
    MissingColumnError,
)
from app.services.ingestion.normalizer import normalize
from app.services.ingestion.parsers.android_log_parser import AndroidLogParser
from app.services.ingestion.parsers.bank_parser import BankParser
from app.services.ingestion.parsers.cdr_parser import CDRParser
from app.services.ingestion.parsers.email_parser import EmailParser

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


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


@pytest.fixture(name="sample_case")
def sample_case_fixture(db_session: Session) -> Case:
    """Create a sample investigation case in the test database."""
    case = Case(name="Operation Phantom Grid", status=CaseStatus.ACTIVE.value)
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def create_evidence_record(
    session: Session, case_id: int, filename: str, source_type: SourceType
) -> EvidenceFile:
    """Helper to persist an EvidenceFile row for FK references."""
    evidence = EvidenceFile(
        case_id=case_id,
        original_filename=filename,
        source_type=source_type,
        file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


# ---------------------------------------------------------------------------
# CDR Parser Tests
# ---------------------------------------------------------------------------


def test_cdr_parser_success():
    """Verify CDR parser processes sample CSV, extracting phones, IMEIs, and links."""
    fixture_path = FIXTURES_DIR / "cdr_sample.csv"
    parser = CDRParser()
    result = parser.parse(fixture_path)

    # 7 rows in file: 6 valid, 1 completely empty/malformed
    assert result.rows_processed == 6
    assert result.rows_skipped == 1
    assert len(result.errors) == 1

    extracted_values = {r.value for r in result.records}
    assert "+919811122233" in extracted_values  # Mule 1
    assert "+919876543210" in extracted_values  # Victim
    assert "860123456789012" in extracted_values  # Shared IMEI

    # Check caller-to-IMEI link
    mule1_records = [
        r
        for r in result.records
        if r.value == "+919811122233" and r.entity_type == EntityType.PHONE
    ]
    assert len(mule1_records) > 0
    linked_to_mule1 = {link.value for r in mule1_records for link in r.linked_entities}
    assert "860123456789012" in linked_to_mule1


def test_cdr_parser_missing_columns():
    """Verify CDR parser raises MissingColumnError when required columns are absent."""
    csv_data = b"foo,bar,baz\n1,2,3\n4,5,6"
    parser = CDRParser()
    with pytest.raises(MissingColumnError) as exc_info:
        parser.parse(csv_data)
    assert "missing identifier columns" in str(exc_info.value)


def test_cdr_parser_empty_file():
    """Verify CDR parser raises EmptyFileError when file has no content."""
    parser = CDRParser()
    with pytest.raises(EmptyFileError):
        parser.parse(b"")


# ---------------------------------------------------------------------------
# Bank Parser Tests
# ---------------------------------------------------------------------------


def test_bank_parser_success():
    """Verify Bank parser extracts accounts, UPI handles, amounts, and linkages."""
    fixture_path = FIXTURES_DIR / "bank_sample.csv"
    parser = BankParser()
    result = parser.parse(fixture_path)

    # 5 rows: 4 valid transfers, 1 malformed row
    assert result.rows_processed == 4
    assert result.rows_skipped == 1
    assert len(result.errors) == 1

    extracted_accounts = {
        r.value for r in result.records if r.entity_type == EntityType.ACCOUNT
    }
    assert "VICTIM_ACC_001" in extracted_accounts
    assert "MULE_ACC_101" in extracted_accounts
    assert "CASHOUT_ACC_303" in extracted_accounts
    assert "cashout_syndicate@paytm" in extracted_accounts

    # Phone extracted from UPI handle (9811122233@okhdfcbank -> +919811122233)
    extracted_phones = {
        r.value for r in result.records if r.entity_type == EntityType.PHONE
    }
    assert "+919811122233" in extracted_phones


def test_bank_parser_missing_columns():
    """Verify Bank parser raises MissingColumnError on schema mismatch."""
    csv_data = b"city,state,country\nDelhi,Delhi,India"
    parser = BankParser()
    with pytest.raises(MissingColumnError):
        parser.parse(csv_data)


def test_bank_parser_empty_file():
    """Verify Bank parser raises EmptyFileError on empty file."""
    parser = BankParser()
    with pytest.raises(EmptyFileError):
        parser.parse(b"")


# ---------------------------------------------------------------------------
# Email Parser Tests
# ---------------------------------------------------------------------------


def test_email_parser_success():
    """Verify Email parser extracts From, To, Received IP hop chain, and links."""
    fixture_path = FIXTURES_DIR / "email_sample_1.eml"
    parser = EmailParser()
    result = parser.parse(fixture_path)

    assert result.rows_processed == 1
    assert result.rows_skipped == 0

    entities_by_type: dict[EntityType, set[str]] = {}
    for r in result.records:
        entities_by_type.setdefault(r.entity_type, set()).add(r.value)

    assert (
        "support-refund@fraud-alert-axis.com"
        in entities_by_type[EntityType.EMAIL_ADDRESS]
    )
    assert "victim.rajesh@gmail.com" in entities_by_type[EntityType.EMAIL_ADDRESS]
    assert "185.220.101.5" in entities_by_type[EntityType.IP_ADDRESS]

    # Verify link between sender email and hop IP
    sender_rec = next(
        r for r in result.records if r.value == "support-refund@fraud-alert-axis.com"
    )
    linked_values = {link.value for link in sender_rec.linked_entities}
    assert "185.220.101.5" in linked_values
    assert "victim.rajesh@gmail.com" in linked_values


def test_email_parser_second_fixture():
    """Verify second email fixture extracts syndicate coordination endpoints."""
    fixture_path = FIXTURES_DIR / "email_sample_2.eml"
    parser = EmailParser()
    result = parser.parse(fixture_path)

    emails = {
        r.value for r in result.records if r.entity_type == EntityType.EMAIL_ADDRESS
    }
    ips = {r.value for r in result.records if r.entity_type == EntityType.IP_ADDRESS}

    assert "internal-mule1@fraud-alert-axis.com" in emails
    assert "cashout-ops@darkmesh.net" in emails
    assert "185.220.101.6" in ips


def test_email_parser_corrupted():
    """Verify email parser raises CorruptedFileError on garbage data."""
    parser = EmailParser()
    with pytest.raises(CorruptedFileError):
        parser.parse(b"This is completely arbitrary text with no email headers.")


def test_email_parser_empty():
    """Verify email parser raises EmptyFileError on empty file."""
    parser = EmailParser()
    with pytest.raises(EmptyFileError):
        parser.parse(b"")


# ---------------------------------------------------------------------------
# Android Log Parser Tests
# ---------------------------------------------------------------------------


def test_android_log_parser_json():
    """Verify Android parser extracts identifiers and links from JSON dump."""
    fixture_path = FIXTURES_DIR / "android_log_sample.json"
    parser = AndroidLogParser()
    result = parser.parse(fixture_path)

    assert result.rows_processed > 0
    assert result.rows_skipped == 0

    imeis = {r.value for r in result.records if r.entity_type == EntityType.DEVICE_IMEI}
    macs = {r.value for r in result.records if r.entity_type == EntityType.MAC_ADDRESS}
    ips = {r.value for r in result.records if r.entity_type == EntityType.IP_ADDRESS}
    phones = {r.value for r in result.records if r.entity_type == EntityType.PHONE}

    assert "860123456789012" in imeis
    assert "00:1A:2B:3C:4D:5E" in macs
    assert "185.220.101.5" in ips
    assert "+919811122233" in phones

    # Check device co-occurrence links
    imei_record = next(r for r in result.records if r.value == "860123456789012")
    imei_links = {link.value for link in imei_record.linked_entities}
    assert "00:1A:2B:3C:4D:5E" in imei_links
    assert "185.220.101.5" in imei_links


def test_android_log_parser_text():
    """Verify Android parser extracts identifiers from plaintext logcat."""
    fixture_path = FIXTURES_DIR / "android_log_sample.txt"
    parser = AndroidLogParser()
    result = parser.parse(fixture_path)

    assert result.rows_processed > 0
    imeis = {r.value for r in result.records if r.entity_type == EntityType.DEVICE_IMEI}
    macs = {r.value for r in result.records if r.entity_type == EntityType.MAC_ADDRESS}
    ips = {r.value for r in result.records if r.entity_type == EntityType.IP_ADDRESS}
    phones = {r.value for r in result.records if r.entity_type == EntityType.PHONE}

    assert "860123456789012" in imeis
    assert "00:1A:2B:3C:4D:5E" in macs
    assert "185.220.101.5" in ips
    assert "+919811122233" in phones


def test_android_log_parser_corrupted():
    """Verify Android parser raises CorruptedFileError when no identifiers exist."""
    parser = AndroidLogParser()
    with pytest.raises(CorruptedFileError):
        parser.parse("Just some random logs without any hardware or network ids\n" * 5)


def test_android_log_parser_empty():
    """Verify Android parser raises EmptyFileError on empty log."""
    parser = AndroidLogParser()
    with pytest.raises(EmptyFileError):
        parser.parse("")


# ---------------------------------------------------------------------------
# Normalizer Integration & Cross-File Deduplication Tests
# ---------------------------------------------------------------------------


def test_normalizer_deduplication_across_files(db_session: Session, sample_case: Case):
    """Verify normalizer dedupes entities across uploaded artifacts in a case."""
    case_id = sample_case.id
    assert case_id is not None

    # 1. Ingest CDR file
    cdr_file = create_evidence_record(
        db_session, case_id, "cdr_dump.csv", SourceType.CDR
    )
    assert cdr_file.id is not None
    cdr_path = FIXTURES_DIR / "cdr_sample.csv"

    res_cdr = normalize(
        file_source=cdr_path,
        source_type=SourceType.CDR,
        case_id=case_id,
        evidence_file_id=cdr_file.id,
        session=db_session,
    )
    assert res_cdr.summary.rows_processed == 6
    assert res_cdr.summary.rows_skipped == 1
    assert res_cdr.summary.entities_created > 0

    # Verify phone +919811122233 exists once in DB
    mule1_phones = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.PHONE)
        .where(Entity.value == "+919811122233")
    ).all()
    assert len(mule1_phones) == 1
    mule1_entity_id = mule1_phones[0].id

    # Verify IMEI 860123456789012 exists once in DB
    imeis_phase1 = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.DEVICE_IMEI)
        .where(Entity.value == "860123456789012")
    ).all()
    assert len(imeis_phase1) == 1

    # 2. Ingest Bank sheet (which includes 9811122233@okhdfcbank -> +919811122233)
    bank_file = create_evidence_record(
        db_session, case_id, "bank_ledger.csv", SourceType.BANK_UPI
    )
    assert bank_file.id is not None
    bank_path = FIXTURES_DIR / "bank_sample.csv"

    res_bank = normalize(
        file_source=bank_path,
        source_type=SourceType.BANK_UPI,
        case_id=case_id,
        evidence_file_id=bank_file.id,
        session=db_session,
    )
    assert res_bank.summary.rows_processed == 4

    # Phone +919811122233 must STILL be exactly 1 record in the case
    mule1_phones_after_bank = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.PHONE)
        .where(Entity.value == "+919811122233")
    ).all()
    assert len(mule1_phones_after_bank) == 1
    assert mule1_phones_after_bank[0].id == mule1_entity_id

    # 3. Ingest Android log (contains IMEI 860123456789012 and Phone +919811122233)
    android_file = create_evidence_record(
        db_session, case_id, "android_dump.json", SourceType.ANDROID_LOG
    )
    assert android_file.id is not None
    android_path = FIXTURES_DIR / "android_log_sample.json"

    res_android = normalize(
        file_source=android_path,
        source_type=SourceType.ANDROID_LOG,
        case_id=case_id,
        evidence_file_id=android_file.id,
        session=db_session,
    )
    assert res_android.summary.rows_processed > 0

    # In Android log: Phone and IMEI were already in DB; only new IDs were added
    mule1_phones_after_android = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.PHONE)
        .where(Entity.value == "+919811122233")
    ).all()
    assert len(mule1_phones_after_android) == 1

    imeis_final = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.DEVICE_IMEI)
        .where(Entity.value == "860123456789012")
    ).all()
    assert len(imeis_final) == 1

    # 4. Ingest Phishing Email 1 (which links suspect IP 185.220.101.5)
    email_file = create_evidence_record(
        db_session, case_id, "phishing.eml", SourceType.EMAIL
    )
    assert email_file.id is not None
    email_path = FIXTURES_DIR / "email_sample_1.eml"

    res_email = normalize(
        file_source=email_path,
        source_type=SourceType.EMAIL,
        case_id=case_id,
        evidence_file_id=email_file.id,
        session=db_session,
    )
    assert res_email.summary.rows_processed == 1

    # Verify IP 185.220.101.5 is deduplicated between Android log and Email
    suspect_ips = db_session.exec(
        select(Entity)
        .where(Entity.case_id == case_id)
        .where(Entity.entity_type == EntityType.IP_ADDRESS)
        .where(Entity.value == "185.220.101.5")
    ).all()
    assert len(suspect_ips) == 1

    # Verify EntityLink rows exist and connect entities across files
    total_links = db_session.exec(
        select(EntityLink).where(EntityLink.case_id == case_id)
    ).all()
    assert len(total_links) > 0


def test_normalizer_unsupported_source_type(db_session: Session, sample_case: Case):
    """Verify normalizer rejects unsupported source types with IngestionError."""
    case_id = sample_case.id
    assert case_id is not None
    ev = create_evidence_record(db_session, case_id, "data.bin", SourceType.CDR)
    assert ev.id is not None

    with pytest.raises(IngestionError) as exc_info:
        normalize(
            file_source=b"test data",
            source_type="unsupported_source_format",
            case_id=case_id,
            evidence_file_id=ev.id,
            session=db_session,
        )
    assert "Unsupported or unrecognized source type" in str(exc_info.value)
