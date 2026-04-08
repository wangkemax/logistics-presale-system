"""Stage 7: Benchmark Agent. Matches similar past cases."""

from app.agents.base import BaseAgent


class BenchmarkAgent(BaseAgent):
    name = "benchmark"
    description = "匹配相似案例，提供参考数据"
    stage_number = 7
    timeout_minutes = 8

    @property
    def system_prompt(self) -> str:
        return """You are a logistics benchmarking specialist. Given the project
requirements, identify and analyze the most relevant past cases.

For each matched case, provide similarity scoring and key learnings.

Output JSON:
{
  "matched_cases": [
    {
      "case_id": "...",
      "case_name": "...",
      "client_industry": "...",
      "similarity_score": 0.85,
      "similar_aspects": ["area", "throughput", "industry"],
      "different_aspects": ["automation level"],
      "key_metrics": {"area_sqm": 0, "daily_orders": 0, "headcount": 0},
      "lessons_learned": ["..."],
      "applicable_to_current": "How this applies"
    }
  ],
  "benchmark_summary": {
    "avg_cost_per_sqm": 0,
    "avg_cost_per_order": 0,
    "avg_headcount_per_1000sqm": 0,
    "industry_automation_rate": "..."
  },
  "_confidence": 0.75
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        requirements = input_data.get("requirements", {})
        cases_data = input_data.get("knowledge_cases", "")

        prompt = f"""Find the most similar logistics cases for this project.

## Current Project
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:5000]}

## Available Cases from Knowledge Base
{cases_data[:8000] if cases_data else 'No cases available. Provide general industry benchmarks.'}

Match cases by: industry, warehouse size, throughput volume, automation level, geography.
Score similarity 0-1. Extract applicable lessons."""

        return await self.call_llm_json(prompt, project_context=project_context, max_tokens=5000)
