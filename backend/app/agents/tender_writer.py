"""Stage 10: Tender Writer Agent. Generates professional proposal content."""

from app.agents.base import BaseAgent


class TenderWriterAgent(BaseAgent):
    name = "tender_writer"
    description = "生成专业投标文档内容"
    stage_number = 10
    timeout_minutes = 20

    @property
    def system_prompt(self) -> str:
        return """你是一位资深的物流行业投标文件撰写专家。
根据项目分析结果，生成简洁专业的投标文档内容。

要求：
- 使用专业中文（简体）
- 每章 100-200 字，重点突出
- 引用具体数据和指标
- 输出纯 JSON，不要 markdown 代码块

输出格式：
{
  "document_structure": [
    {"chapter": 1, "title": "章节标题", "content": "章节内容..."}
  ],
  "executive_summary": "执行摘要（200字以内）",
  "key_differentiators": ["差异化优势1", "差异化优势2"],
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        all_outputs = input_data.get("all_stage_outputs", {})

        # Extract only the most critical data
        solution = all_outputs.get(5, all_outputs.get("5", {}))
        cost = all_outputs.get(8, all_outputs.get("8", {}))
        risks = all_outputs.get(9, all_outputs.get("9", {}))
        requirements = all_outputs.get(1, all_outputs.get("1", {}))

        # Build a very compact summary
        compact = {
            "requirements_count": len(requirements.get("requirements", [])),
            "solution_summary": solution.get("executive_summary", "")[:500],
            "warehouse_area": solution.get("warehouse_design", {}).get("total_area_sqm", "N/A"),
            "cost_indicators": cost.get("financial_indicators", {}),
            "pricing": cost.get("pricing", {}),
            "top_risks": risks.get("top_3_risks", []),
            "risk_level": risks.get("overall_risk_level", "N/A"),
        }

        prompt = f"""根据以下项目分析摘要，生成 5 章投标文档。

## 项目摘要
{json.dumps(compact, ensure_ascii=False, default=str)[:3000]}

## 项目背景
{json.dumps(project_context, ensure_ascii=False, default=str)[:1000]}

请生成以下 5 章：
1. 项目理解与需求分析
2. 物流解决方案设计
3. 自动化与技术方案
4. 报价与投资回报
5. 风险管理与实施计划

每章 100-200 字，直接输出 JSON。"""

        return await self.call_llm_json(prompt, max_tokens=4000)
