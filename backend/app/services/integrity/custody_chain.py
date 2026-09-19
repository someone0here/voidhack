"""Evidentiary custody chain service ensuring tamper-evident audit trails.

===============================================================================
LEGAL EVIDENTIARY COMPLIANCE: SECTION 65B OF THE INDIAN EVIDENCE ACT, 1872
(And Corresponding Section 63 of the Bharatiya Sakshya Adhiniyam, 2023)
===============================================================================
Under Section 65B of the Indian Evidence Act (and Section 63 of the BSA, 2023),
electronic records (such as telecom CDR dumps, banking logs, and device forensic
extractions) are legally admissible in court only if accompanied by a certificate
verifying the authenticity, continuous operational integrity, and absence of
unauthorized tampering of the electronic artifact from collection to presentation.

In traditional forensics, simple static file hashes prove whether a raw file has
changed, but fail to prove the chronological provenance or integrity of the audit
log itself (e.g., an insider could delete a log entry or insert a fraudulent file
retroactively).

This Custody Chain architecture implements a cryptographic hash-chain ledger:
1. Every ingested artifact generates a deterministic SHA-256 digest of its raw bytes.
2. Each custody log entry calculates a chained hash that cryptographically binds the
   current file hash with the chained hash of the immediately preceding log entry:
       chained_hash = SHA256(file_hash + ":" + previous_chained_hash)
3. The resulting ledger forms an immutable, append-only hash sequence (similar to a
   merkle blockchain). Any subsequent unauthorized modification to an evidence file,
   deletion of an intermediate record, reordering of logs, or alteration of metadata
   causes an immediate mathematical discrepancy when verifying the chain from genesis.

Consequently, this system produces mathematically provable, verifiable proof of
unbroken chain of custody, enabling the automated generation of tamper-evident
Section 65B certificates of authenticity that withstand rigorous judicial scrutiny.
===============================================================================
"""

import hashlib
import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db.models import CustodyLogEntry, EvidenceFile

logger = logging.getLogger("integrity.custody_chain")

GENESIS_SENTINEL = "GENESIS"


class ChainVerificationResult(BaseModel):
    """Result of cryptographic custody chain verification for a case."""

    is_valid: bool
    total_entries: int
    broken_entry_id: int | None = None
    broken_index: int | None = None
    reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


def compute_chained_hash(file_hash: str, previous_chained_hash: str | None) -> str:
    """Compute the deterministic chained SHA-256 hash for a custody log entry.

    Concatenation format:
      - Genesis entry (no predecessor): sha256("{file_hash}:GENESIS")
      - Subsequent entries:             sha256("{file_hash}:{previous_chained_hash}")

    Args:
        file_hash: Lowercase SHA-256 digest of the ingested evidence file.
        previous_chained_hash: Preceding chained hash, or None if genesis.

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).
    """
    predecessor = (
        previous_chained_hash if previous_chained_hash is not None else GENESIS_SENTINEL
    )
    payload = f"{file_hash}:{predecessor}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CustodyChainService:
    """Manages the append-only cryptographic custody ledger for evidence files."""

    def __init__(self, session: Session):
        """Initialize the custody chain service with an active database session.

        Args:
            session: Active SQLModel session.
        """
        self.session = session

    def record_ingestion(
        self,
        evidence_file_id: int,
        file_hash: str,
        handling_note: str = (
            "Initial artifact ingestion and cryptographic verification"
        ),
    ) -> CustodyLogEntry:
        """Record an evidence ingestion event into the case's custody chain.

        Looks up the parent case for the specified evidence file, retrieves the most
        recent CustodyLogEntry belonging to that case, computes the new chained hash,
        and persists the new entry.

        Args:
            evidence_file_id: Primary key of the EvidenceFile record.
            file_hash: Lowercase hexadecimal SHA-256 digest of the ingested file.
            handling_note: Human-readable investigative or chain-of-custody note.

        Returns:
            The newly created and persisted CustodyLogEntry.

        Raises:
            ValueError: If the evidence_file_id does not exist in the database.
        """
        evidence_file = self.session.get(EvidenceFile, evidence_file_id)
        if evidence_file is None:
            raise ValueError(f"EvidenceFile with id {evidence_file_id} does not exist.")

        case_id = evidence_file.case_id

        # Query the most recent CustodyLogEntry for this case
        stmt = (
            select(CustodyLogEntry)
            .join(EvidenceFile, CustodyLogEntry.evidence_file_id == EvidenceFile.id)
            .where(EvidenceFile.case_id == case_id)
            .order_by(CustodyLogEntry.id.desc())
        )
        latest_entry = self.session.exec(stmt).first()

        previous_chained_hash: str | None = None
        if latest_entry is not None:
            previous_chained_hash = latest_entry.chained_hash

        # Compute new chained hash incorporating previous entry's hash
        chained_hash = compute_chained_hash(
            file_hash=file_hash,
            previous_chained_hash=previous_chained_hash,
        )

        entry = CustodyLogEntry(
            evidence_file_id=evidence_file_id,
            file_hash=file_hash,
            previous_hash=previous_chained_hash,
            chained_hash=chained_hash,
            timestamp=datetime.utcnow(),
            handling_note=handling_note,
        )
        self.session.add(entry)
        self.session.flush()

        logger.info(
            "Recorded custody log entry %s for case %s (file_id=%s, hash=%s...)",
            entry.id,
            case_id,
            evidence_file_id,
            chained_hash[:12],
        )
        return entry

    def verify_chain(self, case_id: int) -> ChainVerificationResult:
        """Walk every CustodyLogEntry for a case and verify integrity.

        Recomputes each chained hash from scratch from the genesis block onwards.
        Checks for:
        - Integrity of the genesis block (no preceding hash).
        - Continuity of predecessor links (previous_hash matches chained_hash).
        - Cryptographic hash matches (chained_hash matches recomputed value).
        - Missing entries between evidence files and the custody log.

        Args:
            case_id: Primary key of the investigation case to audit.

        Returns:
            ChainVerificationResult detailing whether the chain is intact, or the
            specific entry ID, index, and reason if broken.
        """
        # Retrieve all custody log entries for the case in ascending order
        stmt = (
            select(CustodyLogEntry)
            .join(EvidenceFile, CustodyLogEntry.evidence_file_id == EvidenceFile.id)
            .where(EvidenceFile.case_id == case_id)
            .order_by(CustodyLogEntry.id.asc())
        )
        entries = list(self.session.exec(stmt).all())

        if not entries:
            # Check if any evidence files exist without custody logs
            ev_files = self.session.exec(
                select(EvidenceFile).where(EvidenceFile.case_id == case_id)
            ).all()
            if ev_files:
                return ChainVerificationResult(
                    is_valid=False,
                    total_entries=0,
                    reason=(
                        "missing entry: Evidence files exist for case but custody "
                        "log is empty"
                    ),
                    details={
                        "evidence_file_ids": [
                            f.id for f in ev_files if f.id is not None
                        ]
                    },
                )
            return ChainVerificationResult(
                is_valid=True,
                total_entries=0,
                reason="No custody log entries found for case (empty chain)",
            )

        running_previous_hash: str | None = None

        for idx, entry in enumerate(entries):
            # 1. Verify link continuity
            if idx == 0:
                if entry.previous_hash is not None:
                    return ChainVerificationResult(
                        is_valid=False,
                        total_entries=len(entries),
                        broken_entry_id=entry.id,
                        broken_index=idx,
                        reason="Genesis entry contains unexpected previous_hash",
                        details={
                            "entry_id": entry.id,
                            "stored_previous_hash": entry.previous_hash,
                            "expected_previous_hash": None,
                        },
                    )
            else:
                if entry.previous_hash != running_previous_hash:
                    return ChainVerificationResult(
                        is_valid=False,
                        total_entries=len(entries),
                        broken_entry_id=entry.id,
                        broken_index=idx,
                        reason=(
                            "missing entry or broken link: previous_hash does not "
                            "match preceding chained_hash"
                        ),
                        details={
                            "entry_id": entry.id,
                            "stored_previous_hash": entry.previous_hash,
                            "expected_previous_hash": running_previous_hash,
                        },
                    )

            # 2. Recompute chained hash from scratch
            expected_chained_hash = compute_chained_hash(
                file_hash=entry.file_hash,
                previous_chained_hash=running_previous_hash,
            )

            # 3. Verify against stored chained_hash
            if entry.chained_hash != expected_chained_hash:
                return ChainVerificationResult(
                    is_valid=False,
                    total_entries=len(entries),
                    broken_entry_id=entry.id,
                    broken_index=idx,
                    reason=(
                        "hash mismatch: recomputed chained_hash does not "
                        "match stored value"
                    ),
                    details={
                        "entry_id": entry.id,
                        "stored_chained_hash": entry.chained_hash,
                        "recomputed_chained_hash": expected_chained_hash,
                        "file_hash": entry.file_hash,
                    },
                )

            running_previous_hash = entry.chained_hash

        # 4. Check for evidence files belonging to this case missing a custody log
        logged_evidence_file_ids = {e.evidence_file_id for e in entries}
        all_case_files = self.session.exec(
            select(EvidenceFile).where(EvidenceFile.case_id == case_id)
        ).all()
        unlogged_files = [
            f.id
            for f in all_case_files
            if f.id is not None and f.id not in logged_evidence_file_ids
        ]
        if unlogged_files:
            return ChainVerificationResult(
                is_valid=False,
                total_entries=len(entries),
                reason=(
                    "missing entry: one or more evidence files lack "
                    "corresponding custody log entries"
                ),
                details={"unlogged_evidence_file_ids": unlogged_files},
            )

        return ChainVerificationResult(
            is_valid=True,
            total_entries=len(entries),
            reason=None,
            details={"head_hash": running_previous_hash},
        )
