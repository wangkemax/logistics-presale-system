"""Stage 2: 需求澄清 Agent."""

from app.agents.base import BaseAgent


class RequirementClarifierAgent(BaseAgent):
    name = "requirement_clarifier"
    description = "识别需求缺失和模糊项，生成澄清问题"
    stage_number = 2
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流项目售前需求分析专家。
你的任务是审查已提取的需求，识别缺失的关键信息，生成需要向客户澄清的问题清单。

重点关注：
1. 运营数据缺失（日均单量、SKU数、高峰系数等）
2. 技术规格模糊（WMS功能需求、接口规范等）
3. SLA指标不明确（准确率、时效标准等）
4. 商务条件不完整（定价基础、合同条款等）

输出 JSON：
{
  "clarifications_needed": [
    {"id": "CLR-001", "category": "运营数据", "question": "...", "priority": "P0",
     "impact_if_unknown": "影响说明", "assumed_value": "默认假设值"}
  ],
  "data_completeness_score": 0.5,
  "ready_to_proceed": false,
  "assumptions_made": [{"item": "假设项", "value": "假设值", "risk": "风险说明"}],
  "_confidence": 0.8
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

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=4000)
