"""Stage quality analyzer — programmatic checks for stage outputs.

Uses heuristics (not LLM) to score each stage on multiple dimensions.
Fast, deterministic, no API costs. Complements the LLM-based QA Agent.
"""

from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Project, ProjectStage, KnowledgeEntry

router = APIRouter(prefix="/projects/{project_id}/quality", tags=["quality"])


def _get_field(obj: Any, *keys: str) -> Any:
    """Get first matching field from dict (supports Chinese + English keys)."""
    if not isinstance(obj, dict):
        return None
    for k in keys:
        if k in obj:
            return obj[k]
    return None


def _len_safe(v: Any) -> int:
    if v is None:
        return 0
    if isinstance(v, (list, dict, str)):
        return len(v)
    return 1


def _score_stage_1(data: dict) -> dict:
    """Stage 1: Requirement Extraction."""
    issues = []
    score = 100

    reqs = _get_field(data, "requirements", "需求清单") or []
    if len(reqs) == 0:
        issues.append({"severity": "P0", "msg": "未提取到任何需求"})
        score -= 50
    elif len(reqs) < 5:
        issues.append({"severity": "P1", "msg": f"仅提取到 {len(reqs)} 项需求，可能不完整"})
        score -= 15

    # Check for P0 requirements identified
    p0_reqs = [r for r in reqs if isinstance(r, dict) and r.get("priority") == "P0"]
    if len(reqs) > 5 and len(p0_reqs) == 0:
        issues.append({"severity": "P1", "msg": "未识别任何 P0 关键需求"})
        score -= 10

    # Check key metrics
    metrics = _get_field(data, "key_metrics", "关键指标") or {}
    if not metrics:
        issues.append({"severity": "P1", "msg": "缺少关键指标提取（仓库面积/订单量/SKU 数）"})
        score -= 10

    # Check missing info detection
    missing = _get_field(data, "missing_critical_info", "缺失信息") or []
    if not missing and len(reqs) > 5:
        issues.append({"severity": "P2", "msg": "未标记任何缺失信息（可能太乐观）"})
        score -= 5

    return {
        "stage": 1,
        "name": "招标解析",
        "score": max(0, score),
        "metrics": {
            "requirement_count": len(reqs),
            "p0_requirements": len(p0_reqs),
            "missing_info_items": len(missing),
        },
        "issues": issues,
    }


def _score_stage_4(data: dict) -> dict:
    """Stage 4: Knowledge Base Retrieval."""
    issues = []
    score = 100

    counts = data.get("knowledge_count", {})
    total = (counts.get("automation", 0) +
             counts.get("cost_model", 0) +
             counts.get("logistics", 0))

    if total == 0:
        issues.append({"severity": "P0", "msg": "未检索到任何知识库条目（知识库可能为空）"})
        score -= 60
    elif total < 3:
        issues.append({"severity": "P1", "msg": f"仅检索到 {total} 条相关知识，可能影响后续 Stage 质量"})
        score -= 20

    key_points = data.get("key_data_points", [])
    if not key_points:
        issues.append({"severity": "P1", "msg": "未提取关键数据点（LLM 可能未引用真实数据）"})
        score -= 15
    elif len(key_points) < 3:
        issues.append({"severity": "P2", "msg": f"仅 {len(key_points)} 个关键数据点，建议补充"})
        score -= 5

    synth = data.get("synthesized_context", "")
    if len(synth) < 100:
        issues.append({"severity": "P1", "msg": "综合分析过短（< 100 字）"})
        score -= 10

    return {
        "stage": 4,
        "name": "知识库检索",
        "score": max(0, score),
        "metrics": {
            "automation_cases": counts.get("automation", 0),
            "cost_models": counts.get("cost_model", 0),
            "logistics_cases": counts.get("logistics", 0),
            "key_data_points": len(key_points),
            "synthesis_length": len(synth),
        },
        "issues": issues,
    }


def _score_stage_5(data: dict) -> dict:
    """Stage 5: Logistics Architecture."""
    issues = []
    score = 100

    summary = _get_field(data, "executive_summary", "执行摘要")
    warehouse = _get_field(data, "warehouse_design", "仓库设计")
    staffing = _get_field(data, "staffing", "人员配置")
    perf = _get_field(data, "performance", "绩效指标")

    if not summary:
        issues.append({"severity": "P1", "msg": "缺少执行摘要"})
        score -= 10
    elif len(str(summary)) < 100:
        issues.append({"severity": "P2", "msg": "执行摘要过短"})
        score -= 5

    if not warehouse:
        issues.append({"severity": "P0", "msg": "缺少仓库设计章节"})
        score -= 30
    else:
        area = _get_field(warehouse, "total_area_sqm", "总面积平方米", "总面积")
        if not area or area == 0:
            issues.append({"severity": "P1", "msg": "仓库面积未指定"})
            score -= 15

    if not staffing:
        issues.append({"severity": "P0", "msg": "缺少人员配置"})
        score -= 25
    else:
        head = _get_field(staffing, "total_headcount", "总人数")
        if not head or head == 0:
            issues.append({"severity": "P1", "msg": "总人数未指定"})
            score -= 10

    if not perf:
        issues.append({"severity": "P1", "msg": "缺少绩效指标"})
        score -= 10

    return {
        "stage": 5,
        "name": "方案设计",
        "score": max(0, score),
        "metrics": {
            "has_summary": bool(summary),
            "has_warehouse": bool(warehouse),
            "has_staffing": bool(staffing),
            "has_performance": bool(perf),
            "warehouse_area": _get_field(warehouse or {}, "total_area_sqm", "总面积平方米") or 0,
            "headcount": _get_field(staffing or {}, "total_headcount", "总人数") or 0,
        },
        "issues": issues,
    }


def _score_stage_8(data: dict) -> dict:
    """Stage 8: Cost Model."""
    issues = []
    score = 100

    fi = _get_field(data, "financial_indicators", "财务指标")
    cost = _get_field(data, "cost_breakdown", "成本明细")
    pricing = _get_field(data, "pricing", "报价")

    if not fi:
        issues.append({"severity": "P0", "msg": "缺少财务指标"})
        score -= 30
    else:
        roi = _get_field(fi, "roi_percent", "投资回报率", "ROI")
        irr = _get_field(fi, "irr_percent", "内部收益率", "IRR")
        if roi is None:
            issues.append({"severity": "P1", "msg": "缺少 ROI"})
            score -= 10
        if irr is None:
            issues.append({"severity": "P1", "msg": "缺少 IRR"})
            score -= 10
        try:
            if roi is not None and (float(roi) > 200 or float(roi) < -50):
                issues.append({"severity": "P1", "msg": f"ROI {roi}% 看起来不合理"})
                score -= 10
        except (ValueError, TypeError):
            pass

    if not cost:
        issues.append({"severity": "P0", "msg": "缺少成本明细"})
        score -= 25

    if not pricing:
        issues.append({"severity": "P1", "msg": "缺少报价"})
        score -= 15

    return {
        "stage": 8,
        "name": "成本建模",
        "score": max(0, score),
        "metrics": {
            "has_financial_indicators": bool(fi),
            "has_cost_breakdown": bool(cost),
            "has_pricing": bool(pricing),
        },
        "issues": issues,
    }


def _score_stage_10(data: dict) -> dict:
    """Stage 10: Tender Writing."""
    issues = []
    score = 100

    chapters = data.get("document_structure") or data.get("chapters") or []
    word_count = data.get("total_word_count", 0)

    if len(chapters) == 0:
        issues.append({"severity": "P0", "msg": "未生成任何章节"})
        score -= 60
    elif len(chapters) < 8:
        issues.append({"severity": "P1", "msg": f"仅生成 {len(chapters)} 章，标准应为 10 章"})
        score -= 15

    if word_count == 0:
        # Try to compute from chapters
        word_count = sum(ch.get("word_count", 0) for ch in chapters if isinstance(ch, dict))

    if word_count < 5000:
        issues.append({"severity": "P1", "msg": f"全文仅 {word_count} 字，专业标书建议 8000+ 字"})
        score -= 15
    elif word_count < 8000:
        issues.append({"severity": "P2", "msg": f"全文 {word_count} 字，可继续丰富"})
        score -= 5

    # Check chapter balance
    if chapters:
        word_counts = [ch.get("word_count", 0) for ch in chapters if isinstance(ch, dict)]
        if word_counts:
            avg = sum(word_counts) / len(word_counts)
            min_wc = min(word_counts)
            if min_wc < avg * 0.3:
                issues.append({"severity": "P2", "msg": "章节字数严重不均（最短章节远低于平均）"})
                score -= 5

    return {
        "stage": 10,
        "name": "标书撰写",
        "score": max(0, score),
        "metrics": {
            "chapters": len(chapters),
            "total_word_count": word_count,
        },
        "issues": issues,
    }


def _check_consistency(stages: dict) -> list[dict]:
    """Cross-stage consistency checks."""
    issues = []

    s1 = stages.get(1, {})
    s5 = stages.get(5, {})
    s8 = stages.get(8, {})

    # S1 area vs S5 warehouse area
    s1_area = _get_field(_get_field(s1, "key_metrics", "关键指标") or {},
                          "warehouse_area_sqm", "仓库面积")
    s5_area = _get_field(_get_field(s5, "warehouse_design", "仓库设计") or {},
                          "total_area_sqm", "总面积平方米")

    if s1_area and s5_area:
        try:
            s1f = float(s1_area)
            s5f = float(s5_area)
            if s1f > 0 and s5f > 0:
                ratio = abs(s1f - s5f) / max(s1f, s5f)
                if ratio > 0.3:
                    issues.append({
                        "severity": "P1",
                        "type": "consistency",
                        "msg": f"仓库面积不一致: 需求 {s1f:.0f}㎡ vs 设计 {s5f:.0f}㎡",
                    })
        except (ValueError, TypeError):
            pass

    # S5 staffing vs S8 cost
    s5_head = _get_field(_get_field(s5, "staffing", "人员配置") or {},
                          "total_headcount", "总人数")
    s8_cost = _get_field(_get_field(s8, "cost_breakdown", "成本明细") or {},
                          "labor_annual", "人工年成本")

    if s5_head and s8_cost:
        try:
            head = float(s5_head)
            cost = float(s8_cost)
            if head > 0 and cost > 0:
                per_person = cost / head
                if per_person < 30000:
                    issues.append({
                        "severity": "P2",
                        "type": "consistency",
                        "msg": f"人均年成本 ¥{per_person:.0f} 偏低（< 3万）",
                    })
                elif per_person > 300000:
                    issues.append({
                        "severity": "P2",
                        "type": "consistency",
                        "msg": f"人均年成本 ¥{per_person:.0f} 偏高（> 30万）",
                    })
        except (ValueError, TypeError):
            pass

    return issues


@router.get("/analyze")
async def analyze_quality(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Run programmatic quality checks on all stage outputs."""
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.stages))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    stage_data = {s.stage_number: (s.output_data or {}) for s in project.stages}

    scorers = {
        1: _score_stage_1,
        4: _score_stage_4,
        5: _score_stage_5,
        8: _score_stage_8,
        10: _score_stage_10,
    }

    stage_scores = []
    for n, scorer in scorers.items():
        if n in stage_data:
            stage_scores.append(scorer(stage_data[n]))
        else:
            stage_scores.append({
                "stage": n,
                "name": {1: "招标解析", 4: "知识库检索", 5: "方案设计",
                         8: "成本建模", 10: "标书撰写"}[n],
                "score": 0,
                "metrics": {},
                "issues": [{"severity": "P0", "msg": "Stage 未执行"}],
            })

    consistency_issues = _check_consistency(stage_data)

    # Overall score = avg of stage scores
    valid_scores = [s["score"] for s in stage_scores if s["score"] > 0]
    overall = sum(valid_scores) / len(valid_scores) if valid_scores else 0

    # Severity counts
    all_issues = [issue for s in stage_scores for issue in s["issues"]] + consistency_issues
    p0_count = sum(1 for i in all_issues if i.get("severity") == "P0")
    p1_count = sum(1 for i in all_issues if i.get("severity") == "P1")
    p2_count = sum(1 for i in all_issues if i.get("severity") == "P2")

    # Verdict
    if p0_count > 0:
        verdict = "FAIL"
    elif p1_count > 3:
        verdict = "CONDITIONAL_PASS"
    elif overall < 70:
        verdict = "CONDITIONAL_PASS"
    else:
        verdict = "PASS"

    return {
        "project_id": str(project_id),
        "overall_score": round(overall, 1),
        "verdict": verdict,
        "summary": {
            "p0_count": p0_count,
            "p1_count": p1_count,
            "p2_count": p2_count,
            "total_issues": len(all_issues),
        },
        "stage_scores": stage_scores,
        "consistency_issues": consistency_issues,
    }
