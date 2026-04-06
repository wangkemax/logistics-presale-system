"""Document processing service: extract text from PDF and Word files."""

import io
import structlog

logger = structlog.get_logger()


async def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract text content from uploaded files."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        return await _extract_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return await _extract_docx(file_bytes)
    elif ext == "txt":
        return file_bytes.decode("utf-8", errors="replace")
    else:
        logger.warning("unsupported_file_type", ext=ext, filename=filename)
        return file_bytes.decode("utf-8", errors="replace")


async def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

            # Also extract tables
            tables = page.extract_tables()
            for table in tables:
                if table:
                    rows = []
                    for row in table:
                        cells = [str(c or "").strip() for c in row]
                        rows.append(" | ".join(cells))
                    text_parts.append("TABLE:\n" + "\n".join(rows))

    return "\n\n".join(text_parts)


async def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from Word documents."""
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

    # Extract tables too
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            paragraphs.append(" | ".join(cells))

    return "\n\n".join(paragraphs)
