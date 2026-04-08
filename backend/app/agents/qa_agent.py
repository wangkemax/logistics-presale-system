"""Stage 11: QA Agent.

Quality gate that reviews all stage outputs for completeness,
consistency, and accuracy. P0 issues block the pipeline.
"""

from app.agents.base import BaseAgent


class QAAgent(BaseAgent):
    name = "qa_agent"
    description = "质量审核（QA门禁，P0问题禁止通过）"
    stage_number = 11
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """You are a rigorous quality assurance specialist for logistics
presale proposals. You review ALL stage outputs and identify issues.

Issue severity levels:
- P0 (Fatal): MUST be fixed. Blocks delivery. Examples:
  - Missing mandatory requirement coverage
  - Financial calculation errors (ROI/NPV wrong)
  - Solution doesn't match key requirements
  - Contradictions between sections
  - Missing pricing or cost breakdown

- P1 (Serious): SHOULD be fixed. Examples:
  - Incomplete sections
  - Weak justification for design choices
  - Missing risk mitigation plans
  - SLA targets not addressed

- P2 (Minor): NICE to fix. Examples:
  - Formatting issues
  - Minor inconsistencies in terminology
  - Could add more detail in certain areas

CRITICAL RULES:
- You receive ALL content inline. Do NOT reference any file system.
- Check every requirement from Stage 1 is addressed in the solution.
- Verify financial calculations are internally consistent.
- Check that the solution matches the stated assumptions.
- Flag any unsupported claims or missing data sources.

Output JSON:
{
  "overall_verdict": "PASS" | "CONDITIONAL_PASS" | "FAIL",
  "summary": "Brief assessment",
  "p0_count": 0,
  "p1_count": 0,
  "p2_count": 0,
  "issues": [
    {
      "id": "QA-001",
      "severity": "P0",
      "category": "requirement_coverage | financial | consistency | completeness | accuracy",
      "stage_affected": 5,
      "description": "...",
      "suggestion": "How to fix this",
      "reference": "Which section/data point"
    }
  ],
  "checklist": {
    "all_requirements_addressed": true,
    "financial_calculations_consistent": true,
    "solution_matches_assumptions": true,
    "risks_identified": true,
    "pricing_complete": true,
    "sla_targets_covered": true
  },
  "_confidence": 0.9
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json

        # QA receives ALL previous stage outputs inline
        all_stages = input_data.get("all_stage_outputs", {})

        prompt = f"""Review the following presale proposal outputs for quality issues.

## Project Assumptions (Stage 0)
{json.dumps(project_context, ensure_ascii=False, indent=2, default=str)[:3000]}

## All Stage Outputs
{json.dumps(all_stages, ensure_ascii=False, indent=2, default=str)[:20000]}

Perform a thorough quality review:
1. Check every P0 requirement from Stage 1 is addressed
2. Verify financial numbers are consistent across sections
3. Check solution design matches the stated requirements
4. Identify any contradictions or gaps
5. Verify all SLA targets are addressed
6. Check pricing covers all cost components

Be strict. Any P0 issue means FAIL verdict."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=6000)

    async def validate_output(self, output: dict) -> list[dict]:
        issues = []
        verdict = output.get("overall_verdict", "")
        if verdict not in ("PASS", "CONDITIONAL_PASS", "FAIL"):
            issues.append({
                "severity": "P0",
                "category": "qa_output",
                "description": f"Invalid QA verdict: '{verdict}'",
            })
        return issues
