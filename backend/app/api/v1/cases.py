"""Cases and evidentiary artifact endpoints for investigation workflows."""

import logging
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from app.db.models import Case, Entity, EvidenceFile, SourceType
from app.db.session import get_session
from app.schemas.case import CaseCreate, CaseRead
from app.services.brief import (
    BriefExport,
    generate_brief_json,
    generate_brief_pdf,
)
from app.services.correlation.graph_builder import GraphBuilder
from app.services.correlation.graph_serializer import SerializedGraph, serialize_graph
from app.services.ingestion import IngestionSummary, normalize
from app.services.integrity import (
    ChainVerificationResult,
    CustodyChainService,
    compute_sha256,
)
from app.services.risk.reason_codes import ReasonCode
from app.services.risk.scoring_engine import RiskScoringEngine

logger = logging.getLogger("api.v1.cases")

router = APIRouter(prefix="/cases", tags=["cases"])


class RankedEntityRiskRead(BaseModel):
    """Ranked risk evaluation result for an individual entity."""

    entity_id: int
    entity_type: str
    value: str
    score: int = Field(ge=0, le=100)
    reason_codes: list[str]
    reason_descriptions: list[str]
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create investigation case",
)
def create_case(
    case_in: CaseCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Case:
    """Create an investigation case envelope."""
    case = Case(name=case_in.name, status=case_in.status)
    session.add(case)
    session.commit()
    session.refresh(case)
    logger.info("Created investigation case #%d: '%s'", case.id, case.name)
    return case


@router.get(
    "",
    response_model=list[CaseRead],
    summary="List all investigation cases",
)
def list_cases(
    session: Annotated[Session, Depends(get_session)],
) -> list[Case]:
    """Retrieve all investigation cases."""
    cases = session.exec(select(Case).order_by(Case.id.desc())).all()
    return list(cases)


@router.get(
    "/{case_id}",
    response_model=CaseRead,
    summary="Get case details by ID",
)
def get_case(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> Case:
    """Retrieve details for a single investigation case."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )
    return case


@router.post(
    "/{case_id}/evidence",
    response_model=IngestionSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest evidentiary artifact",
)
async def upload_evidence(
    case_id: int,
    file: Annotated[
        UploadFile,
        File(description="Multipart binary or text evidence artifact"),
    ],
    source_type: Annotated[
        SourceType,
        Form(description="Source format (cdr, bank_upi, email, android_log)"),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> IngestionSummary:
    """Upload evidence file, parse, normalize, and record custody hash chain."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded evidence artifact is completely empty (0 bytes).",
        )

    # Compute initial SHA-256 digest
    file_hash = compute_sha256(file_bytes)

    # Persist preliminary EvidenceFile entry
    evidence_file = EvidenceFile(
        case_id=case_id,
        original_filename=file.filename or "uploaded_artifact",
        source_type=source_type,
        file_hash=file_hash,
    )
    session.add(evidence_file)
    session.commit()
    session.refresh(evidence_file)

    try:
        # Run synchronous parsing, deduplication, and chained custody logging
        ingestion_result = normalize(
            file_source=file_bytes,
            source_type=source_type,
            case_id=case_id,
            evidence_file_id=evidence_file.id,  # type: ignore[arg-type]
            session=session,
        )
        return ingestion_result.summary
    except Exception:
        # Clean up orphaned EvidenceFile record if normalization aborted
        try:
            session.delete(evidence_file)
            session.commit()
        except Exception:
            session.rollback()
        raise


@router.get(
    "/{case_id}/graph",
    response_model=SerializedGraph,
    summary="Get correlated entity graph",
)
def get_case_graph(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, Any]:
    """Execute graph correlation across ingested evidence and return graph."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    graph = GraphBuilder.build_for_case(case_id, session=session)
    return serialize_graph(graph)


@router.get(
    "/{case_id}/risk",
    response_model=list[RankedEntityRiskRead],
    summary="Compute and return ranked risk scores for all entities",
)
def get_case_risk_scores(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> list[RankedEntityRiskRead]:
    """Execute explainable heuristic risk scoring for all entities in the case."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    graph = GraphBuilder.build_for_case(case_id, session=session)
    entities = list(session.exec(select(Entity).where(Entity.case_id == case_id)).all())

    scoring_engine = RiskScoringEngine(session=session)
    results: list[RankedEntityRiskRead] = []

    for ent in entities:
        if ent.id is None:
            continue
        score_res = scoring_engine.score_entity(ent.id, graph, persist=True)

        descriptions = [rule.rendered_message for rule in score_res.triggered_rules]
        if not descriptions and score_res.reason_code_strings:
            for code_str in score_res.reason_code_strings:
                try:
                    descriptions.append(ReasonCode.from_code(code_str).template)
                except ValueError:
                    descriptions.append(code_str)

        ent_type_str = (
            ent.entity_type.value
            if hasattr(ent.entity_type, "value")
            else str(ent.entity_type)
        )

        results.append(
            RankedEntityRiskRead(
                entity_id=ent.id,
                entity_type=ent_type_str,
                value=ent.value,
                score=score_res.score,
                reason_codes=score_res.reason_code_strings,
                reason_descriptions=descriptions,
                recommendation=score_res.recommendation,
            )
        )

    # Rank descending by score, then by entity_id
    results.sort(key=lambda r: (-r.score, r.entity_id))
    return results


@router.get(
    "/{case_id}/brief.json",
    response_model=BriefExport,
    summary="Generate court-ready JSON investigative brief",
)
def get_case_brief_json(
    case_id: int,
    mask_pii: bool = True,
    session: Annotated[Session, Depends(get_session)] = None,  # type: ignore[assignment]
) -> BriefExport:
    """Generate structured JSON investigative brief with Section 65B/BSA 63 audit."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    return generate_brief_json(case_id, session=session, mask_pii=mask_pii)


@router.get(
    "/{case_id}/brief.pdf",
    summary="Download court-ready one-page PDF investigative brief",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Court-ready one-page PDF investigative brief",
        }
    },
)
def get_case_brief_pdf(
    case_id: int,
    mask_pii: bool = True,
    session: Annotated[Session, Depends(get_session)] = None,  # type: ignore[assignment]
) -> Response:
    """Generate and download strictly one-page PDF investigative brief."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    brief_data = generate_brief_json(case_id, session=session, mask_pii=mask_pii)
    pdf_bytes = generate_brief_pdf(brief_data)

    filename = f"case_{case_id}_brief.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "application/pdf",
        },
    )


@router.get(
    "/{case_id}/integrity",
    response_model=ChainVerificationResult,
    summary="Verify evidentiary custody chain integrity",
)
def get_case_integrity(
    case_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> ChainVerificationResult:
    """Verify unbroken cryptographic SHA-256 custody chain under Section 65B/BSA 63."""
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation case #{case_id} not found",
        )

    custody_service = CustodyChainService(session)
    return custody_service.verify_chain(case_id)
