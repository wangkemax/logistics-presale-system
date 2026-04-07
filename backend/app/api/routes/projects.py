"""Project management and pipeline execution API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.llm import get_llm_client
from app.models.models import Project, ProjectStage, Quotation, QAIssue
from app.schemas.schemas import (
    ProjectCreate, ProjectResponse, ProjectDetail,
    StageResponse, StageExecuteRequest, QuotationResponse,
    QAIssueResponse, QAIssueResolve,
)
from app.services.document_service import extract_text_from_file
from app.agents.orchestrator import PipelineOrchestrator

router = APIRouter(prefix="/projects", tags=["projects"])


# ── Project CRUD ──

@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Create a new presale project."""
    project = Project(
        name=data.name,
        description=data.description,
        client_name=data.client_name,
        industry=data.industry,
        created_by=user["user_id"],
    )
    db.add(project)
    await db.flush()

    # Initialize pipeline stages
    orchestrator = PipelineOrchestrator(db, get_llm_client())
    await orchestrator.initialize_project(project)

    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all projects for the current user."""
    result = await db.execute(
        select(Project)
        .where(Project.created_by == user["user_id"])
        .order_by(Project.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get project detail with all stages and quotations."""
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.stages),
            selectinload(Project.quotations),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── File Upload ──

@router.post("/{project_id}/upload-tender")
async def upload_tender_files(
    project_id: UUID,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Upload one or more tender documents (PDF/Word/TXT) to a project."""
    project = await _get_project(project_id, db)

    all_texts: list[str] = []
    uploaded_files: list[dict] = []

    for file in files:
        file_bytes = await file.read()
        if len(file_bytes) > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' too large (max 50MB per file)",
            )

        # Extract text
        document_text = await extract_text_from_file(file_bytes, file.filename)
        all_texts.append(f"=== FILE: {file.filename} ===\n{document_text}")

        uploaded_files.append({
            "file_name": file.filename,
            "text_length": len(document_text),
            "pages_estimated": document_text.count("--- Page"),
        })

    # Merge all file texts
    merged_text = "\n\n".join(all_texts)

    # Store reference
    file_names = [f["file_name"] for f in uploaded_files]
    project.tender_file_url = ", ".join(file_names)

    # Store merged text in stage 1 for pipeline use
    result = await db.execute(
        select(ProjectStage).where(
            ProjectStage.project_id == project_id,
            ProjectStage.stage_number == 1,
        )
    )
    stage = result.scalar_one_or_none()
    if stage:
        stage.output_data = {
            "_uploaded_text": merged_text[:100000],
            "file_name": ", ".join(file_names),
            "file_count": len(files),
        }

    await db.flush()

    return {
        "message": f"{len(files)} file(s) uploaded successfully",
        "files": uploaded_files,
        "total_text_length": len(merged_text),
    }


# ── Pipeline Execution ──

@router.post("/{project_id}/run-pipeline")
async def run_pipeline(
    project_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Start the full 12-stage pipeline for a project."""
    project = await _get_project(project_id, db)

    if project.status == "in_progress":
        raise HTTPException(status_code=409, detail="Pipeline already running")

    # Get uploaded document text
    result = await db.execute(
        select(ProjectStage).where(
            ProjectStage.project_id == project_id,
            ProjectStage.stage_number == 1,
        )
    )
    stage1 = result.scalar_one_or_none()
    doc_text = ""
    if stage1 and stage1.output_data:
        doc_text = stage1.output_data.get("_uploaded_text", "")

    if not doc_text:
        raise HTTPException(status_code=400, detail="No tender document uploaded. Upload first.")

    project.status = "in_progress"
    await db.flush()

    # Run pipeline in background
    background_tasks.add_task(
        _execute_pipeline_bg, project_id, doc_text
    )

    return {"message": "Pipeline started", "project_id": str(project_id)}


@router.post("/{project_id}/run-stage")
async def run_single_stage(
    project_id: UUID,
    request: StageExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Run a single pipeline stage with custom input."""
    project = await _get_project(project_id, db)
    orchestrator = PipelineOrchestrator(db, get_llm_client())

    result = await orchestrator.run_single_stage(
        project, request.stage_number, request.override_input or {}
    )
    return result.model_dump()


# ── Stages ──

@router.get("/{project_id}/stages", response_model=list[StageResponse])
async def list_stages(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get all pipeline stages for a project."""
    result = await db.execute(
        select(ProjectStage)
        .where(ProjectStage.project_id == project_id)
        .order_by(ProjectStage.stage_number)
    )
    return result.scalars().all()


# ── Quotations ──

@router.get("/{project_id}/quotations", response_model=list[QuotationResponse])
async def list_quotations(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get all quotations for a project."""
    result = await db.execute(
        select(Quotation)
        .where(Quotation.project_id == project_id)
        .order_by(Quotation.version.desc())
    )
    return result.scalars().all()


# ── QA Issues ──

@router.get("/{project_id}/qa-issues", response_model=list[QAIssueResponse])
async def list_qa_issues(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get all QA issues for a project."""
    result = await db.execute(
        select(QAIssue)
        .where(QAIssue.project_id == project_id)
        .order_by(QAIssue.severity, QAIssue.created_at)
    )
    return result.scalars().all()


@router.patch("/{project_id}/qa-issues/{issue_id}", response_model=QAIssueResponse)
async def resolve_qa_issue(
    project_id: UUID,
    issue_id: UUID,
    data: QAIssueResolve,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Resolve a QA issue."""
    result = await db.execute(
        select(QAIssue).where(QAIssue.id == issue_id, QAIssue.project_id == project_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(status_code=404, detail="QA issue not found")

    issue.resolution = data.resolution
    issue.status = data.status
    await db.flush()
    await db.refresh(issue)
    return issue


# ── Helpers ──

async def _get_project(project_id: UUID, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _execute_pipeline_bg(project_id: UUID, doc_text: str):
    """Background task to execute the full pipeline."""
    from app.core.database import AsyncSessionLocal
    from app.core.llm import get_llm_client

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one()

            orchestrator = PipelineOrchestrator(db, get_llm_client())
            await orchestrator.run_full_pipeline(project, document_text=doc_text)

            await db.commit()
        except Exception as e:
            await db.rollback()
            # Update project status to failed
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.status = "failed"
                await db.commit()
            raise
