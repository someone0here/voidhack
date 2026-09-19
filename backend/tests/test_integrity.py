"""Comprehensive test suite for the cryptographic evidentiary integrity layer."""

import io
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.db.models import (
    Case,
    CaseStatus,
    CustodyLogEntry,
    EvidenceFile,
    SourceType,
)
from app.services.ingestion.normalizer import normalize
from app.services.integrity import (
    CustodyChainService,
    compute_chained_hash,
    compute_sha256,
)

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
    """Create a sample investigation case."""
    case = Case(name="Operation Iron Gate", status=CaseStatus.ACTIVE.value)
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


def create_evidence_file(
    session: Session,
    case_id: int,
    filename: str,
    source_type: SourceType = SourceType.CDR,
    file_hash: str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
) -> EvidenceFile:
    """Helper to persist an EvidenceFile row."""
    evidence = EvidenceFile(
        case_id=case_id,
        original_filename=filename,
        source_type=source_type,
        file_hash=file_hash,
    )
    session.add(evidence)
    session.commit()
    session.refresh(evidence)
    return evidence


# ---------------------------------------------------------------------------
# Hasher Tests
# ---------------------------------------------------------------------------


def test_hasher_deterministic_known_vectors(tmp_path: Path):
    """Verify SHA-256 computation against standard NIST/RFC test vectors."""
    # Vector 1: Empty string
    empty_hash = compute_sha256(b"")
    assert (
        empty_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )

    # Vector 2: "The quick brown fox jumps over the lazy dog"
    fox_bytes = b"The quick brown fox jumps over the lazy dog"
    expected_fox_hash = (
        "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592"
    )
    assert compute_sha256(fox_bytes) == expected_fox_hash

    # Vector 3: Verify with varying chunk sizes produces identical output
    for chunk_size in [1, 3, 16, 64, 1024, 65536]:
        assert compute_sha256(fox_bytes, chunk_size=chunk_size) == expected_fox_hash

    # Vector 4: File on disk
    test_file = tmp_path / "forensic_sample.bin"
    test_file.write_bytes(fox_bytes)
    assert compute_sha256(test_file) == expected_fox_hash
    assert compute_sha256(str(test_file)) == expected_fox_hash

    # Vector 5: In-memory stream
    stream = io.BytesIO(fox_bytes)
    assert compute_sha256(stream) == expected_fox_hash


def test_hasher_stream_rewind():
    """Verify stream is rewound to byte 0 after hash calculation."""
    stream_data = b"forensic telecommunication payload"
    stream = io.BytesIO(stream_data)

    calculated_hash = compute_sha256(stream)
    assert len(calculated_hash) == 64

    # Ensure stream position was reset back to 0
    assert stream.tell() == 0
    read_again = stream.read()
    assert read_again == stream_data


def test_hasher_error_handling():
    """Verify hasher raises appropriate exceptions for invalid inputs."""
    # Non-existent file path
    with pytest.raises(FileNotFoundError):
        compute_sha256(Path("/path/to/definitely/non_existent_file.bin"))

    # Invalid chunk size
    with pytest.raises(ValueError) as exc_info:
        compute_sha256(b"payload", chunk_size=0)
    assert "chunk_size must be positive" in str(exc_info.value)

    # Unsupported type
    with pytest.raises(ValueError) as exc_info:
        compute_sha256(12345)  # type: ignore
    assert "Unsupported file_source type" in str(exc_info.value)


# ---------------------------------------------------------------------------
# CustodyChainService: Ingestion & Sequential Chaining Tests
# ---------------------------------------------------------------------------


def test_custody_chain_sequential_ingestions(db_session: Session, sample_case: Case):
    """Verify sequential ingestions build an unbroken, deterministic hash chain."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    # 1. Ingest Evidence File 1 (Genesis entry)
    ev1 = create_evidence_file(
        db_session, case_id, "cdr_day1.csv", file_hash="1111" * 16
    )
    assert ev1.id is not None
    entry1 = chain_service.record_ingestion(
        evidence_file_id=ev1.id,
        file_hash=ev1.file_hash,
        handling_note="Intake of CDR Day 1",
    )
    db_session.commit()

    assert entry1.previous_hash is None
    expected_chain1 = compute_chained_hash(ev1.file_hash, None)
    assert entry1.chained_hash == expected_chain1

    # 2. Ingest Evidence File 2 (Chained to Entry 1)
    ev2 = create_evidence_file(
        db_session, case_id, "bank_records.xlsx", file_hash="2222" * 16
    )
    assert ev2.id is not None
    entry2 = chain_service.record_ingestion(
        evidence_file_id=ev2.id,
        file_hash=ev2.file_hash,
        handling_note="Intake of Bank Records",
    )
    db_session.commit()

    assert entry2.previous_hash == entry1.chained_hash
    expected_chain2 = compute_chained_hash(ev2.file_hash, entry1.chained_hash)
    assert entry2.chained_hash == expected_chain2

    # 3. Ingest Evidence File 3 (Chained to Entry 2)
    ev3 = create_evidence_file(
        db_session, case_id, "android_dump.json", file_hash="3333" * 16
    )
    assert ev3.id is not None
    entry3 = chain_service.record_ingestion(
        evidence_file_id=ev3.id,
        file_hash=ev3.file_hash,
        handling_note="Intake of Device Extraction",
    )
    db_session.commit()

    assert entry3.previous_hash == entry2.chained_hash
    expected_chain3 = compute_chained_hash(ev3.file_hash, entry2.chained_hash)
    assert entry3.chained_hash == expected_chain3

    # 4. Verify the entire chain
    verification = chain_service.verify_chain(case_id)
    assert verification.is_valid is True
    assert verification.total_entries == 3
    assert verification.broken_entry_id is None
    assert verification.reason is None
    assert verification.details.get("head_hash") == entry3.chained_hash


def test_custody_chain_empty_case(db_session: Session, sample_case: Case):
    """Verify empty case reports valid state with 0 entries."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)
    result = chain_service.verify_chain(case_id)
    assert result.is_valid is True
    assert result.total_entries == 0


def test_custody_chain_case_isolation(db_session: Session):
    """Verify that multiple distinct cases maintain strictly independent hash chains."""
    case_a = Case(name="Operation Alpha", status=CaseStatus.ACTIVE.value)
    case_b = Case(name="Operation Bravo", status=CaseStatus.ACTIVE.value)
    db_session.add_all([case_a, case_b])
    db_session.commit()
    db_session.refresh(case_a)
    db_session.refresh(case_b)

    chain_service = CustodyChainService(db_session)

    # Ingest for Case A
    ev_a1 = create_evidence_file(db_session, case_a.id, "a1.csv", file_hash="aaaa" * 16)
    entry_a1 = chain_service.record_ingestion(ev_a1.id, ev_a1.file_hash)
    db_session.commit()

    # Ingest for Case B (must have previous_hash = None as its own genesis)
    ev_b1 = create_evidence_file(db_session, case_b.id, "b1.csv", file_hash="bbbb" * 16)
    entry_b1 = chain_service.record_ingestion(ev_b1.id, ev_b1.file_hash)
    db_session.commit()

    assert entry_a1.previous_hash is None
    assert entry_b1.previous_hash is None

    # Ingest another file for Case A
    ev_a2 = create_evidence_file(db_session, case_a.id, "a2.csv", file_hash="a2a2" * 16)
    entry_a2 = chain_service.record_ingestion(ev_a2.id, ev_a2.file_hash)
    db_session.commit()

    # Case A2 links to A1, NOT B1
    assert entry_a2.previous_hash == entry_a1.chained_hash

    # Verify both chains independently
    res_a = chain_service.verify_chain(case_a.id)
    res_b = chain_service.verify_chain(case_b.id)

    assert res_a.is_valid is True
    assert res_a.total_entries == 2
    assert res_b.is_valid is True
    assert res_b.total_entries == 1


# ---------------------------------------------------------------------------
# Tamper Detection Tests
# ---------------------------------------------------------------------------


def test_tamper_detection_mutated_file_hash(db_session: Session, sample_case: Case):
    """Simulate unauthorized alteration of a stored file_hash and verify detection."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    # Create 3 valid entries
    for i in range(1, 4):
        ev = create_evidence_file(
            db_session, case_id, f"file_{i}.csv", file_hash=f"{i}{i}{i}{i}" * 16
        )
        chain_service.record_ingestion(ev.id, ev.file_hash)
    db_session.commit()

    # Pre-condition: chain is initially valid
    assert chain_service.verify_chain(case_id).is_valid is True

    # Tamper: Alter file_hash of entry #2 in the database
    entries = db_session.exec(
        select(CustodyLogEntry).order_by(CustodyLogEntry.id.asc())
    ).all()
    tampered_entry = entries[1]
    tampered_entry.file_hash = "deadbeef" * 8
    db_session.add(tampered_entry)
    db_session.commit()

    # Verify tampering is flagged
    result = chain_service.verify_chain(case_id)
    assert result.is_valid is False
    assert result.broken_entry_id == tampered_entry.id
    assert result.broken_index == 1
    assert "hash mismatch" in result.reason.lower()
    assert result.details["file_hash"] == "deadbeef" * 8


def test_tamper_detection_mutated_chained_hash(db_session: Session, sample_case: Case):
    """Simulate unauthorized alteration of a chained_hash and verify detection."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    for i in range(1, 4):
        ev = create_evidence_file(
            db_session, case_id, f"file_{i}.csv", file_hash=f"{i}{i}{i}{i}" * 16
        )
        chain_service.record_ingestion(ev.id, ev.file_hash)
    db_session.commit()

    entries = db_session.exec(
        select(CustodyLogEntry).order_by(CustodyLogEntry.id.asc())
    ).all()
    tampered_entry = entries[1]
    tampered_entry.chained_hash = "00000000" * 8
    db_session.add(tampered_entry)
    db_session.commit()

    result = chain_service.verify_chain(case_id)
    assert result.is_valid is False
    assert result.broken_entry_id == tampered_entry.id
    assert result.broken_index == 1
    assert "hash mismatch" in result.reason.lower()


def test_tamper_detection_mutated_previous_hash(db_session: Session, sample_case: Case):
    """Simulate alteration of predecessor link (previous_hash) and verify detection."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    for i in range(1, 4):
        ev = create_evidence_file(
            db_session, case_id, f"file_{i}.csv", file_hash=f"{i}{i}{i}{i}" * 16
        )
        chain_service.record_ingestion(ev.id, ev.file_hash)
    db_session.commit()

    entries = db_session.exec(
        select(CustodyLogEntry).order_by(CustodyLogEntry.id.asc())
    ).all()
    tampered_entry = entries[2]  # 3rd entry
    tampered_entry.previous_hash = "ffffffff" * 8
    db_session.add(tampered_entry)
    db_session.commit()

    result = chain_service.verify_chain(case_id)
    assert result.is_valid is False
    assert result.broken_entry_id == tampered_entry.id
    assert result.broken_index == 2
    assert "previous_hash does not match" in result.reason.lower()


def test_tamper_detection_deleted_intermediate_entry(
    db_session: Session, sample_case: Case
):
    """Simulate an attacker deleting a middle audit entry and verify detection."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    ev_files = []
    for i in range(1, 4):
        ev = create_evidence_file(
            db_session, case_id, f"file_{i}.csv", file_hash=f"{i}{i}{i}{i}" * 16
        )
        ev_files.append(ev)
        chain_service.record_ingestion(ev.id, ev.file_hash)
    db_session.commit()

    # Delete entry #2 directly from the custody log table
    entries = db_session.exec(
        select(CustodyLogEntry).order_by(CustodyLogEntry.id.asc())
    ).all()
    entry_to_delete = entries[1]
    db_session.delete(entry_to_delete)
    db_session.commit()

    # The chain now has entries [1, 3]
    result = chain_service.verify_chain(case_id)
    assert result.is_valid is False
    # Entry 3 points to entry 2's chained_hash, but entry 1 is its predecessor in the DB
    assert "previous_hash does not match" in result.reason.lower()


def test_tamper_detection_unlogged_evidence_file(
    db_session: Session, sample_case: Case
):
    """Verify that an evidence file uploaded without a custody log is flagged."""
    case_id = sample_case.id
    assert case_id is not None
    chain_service = CustodyChainService(db_session)

    # Ingest 1 logged file
    ev1 = create_evidence_file(db_session, case_id, "file_1.csv")
    chain_service.record_ingestion(ev1.id, ev1.file_hash)
    db_session.commit()

    # Create a 2nd evidence file but bypass logging
    ev2 = create_evidence_file(db_session, case_id, "unlogged_file.csv")
    db_session.commit()

    result = chain_service.verify_chain(case_id)
    assert result.is_valid is False
    assert "missing entry" in result.reason.lower()
    assert ev2.id in result.details.get("unlogged_evidence_file_ids", [])


# ---------------------------------------------------------------------------
# Normalizer Pipeline Integration Tests
# ---------------------------------------------------------------------------


def test_normalizer_automatic_custody_logging(db_session: Session, sample_case: Case):
    """Verify normalize() automatically computes hash and writes custody log."""
    case_id = sample_case.id
    assert case_id is not None

    # Ingest File 1: CDR
    cdr_ev = create_evidence_file(db_session, case_id, "cdr_sample.csv")
    cdr_res = normalize(
        file_source=FIXTURES_DIR / "cdr_sample.csv",
        source_type=SourceType.CDR,
        case_id=case_id,
        evidence_file_id=cdr_ev.id,
        session=db_session,
    )
    assert cdr_res.custody_log is not None
    assert cdr_res.custody_log.previous_hash is None
    assert len(cdr_res.custody_log.chained_hash) == 64

    # Ingest File 2: Bank
    bank_ev = create_evidence_file(db_session, case_id, "bank_sample.csv")
    bank_res = normalize(
        file_source=FIXTURES_DIR / "bank_sample.csv",
        source_type=SourceType.BANK_UPI,
        case_id=case_id,
        evidence_file_id=bank_ev.id,
        session=db_session,
    )
    assert bank_res.custody_log is not None
    assert bank_res.custody_log.previous_hash == cdr_res.custody_log.chained_hash

    # Ingest File 3: Android log
    android_ev = create_evidence_file(db_session, case_id, "android_log_sample.json")
    android_res = normalize(
        file_source=FIXTURES_DIR / "android_log_sample.json",
        source_type=SourceType.ANDROID_LOG,
        case_id=case_id,
        evidence_file_id=android_ev.id,
        session=db_session,
    )
    assert android_res.custody_log is not None
    assert android_res.custody_log.previous_hash == bank_res.custody_log.chained_hash

    # Now verify the complete multi-file chain via CustodyChainService
    chain_service = CustodyChainService(db_session)
    result = chain_service.verify_chain(case_id)

    assert result.is_valid is True
    assert result.total_entries == 3
    assert result.broken_entry_id is None
    assert result.reason is None
