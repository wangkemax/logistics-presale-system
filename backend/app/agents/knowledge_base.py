"""Stage 4: Knowledge Base Agent. Retrieves relevant knowledge via RAG."""

from app.agents.base import BaseAgent


class KnowledgeBaseAgent(BaseAgent):
    name = "knowledge_base"
    description = "知识库检索（RAG）"
    stage_number = 4
    timeout_minutes = 5

    @property
    def system_prompt(self) -> str:
        return """You are a knowledge retrieval specialist. Given the project
requirements, formulate search queries and synthesize relevant knowledge
from the knowledge base.

Categories to search:
- automation_case: Past automation implementations
- cost_model: Cost benchmarks and pricing references
- logistics_case: Similar logistics project case studies

Output JSON:
{
  "search_queries": ["query1", "query2"],
  "retrieved_knowledge": {
    "automation_cases": [{"title": "...", "summary": "...", "relevance": 0.9}],
    "cost_references": [{"title": "...", "summary": "...", "relevance": 0.8}],
    "logistics_cases": [{"title": "...", "summary": "...", "relevance": 0.85}]
  },
  "synthesized_context": "综合知识摘要 for downstream agents...",
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
