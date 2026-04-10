"""Base Agent class — all 11 agents inherit from this.

Each agent has:
- A system prompt defining its role and expertise
- Input/output schemas for structured data
- Timeout and retry configuration
- Self-validation of outputs
"""

import time
import asyncio
import json
import structlog
from abc import ABC, abstractmethod

from app.core.llm import LLMClient
from app.schemas.schemas import AgentOutput

logger = structlog.get_logger()


class BaseAgent(ABC):
    """Abstract base class for all Presale AI Agents."""

    name: str = "base_agent"
    description: str = ""
    stage_number: int = 0
    timeout_minutes: int = 10

    def __init__(self, llm: LLMClient):
        self.llm = llm

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The system prompt defining this agent's role and expertise."""
        ...

    @abstractmethod
    async def _execute(
        self,
        input_data: dict,
        project_context: dict,
    ) -> dict:
        """Core execution logic. Subclasses implement this."""
        ...

    async def execute(
        self,
        input_data: dict,
        project_context: dict,
        use_cache: bool = True,
    ) -> AgentOutput:
        """Run the agent with caching, timeout, error handling, and output validation."""
        from app.services.agent_cache import get_agent_cache

        start = time.time()
        logger.info("agent_started", agent=self.name, stage=self.stage_number)

        # ── Check cache ──
        if use_cache:
            try:
                cache = get_agent_cache()
                cached = await cache.get(self.name, input_data, project_context)
                if cached:
                    elapsed = time.time() - start
                    logger.info("agent_cache_hit", agent=self.name, elapsed=f"{elapsed:.3f}s")
                    return AgentOutput(
                        stage_number=self.stage_number,
                        agent_name=self.name,
                        status="success",
                        data=cached,
                        confidence=cached.get("_confidence", 0.8),
                        issues=[],
                        execution_time_seconds=round(elapsed, 2),
                    )
            except Exception:
                pass  # Cache miss or error, proceed normally

        try:
            result = await asyncio.wait_for(
                self._execute(input_data, project_context),
                timeout=self.timeout_minutes * 60,
            )

            elapsed = time.time() - start
            issues = await self.validate_output(result)

            output = AgentOutput(
                stage_number=self.stage_number,
                agent_name=self.name,
                status="success",
                data=result,
                confidence=result.get("_confidence", 0.8),
                issues=issues,
                execution_time_seconds=round(elapsed, 2),
            )

            # ── Store in cache ──
            if use_cache and output.status == "success":
                try:
                    cache = get_agent_cache()
                    await cache.set(self.name, input_data, project_context, result)
                except Exception:
                    pass

            # ── Record metrics ──
            try:
                from app.core.metrics import record_agent_execution
                record_agent_execution(self.name, "success", output.execution_time_seconds)
            except Exception:
                pass

            logger.info(
                "agent_completed",
                agent=self.name,
                stage=self.stage_number,
                elapsed=f"{elapsed:.1f}s",
                issues_count=len(issues),
            )
            return output

        except asyncio.TimeoutError:
            elapsed = time.time() - start
            logger.error("agent_timeout", agent=self.name, timeout=self.timeout_minutes)
            try:
                from app.core.metrics import record_agent_execution
                record_agent_execution(self.name, "timeout", round(elapsed, 2))
            except Exception:
                pass
            return AgentOutput(
                stage_number=self.stage_number,
                agent_name=self.name,
                status="error",
                data={"error": f"Agent timed out after {self.timeout_minutes} minutes"},
                confidence=0.0,
                execution_time_seconds=round(elapsed, 2),
            )

        except Exception as e:
            elapsed = time.time() - start
            logger.error("agent_failed", agent=self.name, error=str(e))
            try:
                from app.core.metrics import record_agent_execution
                record_agent_execution(self.name, "error", round(elapsed, 2))
            except Exception:
                pass
            return AgentOutput(
                stage_number=self.stage_number,
                agent_name=self.name,
                status="error",
                data={"error": str(e)},
                confidence=0.0,
                execution_time_seconds=round(elapsed, 2),
            )

    async def validate_output(self, output: dict) -> list[dict]:
        """Self-validate output for common issues. Returns list of issues."""
        issues = []

        # Check for empty output
        if not output or all(v is None for v in output.values() if v != "_confidence"):
            issues.append({
                "severity": "P0",
                "category": "completeness",
                "description": f"Agent {self.name} produced empty output",
            })

        return issues

    @property
    def effective_prompt(self) -> str:
        """Get effective system prompt (override or built-in)."""
        from app.api.routes.prompts import get_effective_prompt
        return get_effective_prompt(self.name, self.system_prompt)

    def _get_lang_instruction(self, project_context: dict | None = None) -> str:
        """Get language instruction to append to system prompt."""
        lang = (project_context or {}).get("_output_language", "zh")
        if lang == "en":
            return "\n\nIMPORTANT: All output must be in English. Use English for JSON field names and all content."
        return (
            "\n\n重要：描述和分析内容使用中文（简体）。"
            "但是JSON字段名（key）必须使用英文（如 warehouse_design, total_area_sqm, executive_summary, "
            "staffing, total_headcount, financial_indicators, roi_percent, irr_percent, npv_at_8pct, "
            "risk_matrix, overall_risk_level, automation_level, recommendations, cost_breakdown, pricing）。"
            "只有value部分使用中文。"
        )

    async def call_llm(self, user_message: str, max_tokens: int = 4096, project_context: dict | None = None) -> str:
        """Convenience: call the LLM with this agent's effective prompt."""
        prompt = self.effective_prompt + self._get_lang_instruction(project_context)
        ctx = project_context or {}
        return await self.llm.generate(
            system_prompt=prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            provider=ctx.get("_llm_provider", ""),
            model=ctx.get("_llm_model", ""),
        )

    async def call_llm_json(self, user_message: str, max_tokens: int = 4096, project_context: dict | None = None) -> dict:
        """Convenience: call LLM and parse JSON response."""
        prompt = self.effective_prompt + self._get_lang_instruction(project_context)
        ctx = project_context or {}
        raw = await self.llm.generate_structured(
            system_prompt=prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            provider=ctx.get("_llm_provider", ""),
            model=ctx.get("_llm_model", ""),
        )
        # Strip any accidental markdown fences, think tags, or other wrappers
        cleaned = raw.strip()
        # Remove <think>...</think> blocks (MiniMax/DeepSeek reasoning)
        import re
        cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL).strip()
        # Remove markdown code fences
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        # Try to find JSON object/array in the text
        if not cleaned.startswith(("{", "[")):
            json_start = -1
            for i, c in enumerate(cleaned):
                if c in ('{', '['):
                    json_start = i
                    break
            if json_start >= 0:
                cleaned = cleaned[json_start:]

        def _try_parse(text: str):
            return json.loads(text)

        def _repair_json(text: str) -> str:
            """Common LLM JSON mistakes: trailing commas, single quotes, unquoted keys."""
            # Remove trailing commas before } or ]
            text = re.sub(r',(\s*[}\]])', r'\1', text)
            # Replace Python None/True/False with JSON null/true/false
            text = re.sub(r'\bNone\b', 'null', text)
            text = re.sub(r'\bTrue\b', 'true', text)
            text = re.sub(r'\bFalse\b', 'false', text)
            return text

        # Attempt 1: parse as-is
        try:
            return _try_parse(cleaned)
        except json.JSONDecodeError:
            pass

        # Attempt 2: extract between first { and last }
        brace_start = cleaned.find('{')
        brace_end = cleaned.rfind('}')
        if brace_start >= 0 and brace_end > brace_start:
            substr = cleaned[brace_start:brace_end + 1]
            try:
                return _try_parse(substr)
            except json.JSONDecodeError:
                pass
            # Attempt 3: repair common JSON issues
            try:
                return _try_parse(_repair_json(substr))
            except json.JSONDecodeError:
                pass

        # Attempt 4: try json5 if available (more lenient)
        try:
            import json5
            return json5.loads(cleaned)
        except (ImportError, Exception):
            pass

        logger.error("json_parse_failed", raw_preview=raw[:500])
        raise json.JSONDecodeError(f"Failed to parse LLM response as JSON. Preview: {raw[:200]}", raw, 0)
