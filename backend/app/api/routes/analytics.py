"""Analytics dashboard API — project statistics, agent performance, trends."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, Quotation, QAIssue, KnowledgeEntry

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get system-wide overview statistics."""
    # Project counts by status
    result = await db.execute(
        select(Project.status, func.count(Project.id))
        .group_by(Project.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}

    # Total projects
    total_projects = sum(status_counts.values())

    # Quotation stats
    result = await db.execute(
        select(
            func.count(Quotation.id),
            func.avg(Quotation.roi),
            func.avg(Quotation.total_price),
        )
    )
    q_row = result.one()
    total_quotations = q_row[0] or 0
    avg_roi = round(float(q_row[1] or 0), 1)
    avg_price = round(float(q_row[2] or 0), 0)

    # QA stats
    result = await db.execute(
        select(QAIssue.severity, func.count(QAIssue.id))
        .group_by(QAIssue.severity)
    )
    qa_by_severity = {row[0]: row[1] for row in result.all()}

    result = await db.execute(
        select(QAIssue.status, func.count(QAIssue.id))
        .group_by(QAIssue.status)
    )
    qa_by_status = {row[0]: row[1] for row in result.all()}

    # Knowledge base size
    result = await db.execute(
        select(func.count(KnowledgeEntry.id))
        .where(KnowledgeEntry.is_active == True)
    )
    kb_count = result.scalar() or 0

    return {
        "projects": {
            "total": total_projects,
            "by_status": status_counts,
        },
        "quotations": {
            "total": total_quotations,
            "avg_roi": avg_roi,
            "avg_price": avg_price,
        },
        "qa_issues": {
            "by_severity": qa_by_severity,
            "by_status": qa_by_status,
            "total": sum(qa_by_severity.values()) if qa_by_severity else 0,
        },
        "knowledge_base": {
            "total_entries": kb_count,
        },
    }


@router.get("/agent-performance")
async def get_agent_performance(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get per-agent execution statistics."""
    result = await db.execute(
        select(
            ProjectStage.agent_name,
            ProjectStage.status,
            func.count(ProjectStage.id),
            func.avg(ProjectStage.execution_time_seconds),
            func.avg(ProjectStage.confidence),
        )
        .where(ProjectStage.agent_name != "manual")
        .group_by(ProjectStage.agent_name, ProjectStage.status)
    )

    agents: dict[str, dict] = {}
    for row in result.all():
        name, status, count, avg_time, avg_conf = row
        if name not in agents:
            agents[name] = {
                "agent_name": name,
                "total_runs": 0,
                "success": 0,
                "failed": 0,
                "avg_time_seconds": 0,
                "avg_confidence": 0,
            }
        agents[name]["total_runs"] += count
        if status == "completed":
            agents[name]["success"] = count
            agents[name]["avg_time_seconds"] = round(float(avg_time or 0), 1)
            agents[name]["avg_confidence"] = round(float(avg_conf or 0), 2)
        elif status == "failed":
            agents[name]["failed"] = count

    # Calculate success rate
    for agent in agents.values():
        total = agent["total_runs"]
        agent["success_rate"] = round(agent["success"] / total * 100, 1) if total > 0 else 0

    return {
        "agents": list(agents.values()),
    }


@router.get("/pipeline-stats")
async def get_pipeline_stats(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get pipeline execution statistics."""
    # Average stages completed per project
    result = await db.execute(
        select(
            ProjectStage.project_id,
            func.count(ProjectStage.id).filter(ProjectStage.status == "completed"),
        )
        .group_by(ProjectStage.project_id)
    )
    project_completions = result.all()

    total_pipelines = len(project_completions)
    if total_pipelines > 0:
        avg_stages = sum(row[1] for row in project_completions) / total_pipelines
        full_completions = sum(1 for row in project_completions if row[1] >= 11)
    else:
        avg_stages = 0
        full_completions = 0

    # Average total pipeline time (sum of all stage times per project)
    result = await db.execute(
        select(
            ProjectStage.project_id,
            func.sum(ProjectStage.execution_time_seconds),
        )
        .where(ProjectStage.execution_time_seconds.isnot(None))
        .group_by(ProjectStage.project_id)
    )
    time_data = result.all()
    avg_pipeline_time = (
        round(sum(float(row[1] or 0) for row in time_data) / len(time_data), 1)
        if time_data else 0
    )

    # QA pass rate
    result = await db.execute(
        select(ProjectStage.qa_result, func.count(ProjectStage.id))
        .where(
            ProjectStage.stage_number == 11,
            ProjectStage.qa_result.isnot(None),
        )
        .group_by(ProjectStage.qa_result)
    )
    qa_results = {row[0]: row[1] for row in result.all()}
    total_qa = sum(qa_results.values())
    pass_rate = round(qa_results.get("PASS", 0) / total_qa * 100, 1) if total_qa > 0 else 0

    return {
        "total_pipelines": total_pipelines,
        "full_completions": full_completions,
        "completion_rate": round(full_completions / total_pipelines * 100, 1) if total_pipelines > 0 else 0,
        "avg_stages_completed": round(avg_stages, 1),
        "avg_pipeline_time_seconds": avg_pipeline_time,
        "qa_pass_rate": pass_rate,
        "qa_results": qa_results,
    }


@router.get("/recent-activity")
async def get_recent_activity(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get recent project activity."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Recent projects
    result = await db.execute(
        select(Project)
        .where(Project.created_at >= cutoff)
        .order_by(Project.created_at.desc())
        .limit(20)
    )
    recent_projects = [
        {
            "id": str(p.id),
            "name": p.name,
            "client_name": p.client_name,
            "industry": p.industry,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in result.scalars().all()
    ]

    # Recent QA issues
    result = await db.execute(
        select(QAIssue)
        .where(QAIssue.created_at >= cutoff)
        .order_by(QAIssue.created_at.desc())
        .limit(10)
    )
    recent_issues = [
        {
            "severity": i.severity,
            "description": i.description[:100],
            "status": i.status,
            "stage_number": i.stage_number,
        }
        for i in result.scalars().all()
    ]

    return {
        "period_days": days,
        "recent_projects": recent_projects,
        "recent_qa_issues": recent_issues,
        "project_count": len(recent_projects),
    }
