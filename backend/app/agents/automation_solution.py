"""Stage 6: Automation Solution Agent.

Recommends automation technologies with ROI scoring
and equipment specifications.
"""

from app.agents.base import BaseAgent


class AutomationSolutionAgent(BaseAgent):
    name = "automation_solution"
    description = "自动化方案推荐（含评分、ROI）"
    stage_number = 6
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """You are an automation specialist for logistics and warehouse operations.
Evaluate and recommend automation solutions based on the project requirements
and solution design.

For each automation opportunity, provide:
- Technology recommendation (AGV, AS/RS, conveyor, pick-to-light, voice picking, AMR, etc.)
- Suitability score (1-10)
- Estimated cost
- ROI analysis
- Implementation complexity
- Vendor recommendations

Output JSON:
{
  "automation_level": "manual | semi-auto | fully-auto",
  "recommendations": [
    {
      "id": "AUTO-001",
      "technology": "...",
      "application_area": "...",
      "suitability_score": 8,
      "estimated_cost_cny": 0,
      "annual_savings_cny": 0,
      "roi_percent": 0,
      "payback_months": 0,
      "implementation_months": 0,
      "complexity": "low | medium | high",
      "justification": "...",
      "vendors": ["vendor1", "vendor2"]
    }
  ],
  "total_automation_investment": 0,
  "total_annual_savings": 0,
  "headcount_reduction": 0,
  "not_recommended": [
    {"technology": "...", "reason": "..."}
  ],
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
