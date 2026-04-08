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
    # Handle both English and Chinese field names from LLM
    indicators = cost_data.get("financial_indicators") or cost_data.get("财务指标") or cost_data.get("投资回报") or {}
    pricing = cost_data.get("pricing") or cost_data.get("报价") or cost_data.get("定价") or {}

    import structlog
    logger = structlog.get_logger()
    logger.info("quotation_extract", 
        indicators_keys=list(indicators.keys()) if indicators else "EMPTY",
        roi=indicators.get("roi_percent"),
        irr=indicators.get("irr_percent"),
        npv=indicators.get("npv_at_8pct"),
        pricing_keys=list(pricing.keys()) if pricing else "EMPTY",
    )

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
        total_cost=_extract_total_cost(cost_data),
        total_price=_extract_total_price(cost_data),
        margin_rate=pricing.get("target_margin_pct", 15) / 100 if pricing.get("target_margin_pct") else None,
        roi=indicators.get("roi_percent"),
        irr=indicators.get("irr_percent"),
        npv=indicators.get("npv_at_8pct") or indicators.get("npv"),
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
    from urllib.parse import quote
    encoded = quote(filename)

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


async def _get_project(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/compare-schemes")
async def generate_scheme_comparison(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate A/B/C scheme comparison from pipeline outputs."""
    from app.core.llm import get_llm_client
    from app.services.scheme_comparison import generate_multi_scheme_comparison

    project = await _get_project(project_id, db)

    # Load required stage outputs
    stages_needed = {1: "requirements", 5: "solution", 8: "cost_model"}
    stage_data = {}
    for num, label in stages_needed.items():
        result = await db.execute(
            select(ProjectStage).where(
                ProjectStage.project_id == project_id,
                ProjectStage.stage_number == num,
                ProjectStage.status == "completed",
            )
        )
        stage = result.scalar_one_or_none()
        if not stage or not stage.output_data:
            raise HTTPException(
                status_code=400,
                detail=f"Stage {num} ({label}) not completed. Run pipeline first.",
            )
        stage_data[num] = stage.output_data

    llm = get_llm_client()
    comparison = await generate_multi_scheme_comparison(
        base_solution=stage_data[5],
        base_cost=stage_data[8],
        requirements=stage_data[1],
        llm=llm,
    )

    # Create quotation records for each scheme
    for scheme_id, scheme_data in comparison.get("schemes", {}).items():
        if "error" in scheme_data:
            continue
        indicators = scheme_data.get("financial_indicators", {})
        cost = scheme_data.get("cost_summary", {})

        q = Quotation(
            project_id=project_id,
            version=1,
            scheme_name=scheme_data.get("scheme_name", f"方案{scheme_id}"),
            cost_breakdown=scheme_data,
            total_cost=cost.get("annual_opex"),
            total_price=cost.get("annual_opex"),
            roi=indicators.get("roi_percent"),
            irr=indicators.get("irr_percent"),
            npv=indicators.get("npv_at_8pct"),
            payback_months=indicators.get("payback_months"),
            status="draft",
        )
        db.add(q)

    await db.flush()
    return comparison


def _extract_total_price(cost_data: dict) -> float | None:
    """Extract total price from cost model output, trying multiple field paths."""
    import structlog
    logger = structlog.get_logger()

    pricing = cost_data.get("pricing") or cost_data.get("报价") or cost_data.get("定价") or {}

    # Try common field names the LLM might use (English + Chinese)
    for key in [
        "recommended_price", "total_annual", "total_price",
        "annual_price", "total_annual_price", "quoted_price",
        "annual_revenue", "total_revenue", "annual_total_price",
        "total", "total_cost", "annual_cost",
        "推荐报价", "年度总价", "总报价", "年报价", "总价",
    ]:
        val = pricing.get(key)
        if val and isinstance(val, (int, float)) and val > 0:
            logger.info("price_found", source="pricing", key=key, value=val)
            return float(val)

    # Try per_order * volume calculation
    per_order = pricing.get("per_order") or pricing.get("per_order_price") or pricing.get("unit_price")
    if per_order and isinstance(per_order, (int, float)):
        daily_volume = pricing.get("daily_volume", 5000)
        result = float(per_order) * daily_volume * 260
        logger.info("price_calculated", source="per_order", per_order=per_order, daily_volume=daily_volume, result=result)
        return result

    # Try cost_summary
    cost_summary = cost_data.get("cost_summary") or cost_data.get("成本汇总") or cost_data.get("费用汇总") or {}
    for key in ["total_annual", "annual_total", "year1_total", "total_cost_year1", "total", "annual_opex_year1",
                "年度总成本", "第一年总成本", "年度运营成本", "总计"]:
        val = cost_summary.get(key)
        if val and isinstance(val, (int, float)) and val > 0:
            logger.info("price_from_cost", source="cost_summary", key=key, value=val)
            return float(val) * 1.15  # Add 15% margin

    # Try summing cost_breakdown year1 values
    breakdown = cost_data.get("cost_breakdown") or cost_data.get("成本分解") or cost_data.get("费用明细") or {}
    year1_total = 0
    for cat_name, cat_data in breakdown.items():
        if isinstance(cat_data, dict):
            for k in ["year1", "annual", "total", "amount"]:
                y1 = cat_data.get(k, 0) or 0
                if isinstance(y1, (int, float)) and y1 > 0:
                    year1_total += y1
                    break
        elif isinstance(cat_data, (int, float)) and cat_data > 0:
            year1_total += cat_data
    if year1_total > 0:
        logger.info("price_from_breakdown", source="cost_breakdown_sum", value=year1_total)
        return float(year1_total) * 1.15

    # Deep search: find ANY numeric value > 10000 in the entire cost_data
    def _find_large_number(obj, path=""):
        if isinstance(obj, (int, float)) and obj > 10000:
            return obj, path
        if isinstance(obj, dict):
            for k, v in obj.items():
                result = _find_large_number(v, f"{path}.{k}")
                if result:
                    return result
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                result = _find_large_number(v, f"{path}[{i}]")
                if result:
                    return result
        return None

    found = _find_large_number(cost_data)
    if found:
        val, path = found
        logger.info("price_deep_search", source="deep_search", path=path, value=val)
        return float(val)

    logger.warning("price_not_found", cost_data_keys=list(cost_data.keys()))
    return None


def _extract_total_cost(cost_data: dict) -> float | None:
    """Extract total cost from cost model output."""
    cost_summary = cost_data.get("cost_summary") or cost_data.get("成本汇总") or cost_data.get("费用汇总") or {}
    for key in ["annual_opex_year1", "total_annual", "year1_total", "annual_opex", "total", "annual_total",
                "年度运营成本", "第一年总成本", "总成本", "年度总成本"]:
        val = cost_summary.get(key)
        if val and isinstance(val, (int, float)) and val > 0:
            return float(val)

    # Sum breakdown
    breakdown = cost_data.get("cost_breakdown") or cost_data.get("成本分解") or cost_data.get("费用明细") or {}
    total = 0
    for cat_data in breakdown.values():
        if isinstance(cat_data, dict):
            for k in ["year1", "annual", "total", "amount"]:
                y1 = cat_data.get(k, 0) or 0
                if isinstance(y1, (int, float)) and y1 > 0:
                    total += y1
                    break
        elif isinstance(cat_data, (int, float)) and cat_data > 0:
            total += cat_data
    return float(total) if total > 0 else None
