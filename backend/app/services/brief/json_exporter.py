"""JSON brief exporter assembling comprehensive investigative dossiers."""

from datetime import datetime
from typing import Any

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app.db.models import Case, Entity, EntityLink, EvidenceFile
from app.services.brief.pii_mask import mask_identifier
from app.services.correlation.graph_builder import GraphBuilder
from app.services.integrity import CustodyChainService
from app.services.risk.reason_codes import ReasonCode
from app.services.risk.scoring_engine import (
    RiskScoringEngine,
)


class CaseSummary(BaseModel):
    """Investigative case profile metadata and volumetric metrics."""

    case_id: int
    name: str
    status: str
    created_at: datetime
    total_evidence_files: int
    total_entities: int
    total_links: int
    total_clusters: int

    model_config = ConfigDict(from_attributes=True)


class RankedEntityExport(BaseModel):
    """Prioritized entity dossier with masked identifiers and explainable heuristics."""

    entity_id: int
    entity_type: str
    identifier: str
    score: int = Field(ge=0, le=100)
    reason_codes: list[str]
    reason_descriptions: list[str]
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


class ClusterSummaryExport(BaseModel):
    """Syndicate cluster topological breakdown."""

    cluster_id: int
    node_count: int
    entity_types: list[str]
    high_risk_entity_count: int

    model_config = ConfigDict(from_attributes=True)


class CustodyIntegrityStatement(BaseModel):
    """Cryptographic chain-of-custody verification statement."""

    is_valid: bool
    total_entries: int
    head_hash: str | None = None
    statutory_statement: str
    broken_reason: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class BriefExport(BaseModel):
    """Complete exported investigative brief payload."""

    classification: str = "LAW ENFORCEMENT SENSITIVE // OFFICIAL BRIEF"
    generated_at: datetime
    case_summary: CaseSummary
    custody_chain: CustodyIntegrityStatement
    top_entities: list[RankedEntityExport]
    clusters: list[ClusterSummaryExport]

    model_config = ConfigDict(from_attributes=True)


def generate_brief_json(
    case_id: int,
    session: Session,
    top_n: int = 10,
    mask_pii: bool = True,
) -> BriefExport:
    """Assemble a court-ready investigative BriefExport for a given case.

    Integrates:
      - Case summary metrics
      - Section 65B IEA / Section 63 BSA 2023 cryptographic chain verification
      - Correlation graph cluster decomposition
      - Risk-ranked entity heuristics with PII masking and advisory recommendations

    Args:
        case_id: Primary key of investigation case.
        session: Active database session.
        top_n: Number of prioritized high-risk entities to include.
        mask_pii: If True, redacts sensitive phone/account/IMEI values.

    Returns:
        BriefExport Pydantic model instance.

    Raises:
        ValueError: If case_id does not exist.
    """
    case = session.get(Case, case_id)
    if case is None:
        raise ValueError(f"Investigation case with id {case_id} not found.")

    # 1. Volumetric Counts
    evidence_count = len(
        session.exec(
            select(EvidenceFile.id).where(EvidenceFile.case_id == case_id)
        ).all()
    )
    entities = list(session.exec(select(Entity).where(Entity.case_id == case_id)).all())
    links_count = len(
        session.exec(select(EntityLink.id).where(EntityLink.case_id == case_id)).all()
    )

    # 2. Custody Chain Verification
    custody_service = CustodyChainService(session)
    chain_result = custody_service.verify_chain(case_id)

    if chain_result.is_valid:
        statutory_text = (
            "Tamper-evident chain of custody mathematically verified intact from "
            f"genesis to head across {chain_result.total_entries} "
            "evidentiary artifact(s). Complies with Section 65B of the Indian "
            "Evidence Act, 1872 and Section 63 of the Bharatiya Sakshya "
            "Adhiniyam, 2023."
        )
    else:
        reason_msg = chain_result.reason or "Unspecified integrity violation"
        statutory_text = (
            "WARNING: Cryptographic custody chain verification FAILED. "
            f"Discrepancy detected: {reason_msg}."
        )

    head_hash = chain_result.details.get("head_hash")

    custody_statement = CustodyIntegrityStatement(
        is_valid=chain_result.is_valid,
        total_entries=chain_result.total_entries,
        head_hash=head_hash,
        statutory_statement=statutory_text,
        broken_reason=chain_result.reason,
        details=chain_result.details,
    )

    # 3. Correlation Graph & Clusters
    graph = GraphBuilder.build_for_case(case_id, session=session)
    components = list(nx.connected_components(graph)) if len(graph) > 0 else []

    # 4. Risk Scoring
    scoring_engine = RiskScoringEngine(session=session)
    scored_entities: list[dict[str, Any]] = []

    for entity in entities:
        if entity.id is None:
            continue

        result = scoring_engine.score_entity(entity.id, graph, persist=True)

        descriptions: list[str] = [
            rule.rendered_message for rule in result.triggered_rules
        ]
        if not descriptions and result.reason_code_strings:
            # Fallback if retrieved from existing codes
            for code_str in result.reason_code_strings:
                try:
                    rc = ReasonCode.from_code(code_str)
                    descriptions.append(rc.template)
                except ValueError:
                    descriptions.append(code_str)

        entity_type_str = (
            entity.entity_type.value
            if hasattr(entity.entity_type, "value")
            else str(entity.entity_type)
        )

        val_display = (
            mask_identifier(entity.value, entity.entity_type)
            if mask_pii
            else entity.value
        )

        scored_entities.append(
            {
                "entity_id": entity.id,
                "entity_type": entity_type_str,
                "identifier": val_display,
                "score": result.score,
                "reason_codes": result.reason_code_strings,
                "reason_descriptions": descriptions,
                "recommendation": result.recommendation,
            }
        )

    # Sort descending by score, then by entity_id ascending
    scored_entities.sort(key=lambda item: (-item["score"], item["entity_id"]))
    top_ranked = [RankedEntityExport(**item) for item in scored_entities[:top_n]]

    # Map of entity_id -> score for cluster stats
    score_by_id = {item["entity_id"]: item["score"] for item in scored_entities}

    # 5. Cluster Summaries
    cluster_summaries: list[ClusterSummaryExport] = []
    for cluster_id, comp in enumerate(components):
        node_types = set()
        high_risk_count = 0
        for node_id in comp:
            node_data = graph.nodes.get(node_id, {})
            node_types.add(node_data.get("entity_type", "unknown"))
            if score_by_id.get(node_id, 0) >= 40:
                high_risk_count += 1

        cluster_summaries.append(
            ClusterSummaryExport(
                cluster_id=cluster_id,
                node_count=len(comp),
                entity_types=sorted(list(node_types)),
                high_risk_entity_count=high_risk_count,
            )
        )

    case_summary = CaseSummary(
        case_id=case_id,
        name=case.name,
        status=case.status,
        created_at=case.created_at,
        total_evidence_files=evidence_count,
        total_entities=len(entities),
        total_links=links_count,
        total_clusters=len(components),
    )

    return BriefExport(
        classification="LAW ENFORCEMENT SENSITIVE // OFFICIAL INVESTIGATIVE BRIEF",
        generated_at=datetime.utcnow(),
        case_summary=case_summary,
        custody_chain=custody_statement,
        top_entities=top_ranked,
        clusters=cluster_summaries,
    )
