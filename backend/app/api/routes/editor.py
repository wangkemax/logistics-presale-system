"""Tender editing API — AI-powered chapter rewriting and refinement."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.llm import get_llm_client
from app.models.models import ProjectStage

router = APIRouter(prefix="/projects/{project_id}/editor", tags=["editor"])


class RewriteRequest(BaseModel):
    chapter_title: str
    original_content: str
    instruction: str = "改写得更专业、更有说服力"
    style: str = "professional"  # professional / concise / detailed / persuasive
    language: str = "zh"


class RewriteResponse(BaseModel):
    rewritten_content: str
    changes_summary: str
    word_count: int


class ExpandRequest(BaseModel):
    section_title: str
    brief_content: str
    target_words: int = 500
    context: str = ""


class PolishRequest(BaseModel):
    content: str
    focus: str = "all"  # all / grammar / flow / data / persuasion


STYLE_PROMPTS = {
    "professional": "使用专业的商务语言，措辞精准，数据翔实，结构清晰。适合正式投标文件。",
    "concise": "精简扼要，去除冗余，每句话都传递关键信息。适合高管摘要。",
    "detailed": "详细展开，补充背景说明和具体方案细节。适合技术方案章节。",
    "persuasive": "突出优势和差异化，使用有说服力的论证。适合商务报价和公司介绍。",
}


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_chapter(
    project_id: UUID,
    request: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """AI-powered chapter rewriting with style control."""
    llm = get_llm_client()

    style_desc = STYLE_PROMPTS.get(request.style, STYLE_PROMPTS["professional"])

    system = f"""你是一位资深的物流行业投标文件撰写专家。
你的任务是改写标书章节内容，使其更加专业和有竞争力。

写作风格要求：{style_desc}

规则：
1. 保留原文的核心数据和事实
2. 改善表达方式和结构
3. 补充必要的过渡语句
4. 确保术语使用准确
5. 使用{"中文" if request.language == "zh" else "English"}
6. 不要编造数据"""

    prompt = f"""请改写以下标书章节。

## 章节标题
{request.chapter_title}

## 原始内容
{request.original_content}

## 改写要求
{request.instruction}

请直接输出改写后的内容，不需要额外说明。改写完后，在最后一行用 "---CHANGES---" 分隔，
然后用一句话总结你做了哪些改动。"""

    result = await llm.generate(system, prompt, max_tokens=4000, temperature=0.4)

    parts = result.split("---CHANGES---")
    rewritten = parts[0].strip()
    changes = parts[1].strip() if len(parts) > 1 else "内容已改写优化"

    return RewriteResponse(
        rewritten_content=rewritten,
        changes_summary=changes,
        word_count=len(rewritten),
    )


@router.post("/expand")
async def expand_section(
    project_id: UUID,
    request: ExpandRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Expand a brief section into detailed content."""
    llm = get_llm_client()

    system = """你是物流行业投标文件撰写专家。根据简短的要点，
扩展成详细、专业的标书内容。使用具体数据和案例支撑论点。"""

    prompt = f"""请将以下简要内容扩展为约 {request.target_words} 字的详细章节。

## 章节标题
{request.section_title}

## 简要内容
{request.brief_content}

## 上下文
{request.context or "无额外上下文"}

请直接输出扩展后的内容。"""

    result = await llm.generate(system, prompt, max_tokens=4000, temperature=0.5)

    return {
        "expanded_content": result.strip(),
        "word_count": len(result.strip()),
    }


@router.post("/polish")
async def polish_content(
    project_id: UUID,
    request: PolishRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Polish and refine existing content — fix grammar, improve flow."""
    llm = get_llm_client()

    focus_map = {
        "all": "全面优化语法、表达流畅度、数据呈现和说服力",
        "grammar": "仅修正语法和用词错误，保持原意不变",
        "flow": "改善段落间的衔接和逻辑流畅度",
        "data": "改善数据的呈现方式，使数字更有冲击力",
        "persuasion": "增强说服力，突出优势和差异化价值",
    }

    system = f"""你是标书润色专家。任务：{focus_map.get(request.focus, focus_map['all'])}。
不要改变原文含义，仅优化表达。对比标注你修改的地方。"""

    prompt = f"""请润色以下内容：

{request.content}

直接输出润色后的内容。"""

    result = await llm.generate(system, prompt, max_tokens=4000, temperature=0.3)

    return {
        "polished_content": result.strip(),
        "word_count": len(result.strip()),
    }


@router.get("/chapters")
async def get_tender_chapters(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Get all tender chapters from Stage 10 output."""
    result = await db.execute(
        select(ProjectStage).where(
            ProjectStage.project_id == project_id,
            ProjectStage.stage_number == 10,
        )
    )
    stage = result.scalar_one_or_none()

    if not stage or not stage.output_data:
        return {"chapters": [], "message": "Stage 10 (标书撰写) 未完成"}

    chapters = stage.output_data.get("document_structure", [])
    exec_summary = stage.output_data.get("executive_summary", "")

    return {
        "chapters": chapters,
        "executive_summary": exec_summary,
        "total_chapters": len(chapters),
    }
