"""Batch operations API for managing multiple projects at once."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, Quotation

router = APIRouter(prefix="/batch", tags=["batch"])


class BatchArchiveRequest(BaseModel):
    project_ids: list[str]


class BatchDeleteStagesRequest(BaseModel):
    project_id: str
    stage_numbers: list[int]


class BatchStatusResponse(BaseModel):
    total: int
    succeeded: int
    failed: int
    details: list[dict]


@router.post("/archive", response_model=BatchStatusResponse)
async def batch_archive(
    request: BatchArchiveRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Archive multiple projects at once."""
    results = []
    succeeded = 0

    for pid in request.project_ids:
        try:
            result = await db.execute(
                select(Project).where(Project.id == UUID(pid))
            )
            project = result.scalar_one_or_none()
            if project:
                project.status = "archived"
                succeeded += 1
                results.append({"id": pid, "status": "archived"})
            else:
                results.append({"id": pid, "status": "not_found"})
        except Exception as e:
            results.append({"id": pid, "status": f"error: {str(e)}"})

    await db.flush()

    return BatchStatusResponse(
        total=len(request.project_ids),
        succeeded=succeeded,
        failed=len(request.project_ids) - succeeded,
        details=results,
    )


@router.post("/reset-stages")
async def batch_reset_stages(
    request: BatchDeleteStagesRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Reset specific stages of a project back to 'pending' so they can be re-run."""
    project_id = UUID(request.project_id)

    reset_count = 0
    for stage_num in request.stage_numbers:
        result = await db.execute(
            select(ProjectStage).where(
                ProjectStage.project_id == project_id,
                ProjectStage.stage_number == stage_num,
            )
        )
        stage = result.scalar_one_or_none()
        if stage:
            stage.status = "pending"
            stage.output_data = None
            stage.qa_result = None
            stage.error_message = None
            stage.confidence = None
            stage.execution_time_seconds = None
            stage.started_at = None
            stage.completed_at = None
            reset_count += 1

    await db.flush()

    return {
        "message": f"Reset {reset_count} stage(s) to pending",
        "project_id": str(project_id),
        "stages_reset": request.stage_numbers,
    }


class BatchProjectStats(BaseModel):
    total_projects: int
    by_status: dict
    total_stages_completed: int
    total_quotations: int
    avg_pipeline_time_seconds: float | None


@router.get("/stats", response_model=BatchProjectStats)
async def get_global_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get global statistics across all projects."""
    from sqlalchemy import func

    # Project counts by status
    result = await db.execute(
        select(Project.status, func.count(Project.id))
        .where(Project.created_by == user["user_id"])
        .group_by(Project.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}
    total = sum(status_counts.values())

    # Completed stages
    result = await db.execute(
        select(func.count(ProjectStage.id))
        .where(ProjectStage.status == "completed")
    )
    completed_stages = result.scalar() or 0

    # Quotations
    result = await db.execute(select(func.count(Quotation.id)))
    total_quotations = result.scalar() or 0

    # Avg pipeline time
    result = await db.execute(
        select(func.avg(ProjectStage.execution_time_seconds))
        .where(ProjectStage.status == "completed")
    )
    avg_time = result.scalar()

    return BatchProjectStats(
        total_projects=total,
        by_status=status_counts,
        total_stages_completed=completed_stages,
        total_quotations=total_quotations,
        avg_pipeline_time_seconds=round(avg_time, 2) if avg_time else None,
    )
