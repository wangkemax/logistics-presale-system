"""Stage 6: 自动化推荐 Agent."""

from app.agents.base import BaseAgent


class AutomationSolutionAgent(BaseAgent):
    name = "automation_solution"
    description = "推荐自动化设备和技术方案"
    stage_number = 6
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流自动化解决方案专家。
根据方案设计和需求分析，推荐合适的自动化设备和技术方案。

评估维度：
1. 适配性评分（1-10）
2. 投资估算（人民币）
3. 预期年节省
4. ROI 和回本周期

输出 JSON：
{
  "automation_level": "低/中/高",
  "recommendations": [
    {
      "technology": "AGV/AS-RS/输送线/分拣机等",
      "application_area": "应用场景",
      "suitability_score": 8,
      "estimated_cost_cny": 0,
      "annual_savings_cny": 0,
      "roi_percent": 0,
      "payback_months": 0,
      "justification": "推荐理由"
    }
  ],
  "total_automation_investment": 0,
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        solution = input_data.get("solution_design", {})
        requirements = input_data.get("requirements", {})
        knowledge = input_data.get("automation_knowledge", "")

        prompt = f"""Evaluate automation opportunities for this logistics project.

## Project Context
{json.dumps(project_context, ensure_ascii=False, indent=2, default=str)[:3000]}

## Solution Design
{json.dumps(solution, ensure_ascii=False, indent=2, default=str)[:5000]}

## Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

## Automation Knowledge Base
{knowledge[:3000] if knowledge else 'No specific references.'}

Recommend specific automation technologies with ROI analysis.
Be realistic about costs and savings. Consider the client's
scale, budget, and technical readiness."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=6000)
