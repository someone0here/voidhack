"""Court-ready, strictly one-page PDF investigative brief generator using ReportLab."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from app.services.brief.json_exporter import BriefExport

# Layout constants (A4 is 595.27 x 841.89 pt)
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 36.0  # 0.5 inch margins
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN_X)

# Visual Design Palette
COLOR_CANVAS_DARK = colors.HexColor("#0F172A")
COLOR_DOSSIER_SLATE = colors.HexColor("#1E293B")
COLOR_BORDER = colors.HexColor("#334155")
COLOR_AMBER = colors.HexColor("#D97706")
COLOR_CRIMSON = colors.HexColor("#DC2626")
COLOR_CYAN = colors.HexColor("#0891B2")
COLOR_TEXT_PRIMARY = colors.HexColor("#0F172A")
COLOR_TEXT_SECONDARY = colors.HexColor("#475569")
COLOR_BG_CARD = colors.HexColor("#F8FAFC")
COLOR_SUCCESS = colors.HexColor("#15803D")


class PDFBriefGenerator:
    """Renders a court-ready, strictly one-page investigative dossier."""

    def __init__(self, brief: BriefExport) -> None:
        """Initialize generator with BriefExport data payload."""
        self.brief = brief
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self) -> None:
        """Initialize custom paragraph styles for tight, high-density layout."""
        self.styles.add(
            ParagraphStyle(
                name="HeaderTitle",
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=15,
                textColor=colors.white,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="HeaderMeta",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#CBD5E1"),
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="SectionTitle",
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=11,
                textColor=COLOR_DOSSIER_SLATE,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CellText",
                fontName="Helvetica",
                fontSize=7.5,
                leading=9,
                textColor=COLOR_TEXT_PRIMARY,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CellTextBold",
                fontName="Helvetica-Bold",
                fontSize=7.5,
                leading=9,
                textColor=COLOR_TEXT_PRIMARY,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="CellTextCode",
                fontName="Courier",
                fontSize=7.0,
                leading=8.5,
                textColor=COLOR_TEXT_PRIMARY,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="AdvisoryNote",
                fontName="Helvetica",
                fontSize=6.5,
                leading=8.5,
                textColor=COLOR_TEXT_SECONDARY,
            )
        )

    def generate(self) -> bytes:
        """Render the complete brief into raw PDF bytes.

        Guaranteed to generate exactly ONE page by using fixed-budget layout zones
        and truncating overflow content with explicit record notes.
        """
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        # Draw page elements using hard vertical budget (from y_top down to y_bottom)
        y_cursor = PAGE_HEIGHT - 32.0

        y_cursor = self._draw_header_banner(c, y_cursor)
        y_cursor -= 10.0

        y_cursor = self._draw_case_telemetry(c, y_cursor)
        y_cursor -= 10.0

        y_cursor = self._draw_clusters_summary(c, y_cursor)
        y_cursor -= 10.0

        y_cursor = self._draw_priority_entities(c, y_cursor)
        y_cursor -= 10.0

        y_cursor = self._draw_advisory_box(c, y_cursor)

        self._draw_footer(c)

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.getvalue()

    def _draw_header_banner(self, c: canvas.Canvas, y_top: float) -> float:
        """Render classified header banner. Height: ~56 pt."""
        height = 56.0
        y_bottom = y_top - height

        # Slate header box
        c.setFillColor(COLOR_DOSSIER_SLATE)
        c.roundRect(
            MARGIN_X, y_bottom, CONTENT_WIDTH, height, 3, fill=True, stroke=False
        )

        # Red classification tag in top right
        c.setFillColor(COLOR_CRIMSON)
        c.roundRect(
            MARGIN_X + CONTENT_WIDTH - 150.0,
            y_top - 18.0,
            144.0,
            14.0,
            2,
            fill=True,
            stroke=False,
        )
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawString(
            MARGIN_X + CONTENT_WIDTH - 146.0,
            y_top - 13.0,
            "LAW ENFORCEMENT SENSITIVE",
        )

        # Title and Subtitle
        title_para = Paragraph(
            "CYBER FRAUD CORRELATION & RISK INTELLIGENCE BRIEF",
            self.styles["HeaderTitle"],
        )
        title_para.wrapOn(c, CONTENT_WIDTH - 160.0, 20.0)
        title_para.drawOn(c, MARGIN_X + 10.0, y_top - 20.0)

        cs = self.brief.case_summary
        gen_date = self.brief.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        meta_text = (
            f"<b>CASE ID:</b> {cs.case_id} &nbsp;|&nbsp; "
            f"<b>NAME:</b> {cs.name} &nbsp;|&nbsp; "
            f"<b>STATUS:</b> {cs.status.upper()} &nbsp;|&nbsp; "
            f"<b>GENERATED:</b> {gen_date}"
        )
        meta_para = Paragraph(meta_text, self.styles["HeaderMeta"])
        meta_para.wrapOn(c, CONTENT_WIDTH - 20.0, 16.0)
        meta_para.drawOn(c, MARGIN_X + 10.0, y_top - 46.0)

        return y_bottom

    def _draw_case_telemetry(self, c: canvas.Canvas, y_top: float) -> float:
        """Render case metrics and Section 65B/BSA 63 integrity block."""
        cs = self.brief.case_summary
        cc = self.brief.custody_chain

        # Section Header
        c.setFillColor(COLOR_DOSSIER_SLATE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(
            MARGIN_X,
            y_top - 2.0,
            "1. EVIDENTIARY TELEMETRY & SECTION 65B / BSA 63 CUSTODY AUDIT",
        )
        y_cursor = y_top - 12.0

        # Status badge color
        status_color = COLOR_SUCCESS if cc.is_valid else COLOR_CRIMSON
        status_label = "VERIFIED INTACT" if cc.is_valid else "FAILED / ALTERED"

        head_hash_trunc = (
            f"{cc.head_hash[:32]}..." if cc.head_hash else "None (Empty Ledger)"
        )

        data = [
            [
                Paragraph("<b>Evidence Files:</b>", self.styles["CellText"]),
                Paragraph(str(cs.total_evidence_files), self.styles["CellTextBold"]),
                Paragraph("<b>Unique Entities:</b>", self.styles["CellText"]),
                Paragraph(str(cs.total_entities), self.styles["CellTextBold"]),
                Paragraph("<b>Correlated Links:</b>", self.styles["CellText"]),
                Paragraph(str(cs.total_links), self.styles["CellTextBold"]),
                Paragraph("<b>Syndicate Clusters:</b>", self.styles["CellText"]),
                Paragraph(str(cs.total_clusters), self.styles["CellTextBold"]),
            ],
            [
                Paragraph("<b>Custody Chain:</b>", self.styles["CellText"]),
                Paragraph(
                    f"<font color='{status_color.hexval()}'>"
                    f"<b>{status_label}</b></font>",
                    self.styles["CellText"],
                ),
                Paragraph("<b>Audited Artifacts:</b>", self.styles["CellText"]),
                Paragraph(str(cc.total_entries), self.styles["CellTextBold"]),
                Paragraph("<b>Ledger Head Hash:</b>", self.styles["CellText"]),
                Paragraph(
                    f"<font size=6>{head_hash_trunc}</font>",
                    self.styles["CellTextCode"],
                ),
                Paragraph("<b>Statutory Basis:</b>", self.styles["CellText"]),
                Paragraph("Sec 65B IEA / BSA 63", self.styles["CellTextBold"]),
            ],
        ]

        col_w = CONTENT_WIDTH / 8.0
        table = Table(data, colWidths=[col_w] * 8, rowHeights=[18.0, 18.0])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_CARD),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        w, h = table.wrapOn(c, CONTENT_WIDTH, 40.0)
        table.drawOn(c, MARGIN_X, y_cursor - h)
        y_cursor -= h + 4.0

        # Legal statutory certificate note
        stat_para = Paragraph(
            f"<b>Evidentiary Certification:</b> {cc.statutory_statement}",
            self.styles["AdvisoryNote"],
        )
        stat_para.wrapOn(c, CONTENT_WIDTH, 20.0)
        stat_para.drawOn(c, MARGIN_X, y_cursor - 14.0)

        return y_cursor - 18.0

    def _draw_clusters_summary(self, c: canvas.Canvas, y_top: float) -> float:
        """Render syndicate cluster topological summary. Height: ~55 pt."""
        c.setFillColor(COLOR_DOSSIER_SLATE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(MARGIN_X, y_top - 2.0, "2. SYNDICATE TOPOLOGY & NETWORK CLUSTERS")
        y_cursor = y_top - 12.0

        clusters = self.brief.clusters[:3]  # Layout budget: show top 3 clusters
        if not clusters:
            data = [
                [
                    Paragraph(
                        "<i>No connected clusters discovered in evidence.</i>",
                        self.styles["CellText"],
                    )
                ]
            ]
            col_widths = [CONTENT_WIDTH]
        else:
            headers = [
                Paragraph("<b>Cluster ID</b>", self.styles["CellTextBold"]),
                Paragraph("<b>Node Count</b>", self.styles["CellTextBold"]),
                Paragraph("<b>High-Risk Nodes (>=40)</b>", self.styles["CellTextBold"]),
                Paragraph(
                    "<b>Associated Entity Types</b>", self.styles["CellTextBold"]
                ),
            ]
            rows = [headers]
            for cl in clusters:
                types_str = ", ".join(cl.entity_types) if cl.entity_types else "None"
                rows.append(
                    [
                        Paragraph(
                            f"Cluster #{cl.cluster_id}", self.styles["CellTextBold"]
                        ),
                        Paragraph(str(cl.node_count), self.styles["CellText"]),
                        Paragraph(
                            str(cl.high_risk_entity_count),
                            (
                                self.styles["CellTextBold"]
                                if cl.high_risk_entity_count > 0
                                else self.styles["CellText"]
                            ),
                        ),
                        Paragraph(types_str, self.styles["CellText"]),
                    ]
                )

            if len(self.brief.clusters) > 3:
                overflow_count = len(self.brief.clusters) - 3
                rows.append(
                    [
                        Paragraph(
                            f"<i>+{overflow_count} additional smaller "
                            "clusters in electronic record.</i>",
                            self.styles["AdvisoryNote"],
                        ),
                        Paragraph("", self.styles["CellText"]),
                        Paragraph("", self.styles["CellText"]),
                        Paragraph("", self.styles["CellText"]),
                    ]
                )

            col_widths = [
                CONTENT_WIDTH * 0.15,
                CONTENT_WIDTH * 0.15,
                CONTENT_WIDTH * 0.25,
                CONTENT_WIDTH * 0.45,
            ]
            data = rows

        table = Table(data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        w, h = table.wrapOn(c, CONTENT_WIDTH, 50.0)
        table.drawOn(c, MARGIN_X, y_cursor - h)

        return y_cursor - h

    def _draw_priority_entities(self, c: canvas.Canvas, y_top: float) -> float:
        """Render top risk-ranked entities with hard layout budget (max 5 rows)."""
        c.setFillColor(COLOR_DOSSIER_SLATE)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(
            MARGIN_X,
            y_top - 2.0,
            "3. PRIORITY TARGETS & OPERATIONAL FRAUD RISK SCORING (MASKED IDENTIFIERS)",
        )
        y_cursor = y_top - 12.0

        headers = [
            Paragraph("<b>Rank</b>", self.styles["CellTextBold"]),
            Paragraph("<b>Type</b>", self.styles["CellTextBold"]),
            Paragraph("<b>Masked Identifier</b>", self.styles["CellTextBold"]),
            Paragraph("<b>Risk Score</b>", self.styles["CellTextBold"]),
            Paragraph(
                "<b>Triggered Forensic Heuristics</b>", self.styles["CellTextBold"]
            ),
        ]
        rows = [headers]

        # Strictly enforce layout budget: max 5 rows to ensure 1 page
        MAX_DISPLAY_ENTITIES = 5
        entities_to_show = self.brief.top_entities[:MAX_DISPLAY_ENTITIES]

        for idx, ent in enumerate(entities_to_show, start=1):
            score_color = (
                COLOR_CRIMSON
                if ent.score >= 70
                else (COLOR_AMBER if ent.score >= 40 else COLOR_SUCCESS)
            )

            # Format reasons compactly
            if ent.reason_descriptions:
                reasons_html = "<br/>• ".join(
                    [r.replace("\n", " ") for r in ent.reason_descriptions]
                )
                reasons_text = f"• {reasons_html}"
            else:
                reasons_text = "No heuristic alerts triggered (Baseline)"

            rows.append(
                [
                    Paragraph(f"#{idx}", self.styles["CellTextBold"]),
                    Paragraph(ent.entity_type.upper(), self.styles["CellText"]),
                    Paragraph(f"<b>{ent.identifier}</b>", self.styles["CellTextCode"]),
                    Paragraph(
                        f"<font color='{score_color.hexval()}'>"
                        f"<b>{ent.score}/100</b></font>",
                        self.styles["CellTextBold"],
                    ),
                    Paragraph(reasons_text, self.styles["CellText"]),
                ]
            )

        # Truncation notice row if more entities exist
        if len(self.brief.top_entities) > MAX_DISPLAY_ENTITIES:
            overflow = len(self.brief.top_entities) - MAX_DISPLAY_ENTITIES
            rows.append(
                [
                    Paragraph(
                        f"<b>+{overflow} more entities</b> cataloged in "
                        "electronic case record.",
                        self.styles["AdvisoryNote"],
                    ),
                    Paragraph("", self.styles["CellText"]),
                    Paragraph("", self.styles["CellText"]),
                    Paragraph("", self.styles["CellText"]),
                    Paragraph(
                        "Full unmasked records accessible via authenticated "
                        "investigator console.",
                        self.styles["AdvisoryNote"],
                    ),
                ]
            )

        col_widths = [
            CONTENT_WIDTH * 0.08,
            CONTENT_WIDTH * 0.16,
            CONTENT_WIDTH * 0.26,
            CONTENT_WIDTH * 0.14,
            CONTENT_WIDTH * 0.36,
        ]

        table = Table(rows, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        w, h = table.wrapOn(c, CONTENT_WIDTH, 300.0)
        table.drawOn(c, MARGIN_X, y_cursor - h)

        return y_cursor - h

    def _draw_advisory_box(self, c: canvas.Canvas, y_top: float) -> float:
        """Render mandatory human-in-the-loop advisory notice. Height: ~55 pt."""
        height = 50.0
        y_bottom = y_top - height

        c.setFillColor(colors.HexColor("#FEF3C7"))  # Soft amber container
        c.roundRect(
            MARGIN_X, y_bottom, CONTENT_WIDTH, height, 3, fill=True, stroke=True
        )

        c.setStrokeColor(COLOR_AMBER)
        c.setLineWidth(1.0)
        c.roundRect(
            MARGIN_X, y_bottom, CONTENT_WIDTH, height, 3, fill=False, stroke=True
        )

        adv_text = (
            "<b>HUMAN-IN-THE-LOOP ADVISORY DIRECTIVE:</b> "
            "All risk scores, cluster linkages, and heuristic flags are automated "
            "analytical indicators generated to advise sworn investigating officers. "
            "<b>The system does not mandate or perform autonomous "
            "enforcement actions.</b> "
            "Independent corroboration of electronic records with primary bank "
            "ledgers, telecom certificates, or physical ground truth is "
            "mandatory before filing charges or executing search warrants."
        )
        adv_para = Paragraph(adv_text, self.styles["AdvisoryNote"])
        adv_para.wrapOn(c, CONTENT_WIDTH - 16.0, height - 8.0)
        adv_para.drawOn(c, MARGIN_X + 8.0, y_top - 42.0)

        return y_bottom

    def _draw_footer(self, c: canvas.Canvas) -> None:
        """Render standardized footer divider and page telemetry."""
        y_footer = 22.0

        c.setStrokeColor(COLOR_BORDER)
        c.setLineWidth(0.5)
        c.line(MARGIN_X, y_footer + 10.0, MARGIN_X + CONTENT_WIDTH, y_footer + 10.0)

        c.setFillColor(COLOR_TEXT_SECONDARY)
        c.setFont("Helvetica", 6.5)
        c.drawString(
            MARGIN_X,
            y_footer,
            "CYBER FRAUD CORRELATOR — COURT-READY INVESTIGATIVE SUMMARY DOSSIER",
        )

        c.setFont("Helvetica-Bold", 7.0)
        c.drawRightString(MARGIN_X + CONTENT_WIDTH, y_footer, "PAGE 1 OF 1")


def generate_brief_pdf(brief: BriefExport) -> bytes:
    """Convenience helper to render a BriefExport to one-page PDF bytes."""
    generator = PDFBriefGenerator(brief)
    return generator.generate()
