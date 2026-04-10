"""Knowledge base management and search API routes."""

import os
import uuid as uuid_lib
from pathlib import Path
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import KnowledgeEntry
from app.services.knowledge_service import get_knowledge_service

from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

COLLECTION_NAME = "logistics_knowledge"

# Directory for storing original uploaded knowledge source files
KNOWLEDGE_FILES_DIR = Path(os.getenv("KNOWLEDGE_FILES_DIR", "/app/uploads/knowledge"))
try:
    KNOWLEDGE_FILES_DIR.mkdir(parents=True, exist_ok=True)
except (PermissionError, OSError):
    # In CI/test environments without write access, fall back to /tmp
    KNOWLEDGE_FILES_DIR = Path("/tmp/knowledge_uploads")
    try:
        KNOWLEDGE_FILES_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _save_uploaded_file(file_bytes: bytes, original_filename: str) -> tuple[str, str]:
    """Save uploaded file to disk and return (file_path, original_filename)."""
    safe_name = os.path.basename(original_filename or "unknown")
    unique_name = f"{uuid_lib.uuid4().hex}_{safe_name}"
    file_path = KNOWLEDGE_FILES_DIR / unique_name
    file_path.write_bytes(file_bytes)
    return str(file_path), safe_name


# ── Schemas ──

class KnowledgeCreate(BaseModel):
    category: str = Field(description="automation_case / cost_model / logistics_case")
    title: str
    content: str
    tags: list[str] = []
    metadata_: dict = Field(default_factory=dict, alias="metadata")

    model_config = {"populate_by_name": True}


class KnowledgeResponse(BaseModel):
    id: UUID
    category: str
    title: str
    content: str
    tags: list[str] | None
    is_active: bool
    file_name: str | None = None
    has_file: bool = False

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str
    category: str | None = None
    keyword: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    category: str
    tags: str


# ── CRUD ──

@router.post("", response_model=KnowledgeResponse, status_code=201)
async def create_entry(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a knowledge base entry and index it in vector DB."""
    entry = KnowledgeEntry(
        category=data.category,
        title=data.title,
        content=data.content,
        tags=data.tags,
        metadata_=data.metadata_,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    # Index in vector DB
    try:
        ks = get_knowledge_service()
        await ks.index_documents(COLLECTION_NAME, [{
            "id": str(entry.id),
            "content": f"{entry.title}\n\n{entry.content}",
            "category": entry.category,
            "tags": entry.tags or [],
            "metadata": {"title": entry.title},
        }])
    except Exception:
        pass  # Vector indexing is best-effort

    return entry


@router.get("", response_model=list[KnowledgeResponse])
async def list_entries(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List knowledge base entries with optional category filter."""
    q = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
    if category:
        q = q.where(KnowledgeEntry.category == category)
    q = q.order_by(KnowledgeEntry.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(q)
    entries = result.scalars().all()
    return [
        KnowledgeResponse(
            id=e.id, category=e.category, title=e.title, content=e.content,
            tags=e.tags, is_active=e.is_active,
            file_name=e.file_name, has_file=bool(e.file_path),
        )
        for e in entries
    ]


@router.get("/{entry_id}/download")
async def download_entry_file(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Download the original source file of a knowledge entry."""
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not entry.file_path:
        raise HTTPException(status_code=404, detail="No source file for this entry")
    if not os.path.exists(entry.file_path):
        raise HTTPException(status_code=404, detail="Source file no longer exists on disk")
    return FileResponse(
        entry.file_path,
        filename=entry.file_name or "download",
        media_type="application/octet-stream",
    )


@router.get("/{entry_id}", response_model=KnowledgeResponse)
async def get_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get a single knowledge base entry."""
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return KnowledgeResponse(
        id=entry.id, category=entry.category, title=entry.title, content=entry.content,
        tags=entry.tags, is_active=entry.is_active,
        file_name=entry.file_name, has_file=bool(entry.file_path),
    )


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Soft-delete a knowledge base entry."""
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry.is_active = False
    await db.flush()

    # Remove from vector DB
    try:
        ks = get_knowledge_service()
        await ks.delete_documents(COLLECTION_NAME, [str(entry_id)])
    except Exception:
        pass


# ── Semantic Search ──

@router.post("/search", response_model=list[SearchResult])
async def search_knowledge(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Search knowledge base. Uses Milvus vector search if available, 
    otherwise falls back to PostgreSQL keyword search."""
    
    # Try Milvus vector search first
    try:
        ks = get_knowledge_service()
        if request.keyword:
            results = await ks.hybrid_search(
                collection_name=COLLECTION_NAME,
                query=request.query,
                keyword=request.keyword,
                top_k=request.top_k,
                category=request.category,
            )
        else:
            results = await ks.search(
                collection_name=COLLECTION_NAME,
                query=request.query,
                top_k=request.top_k,
                filters={"category": request.category} if request.category else None,
            )
        if results:
            return [
                SearchResult(
                    id=r["id"],
                    title=r.get("metadata", {}).get("title", ""),
                    content=r["content"][:500],
                    score=r["score"],
                    category=r["category"],
                    tags=r["tags"],
                )
                for r in results
            ]
    except Exception:
        pass  # Fall through to keyword search
    
    # Fallback: PostgreSQL ILIKE keyword search across title + content + tags
    from sqlalchemy import or_, cast, String
    
    query = request.query.strip()
    if not query:
        return []
    
    # Build search query — match in title, content, or tags
    pattern = f"%{query}%"
    q = select(KnowledgeEntry).where(
        KnowledgeEntry.is_active == True,
        or_(
            KnowledgeEntry.title.ilike(pattern),
            KnowledgeEntry.content.ilike(pattern),
            cast(KnowledgeEntry.tags, String).ilike(pattern),
        )
    )
    if request.category:
        q = q.where(KnowledgeEntry.category == request.category)
    q = q.limit(request.top_k)
    
    result = await db.execute(q)
    entries = result.scalars().all()
    
    # Score by simple keyword frequency
    def calc_score(e: KnowledgeEntry) -> float:
        text = f"{e.title} {e.content}".lower()
        q_lower = query.lower()
        title_match = 0.5 if q_lower in e.title.lower() else 0.0
        content_count = text.count(q_lower)
        return min(1.0, title_match + content_count * 0.1)
    
    return [
        SearchResult(
            id=str(e.id),
            title=e.title,
            content=e.content[:500],
            score=calc_score(e),
            category=e.category,
            tags=",".join(e.tags) if isinstance(e.tags, list) else (e.tags or ""),
        )
        for e in sorted(entries, key=calc_score, reverse=True)
    ]


# ── Batch Import ──

class BatchImportRequest(BaseModel):
    entries: list[KnowledgeCreate]


@router.post("/batch-import")
async def batch_import(
    data: BatchImportRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Batch import knowledge base entries."""
    created_ids = []

    for entry_data in data.entries:
        entry = KnowledgeEntry(
            category=entry_data.category,
            title=entry_data.title,
            content=entry_data.content,
            tags=entry_data.tags,
            metadata_=entry_data.metadata_,
        )
        db.add(entry)
        await db.flush()
        created_ids.append(str(entry.id))

    # Batch index in vector DB
    try:
        ks = get_knowledge_service()
        docs = [
            {
                "id": cid,
                "content": f"{e.title}\n\n{e.content}",
                "category": e.category,
                "tags": e.tags,
                "metadata": {"title": e.title},
            }
            for cid, e in zip(created_ids, data.entries)
        ]
        await ks.index_documents(COLLECTION_NAME, docs)
    except Exception:
        pass

    return {"imported": len(created_ids), "ids": created_ids}


@router.post("/upload-roi-excel")
async def upload_roi_excel(
    file: UploadFile = File(...),
    project_name: str = Query("", description="Project name for context"),
    client_name: str = Query("", description="Client name"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload an ROI Excel file and auto-convert each equipment row to a knowledge entry.
    
    Expects an Excel with a 'List' sheet containing columns:
    Equipments_EN, Equipments_CN, QTY, Investment, Running Cost, Savings, IRR, NPV, Payback period(months)
    """
    import pandas as pd
    import io

    file_bytes = await file.read()
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {e}")

    # Save original file to disk
    saved_path, original_name = _save_uploaded_file(file_bytes, file.filename or "roi.xlsx")

    # Find the summary sheet (List, Summary, 总览, etc.)
    summary_sheet = None
    for s in xl.sheet_names:
        if s.lower() in ("list", "summary", "总览", "汇总"):
            summary_sheet = s
            break
    if not summary_sheet:
        summary_sheet = xl.sheet_names[0]

    df = pd.read_excel(xl, summary_sheet)

    # Find column names flexibly
    def find_col(df, *names):
        for n in names:
            for c in df.columns:
                if n.lower() in str(c).lower():
                    return c
        return None

    col_en = find_col(df, "equipments_en", "equipment_en", "name_en")
    col_cn = find_col(df, "equipments_cn", "equipment_cn", "名称", "设备")
    col_qty = find_col(df, "qty", "数量", "quantity")
    col_inv = find_col(df, "investment", "投资", "cost")
    col_run = find_col(df, "running cost", "运行", "operating")
    col_sav = find_col(df, "savings", "节省", "saving")
    col_irr = find_col(df, "irr", "收益率")
    col_npv = find_col(df, "npv", "净现值")
    col_pay = find_col(df, "payback", "回本", "回收")

    if not col_inv:
        raise HTTPException(status_code=400, detail="Cannot find 'Investment' column in the Excel")

    entries = []
    for _, row in df.iterrows():
        eq_en = row.get(col_en) if col_en else None
        eq_cn = row.get(col_cn) if col_cn else None
        if pd.isna(eq_en) and pd.isna(eq_cn):
            continue
        investment = row.get(col_inv) if col_inv else None
        if pd.isna(investment):
            continue

        eq_label = eq_cn or eq_en
        title = f"{project_name or '未命名项目'} - {eq_label}"
        if eq_en and eq_cn:
            title = f"{project_name or '未命名项目'} - {eq_cn} ({eq_en})"

        qty = row.get(col_qty) if col_qty else None
        running = row.get(col_run) if col_run else None
        savings = row.get(col_sav) if col_sav else None
        irr = row.get(col_irr) if col_irr else None
        npv = row.get(col_npv) if col_npv else None
        payback = row.get(col_pay) if col_pay else None

        def _num(v):
            try:
                return float(v) if not pd.isna(v) else None
            except (ValueError, TypeError):
                return None

        investment_n = _num(investment)
        running_n = _num(running)
        savings_n = _num(savings)
        irr_n = _num(irr)
        npv_n = _num(npv)
        payback_n = _num(payback)
        qty_n = _num(qty)

        if investment_n is None:
            continue

        lines = [
            f"客户：{client_name}" if client_name else "",
            f"项目：{project_name}" if project_name else "",
            f"设备：{eq_label}",
            f"数量：{qty_n} 台" if qty_n is not None else "",
            f"一次性投资：¥{investment_n:,.0f}",
            f"年运行成本:¥{running_n:,.0f}" if running_n is not None else "",
            f"年节省：¥{savings_n:,.0f}" if savings_n is not None else "",
            f"IRR（内部收益率）：{irr_n*100:.1f}%" if irr_n is not None else "",
            f"NPV（净现值）：¥{npv_n:,.0f}" if npv_n is not None else "",
            f"投资回报周期：{payback_n:.1f} 个月" if payback_n is not None else "",
        ]
        content = "\n".join(l for l in lines if l)

        metadata = {
            "客户": client_name,
            "项目": project_name,
            "设备类型": str(eq_label),
            "投资金额": investment_n,
            "IRR": irr_n,
            "回本月数": payback_n,
        }

        tags = ["自动化", "ROI"]
        if client_name:
            tags.append(client_name)
        eq_str = str(eq_en or eq_cn or "")
        if "AGV" in eq_str.upper():
            tags.append("AGV")
        if "Robot" in eq_str or "机器人" in eq_str:
            tags.append("机器人")

        entry = KnowledgeEntry(
            category="automation_case",
            title=title,
            content=content,
            tags=tags,
            metadata_=metadata,
            file_path=saved_path,
            file_name=original_name,
        )
        db.add(entry)
        entries.append(entry)

    await db.flush()
    created_ids = [str(e.id) for e in entries]

    # Index in vector DB if available
    try:
        ks = get_knowledge_service()
        docs = [
            {
                "id": str(e.id),
                "content": f"{e.title}\n\n{e.content}",
                "category": e.category,
                "tags": e.tags,
                "metadata": {"title": e.title},
            }
            for e in entries
        ]
        await ks.index_documents(COLLECTION_NAME, docs)
    except Exception:
        pass

    return {"imported": len(entries), "ids": created_ids, "preview": [{"title": e.title} for e in entries[:5]]}


@router.post("/upload-cost-model")
async def upload_cost_model(
    file: UploadFile = File(...),
    project_name: str = Query("", description="Project name"),
    client_name: str = Query("", description="Client name"),
    industry: str = Query("", description="Industry e.g. 汽车备件"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload a Cost Model Excel file and convert to a cost_model knowledge entry.
    
    Looks for 'P&L Sheet' or similar to extract revenue/cost categories per year.
    Creates ONE comprehensive entry with all cost components.
    """
    import pandas as pd
    import io

    file_bytes = await file.read()
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Excel file: {e}")

    # Save original file
    saved_path, original_name = _save_uploaded_file(file_bytes, file.filename or "cost_model.xlsx")

    # Find P&L sheet
    pl_sheet = None
    for s in xl.sheet_names:
        if s.lower() in ("p&l sheet", "p&l", "pnl", "profit", "损益"):
            pl_sheet = s
            break

    if not pl_sheet:
        raise HTTPException(status_code=400, detail="Cannot find P&L sheet in Excel")

    df = pd.read_excel(xl, pl_sheet)

    # Extract revenue and cost line items (label in col 1, year1 value in col 2)
    revenue_items = []
    cost_items = []
    section = "revenue"

    for _, row in df.iterrows():
        if len(row) < 3:
            continue
        label = row.iloc[1]
        y1 = row.iloc[2]
        if pd.isna(label) or not isinstance(label, str):
            continue
        label_str = str(label).strip()
        if len(label_str) < 3:
            continue

        # Section detection
        upper = label_str.upper()
        if "DIRECT COST" in upper or "TOTAL COSTS" in upper:
            section = "cost"
        if "TOTAL REV" in upper:
            section = "revenue"

        # Try to convert y1 to number
        try:
            y1_num = float(y1) if pd.notna(y1) else None
        except (ValueError, TypeError):
            y1_num = None

        if y1_num is None:
            continue

        item = {"label": label_str, "y1_value": y1_num}
        if section == "revenue":
            revenue_items.append(item)
        else:
            cost_items.append(item)

    if not revenue_items and not cost_items:
        raise HTTPException(status_code=400, detail="No valid P&L data extracted")

    # Build content
    title = f"{client_name or '未命名'} - 成本模型"
    if project_name:
        title = f"{client_name} - {project_name} - 成本模型" if client_name else f"{project_name} - 成本模型"

    lines = [
        f"客户：{client_name}" if client_name else "",
        f"项目：{project_name}" if project_name else "",
        f"行业：{industry}" if industry else "",
        "",
        "## 收入项 (Year 1)",
    ]
    total_rev = 0
    for item in revenue_items:
        lines.append(f"- {item['label']}: ¥{item['y1_value']:,.0f}")
        total_rev += item['y1_value']

    lines.append("")
    lines.append("## 成本项 (Year 1)")
    total_cost = 0
    for item in cost_items:
        lines.append(f"- {item['label']}: ¥{item['y1_value']:,.0f}")
        total_cost += item['y1_value']

    lines.append("")
    lines.append(f"## 汇总")
    lines.append(f"- 收入总计: ¥{total_rev:,.0f}")
    lines.append(f"- 成本总计: ¥{total_cost:,.0f}")
    lines.append(f"- 毛利: ¥{total_rev - total_cost:,.0f}")
    if total_rev > 0:
        margin = (total_rev - total_cost) / total_rev * 100
        lines.append(f"- 毛利率: {margin:.1f}%")

    content = "\n".join(l for l in lines if l != "" or True)

    metadata = {
        "客户": client_name,
        "项目": project_name,
        "行业": industry,
        "年度收入": total_rev,
        "年度成本": total_cost,
        "毛利": total_rev - total_cost,
        "收入项数": len(revenue_items),
        "成本项数": len(cost_items),
    }

    tags = ["成本模型", "P&L"]
    if client_name:
        tags.append(client_name)
    if industry:
        tags.append(industry)

    entry = KnowledgeEntry(
        category="cost_model",
        title=title,
        content=content,
        tags=tags,
        metadata_=metadata,
        file_path=saved_path,
        file_name=original_name,
    )
    db.add(entry)
    await db.flush()

    # Index in vector DB
    try:
        ks = get_knowledge_service()
        await ks.index_documents(COLLECTION_NAME, [{
            "id": str(entry.id),
            "content": f"{entry.title}\n\n{entry.content}",
            "category": entry.category,
            "tags": entry.tags,
            "metadata": {"title": entry.title},
        }])
    except Exception:
        pass

    return {
        "imported": 1,
        "id": str(entry.id),
        "title": entry.title,
        "summary": {
            "revenue_items": len(revenue_items),
            "cost_items": len(cost_items),
            "total_revenue": total_rev,
            "total_cost": total_cost,
        }
    }


@router.post("/upload-logistics-case")
async def upload_logistics_case(
    file: UploadFile = File(...),
    title: str = Query("", description="Case title"),
    client_name: str = Query("", description="Client name"),
    industry: str = Query("", description="Industry"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload a logistics case document (PDF/Word/TXT/MD) and add to knowledge base.
    
    Extracts text content and stores as logistics_case entry.
    For long documents, the full text is preserved (used for RAG retrieval).
    """
    from app.services.document_service import extract_text_from_file

    file_bytes = await file.read()
    filename = file.filename or "case.pdf"

    try:
        text = await extract_text_from_file(file_bytes, filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {e}")

    if not text or len(text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Document is empty or too short")

    # Save original file
    saved_path, original_name = _save_uploaded_file(file_bytes, filename)

    # Limit content to 50K chars for storage (still enough for RAG)
    content = text[:50000]
    if len(text) > 50000:
        content += f"\n\n[文档已截断，原文共 {len(text)} 字符]"

    auto_title = title or f"{client_name or '未命名'} - {filename}"

    metadata = {
        "客户": client_name,
        "行业": industry,
        "原始文件名": filename,
        "文档字数": len(text),
    }

    tags = ["物流案例"]
    if client_name:
        tags.append(client_name)
    if industry:
        tags.append(industry)

    entry = KnowledgeEntry(
        category="logistics_case",
        title=auto_title,
        content=content,
        tags=tags,
        metadata_=metadata,
        file_path=saved_path,
        file_name=original_name,
    )
    db.add(entry)
    await db.flush()

    # Index in vector DB
    try:
        ks = get_knowledge_service()
        await ks.index_documents(COLLECTION_NAME, [{
            "id": str(entry.id),
            "content": f"{entry.title}\n\n{entry.content}",
            "category": entry.category,
            "tags": entry.tags,
            "metadata": {"title": entry.title},
        }])
    except Exception:
        pass

    return {
        "imported": 1,
        "id": str(entry.id),
        "title": entry.title,
        "char_count": len(text),
    }
