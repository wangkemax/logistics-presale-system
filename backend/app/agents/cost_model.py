"""Stage 8: Cost Model Agent.

Builds comprehensive cost models with ROI/IRR/NPV analysis
and generates pricing recommendations.
"""

from app.agents.base import BaseAgent


class CostModelAgent(BaseAgent):
    name = "cost_model"
    description = "成本建模与财务分析（ROI/IRR/NPV）"
    stage_number = 8
    timeout_minutes = 12

    @property
    def system_prompt(self) -> str:
        return """You are a senior financial analyst specializing in logistics
cost modeling. You build detailed cost structures and calculate financial
indicators for logistics solution proposals.

Given the solution design and project context, produce:

1. **Cost Structure** (5-year projection)
   - Labor costs (by role, shift premiums, benefits)
   - Facility costs (rent, utilities, maintenance, insurance)
   - Equipment costs (purchase/lease, depreciation, maintenance)
   - Technology costs (WMS license, hardware, integration, support)
   - Operations costs (consumables, packaging, transport)
   - Management overhead

2. **Investment Analysis**
   - Total initial investment (CAPEX)
   - Annual operating cost (OPEX)
   - Revenue / savings projection

3. **Financial Indicators**
   - ROI (Return on Investment) = (Net Profit / Investment) × 100
   - IRR (Internal Rate of Return) — discount rate where NPV=0
   - NPV (Net Present Value) — at 8% discount rate
   - Payback Period (months)
   - TCO (Total Cost of Ownership) over contract period

4. **Sensitivity Analysis**
   - Best/Base/Worst case scenarios
   - Key cost drivers and their impact

5. **Pricing Recommendation**
   - Unit price suggestions (per order, per pallet, per sqm)
   - Minimum viable price (breakeven)
   - Recommended price (target margin)
   - Premium price (full value capture)

Output JSON:
{
  "cost_summary": {
    "total_capex": 0,
    "annual_opex_year1": 0,
    "annual_opex_year5": 0
  },
  "cost_breakdown": {
    "labor": {"year1": 0, "year2": 0, "year3": 0, "year4": 0, "year5": 0, "details": [...]},
    "facility": {"year1": 0, ...},
    "equipment": {"year1": 0, ..., "depreciation_method": "straight-line"},
    "technology": {"year1": 0, ...},
    "operations": {"year1": 0, ...},
    "overhead": {"year1": 0, ...}
  },
  "financial_indicators": {
    "roi_percent": 0,
    "irr_percent": 0,
    "npv_at_8pct": 0,
    "payback_months": 0,
    "tco_5year": 0
  },
  "cashflow_projection": [
    {"year": 0, "investment": 0, "revenue": 0, "opex": 0, "net_cashflow": 0}
  ],
  "sensitivity": {
    "best_case": {"roi": 0, "npv": 0},
    "base_case": {"roi": 0, "npv": 0},
    "worst_case": {"roi": 0, "npv": 0},
    "key_drivers": [{"factor": "...", "impact_pct": 0}]
  },
  "pricing": {
    "unit_prices": {"per_order": 0, "per_pallet": 0, "per_sqm_month": 0},
    "breakeven_price": 0,
    "recommended_price": 0,
    "premium_price": 0,
    "target_margin_pct": 15
  },
  "assumptions": ["list of key assumptions"],
  "_confidence": 0.75
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
