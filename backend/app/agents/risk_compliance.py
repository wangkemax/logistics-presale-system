"""Stage 9: Risk & Compliance Agent."""

from app.agents.base import BaseAgent


class RiskComplianceAgent(BaseAgent):
    name = "risk_compliance"
    description = "风险识别与合规检查"
    stage_number = 9
    timeout_minutes = 8

    @property
    def system_prompt(self) -> str:
        return """You are a risk management and compliance specialist for logistics projects.
Identify all risks and compliance requirements.

Output JSON:
{
  "risk_matrix": [
    {
      "id": "RISK-001",
      "category": "operational | financial | technical | regulatory | market",
      "description": "...",
      "likelihood": "low | medium | high",
      "impact": "low | medium | high",
      "risk_score": 0,
      "mitigation": "...",
      "contingency": "...",
      "owner": "..."
    }
  ],
  "compliance_checklist": [
    {
      "requirement": "...",
      "regulation": "...",
      "status": "compliant | action_needed | not_applicable",
      "action": "..."
    }
  ],
  "overall_risk_level": "low | medium | high",
  "top_3_risks": ["..."],
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        solution = input_data.get("solution_design", {})
        requirements = input_data.get("requirements", {})

        prompt = f"""Identify all risks and compliance requirements.

## Project Context
{json.dumps(project_context, ensure_ascii=False, indent=2, default=str)[:2000]}

## Solution Design
{json.dumps(solution, ensure_ascii=False, indent=2, default=str)[:5000]}

## Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

Cover: operational risks, financial risks, technology risks,
regulatory compliance (fire safety, food safety if applicable,
labor laws, environmental), market risks, and implementation risks."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=5000)
