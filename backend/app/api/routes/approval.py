"""Quotation approval workflow.

Flow: consultant creates draft → submits for review → manager approves/rejects → client delivery
"""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Quotation, Project

router = APIRouter(prefix="/projects/{project_id}/quotations", tags=["approval"])


class SubmitForReviewRequest(BaseModel):
    notes: str = ""


class ApprovalDecision(BaseModel):
    decision: str  # "approved" | "rejected" | "revision_needed"
    comments: str = ""
    adjusted_price: float | None = None


class ApprovalHistoryEntry(BaseModel):
    action: str
    by_role: str
    timestamp: str
    comments: str


@router.post("/{quotation_id}/submit")
async def submit_for_review(
    project_id: UUID,
    quotation_id: UUID,
    request: SubmitForReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Consultant submits a quotation for manager review."""
    quotation = await _get_quotation(project_id, quotation_id, db)

    if quotation.status not in ("draft", "revision_needed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit quotation in '{quotation.status}' status",
        )

    quotation.status = "submitted"

    # Store approval history in cost_breakdown metadata
    history = _get_history(quotation)
    history.append({
        "action": "submitted",
        "by_role": user.get("role", "consultant"),
        "by_user": user.get("user_id", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comments": request.notes,
    })
    _set_history(quotation, history)

    await db.flush()
    return {"message": "Quotation submitted for review", "status": "submitted"}


@router.post("/{quotation_id}/approve")
async def approve_quotation(
    project_id: UUID,
    quotation_id: UUID,
    decision: ApprovalDecision,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Manager approves, rejects, or requests revision of a quotation."""
    if user.get("role") not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Only managers can approve quotations")

    quotation = await _get_quotation(project_id, quotation_id, db)

    if quotation.status != "submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve quotation in '{quotation.status}' status (must be 'submitted')",
        )

    if decision.decision not in ("approved", "rejected", "revision_needed"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    quotation.status = decision.decision

    if decision.adjusted_price is not None:
        quotation.total_price = decision.adjusted_price

    history = _get_history(quotation)
    history.append({
        "action": decision.decision,
        "by_role": user.get("role", "manager"),
        "by_user": user.get("user_id", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comments": decision.comments,
    })
    _set_history(quotation, history)

    await db.flush()
    return {
        "message": f"Quotation {decision.decision}",
        "status": decision.decision,
    }


@router.post("/{quotation_id}/send-to-client")
async def send_to_client(
    project_id: UUID,
    quotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Mark an approved quotation as sent to client."""
    quotation = await _get_quotation(project_id, quotation_id, db)

    if quotation.status != "approved":
        raise HTTPException(
            status_code=400,
            detail="Only approved quotations can be sent to client",
        )

    quotation.status = "sent_to_client"

    history = _get_history(quotation)
    history.append({
        "action": "sent_to_client",
        "by_role": user.get("role"),
        "by_user": user.get("user_id", ""),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "comments": "",
    })
    _set_history(quotation, history)

    await db.flush()
    return {"message": "Quotation sent to client", "status": "sent_to_client"}


@router.get("/{quotation_id}/history")
async def get_approval_history(
    project_id: UUID,
    quotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get the approval history of a quotation."""
    quotation = await _get_quotation(project_id, quotation_id, db)
    return {
        "quotation_id": str(quotation_id),
        "current_status": quotation.status,
        "history": _get_history(quotation),
    }


# ── Helpers ──

async def _get_quotation(project_id: UUID, quotation_id: UUID, db: AsyncSession) -> Quotation:
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.project_id == project_id,
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    return q


def _get_history(quotation: Quotation) -> list[dict]:
    breakdown = quotation.cost_breakdown or {}
    return breakdown.get("_approval_history", [])


def _set_history(quotation: Quotation, history: list[dict]):
    breakdown = quotation.cost_breakdown or {}
    breakdown["_approval_history"] = history
    quotation.cost_breakdown = breakdown
