"""Stage 4: 知识库检索 Agent."""

from app.agents.base import BaseAgent


class KnowledgeBaseAgent(BaseAgent):
    name = "knowledge_base"
    description = "从知识库检索相关案例和最佳实践"
    stage_number = 4
    timeout_minutes = 10

    @property
    def system_prompt(self) -> str:
        return """你是物流行业知识管理专家。
根据项目需求，从知识库中检索并综合相关的行业知识、案例经验和最佳实践。

检索维度：
1. 自动化案例：类似规模项目的自动化方案和投资回报
2. 成本基准：行业成本参考数据
3. 物流案例：类似行业/规模的成功案例

输出 JSON：
{
  "retrieved_knowledge": {
    "automation_cases": "自动化案例摘要...",
    "cost_benchmarks": "成本基准数据...",
    "logistics_cases": "物流案例摘要..."
  },
  "synthesized_context": "综合分析上下文...",
  "relevance_score": 0.8,
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        requirements = input_data.get("requirements", {})

        # TODO: Replace with actual vector DB search when Milvus is set up
        prompt = f"""Based on these project requirements, determine what knowledge
would be most valuable and formulate search queries.

## Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:5000]}

For now, synthesize relevant logistics industry knowledge based on
the project type, scale, and requirements. Provide realistic
benchmarks and best practices."""

        return await self.call_llm_json(prompt, max_tokens=4000)
