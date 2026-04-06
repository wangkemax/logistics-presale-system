"""Stage 2: Requirement Clarifier Agent.

Identifies missing data, ambiguous requirements, and generates
clarification questions for the client.
"""

from app.agents.base import BaseAgent


class RequirementClarifierAgent(BaseAgent):
    name = "requirement_clarifier"
    description = "识别缺失数据和模糊需求，生成澄清问题"
    stage_number = 2
    timeout_minutes = 8

    @property
    def system_prompt(self) -> str:
        return """You are a logistics presale consultant reviewing extracted
requirements to identify gaps and ambiguities.

For each unclear or missing item, generate a specific clarification question.
Categorize questions by priority and provide default assumptions if the
client doesn't respond.

Output JSON:
{
  "clarifications_needed": [
    {
      "id": "CLR-001",
      "requirement_id": "REQ-xxx",
      "category": "operations | technology | commercial | compliance",
      "priority": "P0 | P1 | P2",
      "question": "The specific question to ask the client",
      "context": "Why this matters for the solution",
      "default_assumption": "What we'll assume if no answer"
    }
  ],
  "ambiguous_requirements": [
    {
      "requirement_id": "REQ-xxx",
      "issue": "description of ambiguity",
      "possible_interpretations": ["interpretation A", "interpretation B"],
      "recommended_interpretation": "A"
    }
  ],
  "data_completeness_score": 0.7,
  "ready_to_proceed": true,
  "_confidence": 0.85
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json

        requirements = input_data.get("requirements", {})
        missing_info = input_data.get("missing_critical_info", [])

        prompt = f"""Review these extracted requirements and identify all gaps.

## Project Assumptions
{json.dumps(project_context, ensure_ascii=False, indent=2, default=str)[:2000]}

## Extracted Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:8000]}

## Already Identified Missing Info
{json.dumps(missing_info, ensure_ascii=False, default=str)}

Generate clarification questions for ALL gaps. Focus on data critical
for solution design and cost modeling."""

        return await self.call_llm_json(prompt, max_tokens=4000)
