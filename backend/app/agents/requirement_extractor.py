"""Stage 1: Tender Requirement Extractor Agent.

Parses uploaded tender documents (PDF/Word) and extracts
structured requirements for downstream agents.
"""

from app.agents.base import BaseAgent


class RequirementExtractorAgent(BaseAgent):
    name = "requirement_extractor"
    description = "从招标文件中提取结构化需求"
    stage_number = 1
    timeout_minutes = 15

    @property
    def system_prompt(self) -> str:
        return """You are a senior logistics presale consultant specializing in
analyzing tender documents. Your task is to extract structured requirements
from tender/RFP documents.

Extract the following categories:
1. **Basic Info**: Project name, client, industry, location, timeline, budget range
2. **Logistics Requirements**: Warehouse specs (area, temperature, zones), 
   throughput (inbound/outbound volumes), SKU profile, order types
3. **Service Scope**: Storage, picking, packing, shipping, returns, VAS
4. **Technology Requirements**: WMS, TMS, automation, integration needs
5. **SLA Requirements**: Accuracy rates, lead times, availability
6. **Compliance**: Certifications, safety, environmental, regulatory
7. **Commercial Terms**: Contract period, payment terms, pricing model
8. **Evaluation Criteria**: Scoring weights, mandatory requirements

For each requirement, assign:
- priority: P0 (mandatory) / P1 (important) / P2 (nice-to-have)
- clarity: clear / ambiguous / missing
- source_reference: page/section in the original document

Respond in JSON format with the structure:
{
  "project_overview": {...},
  "requirements": [
    {
      "id": "REQ-001",
      "category": "...",
      "description": "...",
      "priority": "P0",
      "clarity": "clear",
      "source_reference": "Section 3.2, Page 12",
      "raw_text": "original text from document"
    }
  ],
  "key_metrics": {
    "warehouse_area_sqm": null,
    "daily_order_volume": null,
    "sku_count": null,
    "temperature_zones": []
  },
  "missing_critical_info": ["list of P0 info not found in document"],
  "_confidence": 0.85
}"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        """Parse tender document text and extract structured requirements."""
        document_text = input_data.get("document_text", "")
        file_name = input_data.get("file_name", "unknown")

        if not document_text:
            return {
                "error": "No document text provided",
                "requirements": [],
                "_confidence": 0.0,
            }

        prompt = f"""Analyze the following tender document and extract all requirements.

Document: {file_name}

--- DOCUMENT CONTENT ---
{document_text[:30000]}
--- END DOCUMENT ---

Extract ALL requirements following the schema in your instructions.
Pay special attention to:
- Warehouse area, temperature requirements, throughput volumes
- Automation and technology specifications
- SLA targets and penalty clauses
- Contract duration and commercial terms"""

        result = await self.call_llm_json(prompt, max_tokens=8000)
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
