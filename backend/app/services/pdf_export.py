"""PDF export service.

Converts HTML content to PDF for tender documents and reports.
Uses a lightweight HTML-to-PDF approach that works in Docker.
"""

import io
import structlog
from datetime import datetime

logger = structlog.get_logger()


async def generate_pdf_from_html(html_content: str, title: str = "Document") -> bytes:
    """Convert HTML string to PDF bytes.

    Uses markdown-to-html + basic CSS for styling.
    Falls back to plain text PDF if HTML rendering fails.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            title=title,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        styles.add(ParagraphStyle(
            name="ChTitle",
            fontSize=18, leading=24,
            spaceAfter=12, spaceBefore=24,
            textColor=colors.HexColor("#1F3864"),
            fontName="Helvetica-Bold",
        ))
        styles.add(ParagraphStyle(
            name="ChBody",
            fontSize=11, leading=16,
            spaceAfter=8,
            fontName="Helvetica",
        ))
        styles.add(ParagraphStyle(
            name="CoverTitle",
            fontSize=28, leading=36,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F3864"),
            fontName="Helvetica-Bold",
            spaceAfter=20,
        ))
        styles.add(ParagraphStyle(
            name="CoverSub",
            fontSize=14, leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
            fontName="Helvetica",
        ))

        elements = []

        # Cover page
        elements.append(Spacer(1, 6 * cm))
        elements.append(Paragraph(title, styles["CoverTitle"]))
        elements.append(Paragraph("Technical Proposal &amp; Commercial Quotation", styles["CoverSub"]))
        elements.append(Spacer(1, 2 * cm))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", styles["CoverSub"]))
        elements.append(PageBreak())

        # Parse HTML content into paragraphs
        lines = html_content.replace("<br>", "\n").replace("<br/>", "\n")
        # Strip HTML tags for simple rendering
        import re
        clean = re.sub(r"<[^>]+>", "", lines)

        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                elements.append(Spacer(1, 6))
                continue
            if stripped.startswith("# "):
                elements.append(PageBreak())
                elements.append(Paragraph(stripped[2:], styles["ChTitle"]))
            elif stripped.startswith("## "):
                elements.append(Spacer(1, 12))
                elements.append(Paragraph(stripped[3:], styles["ChTitle"]))
            else:
                # Escape XML special chars for reportlab
                safe = stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                elements.append(Paragraph(safe, styles["ChBody"]))

        doc.build(elements)
        return buffer.getvalue()

    except ImportError:
        logger.warning("reportlab_not_available", msg="Falling back to plain text PDF")
        return _plain_text_pdf(html_content, title)


async def generate_pdf_from_stages(stage_outputs: dict, project_info: dict) -> bytes:
    """Generate a PDF report from pipeline stage outputs."""
    sections = []
    sections.append(f"# {project_info.get('name', 'Project Report')}")
    sections.append(f"Client: {project_info.get('client_name', 'N/A')}")
    sections.append(f"Industry: {project_info.get('industry', 'N/A')}")
    sections.append(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    sections.append("")

    # Stage 1: Requirements
    reqs = stage_outputs.get(1, {})
    if reqs.get("requirements"):
        sections.append("## Requirements Summary")
        for r in reqs["requirements"][:15]:
            sections.append(f"- [{r.get('priority', 'P1')}] {r.get('description', '')[:100]}")
        sections.append("")

    # Stage 5: Solution
    sol = stage_outputs.get(5, {})
    if sol.get("executive_summary"):
        sections.append("## Solution Design")
        sections.append(sol["executive_summary"])
        sections.append("")

    # Stage 8: Cost
    cost = stage_outputs.get(8, {})
    indicators = cost.get("financial_indicators", {})
    if indicators:
        sections.append("## Financial Indicators")
        sections.append(f"- ROI: {indicators.get('roi_percent', 'N/A')}%")
        sections.append(f"- IRR: {indicators.get('irr_percent', 'N/A')}%")
        sections.append(f"- NPV: {indicators.get('npv_at_8pct', 'N/A')}")
        sections.append(f"- Payback: {indicators.get('payback_months', 'N/A')} months")
        sections.append("")

    # Stage 9: Risks
    risks = stage_outputs.get(9, {})
    risk_items = risks.get("risk_matrix", [])
    if risk_items:
        sections.append("## Key Risks")
        for r in risk_items[:5]:
            sections.append(f"- [{r.get('likelihood', '')}] {r.get('description', '')[:80]}")
        sections.append("")

    # Stage 10: Tender content
    tender = stage_outputs.get(10, {})
    chapters = tender.get("document_structure", [])
    for ch in chapters:
        sections.append(f"## {ch.get('title', '')}")
        sections.append(ch.get("content", ""))
        sections.append("")

    html = "\n".join(sections)
    return await generate_pdf_from_html(html, project_info.get("name", "Report"))


def _plain_text_pdf(text: str, title: str) -> bytes:
    """Minimal PDF generation without reportlab."""
    import re
    clean = re.sub(r"<[^>]+>", "", text)

    # Minimal valid PDF
    lines_list = clean.split("\n")
    content = "\n".join(lines_list[:200])  # Limit pages

    pdf_content = f"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length {len(content) + 50}>>
stream
BT /F1 10 Tf 50 800 Td ({title}) Tj ET
BT /F1 9 Tf 50 780 Td"""

    y = 780
    for line in lines_list[:80]:
        safe = line.replace("(", "\\(").replace(")", "\\)")[:100]
        pdf_content += f" ({safe}) Tj 0 -14 Td"
        y -= 14

    pdf_content += """ ET
endstream
endobj
xref
0 6
trailer<</Size 6/Root 1 0 R>>
startxref
0
%%EOF"""

    return pdf_content.encode("latin-1", errors="replace")
