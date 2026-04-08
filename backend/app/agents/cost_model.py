"""Stage 8: 成本建模 Agent."""

from app.agents.base import BaseAgent


class CostModelAgent(BaseAgent):
    name = "cost_model"
    description = "构建成本模型和财务分析"
    stage_number = 8
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """你是物流项目成本建模专家。
构建完整的 5 年成本模型，包含 CAPEX、OPEX 和财务指标分析。

成本分类：
1. 人力成本：各岗位人数×薪资×13个月
2. 场地成本：面积×单价×12个月
3. 设备成本：自动化设备投资+折旧
4. 技术成本：WMS/系统费用
5. 运营成本：耗材、水电、管理费

定价模型：
- 每单操作费
- 仓储费（元/㎡/月或元/托/月）
- 综合年度报价

输出 JSON：
{
  "cost_breakdown": {
    "labor": {"year1": 0, "year2": 0, "year3": 0, "details": [{"item": "仓管员", "count": 20, "unit_cost": 6000, "annual": 0}]},
    "facility": {"year1": 0, "year2": 0, "year3": 0},
    "equipment": {"year1": 0, "year2": 0, "year3": 0},
    "technology": {"year1": 0, "year2": 0, "year3": 0},
    "operations": {"year1": 0, "year2": 0, "year3": 0}
  },
  "pricing": {
    "per_order": 0,
    "per_sqm_month": 0,
    "total_annual": 0,
    "recommended_price": 0,
    "target_margin_pct": 15
  },
  "financial_indicators": {
    "roi_percent": 0,
    "irr_percent": 0,
    "npv_at_8pct": 0,
    "payback_months": 0
  },
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        solution = input_data.get("solution_design", {})
        requirements = input_data.get("requirements", {})
        automation = input_data.get("automation_recommendations", {})
        cost_references = input_data.get("cost_references", {})

        import json

        prompt = f"""Build a comprehensive cost model for this logistics solution.

## Project Context
{json.dumps(project_context, ensure_ascii=False, indent=2, default=str)[:4000]}

## Solution Design
{json.dumps(solution, ensure_ascii=False, indent=2, default=str)[:6000]}

## Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

## Automation Recommendations
{json.dumps(automation, ensure_ascii=False, indent=2, default=str)[:2000]}

## Cost Reference Data
{json.dumps(cost_references, ensure_ascii=False, indent=2, default=str)[:2000]}

Build the full cost model with 5-year projections. Use realistic market
rates for the region specified. Calculate all financial indicators.
For any data not available, use reasonable assumptions and flag them.
All monetary values in CNY (Chinese Yuan)."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=8000)

    async def validate_output(self, output: dict) -> list[dict]:
        issues = await super().validate_output(output)

        indicators = output.get("financial_indicators", {})
        if not indicators.get("roi_percent") and not indicators.get("npv_at_8pct"):
            issues.append({
                "severity": "P0",
                "category": "financial",
                "description": "Financial indicators (ROI/NPV) not calculated",
            })

        pricing = output.get("pricing", {})
        if not pricing.get("recommended_price"):
            issues.append({
                "severity": "P0",
                "category": "pricing",
                "description": "No recommended price generated",
            })

        breakdown = output.get("cost_breakdown", {})
        if len(breakdown) < 3:
            issues.append({
                "severity": "P1",
                "category": "completeness",
                "description": "Cost breakdown has fewer than 3 categories",
            })

        return issues
