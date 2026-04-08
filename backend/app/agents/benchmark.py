"""Stage 7: 案例匹配 Agent."""

from app.agents.base import BaseAgent


class BenchmarkAgent(BaseAgent):
    name = "benchmark"
    description = "匹配相似案例，提取可借鉴经验"
    stage_number = 7
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流行业案例分析专家。
根据当前项目特征，匹配并分析相似的成功案例。

每个案例需包含：
1. 案例名称和客户行业
2. 项目规模（面积、单量、SKU数）
3. 相似度评分（0-1）
4. 可借鉴的经验和教训
5. 对当前项目的适用性

输出 JSON：
{
  "matched_cases": [
    {
      "case_name": "案例名称",
      "client_industry": "行业",
      "project_scale": "规模描述",
      "similarity_score": 0.85,
      "key_learnings": ["经验1", "经验2"],
      "applicable_to_current": "适用性说明"
    }
  ],
  "industry_benchmarks": {"avg_cost_per_order": 0, "avg_accuracy": "99.5%"},
  "_confidence": 0.8
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
