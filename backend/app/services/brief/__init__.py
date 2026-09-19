"""Investigative brief generation package.

Includes PII masking, JSON assembly, and PDF rendering.
"""

from app.services.brief.json_exporter import (
    BriefExport,
    CaseSummary,
    ClusterSummaryExport,
    CustodyIntegrityStatement,
    RankedEntityExport,
    generate_brief_json,
)
from app.services.brief.pdf_generator import (
    PDFBriefGenerator,
    generate_brief_pdf,
)
from app.services.brief.pii_mask import (
    mask_account,
    mask_email,
    mask_identifier,
    mask_imei,
    mask_phone,
)

__all__ = [
    "BriefExport",
    "CaseSummary",
    "ClusterSummaryExport",
    "CustodyIntegrityStatement",
    "PDFBriefGenerator",
    "RankedEntityExport",
    "generate_brief_json",
    "generate_brief_pdf",
    "mask_account",
    "mask_email",
    "mask_identifier",
    "mask_imei",
    "mask_phone",
]
