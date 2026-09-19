"""End-to-end API integration tests for Cyber Fraud Correlator.

Exercises the complete investigative lifecycle across all routes:
  1. Case creation
  2. Multi-source evidence ingestion & custody logging
  3. Graph correlation retrieval
  4. Operational fraud risk scoring
  5. Court-ready JSON & single-page PDF brief generation
  6. Section 65B/BSA 63 chain of custody integrity verification
  7. Error handling & PII redacting guards
"""

import io
import re
import sqlite3
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import app.db.session as session_module
from app.db.models import SourceType
from app.db.session import get_session
from app.main import app
from app.schemas.case import CaseRead
from app.services.brief import (
    BriefExport,
    mask_account,
    mask_email,
    mask_identifier,
    mask_imei,
    mask_phone,
)
from app.services.correlation.graph_serializer import SerializedGraph
from app.services.ingestion.models import IngestionSummary
from app.services.integrity import ChainVerificationResult

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(name="test_engine")
def test_engine_fixture():
    """Create isolated in-memory engine with StaticPool."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(test_engine) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_session dependency and patched engine."""

    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with patch.object(session_module, "engine", test_engine):
        with TestClient(app) as test_client:
            yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PII Masking Unit Tests
# ---------------------------------------------------------------------------


def test_pii_masking_rules():
    """Verify phone, account, and IMEI masking enforces last-4-digits-visible format."""
    # Phone numbers
    assert mask_phone("+919876543210") == "+91******3210"
    assert mask_phone("9876543210") == "******3210"
    assert mask_phone("+14155552671") == "+1******2671"
    assert mask_phone("123") == "123"

    # Accounts & UPI
    assert mask_account("123456789012") == "********9012"
    assert mask_account("mule1@okhdfcbank") == "*ule1@okhdfcbank"
    assert mask_account("victim.pay@upi") == "******.pay@upi"

    # IMEIs
    assert mask_imei("860123456789012") == "***********9012"
    assert mask_imei("1234") == "1234"

    # Emails
    assert mask_email("investigator@agency.gov") == "i**********r@agency.gov"

    # Generic dispatcher
    assert mask_identifier("+919876543210", "phone") == "+91******3210"
    assert mask_identifier("860123456789012", "device_imei") == "***********9012"
    assert mask_identifier("123456789012", "account") == "********9012"


# ---------------------------------------------------------------------------
# System & Middleware Tests
# ---------------------------------------------------------------------------


def test_health_check_and_request_id(client: TestClient):
    """Verify /health returns 200 and assigns X-Request-ID header."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "phase" in data
    assert "X-Request-ID" in response.headers


def test_custom_request_id_preserved(client: TestClient):
    """Verify client-provided X-Request-ID is echoed back in response headers."""
    custom_id = "test-req-999"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


# ---------------------------------------------------------------------------
# End-to-End Investigation Flow Tests
# ---------------------------------------------------------------------------


def test_full_investigation_lifecycle_e2e(client: TestClient):
    """Execute complete end-to-end investigative workflow using Phase 2 fixtures.

    Flow:
      1. POST /cases -> create case envelope
      2. POST /cases/{id}/evidence -> upload CDR, Bank, Email, and Android artifacts
      3. GET /cases/{id}/graph -> verify correlation graph topology and serialization
      4. GET /cases/{id}/risk -> verify explainable risk scoring and ranking
      5. GET /cases/{id}/brief.json -> verify structured brief and PII masking
      6. GET /cases/{id}/brief.pdf -> verify single-page PDF download
      7. GET /cases/{id}/integrity -> verify Section 65B/BSA 63 custody chain
    """
    # 1. Create Case
    case_payload = {"name": "Operation Iron Falcon", "status": "active"}
    case_resp = client.post("/cases", json=case_payload)
    assert case_resp.status_code == 201
    case_data = case_resp.json()
    case_read = CaseRead.model_validate(case_data)
    case_id = case_read.id
    assert case_read.name == "Operation Iron Falcon"

    # Also test GET /cases and GET /cases/{case_id}
    list_resp = client.get("/cases")
    assert list_resp.status_code == 200
    assert any(c["id"] == case_id for c in list_resp.json())

    single_resp = client.get(f"/cases/{case_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["id"] == case_id

    # 2. Upload Evidence Artifacts (Phase 2 fixtures)
    fixtures_to_upload = [
        ("cdr_sample.csv", SourceType.CDR.value),
        ("bank_sample.csv", SourceType.BANK_UPI.value),
        ("email_sample_1.eml", SourceType.EMAIL.value),
        ("android_log_sample.json", SourceType.ANDROID_LOG.value),
    ]

    total_entities_created = 0
    total_links_created = 0

    for filename, source_type in fixtures_to_upload:
        filepath = FIXTURES_DIR / filename
        assert filepath.exists(), f"Fixture {filename} missing"

        with open(filepath, "rb") as f:
            upload_resp = client.post(
                f"/cases/{case_id}/evidence",
                data={"source_type": source_type},
                files={"file": (filename, f, "application/octet-stream")},
            )

        assert (
            upload_resp.status_code == 201
        ), f"Failed upload for {filename}: {upload_resp.text}"
        summary = IngestionSummary(**upload_resp.json())
        assert summary.rows_processed > 0
        total_entities_created += summary.entities_created
        total_links_created += summary.entity_links_created

    assert total_entities_created > 0
    assert total_links_created > 0

    # 3. GET /cases/{case_id}/graph — Correlated Entity Graph
    graph_resp = client.get(f"/cases/{case_id}/graph")
    assert graph_resp.status_code == 200
    graph_data = graph_resp.json()
    serialized_graph = SerializedGraph.model_validate(graph_data)
    assert len(serialized_graph.nodes) > 0
    assert len(serialized_graph.edges) > 0

    # Ensure nodes have cluster IDs assigned
    assert all(hasattr(n, "cluster_id") for n in serialized_graph.nodes)
    # Ensure edges have confidence labels
    assert all(
        e.confidence_label in ("Strong", "Medium", "Weak")
        for e in serialized_graph.edges
    )

    # Also check /api/v1/cases/{case_id}/graph prefix works identical
    v1_graph_resp = client.get(f"/api/v1/cases/{case_id}/graph")
    assert v1_graph_resp.status_code == 200

    # 4. GET /cases/{case_id}/risk — Heuristic Risk Scores
    risk_resp = client.get(f"/cases/{case_id}/risk")
    assert risk_resp.status_code == 200
    risk_list = risk_resp.json()
    assert len(risk_list) > 0

    # Verify descending score order
    scores = [item["score"] for item in risk_list]
    assert scores == sorted(scores, reverse=True)

    # Verify non-directive advisory language across all scores
    directive_terms = ["arrest", "seize", "detain", "charge", "convict"]
    for item in risk_list:
        assert 0 <= item["score"] <= 100
        rec = item["recommendation"].lower()
        for term in directive_terms:
            assert term not in rec

    # 5. GET /cases/{case_id}/brief.json — Structured JSON Brief
    brief_json_resp = client.get(f"/cases/{case_id}/brief.json")
    assert brief_json_resp.status_code == 200
    brief_export = BriefExport.model_validate(brief_json_resp.json())

    assert brief_export.case_summary.case_id == case_id
    assert brief_export.case_summary.total_evidence_files == 4
    assert brief_export.custody_chain.is_valid is True
    assert brief_export.custody_chain.total_entries == 4
    assert "Section 65B" in brief_export.custody_chain.statutory_statement

    # Verify PII masking on top entities: phones and IMEIs should have '*'
    masked_found = False
    for entity in brief_export.top_entities:
        if entity.entity_type in ("phone", "account", "device_imei"):
            if "*" in entity.identifier:
                masked_found = True
    assert masked_found, "Expected at least one masked identifier in top entities"

    # 6. GET /cases/{case_id}/brief.pdf — One-Page PDF Download
    pdf_resp = client.get(f"/cases/{case_id}/brief.pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["Content-Type"] == "application/pdf"
    assert f"case_{case_id}_brief.pdf" in pdf_resp.headers.get(
        "Content-Disposition", ""
    )

    pdf_bytes = pdf_resp.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Ensure strictly ONE page is rendered in the PDF output
    page_matches = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
    assert (
        len(page_matches) == 1
    ), f"Expected exactly 1 page in brief PDF, found {len(page_matches)}"

    # 7. GET /cases/{case_id}/integrity — Custody Chain Audit
    integrity_resp = client.get(f"/cases/{case_id}/integrity")
    assert integrity_resp.status_code == 200
    chain_result = ChainVerificationResult.model_validate(integrity_resp.json())
    assert chain_result.is_valid is True
    assert chain_result.total_entries == 4
    assert chain_result.broken_entry_id is None


# ---------------------------------------------------------------------------
# Error Handling & Edge Case Tests
# ---------------------------------------------------------------------------


def test_not_found_errors(client: TestClient):
    """Verify 404 responses for non-existent case IDs across all endpoints."""
    bad_id = 99999

    assert client.get(f"/cases/{bad_id}").status_code == 404
    assert client.get(f"/cases/{bad_id}/graph").status_code == 404
    assert client.get(f"/cases/{bad_id}/risk").status_code == 404
    assert client.get(f"/cases/{bad_id}/brief.json").status_code == 404
    assert client.get(f"/cases/{bad_id}/brief.pdf").status_code == 404
    assert client.get(f"/cases/{bad_id}/integrity").status_code == 404

    # Upload to non-existent case
    fake_file = io.BytesIO(b"phone,imei\n+919999999999,860000000000001\n")
    res = client.post(
        f"/cases/{bad_id}/evidence",
        data={"source_type": "cdr"},
        files={"file": ("test.csv", fake_file, "text/csv")},
    )
    assert res.status_code == 404


def test_empty_file_upload_rejected(client: TestClient):
    """Verify empty file uploads are rejected with 400 Bad Request."""
    case_resp = client.post("/cases", json={"name": "Empty Upload Case"})
    case_id = case_resp.json()["id"]

    res = client.post(
        f"/cases/{case_id}/evidence",
        data={"source_type": "cdr"},
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_invalid_source_type_rejected(client: TestClient):
    """Verify invalid source type values are rejected with 422 Unprocessable Entity."""
    case_resp = client.post("/cases", json={"name": "Bad Source Type Case"})
    case_id = case_resp.json()["id"]

    res = client.post(
        f"/cases/{case_id}/evidence",
        data={"source_type": "invalid_telecom_type"},
        files={"file": ("sample.csv", io.BytesIO(b"sample data"), "text/csv")},
    )
    assert res.status_code == 422


def test_corrupted_file_ingestion_error_handling(client: TestClient):
    """Verify IngestionError converts to clean JSON without leaking stack traces."""
    case_resp = client.post("/cases", json={"name": "Corrupted File Case"})
    case_id = case_resp.json()["id"]

    # Bank CSV with completely invalid format/header
    bad_csv = b"random_unrelated_column,another_column\n123,456\n"
    res = client.post(
        f"/cases/{case_id}/evidence",
        data={"source_type": "bank_upi"},
        files={"file": ("bad_bank.csv", io.BytesIO(bad_csv), "text/csv")},
    )
    # Should return 400 IngestionError cleanly
    assert res.status_code == 400
    err_json = res.json()
    assert "error" in err_json
    assert "detail" in err_json
    assert "traceback" not in err_json
    assert "Traceback" not in res.text
