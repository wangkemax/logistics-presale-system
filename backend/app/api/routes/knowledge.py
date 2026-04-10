"""Knowledge base management and search API routes."""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import KnowledgeEntry
from app.services.knowledge_service import get_knowledge_service

from pydantic import BaseModel, Field

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

COLLECTION_NAME = "logistics_knowledge"


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
    return result.scalars().all()


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
    return entry


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
    user: dict = Depends(get_current_user),
):
    """Semantic search across the knowledge base."""
    ks = get_knowledge_service()

    try:
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
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Search service unavailable: {str(e)}")

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

        lines = [
            f"客户：{client_name}" if client_name else "",
            f"项目：{project_name}" if project_name else "",
            f"设备：{eq_label}",
            f"数量：{qty} 台" if not pd.isna(qty) else "",
            f"一次性投资：¥{investment:,.0f}",
            f"年运行成本：¥{running:,.0f}" if not pd.isna(running) else "",
            f"年节省：¥{savings:,.0f}" if not pd.isna(savings) else "",
            f"IRR（内部收益率）：{irr*100:.1f}%" if not pd.isna(irr) else "",
            f"NPV（净现值）：¥{npv:,.0f}" if not pd.isna(npv) else "",
            f"投资回报周期：{payback:.1f} 个月" if not pd.isna(payback) else "",
        ]
        content = "\n".join(l for l in lines if l)

        metadata = {
            "客户": client_name,
            "项目": project_name,
            "设备类型": str(eq_label),
            "投资金额": float(investment),
            "IRR": float(irr) if not pd.isna(irr) else None,
            "回本月数": float(payback) if not pd.isna(payback) else None,
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
