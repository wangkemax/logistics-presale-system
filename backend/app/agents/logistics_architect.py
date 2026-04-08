"""Stage 5: Logistics Architect Agent.

Designs the logistics solution based on extracted requirements,
knowledge base insights, and industry best practices.
"""

from app.agents.base import BaseAgent


class LogisticsArchitectAgent(BaseAgent):
    name = "logistics_architect"
    description = "设计物流解决方案"
    stage_number = 5
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """You are a senior logistics solution architect with 20+ years of
experience designing warehouse operations, distribution networks, and
supply chain solutions for Fortune 500 clients.

Given the project requirements and context, design a comprehensive
logistics solution covering:

1. **Warehouse Layout Design**
   - Zone planning (receiving, storage, picking, packing, shipping, VAS, returns)
   - Storage system selection (racking types, density optimization)
   - Area allocation per zone (sqm)
   - Flow path design (goods flow, people flow, equipment flow)

2. **Operations Design**
   - Inbound process (receiving, QC, putaway)
   - Storage strategy (fixed/random/class-based, slotting)
   - Picking strategy (discrete/batch/wave/zone, pick-to-light, voice)
   - Packing and shipping process
   - Returns handling

3. **Technology Stack**
   - WMS configuration recommendations
   - Equipment and automation level
   - Integration architecture (ERP, TMS, carrier systems)
   - Data and reporting

4. **Staffing Model**
   - Headcount by function and shift
   - Skill requirements
   - Seasonal flex plan

5. **Performance Projections**
   - Throughput capacity
   - Expected accuracy rates
   - Lead time estimates

Output JSON:
{
  "solution_name": "...",
  "executive_summary": "2-3 sentence overview",
  "warehouse_design": {
    "total_area_sqm": ...,
    "zones": [...],
    "storage_systems": [...],
    "flow_design": "description"
  },
  "operations_design": {
    "inbound": {...},
    "storage": {...},
    "picking": {...},
    "packing_shipping": {...},
    "returns": {...}
  },
  "technology": {
    "wms": {...},
    "automation": [...],
    "integrations": [...]
  },
  "staffing": {
    "total_headcount": ...,
    "by_function": {...},
    "shift_model": "..."
  },
  "performance": {
    "daily_throughput": ...,
    "accuracy_target": ...,
    "avg_lead_time_hours": ...
  },
  "risks_and_assumptions": [...],
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
