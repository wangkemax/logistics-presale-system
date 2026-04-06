"""Document generation API routes (Word tender + PPT)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import io

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, TenderDocument
from app.services.tender_docx import generate_tender_docx
from app.services.ppt_generator import generate_solution_pptx
from app.services.storage_service import get_storage_service

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])


class GenerateRequest(BaseModel):
    doc_type: str  # "tender" or "ppt"


@router.post("/generate")
async def generate_document(
    project_id: UUID,
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate a tender Word document or solution PPT from pipeline outputs."""
    # Load project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Load all completed stage outputs
    result = await db.execute(
        select(ProjectStage).where(
            ProjectStage.project_id == project_id,
            ProjectStage.status == "completed",
        )
    )
    completed_stages = result.scalars().all()

    if len(completed_stages) < 5:
        raise HTTPException(
            status_code=400,
            detail=f"At least 5 completed stages required, found {len(completed_stages)}",
        )

    # Build stage outputs dict
    stage_outputs: dict[int, dict] = {}
    for stage in completed_stages:
        if stage.output_data:
            stage_outputs[stage.stage_number] = stage.output_data

    project_info = {
        "name": project.name,
        "client_name": project.client_name or "",
        "industry": project.industry or "",
    }

    # Generate document
    if request.doc_type == "tender":
        file_bytes = await generate_tender_docx(stage_outputs, project_info)
        filename = f"{project.name}_投标文件.docx"
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif request.doc_type == "ppt":
        file_bytes = await generate_solution_pptx(stage_outputs, project_info)
        filename = f"{project.name}_方案汇报.pptx"
        content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        raise HTTPException(status_code=400, detail="doc_type must be 'tender' or 'ppt'")

    # Save record to DB
    storage = get_storage_service()
    try:
        key = storage.generate_key(str(project_id), filename, category="output")
        file_url = await storage.upload_file(file_bytes, key, content_type)
    except Exception:
        file_url = f"/generated/{filename}"

    doc_record = TenderDocument(
        project_id=project_id,
        doc_type=request.doc_type,
        file_url=file_url,
        file_name=filename,
    )
    db.add(doc_record)
    await db.flush()

    # Return file directly
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("")
async def list_documents(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all generated documents for a project."""
    result = await db.execute(
        select(TenderDocument)
        .where(TenderDocument.project_id == project_id)
        .order_by(TenderDocument.generated_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "file_url": d.file_url,
            "version": d.version,
            "generated_at": d.generated_at.isoformat() if d.generated_at else None,
        }
        for d in docs
    ]
