"""Stage 10: Tender Writer Agent.

Generates professional proposal content by writing one chapter at a time,
then merging into a complete document. This avoids LLM timeout issues
while producing full-length tender content (500-800 words per chapter).
"""

import json
import asyncio
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()

# Chapter definitions with context hints for each
CHAPTERS = [
    {
        "number": 1,
        "title": "公司介绍与资质",
        "hint": "公司概况、核心能力、物流行业经验、资质认证、服务网络",
        "data_keys": [],
    },
    {
        "number": 2,
        "title": "项目理解与需求分析",
        "hint": "客户背景、项目目标、核心需求清单、需求优先级、关键挑战",
        "data_keys": ["requirements", "clarifications"],
    },
    {
        "number": 3,
        "title": "物流解决方案设计",
        "hint": "仓储布局、功能分区、存储系统、作业流程、WMS系统、KPI指标",
        "data_keys": ["solution", "data_analysis"],
    },
    {
        "number": 4,
        "title": "自动化与技术方案",
        "hint": "自动化设备推荐、WMS/TMS系统、物联网方案、实施路线图",
        "data_keys": ["automation"],
    },
    {
        "number": 5,
        "title": "实施计划与里程碑",
        "hint": "项目阶段划分、时间节点、团队配置、验收标准、培训计划",
        "data_keys": ["solution"],
    },
    {
        "number": 6,
        "title": "团队配置与培训",
        "hint": "组织架构、岗位设置、人员编制、培训体系、考核标准",
        "data_keys": ["solution"],
    },
    {
        "number": 7,
        "title": "质量管理与SLA承诺",
        "hint": "质量管理体系、KPI指标、SLA承诺、处罚机制、持续改善",
        "data_keys": ["solution"],
    },
    {
        "number": 8,
        "title": "风险管理与应急预案",
        "hint": "风险识别、影响评估、缓解措施、应急预案、BCP计划",
        "data_keys": ["risks"],
    },
    {
        "number": 9,
        "title": "报价方案",
        "hint": "定价模型、费用明细、付款方式、优惠条件、ROI分析",
        "data_keys": ["cost_model"],
    },
    {
        "number": 10,
        "title": "成功案例参考",
        "hint": "相似项目经验、客户名称、项目规模、实施成果、客户评价",
        "data_keys": ["benchmarks"],
    },
]


class TenderWriterAgent(BaseAgent):
    name = "tender_writer"
    description = "分章节生成专业投标文档内容"
    stage_number = 10
    timeout_minutes = 30  # Allow more time for 10 sequential calls

    @property
    def system_prompt(self) -> str:
        return """你是一位资深的物流行业投标文件撰写专家。
你的任务是撰写投标文件的单个章节。

要求：
1. 使用专业中文（简体），商务正式语气
2. 内容详实，引用具体数据和指标
3. 每个章节 500-800 字
4. 结构清晰，使用小标题分段
5. 仅输出章节正文内容，不要 JSON 格式，不要章节标题"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        all_outputs = input_data.get("all_stage_outputs", {})

        # Prepare data context for each chapter
        data_map = self._build_data_map(all_outputs)
        context_str = json.dumps(project_context, ensure_ascii=False, default=str)[:800]

        # Generate chapters one by one
        chapters = []
        executive_summary_parts = []

        for ch_def in CHAPTERS:
            logger.info(
                "tender_writing_chapter",
                chapter=ch_def["number"],
                title=ch_def["title"],
            )

            try:
                content = await self._write_chapter(ch_def, data_map, context_str)
                chapters.append({
                    "chapter": ch_def["number"],
                    "title": ch_def["title"],
                    "content": content,
                    "word_count": len(content),
                })
                # Collect first sentence of each chapter for executive summary
                first_line = content.split("\n")[0].strip()[:100]
                executive_summary_parts.append(f"{ch_def['title']}：{first_line}")

            except Exception as e:
                logger.error(
                    "tender_chapter_failed",
                    chapter=ch_def["number"],
                    error=str(e),
                )
                chapters.append({
                    "chapter": ch_def["number"],
                    "title": ch_def["title"],
                    "content": f"[章节生成失败: {str(e)[:100]}]",
                    "word_count": 0,
                })

        # Generate executive summary from collected parts
        exec_summary = await self._write_executive_summary(
            executive_summary_parts, context_str
        )

        total_words = sum(ch["word_count"] for ch in chapters)

        return {
            "document_structure": chapters,
            "executive_summary": exec_summary,
            "key_differentiators": self._extract_differentiators(chapters),
            "total_word_count": total_words,
            "chapters_completed": len([c for c in chapters if c["word_count"] > 0]),
            "chapters_total": len(CHAPTERS),
            "_confidence": 0.85 if total_words > 3000 else 0.6,
        }

    async def _write_chapter(
        self, ch_def: dict, data_map: dict, context_str: str
    ) -> str:
        """Write a single chapter using LLM."""
        # Gather relevant data for this chapter
        relevant_data = {}
        for key in ch_def.get("data_keys", []):
            if key in data_map:
                relevant_data[key] = data_map[key]

        data_str = json.dumps(relevant_data, ensure_ascii=False, default=str)[:4000] if relevant_data else "无具体数据，请基于行业经验撰写"

        prompt = f"""请撰写投标文件的第 {ch_def['number']} 章：{ch_def['title']}

## 本章要点
{ch_def['hint']}

## 项目背景
{context_str}

## 相关分析数据
{data_str}

请撰写 500-800 字的完整章节内容。使用小标题分段，引用具体数据。
直接输出正文，不需要输出章节标题。"""

        # Use the base class LLM call (not JSON mode)
        return await self.call_llm(prompt, max_tokens=2000)

    async def _write_executive_summary(
        self, parts: list[str], context_str: str
    ) -> str:
        """Generate a cohesive executive summary."""
        parts_text = "\n".join(f"- {p}" for p in parts)

        prompt = f"""基于以下各章节要点，撰写一份 300-500 字的执行摘要。

## 项目背景
{context_str}

## 各章节核心要点
{parts_text}

要求：
- 突出方案亮点和核心竞争力
- 包含关键数据指标
- 表达合作诚意
直接输出摘要正文。"""

        return await self.call_llm(prompt, max_tokens=1500)

    def _build_data_map(self, all_outputs: dict) -> dict:
        """Extract and organize key data from all stage outputs."""

        def get(stage_num):
            return all_outputs.get(stage_num, all_outputs.get(str(stage_num), {}))

        reqs = get(1)
        clarifications = get(2)
        data_analysis = get(3)
        solution = get(5)
        automation = get(6)
        benchmarks = get(7)
        cost_model = get(8)
        risks = get(9)

        return {
            "requirements": {
                "count": len(reqs.get("requirements", [])),
                "top_requirements": reqs.get("requirements", [])[:10],
                "key_metrics": reqs.get("key_metrics", {}),
                "project_overview": reqs.get("project_overview", {}),
            },
            "clarifications": {
                "needs": clarifications.get("clarifications_needed", [])[:5],
                "data_completeness": clarifications.get("data_completeness_score", 0),
            },
            "data_analysis": {
                "summary": json.dumps(data_analysis, ensure_ascii=False, default=str)[:1500],
            },
            "solution": {
                "executive_summary": solution.get("executive_summary", "")[:800],
                "warehouse_design": solution.get("warehouse_design", {}),
                "operations_design": {
                    k: str(v)[:300] for k, v in solution.get("operations_design", {}).items()
                },
                "technology": solution.get("technology", {}),
                "staffing": solution.get("staffing", {}),
                "performance": solution.get("performance", {}),
            },
            "automation": {
                "level": automation.get("automation_level", ""),
                "recommendations": automation.get("recommendations", [])[:5],
            },
            "benchmarks": {
                "matched_cases": benchmarks.get("matched_cases", [])[:3],
            },
            "cost_model": {
                "pricing": cost_model.get("pricing", {}),
                "financial_indicators": cost_model.get("financial_indicators", {}),
                "cost_breakdown_summary": {
                    k: v.get("year1", 0) if isinstance(v, dict) else v
                    for k, v in cost_model.get("cost_breakdown", {}).items()
                },
            },
            "risks": {
                "overall_level": risks.get("overall_risk_level", ""),
                "top_risks": risks.get("risk_matrix", [])[:5],
                "compliance": risks.get("compliance_status", {}),
            },
        }

    def _extract_differentiators(self, chapters: list[dict]) -> list[str]:
        """Extract key differentiators from generated chapters."""
        # Simple heuristic: look for bullet points in chapters
        diffs = []
        keywords = ["优势", "领先", "独特", "核心", "差异化", "创新", "专业"]
        for ch in chapters:
            for line in ch.get("content", "").split("\n"):
                stripped = line.strip()
                if any(kw in stripped for kw in keywords) and len(stripped) > 10:
                    diffs.append(stripped[:80])
                    if len(diffs) >= 5:
                        return diffs
        if not diffs:
            diffs = ["专业物流解决方案", "丰富的行业经验", "高性价比方案"]
        return diffs
