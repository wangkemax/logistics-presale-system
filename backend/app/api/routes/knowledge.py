"""Knowledge base management and search API routes."""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
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
