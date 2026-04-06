"""Multi-scheme comparison service.

Generates multiple solution variants (方案A/B/C) with different
automation levels and cost profiles for side-by-side comparison.
"""

import json
import structlog

from app.core.llm import LLMClient

logger = structlog.get_logger()

SCHEME_PROFILES = {
    "A": {
        "name": "方案A — 经济型",
        "description": "以人工为主，适度自动化，投资最低",
        "automation_level": "low",
        "automation_budget_pct": 0.10,
    },
    "B": {
        "name": "方案B — 均衡型",
        "description": "人机协同，核心环节自动化，性价比最优",
        "automation_level": "medium",
        "automation_budget_pct": 0.30,
    },
    "C": {
        "name": "方案C — 高端型",
        "description": "高度自动化，最大化效率与准确率",
        "automation_level": "high",
        "automation_budget_pct": 0.55,
    },
}


async def generate_multi_scheme_comparison(
    base_solution: dict,
    base_cost: dict,
    requirements: dict,
    llm: LLMClient,
) -> dict:
    """Generate 3 scheme variants from a base solution.

    Args:
        base_solution: Stage 5 output (logistics architect).
        base_cost: Stage 8 output (cost model).
        requirements: Stage 1 output (requirements).
        llm: LLM client.

    Returns:
        Dict with schemes A/B/C, each containing adjusted solution + cost.
    """
    schemes = {}

    for scheme_id, profile in SCHEME_PROFILES.items():
        prompt = f"""Based on the following logistics solution, generate a {profile['automation_level']}
automation variant called "{profile['name']}".

Profile: {profile['description']}
Automation budget: {profile['automation_budget_pct']*100:.0f}% of total investment

## Base Solution
{json.dumps(base_solution, ensure_ascii=False, indent=2, default=str)[:6000]}

## Base Cost Model
{json.dumps(base_cost, ensure_ascii=False, indent=2, default=str)[:4000]}

## Requirements
{json.dumps(requirements, ensure_ascii=False, indent=2, default=str)[:3000]}

Adjust the solution to match the {profile['automation_level']} automation level:
- For "low": minimal automation, maximize manual labor, lowest CAPEX
- For "medium": automate high-volume repetitive tasks, balanced investment
- For "high": full automation where feasible, highest CAPEX, lowest OPEX

Output JSON with this structure:
{{
  "scheme_id": "{scheme_id}",
  "scheme_name": "{profile['name']}",
  "automation_level": "{profile['automation_level']}",
  "summary": "2-sentence scheme description",
  "key_changes": ["list of changes from base solution"],
  "headcount": {{"total": 0, "vs_base": "-20%"}},
  "automation_equipment": ["list of equipment"],
  "cost_summary": {{
    "total_capex": 0,
    "annual_opex": 0,
    "vs_base_capex_pct": 0,
    "vs_base_opex_pct": 0
  }},
  "financial_indicators": {{
    "roi_percent": 0,
    "irr_percent": 0,
    "npv_at_8pct": 0,
    "payback_months": 0
  }},
  "pros": ["advantages"],
  "cons": ["disadvantages"],
  "recommended_for": "description of ideal client profile",
  "_confidence": 0.75
}}"""

        system = (
            "You are a logistics solution architect. Generate realistic cost and "
            "performance variations. All monetary values in CNY. Be specific with numbers."
        )

        try:
            raw = await llm.generate_structured(system, prompt, max_tokens=4000)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            scheme_data = json.loads(cleaned.strip())
            schemes[scheme_id] = scheme_data
            logger.info("scheme_generated", scheme=scheme_id, name=profile["name"])
        except Exception as e:
            logger.error("scheme_generation_failed", scheme=scheme_id, error=str(e))
            schemes[scheme_id] = {
                "scheme_id": scheme_id,
                "scheme_name": profile["name"],
                "error": str(e),
            }

    # Build comparison summary
    comparison = {
        "schemes": schemes,
        "recommendation": _pick_recommendation(schemes),
        "comparison_matrix": _build_matrix(schemes),
    }

    return comparison


def _pick_recommendation(schemes: dict) -> dict:
    """Pick the recommended scheme based on ROI."""
    best_id = "B"
    best_roi = 0
    for sid, data in schemes.items():
        roi = data.get("financial_indicators", {}).get("roi_percent", 0) or 0
        if roi > best_roi:
            best_roi = roi
            best_id = sid
    return {
        "recommended_scheme": best_id,
        "reason": f"方案{best_id} ROI 最高 ({best_roi:.1f}%)，综合性价比最优",
    }


def _build_matrix(schemes: dict) -> list[dict]:
    """Build a comparison matrix for easy display."""
    metrics = ["total_capex", "annual_opex", "roi_percent", "irr_percent", "payback_months", "headcount"]
    matrix = []

    for metric in metrics:
        row = {"metric": metric}
        for sid, data in schemes.items():
            if metric == "headcount":
                row[f"scheme_{sid}"] = data.get("headcount", {}).get("total", "—")
            elif metric in ("roi_percent", "irr_percent", "payback_months"):
                row[f"scheme_{sid}"] = data.get("financial_indicators", {}).get(metric, "—")
            else:
                row[f"scheme_{sid}"] = data.get("cost_summary", {}).get(metric, "—")
        matrix.append(row)

    return matrix
