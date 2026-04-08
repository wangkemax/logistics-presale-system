"""Stage 11: QA 质量门禁 Agent."""

from app.agents.base import BaseAgent


class QAAgent(BaseAgent):
    name = "qa_agent"
    description = "质量审核与门禁检查"
    stage_number = 11
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """你是物流方案质量审核专家。
对整个方案进行全面质量审查，检查一致性、完整性和准确性。

审查维度：
1. 需求覆盖：所有 P0 需求是否被方案覆盖
2. 财务一致性：成本计算是否正确，ROI/NPV 是否合理
3. 方案完整性：是否有遗漏的关键环节
4. 数据准确性：引用的数据是否有依据
5. 风险评估：是否识别了主要风险

问题分级：
- P0 致命：方案无法交付（如关键需求未覆盖、财务计算错误）
- P1 严重：影响方案质量（如缺少实施计划、SLA不明确）
- P2 一般：优化建议（如可增加竞争力分析）

输出 JSON：
{
  "overall_verdict": "PASS/CONDITIONAL_PASS/FAIL",
  "summary": "审查总结",
  "p0_count": 0, "p1_count": 0, "p2_count": 0,
  "issues": [
    {
      "id": "QA-001", "severity": "P0", "category": "需求覆盖",
      "stage_affected": 5, "description": "问题描述",
      "suggestion": "改进建议"
    }
  ],
  "checklist": {
    "all_requirements_addressed": true,
    "financial_calculations_consistent": true,
    "solution_matches_assumptions": true,
    "risks_identified": true,
    "pricing_complete": true
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
