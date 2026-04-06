"""Stage 10: Tender Writer Agent. Generates professional proposal content."""

from app.agents.base import BaseAgent


class TenderWriterAgent(BaseAgent):
    name = "tender_writer"
    description = "生成专业投标文档内容"
    stage_number = 10
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """You are a professional tender/proposal writer for logistics solutions.
Generate polished, persuasive content for each section of the proposal.

Write in professional Chinese (简体中文), formal business tone.
Use concrete numbers and specific references to the solution design.

Output JSON:
{
  "document_structure": [
    {
      "chapter": 1,
      "title": "公司介绍",
      "content": "Full chapter content in markdown...",
      "word_count": 0
    }
  ],
  "executive_summary": "2-page executive summary in markdown",
  "key_differentiators": ["..."],
  "total_word_count": 0,
  "_confidence": 0.8
}

Standard chapter structure:
1. 公司介绍与资质
2. 项目理解与需求分析
3. 物流解决方案设计
4. 自动化与技术方案
5. 实施计划与里程碑
6. 团队配置与培训
7. 质量管理与SLA承诺
8. 风险管理与应急预案
9. 报价方案
10. 成功案例参考"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        import json
        all_outputs = input_data.get("all_stage_outputs", {})

        prompt = f"""Generate a complete tender proposal based on all analysis results.

## All Stage Outputs
{json.dumps(all_outputs, ensure_ascii=False, indent=2, default=str)[:20000]}

Write each chapter in professional Chinese. Be specific and persuasive.
Include numbers, metrics, and concrete commitments throughout."""

        return await self.call_llm_json(prompt, max_tokens=12000)
