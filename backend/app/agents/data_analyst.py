"""Stage 3: 数据分析 Agent."""

from app.agents.base import BaseAgent


class DataAnalystAgent(BaseAgent):
    name = "data_analyst"
    description = "分析运营数据，提供量化洞察"
    stage_number = 3
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流运营数据分析专家。
根据招标文件中的运营数据，进行深度分析并提供量化洞察。

分析维度：
1. 订单分析：日均单量、波动规律、高峰系数、订单结构
2. SKU分析：SKU数量、ABC分类、周转率、尺寸分布
3. 容量分析：存储需求、吞吐需求、峰值容量
4. 效率基准：行业对标、改进空间、自动化潜力

输出 JSON：
{
  "order_analysis": {"daily_avg": 0, "peak_factor": 0, "order_types": {}},
  "sku_analysis": {"total_skus": 0, "abc_distribution": {}, "turnover_rate": 0},
  "capacity_analysis": {"storage_positions_needed": 0, "throughput_capacity": {}},
  "efficiency_benchmarks": {"current_vs_industry": {}, "improvement_potential": ""},
  "key_insights": ["洞察1", "洞察2"],
  "_confidence": 0.8
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

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=4000)
