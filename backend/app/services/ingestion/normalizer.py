"""Normalizer: dispatches parsers, deduplicates and persists Entity/EntityLink rows."""

import logging
from pathlib import Path
from typing import BinaryIO

from sqlmodel import Session, select

from app.db.models import Entity, EntityLink, EntityType, EvidenceFile, SourceType
from app.services.ingestion.exceptions import (
    IngestionError,
    UnsupportedFormatError,
)
from app.services.ingestion.models import IngestionResult, IngestionSummary
from app.services.ingestion.parsers.android_log_parser import AndroidLogParser
from app.services.ingestion.parsers.bank_parser import BankParser
from app.services.ingestion.parsers.base import BaseParser
from app.services.ingestion.parsers.cdr_parser import CDRParser
from app.services.ingestion.parsers.email_parser import EmailParser
from app.services.integrity import CustodyChainService, compute_sha256

logger = logging.getLogger("ingestion.normalizer")


def get_parser(source_type: SourceType | str) -> BaseParser:
    """Resolve the appropriate parser instance for a given source type."""
    if isinstance(source_type, str):
        try:
            source_type = SourceType(source_type.lower())
        except ValueError as err:
            raise UnsupportedFormatError(
                f"Unsupported or unrecognized source type: '{source_type}'"
            ) from err

    if source_type in {SourceType.CDR, SourceType.IPDR}:
        return CDRParser()
    elif source_type == SourceType.BANK_UPI:
        return BankParser()
    elif source_type == SourceType.EMAIL:
        return EmailParser()
    elif source_type == SourceType.ANDROID_LOG:
        return AndroidLogParser()
    else:
        raise UnsupportedFormatError(
            f"No parser implemented for source type '{source_type}'"
        )


def normalize(
    file_source: str | Path | bytes | BinaryIO,
    source_type: SourceType | str,
    case_id: int,
    evidence_file_id: int,
    session: Session,
) -> IngestionResult:
    """Parse evidence, deduplicate entities, and persist Entity + EntityLink rows.

    Args:
        file_source: File path, bytes, or file-like buffer.
        source_type: Source type (CDR, BANK_UPI, EMAIL, ANDROID_LOG, etc.).
        case_id: Primary key of parent investigation case.
        evidence_file_id: Primary key of EvidenceFile record being parsed.
        session: Active SQLModel database session.

    Returns:
        IngestionResult containing per-file summary, created entities, and links.

    Raises:
        IngestionError: If parsing or database ingestion fails unrecoverably.
    """
    try:
        calculated_file_hash = compute_sha256(file_source)
    except Exception as e:
        logger.error(
            "Failed to compute SHA-256 for evidence file %d: %s",
            evidence_file_id,
            e,
            exc_info=True,
        )
        raise IngestionError(f"Evidentiary hash computation failed: {e}") from e

    parser = get_parser(source_type)

    try:
        parser_result = parser.parse(file_source)
    except IngestionError:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error parsing '%s' (source_type='%s'): %s",
            file_source,
            source_type,
            e,
            exc_info=True,
        )
        raise IngestionError(f"Parsing failed for artifact: {e}") from e

    # Log skipped rows
    for error_msg in parser_result.errors:
        logger.info(
            "[Ingestion Warning] Case %d File %d: %s",
            case_id,
            evidence_file_id,
            error_msg,
        )

    # Database normalization and case-scoped deduplication
    try:
        # Load existing entities for this case into a lookup cache
        existing_entities = session.exec(
            select(Entity).where(Entity.case_id == case_id)
        ).all()
        entity_cache: dict[tuple[EntityType, str], Entity] = {
            (e.entity_type, e.value): e for e in existing_entities
        }

        # Load existing entity links for this case into a link cache
        existing_links = session.exec(
            select(EntityLink).where(EntityLink.case_id == case_id)
        ).all()
        link_cache: set[tuple[int, int, str]] = {
            (
                min(link.entity_a_id, link.entity_b_id),
                max(link.entity_a_id, link.entity_b_id),
                (
                    link.link_type.value
                    if hasattr(link.link_type, "value")
                    else str(link.link_type)
                ),
            )
            for link in existing_links
        }

        entities_created = 0
        entity_links_created = 0
        persisted_entities: list[Entity] = []
        persisted_links: list[EntityLink] = []

        for record in parser_result.records:
            # 1. Resolve or create root entity
            root_key = (record.entity_type, record.value)
            if root_key not in entity_cache:
                root_entity = Entity(
                    case_id=case_id,
                    entity_type=record.entity_type,
                    value=record.value,
                )
                session.add(root_entity)
                session.flush()  # Populate generated primary key
                entity_cache[root_key] = root_entity
                entities_created += 1
                persisted_entities.append(root_entity)
            else:
                root_entity = entity_cache[root_key]

            # 2. Resolve or create linked entities and cross-link them
            for linked_ref in record.linked_entities:
                target_key = (linked_ref.entity_type, linked_ref.value)
                if target_key not in entity_cache:
                    target_entity = Entity(
                        case_id=case_id,
                        entity_type=linked_ref.entity_type,
                        value=linked_ref.value,
                    )
                    session.add(target_entity)
                    session.flush()
                    entity_cache[target_key] = target_entity
                    entities_created += 1
                    persisted_entities.append(target_entity)
                else:
                    target_entity = entity_cache[target_key]

                # Create link if non-self and not already linked
                if root_entity.id is not None and target_entity.id is not None:
                    if root_entity.id != target_entity.id:
                        min_id = min(root_entity.id, target_entity.id)
                        max_id = max(root_entity.id, target_entity.id)
                        link_type_str = (
                            linked_ref.link_type.value
                            if hasattr(linked_ref.link_type, "value")
                            else str(linked_ref.link_type)
                        )
                        link_key = (min_id, max_id, link_type_str)

                        if link_key not in link_cache:
                            new_link = EntityLink(
                                case_id=case_id,
                                entity_a_id=min_id,
                                entity_b_id=max_id,
                                link_type=linked_ref.link_type,
                                confidence_score=linked_ref.confidence_score,
                                source_evidence_file_id=evidence_file_id,
                            )
                            session.add(new_link)
                            session.flush()
                            link_cache.add(link_key)
                            entity_links_created += 1
                            persisted_links.append(new_link)

        # Look up EvidenceFile to sync hash and prepare custody logging
        evidence_file = session.get(EvidenceFile, evidence_file_id)
        source_label = (
            source_type.value if hasattr(source_type, "value") else str(source_type)
        )
        filename_label = (
            evidence_file.original_filename if evidence_file else str(evidence_file_id)
        )
        if (
            evidence_file is not None
            and evidence_file.file_hash != calculated_file_hash
        ):
            evidence_file.file_hash = calculated_file_hash
            session.add(evidence_file)
            session.flush()

        # Automatic tamper-evident custody chain recording (non-skippable)
        handling_note = (
            f"Forensic ingestion and cryptographic verification for {filename_label} "
            f"(source: {source_label})"
        )
        chain_service = CustodyChainService(session)
        custody_entry = chain_service.record_ingestion(
            evidence_file_id=evidence_file_id,
            file_hash=calculated_file_hash,
            handling_note=handling_note,
        )

        session.commit()

        summary = IngestionSummary(
            rows_processed=parser_result.rows_processed,
            rows_skipped=parser_result.rows_skipped,
            entities_created=entities_created,
            entity_links_created=entity_links_created,
            skipped_reasons=parser_result.errors,
        )

        return IngestionResult(
            summary=summary,
            entities=persisted_entities,
            entity_links=persisted_links,
            custody_log=custody_entry,
        )

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to persist normalized entities for case %d: %s",
            case_id,
            e,
            exc_info=True,
        )
        raise IngestionError(
            f"Database persistence failed during normalization: {e}"
        ) from e
