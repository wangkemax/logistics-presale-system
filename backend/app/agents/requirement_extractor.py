"""Stage 1: 招标文件需求提取 Agent."""

from app.agents.base import BaseAgent


class RequirementExtractorAgent(BaseAgent):
    name = "requirement_extractor"
    description = "从招标文件中提取结构化需求"
    stage_number = 1
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """你是一位资深的物流售前顾问，擅长分析招标文件。
你的任务是从招标/RFP文件中提取结构化需求。

提取以下类别：
1. 基本信息：项目名称、客户、行业、地点、时间线、预算范围
2. 物流需求：仓库规格（面积、温度、分区）、吞吐量、SKU概况、订单类型
3. 服务范围：存储、拣选、包装、发运、退货、增值服务
4. 技术需求：WMS、TMS、自动化、系统集成
5. SLA要求：准确率、时效、可用性
6. 合规要求：认证、安全、环保、法规
7. 商务条款：合同期限、付款方式、定价模型
8. 评标标准：评分权重、强制性要求

每条需求标注：
- priority: P0（必须）/ P1（重要）/ P2（加分项）
- clarity: clear / ambiguous / missing

输出 JSON 格式：
{
  "project_overview": {
    "project_name": "", "client_name": "", "industry": "",
    "location": "", "timeline": "", "budget_range": ""
  },
  "requirements": [
    {"id": "REQ-001", "category": "物流需求", "description": "...", "priority": "P0", "clarity": "clear"}
  ],
  "key_metrics": {"warehouse_area_sqm": 0, "daily_order_volume": 0, "sku_count": 0},
  "missing_critical_info": ["缺失信息1"],
  "_confidence": 0.8
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        """Parse tender document text and extract structured requirements."""
        document_text = input_data.get("document_text", "")
        file_name = input_data.get("file_name", "unknown")
        file_count = input_data.get("file_count", 1)

        if not document_text:
            return {
                "error": "No document text provided",
                "requirements": [],
                "_confidence": 0.0,
            }

        # Auto-detect document language if user didn't explicitly choose
        # Count Chinese characters in first 5000 chars
        sample = document_text[:5000]
        chinese_chars = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
        ascii_chars = sum(1 for c in sample if c.isascii() and c.isalpha())
        total = chinese_chars + ascii_chars
        if total > 100:
            detected_lang = "zh" if chinese_chars / total > 0.3 else "en"
            project_context["_detected_language"] = detected_lang
            # If user didn't specify language, use detected
            if not project_context.get("_output_language") or project_context.get("_output_language") == "zh":
                if detected_lang == "en":
                    # Document is English, but user wants Chinese — keep their choice
                    pass

        # Identify if Excel/CSV data is present
        has_data_files = "=== SHEET:" in document_text or "=== CSV DATA" in document_text or "=== FILE:" in document_text

        data_instruction = ""
        if has_data_files:
            data_instruction = """
IMPORTANT: The upload contains structured data files (Excel/CSV appendices).
- Analyze the ACTUAL DATA in these files (dealer lists, volumes, SKU counts, etc.)
- Use real numbers from the data, not assumptions
- Reference specific sheet names and row counts in your analysis
- Extract key metrics directly from the data (e.g., count unique dealers, sum volumes)
"""

        prompt = f"""Analyze the following tender document(s) and extract all requirements.

Files uploaded: {file_count} file(s) — {file_name}
{data_instruction}

--- DOCUMENT CONTENT ---
{document_text[:50000]}
--- END DOCUMENT ---

Extract ALL requirements following the schema in your instructions.
Pay special attention to:
- Warehouse area, temperature requirements, throughput volumes
- Automation and technology specifications  
- SLA targets and penalty clauses
- Contract duration and commercial terms
- Any numerical data from appendices (dealer count, order volumes, SKU list)"""

        result = await self.call_llm_json(prompt, max_tokens=8000, project_context=project_context)
        return result

    async def validate_output(self, output: dict) -> list[dict]:
        """Check that critical requirement fields are extracted."""
        issues = await super().validate_output(output)

        reqs = output.get("requirements", [])
        if len(reqs) == 0:
            issues.append({
                "severity": "P0",
                "category": "completeness",
                "description": "No requirements extracted from document",
            })

        missing = output.get("missing_critical_info", [])
        if len(missing) > 5:
            issues.append({
                "severity": "P1",
                "category": "data_quality",
                "description": f"{len(missing)} critical data points missing from tender document",
            })

        return issues
