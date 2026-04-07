"""Project export and archive API."""

import json
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, Quotation, TenderDocument, QAIssue

router = APIRouter(prefix="/projects/{project_id}", tags=["projects"])


@router.get("/export")
async def export_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Export complete project data as a JSON bundle.

    Includes: project info, all stage outputs, quotations, QA issues,
    and document references. Useful for backup, migration, or analysis.
    """
    # Load everything
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stages_result = await db.execute(
        select(ProjectStage)
        .where(ProjectStage.project_id == project_id)
        .order_by(ProjectStage.stage_number)
    )
    stages = stages_result.scalars().all()

    quotations_result = await db.execute(
        select(Quotation)
        .where(Quotation.project_id == project_id)
        .order_by(Quotation.version)
    )
    quotations = quotations_result.scalars().all()

    issues_result = await db.execute(
        select(QAIssue)
        .where(QAIssue.project_id == project_id)
        .order_by(QAIssue.severity, QAIssue.created_at)
    )
    issues = issues_result.scalars().all()

    docs_result = await db.execute(
        select(TenderDocument)
        .where(TenderDocument.project_id == project_id)
    )
    docs = docs_result.scalars().all()

    # Build export bundle
    bundle = {
        "export_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "id": str(project.id),
            "name": project.name,
            "description": project.description,
            "client_name": project.client_name,
            "industry": project.industry,
            "status": project.status,
            "assumptions": project.assumptions,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        },
        "stages": [
            {
                "stage_number": s.stage_number,
                "stage_name": s.stage_name,
                "agent_name": s.agent_name,
                "status": s.status,
                "output_data": s.output_data,
                "qa_result": s.qa_result,
                "confidence": s.confidence,
                "execution_time_seconds": s.execution_time_seconds,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            }
            for s in stages
        ],
        "quotations": [
            {
                "id": str(q.id),
                "version": q.version,
                "scheme_name": q.scheme_name,
                "cost_breakdown": q.cost_breakdown,
                "total_cost": q.total_cost,
                "total_price": q.total_price,
                "roi": q.roi,
                "irr": q.irr,
                "npv": q.npv,
                "payback_months": q.payback_months,
                "status": q.status,
            }
            for q in quotations
        ],
        "qa_issues": [
            {
                "severity": i.severity,
                "category": i.category,
                "description": i.description,
                "suggestion": i.suggestion,
                "resolution": i.resolution,
                "status": i.status,
                "stage_number": i.stage_number,
            }
            for i in issues
        ],
        "documents": [
            {
                "doc_type": d.doc_type,
                "file_name": d.file_name,
                "file_url": d.file_url,
                "version": d.version,
            }
            for d in docs
        ],
        "summary": {
            "total_stages_completed": sum(1 for s in stages if s.status == "completed"),
            "total_quotations": len(quotations),
            "total_qa_issues": len(issues),
            "p0_issues_open": sum(1 for i in issues if i.severity == "P0" and i.status == "open"),
            "total_documents": len(docs),
        },
    }

    # Return as downloadable JSON
    content = json.dumps(bundle, ensure_ascii=False, indent=2, default=str)
    filename = f"{project.name}_export_{datetime.now().strftime('%Y%m%d')}.json"

    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/archive")
async def archive_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Archive a project (soft-delete, keeps all data)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "archived"
    await db.flush()

    return {"message": f"Project '{project.name}' archived", "status": "archived"}


@router.post("/duplicate")
async def duplicate_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Duplicate a project (copies settings, not stage outputs)."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Project not found")

    new_project = Project(
        name=f"{original.name} (副本)",
        description=original.description,
        client_name=original.client_name,
        industry=original.industry,
        created_by=user["user_id"],
        assumptions=original.assumptions,
    )
    db.add(new_project)
    await db.flush()

    # Initialize stages
    from app.agents.orchestrator import PipelineOrchestrator, STAGE_DEFINITIONS
    for defn in STAGE_DEFINITIONS:
        stage = ProjectStage(
            project_id=new_project.id,
            stage_number=defn["number"],
            stage_name=defn["name"],
            agent_name=defn["agent"].__name__ if defn["agent"] else "manual",
            status="pending",
        )
        db.add(stage)

    await db.flush()
    await db.refresh(new_project)

    return {
        "message": f"Project duplicated as '{new_project.name}'",
        "new_project_id": str(new_project.id),
    }
