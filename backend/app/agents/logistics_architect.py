"""Stage 5: 物流方案设计 Agent."""

from app.agents.base import BaseAgent


class LogisticsArchitectAgent(BaseAgent):
    name = "logistics_architect"
    description = "设计完整的物流仓储解决方案"
    stage_number = 5
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """你是资深物流方案架构师。
根据需求分析和知识库洞察，设计完整的物流仓储解决方案。

方案必须包含：
1. 执行摘要：方案亮点和核心价值
2. 仓库设计：总面积、功能分区、存储系统、动线设计
3. 运营设计：入库流程、存储策略、拣选方案、包装发运
4. 技术方案：WMS系统、自动化设备、系统集成
5. 人员配置：组织架构、岗位设置、班次安排
6. 绩效指标：准确率、时效、产能目标

输出 JSON：
{
  "executive_summary": "方案摘要...",
  "warehouse_design": {
    "total_area_sqm": 10000,
    "zones": [{"name": "收货区", "area_sqm": 500}],
    "storage_systems": [{"type": "横梁式货架", "capacity": "3600托位"}],
    "flow_design": "动线设计说明..."
  },
  "operations_design": {
    "inbound": {"strategy": "...", "capacity": "..."},
    "picking": {"strategy": "...", "methods": [], "productivity": "..."},
    "packing_shipping": {"packing_strategy": "...", "shipping_methods": []}
  },
  "technology": {
    "wms": {"system": "...", "modules": []},
    "automation": [{"type": "设备名", "description": "...", "capacity": "..."}]
  },
  "staffing": {"total_headcount": 0, "shift_model": "两班制", "by_function": {}},
  "performance": {"accuracy_target": "99.5%", "daily_throughput": 0},
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        requirements = input_data.get("requirements", {})
        knowledge = input_data.get("knowledge_context", "")
        benchmark_cases = input_data.get("benchmark_cases", [])

        prompt = f"""Design a comprehensive logistics solution for this project.

## Project Assumptions
{_fmt_dict(project_context)}

## Extracted Requirements
{_fmt_dict(requirements)}

## Relevant Knowledge & Best Practices
{knowledge[:5000] if knowledge else 'No additional knowledge available.'}

## Similar Case References
{_fmt_list(benchmark_cases) if benchmark_cases else 'No benchmark cases available.'}

Design the optimal solution following your instructions. Be specific with
numbers (areas, headcounts, throughput). Justify key design decisions."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=8000)


def _fmt_dict(d: dict) -> str:
    import json
    return json.dumps(d, ensure_ascii=False, indent=2, default=str)[:8000]


def _fmt_list(items: list) -> str:
    import json
    return json.dumps(items, ensure_ascii=False, indent=2, default=str)[:3000]
