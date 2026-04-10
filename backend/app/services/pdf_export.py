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

        # Try to register a Chinese-capable font
        chinese_font = "Helvetica"
        chinese_font_bold = "Helvetica-Bold"
        try:
            import os
            # Try common Chinese font paths
            for font_path in [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            ]:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont("ChineseFont", font_path))
                    chinese_font = "ChineseFont"
                    chinese_font_bold = "ChineseFont"
                    break
        except Exception:
            pass  # Fall back to Helvetica

        # Custom styles
        styles.add(ParagraphStyle(
            name="ChTitle",
            fontSize=18, leading=24,
            spaceAfter=12, spaceBefore=24,
            textColor=colors.HexColor("#1F3864"),
            fontName=chinese_font_bold,
        ))
        styles.add(ParagraphStyle(
            name="ChBody",
            fontSize=11, leading=16,
            spaceAfter=8,
            fontName=chinese_font,
        ))
        styles.add(ParagraphStyle(
            name="CoverTitle",
            fontSize=28, leading=36,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1F3864"),
            fontName=chinese_font_bold,
            spaceAfter=20,
        ))
        styles.add(ParagraphStyle(
            name="CoverSub",
            fontSize=14, leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#64748B"),
            fontName=chinese_font,
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
    req_list = reqs.get("requirements") or reqs.get("需求") or reqs.get("需求列表") or []
    if req_list:
        sections.append("## 需求概要 (Requirements Summary)")
        for r in req_list[:15]:
            desc = r.get('description', '') or r.get('描述', '') or str(r)
            prio = r.get('priority', '') or r.get('优先级', 'P1')
            sections.append(f"- [{prio}] {desc[:100]}")
        sections.append("")

    # Stage 5: Solution
    sol = stage_outputs.get(5, {})
    summary = sol.get("executive_summary") or sol.get("执行摘要") or sol.get("方案概要") or ""
    if summary:
        sections.append("## 方案设计 (Solution Design)")
        sections.append(summary)
        sections.append("")

    # Stage 8: Cost
    cost = stage_outputs.get(8, {})
    indicators = cost.get("financial_indicators") or cost.get("财务指标") or {}
    if indicators:
        sections.append("## 财务指标 (Financial Indicators)")
        roi = indicators.get('roi_percent') or indicators.get('投资回报率') or 'N/A'
        irr = indicators.get('irr_percent') or indicators.get('内部收益率') or 'N/A'
        npv = indicators.get('npv_at_8pct') or indicators.get('净现值8折现') or 'N/A'
        payback = indicators.get('payback_months') or indicators.get('回本周期月数') or 'N/A'
        sections.append(f"- ROI: {roi}%")
        sections.append(f"- IRR: {irr}%")
        sections.append(f"- NPV: {npv}")
        sections.append(f"- Payback: {payback} months")
        sections.append("")

    # Stage 9: Risks
    risks = stage_outputs.get(9, {})
    risk_items = risks.get("risk_matrix") or risks.get("风险矩阵") or risks.get("风险") or []
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
