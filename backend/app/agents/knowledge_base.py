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
根据项目需求和检索到的真实历史案例数据，综合提供可参考的行业经验。

输入会包含：
1. 项目需求
2. 从知识库检索到的真实历史案例（自动化设备 ROI、成本模型、物流案例文档）

你需要：
- 引用具体的历史数据（设备投资额、IRR、成本结构等）
- 给出可直接被后续 Stage 使用的基准数据
- 不要凭空编造数字 — 只使用输入中提供的真实数据

输出 JSON：
{
  "retrieved_knowledge": {
    "automation_cases": "引用的自动化案例摘要（包含真实数据）",
    "cost_benchmarks": "引用的成本基准（包含真实数据）",
    "logistics_cases": "引用的物流案例摘要"
  },
  "key_data_points": [
    {"type": "equipment_cost", "source": "迪士尼项目", "value": "AGV ¥2,859,963/台 IRR 11.9%"}
  ],
  "synthesized_context": "综合分析上下文，可直接供后续 Stage 引用",
  "knowledge_count": {"automation": 0, "cost_model": 0, "logistics": 0},
  "relevance_score": 0.8,
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        from app.core.database import AsyncSessionLocal
        from app.models.models import KnowledgeEntry
        from sqlalchemy import select, or_, cast, String

        requirements = input_data.get("requirements", {})

        # Build search keywords from requirements
        search_terms = []
        
        # Extract industry/client keywords from requirements
        req_str = json.dumps(requirements, ensure_ascii=False, default=str).lower()
        
        # Common logistics keywords to match
        keyword_pool = [
            "汽车", "automotive", "auto", "汽配", "备件",
            "电商", "e-commerce", "零售", "retail",
            "冷链", "cold-chain", "医药", "pharma",
            "AGV", "WMS", "自动化", "automation",
            "仓储", "warehouse", "storage",
            "拣选", "picking", "包装", "packing",
        ]
        
        for kw in keyword_pool:
            if kw.lower() in req_str:
                search_terms.append(kw)

        # Always search regardless of keyword match
        async with AsyncSessionLocal() as db:
            # Build query: match active entries, optionally filter by keywords
            base_q = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
            
            if search_terms:
                conditions = []
                for term in search_terms[:5]:  # limit to 5 terms
                    pattern = f"%{term}%"
                    conditions.append(or_(
                        KnowledgeEntry.title.ilike(pattern),
                        KnowledgeEntry.content.ilike(pattern),
                        cast(KnowledgeEntry.tags, String).ilike(pattern),
                    ))
                if conditions:
                    base_q = base_q.where(or_(*conditions))
            
            # Get up to 5 entries per category
            automation_q = base_q.where(KnowledgeEntry.category == "automation_case").limit(5)
            cost_q = base_q.where(KnowledgeEntry.category == "cost_model").limit(3)
            logistics_q = base_q.where(KnowledgeEntry.category == "logistics_case").limit(3)
            
            auto_results = (await db.execute(automation_q)).scalars().all()
            cost_results = (await db.execute(cost_q)).scalars().all()
            logistics_results = (await db.execute(logistics_q)).scalars().all()

        # If keyword filter returned nothing, fall back to most recent entries
        if not auto_results and not cost_results and not logistics_results:
            async with AsyncSessionLocal() as db:
                fallback_q = select(KnowledgeEntry).where(
                    KnowledgeEntry.is_active == True
                ).order_by(KnowledgeEntry.created_at.desc()).limit(10)
                fallback = (await db.execute(fallback_q)).scalars().all()
                auto_results = [e for e in fallback if e.category == "automation_case"][:5]
                cost_results = [e for e in fallback if e.category == "cost_model"][:3]
                logistics_results = [e for e in fallback if e.category == "logistics_case"][:3]

        # Build context for LLM
        def format_entries(entries, max_chars_per_entry=800):
            if not entries:
                return "（知识库中没有相关条目）"
            parts = []
            for e in entries:
                snippet = e.content[:max_chars_per_entry]
                parts.append(f"### {e.title}\n{snippet}")
            return "\n\n".join(parts)

        knowledge_context = f"""
## 检索到的自动化案例 ({len(auto_results)} 条)
{format_entries(auto_results)}

## 检索到的成本模型 ({len(cost_results)} 条)
{format_entries(cost_results)}

## 检索到的物流案例 ({len(logistics_results)} 条)
{format_entries(logistics_results)}
"""

        # If knowledge base is completely empty, fall back to LLM-only mode
        total_count = len(auto_results) + len(cost_results) + len(logistics_results)
        if total_count == 0:
            prompt = f"""项目需求如下，知识库中暂无任何条目。
请基于物流行业通用经验，提供大致的基准数据和最佳实践。

## 项目需求
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

注意：knowledge_count 三项都填 0，并在 synthesized_context 中明确说明
"知识库为空，以下数据为通用行业估算"。"""
        else:
            prompt = f"""根据以下项目需求和知识库中检索到的真实历史案例，
提取可直接用于后续 Stage 的关键数据点和基准。

## 项目需求
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

{knowledge_context[:8000]}

请：
1. 从上述案例中提取和当前项目最相关的具体数据（金额、IRR、占比等）
2. 在 key_data_points 数组中列出每个数据点的来源
3. 在 synthesized_context 中给出综合建议（200-400字）
4. knowledge_count 字段填入实际检索到的条目数：
   automation={len(auto_results)}, cost_model={len(cost_results)}, logistics={len(logistics_results)}"""

        result = await self.call_llm_json(prompt, max_tokens=4000, project_context=project_context)
        
        # Ensure knowledge_count reflects reality
        if "knowledge_count" not in result:
            result["knowledge_count"] = {}
        result["knowledge_count"]["automation"] = len(auto_results)
        result["knowledge_count"]["cost_model"] = len(cost_results)
        result["knowledge_count"]["logistics"] = len(logistics_results)
        result["_total_retrieved"] = total_count
        
        return result
