"""Stage 9: 风险评估 Agent."""

from app.agents.base import BaseAgent


class RiskComplianceAgent(BaseAgent):
    name = "risk_compliance"
    description = "识别项目风险并制定缓解策略"
    stage_number = 9
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流项目风险管理专家。
识别项目全生命周期的风险，评估影响并制定缓解策略。

风险类别：
1. 运营风险：产能不足、质量波动、人员流动
2. 技术风险：系统故障、集成延迟、数据安全
3. 商务风险：成本超支、合同纠纷、需求变更
4. 合规风险：法规变化、认证要求、安全标准
5. 外部风险：市场波动、供应链中断、不可抗力

输出 JSON：
{
  "risk_matrix": [
    {
      "id": "RISK-001",
      "category": "运营风险",
      "description": "风险描述",
      "likelihood": "高/中/低",
      "impact": "高/中/低",
      "risk_score": 0,
      "mitigation": "缓解措施",
      "contingency": "应急预案"
    }
  ],
  "overall_risk_level": "中等",
  "top_3_risks": ["风险1", "风险2", "风险3"],
  "compliance_status": {"certifications_needed": [], "gaps": []},
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
