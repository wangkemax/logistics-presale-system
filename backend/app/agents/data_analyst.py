"""Stage 3: Data Analyst Agent. Analyzes operational data."""

from app.agents.base import BaseAgent


class DataAnalystAgent(BaseAgent):
    name = "data_analyst"
    description = "分析运营数据，生成洞察"
    stage_number = 3
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """You are a logistics data analyst. Analyze the available data
to extract key operational insights that inform solution design.

Analyze: order profiles, SKU distribution, seasonal patterns,
volume forecasts, geographic distribution, and performance baselines.

Output JSON:
{
  "data_summary": {
    "data_sources": ["..."],
    "data_quality_score": 0.8,
    "time_period_analyzed": "..."
  },
  "order_analysis": {
    "daily_avg": 0, "peak_daily": 0, "peak_factor": 1.5,
    "order_type_distribution": {},
    "seasonal_pattern": "description"
  },
  "sku_analysis": {
    "total_skus": 0, "abc_distribution": {"A": 0, "B": 0, "C": 0},
    "velocity_profile": "description"
  },
  "volume_forecast": {
    "growth_rate_annual": 0.1,
    "year1": 0, "year3": 0, "year5": 0
  },
  "key_insights": ["..."],
  "recommendations": ["..."],
  "_confidence": 0.7
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        requirements = input_data.get("requirements", {})
        raw_data = input_data.get("operational_data", "")

        prompt = f"""Analyze the operational data for this logistics project.

## Requirements with Data Points
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:6000]}

## Raw Operational Data (if available)
{raw_data[:5000] if raw_data else 'No raw data. Derive insights from requirements.'}

Extract patterns and provide actionable insights for solution design."""

        return await self.call_llm_json(prompt, max_tokens=4000)
