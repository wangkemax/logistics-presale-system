"""Quotation management API routes with Excel export."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, Quotation
from app.schemas.schemas import QuotationCreate, QuotationResponse, QuotationUpdate
from app.services.quotation_excel import generate_quotation_excel

router = APIRouter(prefix="/projects/{project_id}/quotations", tags=["quotations"])


@router.post("", response_model=QuotationResponse, status_code=201)
async def create_quotation(
    project_id: UUID,
    data: QuotationCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new quotation for a project."""
    project = await _get_project(project_id, db)

    # Get next version number
    result = await db.execute(
        select(Quotation)
        .where(Quotation.project_id == project_id)
        .order_by(Quotation.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest.version + 1) if latest else 1

    quotation = Quotation(
        project_id=project_id,
        version=next_version,
        scheme_name=data.scheme_name,
        cost_breakdown=data.cost_breakdown,
    )
    db.add(quotation)
    await db.flush()
    await db.refresh(quotation)
    return quotation


@router.post("/generate-from-pipeline", response_model=QuotationResponse)
async def generate_quotation_from_pipeline(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Auto-generate a quotation from the cost model stage (stage 8) output."""
    project = await _get_project(project_id, db)

    # Get stage 8 (cost model) output
    result = await db.execute(
        select(ProjectStage).where(
            ProjectStage.project_id == project_id,
            ProjectStage.stage_number == 8,
            ProjectStage.status == "completed",
        )
    )
    cost_stage = result.scalar_one_or_none()
    if not cost_stage or not cost_stage.output_data:
        raise HTTPException(
            status_code=400,
            detail="Cost model stage (stage 8) not completed yet. Run the pipeline first.",
        )

    cost_data = cost_stage.output_data
    indicators = cost_data.get("financial_indicators", {})
    pricing = cost_data.get("pricing", {})

    # Get next version
    result = await db.execute(
        select(Quotation)
        .where(Quotation.project_id == project_id)
        .order_by(Quotation.version.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    next_version = (latest.version + 1) if latest else 1

    quotation = Quotation(
        project_id=project_id,
        version=next_version,
        scheme_name="方案A (AI 生成)",
        cost_breakdown=cost_data.get("cost_breakdown"),
        total_cost=cost_data.get("cost_summary", {}).get("annual_opex_year1"),
        total_price=pricing.get("recommended_price") or pricing.get("total_annual"),
        margin_rate=pricing.get("target_margin_pct", 15) / 100 if pricing.get("target_margin_pct") else None,
        roi=indicators.get("roi_percent"),
        irr=indicators.get("irr_percent"),
        npv=indicators.get("npv_at_8pct"),
        payback_months=indicators.get("payback_months"),
        status="draft",
    )
    db.add(quotation)
    await db.flush()
    await db.refresh(quotation)
    return quotation


@router.patch("/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    project_id: UUID,
    quotation_id: UUID,
    data: QuotationUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Update a quotation's pricing or status."""
    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.project_id == project_id,
        )
    )
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if data.cost_breakdown is not None:
        quotation.cost_breakdown = data.cost_breakdown
    if data.total_price is not None:
        quotation.total_price = data.total_price
    if data.margin_rate is not None:
        quotation.margin_rate = data.margin_rate
    if data.status is not None:
        quotation.status = data.status

    await db.flush()
    await db.refresh(quotation)
    return quotation


@router.get("/{quotation_id}/export-excel")
async def export_quotation_excel(
    project_id: UUID,
    quotation_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Export a quotation as a formatted Excel file."""
    project = await _get_project(project_id, db)

    result = await db.execute(
        select(Quotation).where(
            Quotation.id == quotation_id,
            Quotation.project_id == project_id,
        )
    )
    quotation = result.scalar_one_or_none()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    # Build data for Excel generator
    excel_data = {
        "project_name": project.name,
        "client_name": project.client_name or "",
        "scheme_name": quotation.scheme_name,
        "date": quotation.created_at.strftime("%Y-%m-%d"),
        "cost_breakdown": quotation.cost_breakdown or {},
        "financial_indicators": {
            "roi_percent": quotation.roi,
            "irr_percent": quotation.irr,
            "npv_at_8pct": quotation.npv,
            "payback_months": quotation.payback_months,
        },
        "pricing": {
            "per_order": (quotation.cost_breakdown or {}).get("pricing", {}).get("per_order"),
            "per_pallet": (quotation.cost_breakdown or {}).get("pricing", {}).get("per_pallet"),
            "per_sqm_month": (quotation.cost_breakdown or {}).get("pricing", {}).get("per_sqm_month"),
            "total_annual": quotation.total_price,
        },
    }

    excel_bytes = await generate_quotation_excel(excel_data)

    filename = f"报价单_{project.name}_{quotation.scheme_name}_v{quotation.version}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _get_project(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
