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
    ) -> AgentOutput:
        """Run the agent with timeout, error handling, and output validation."""
        start = time.time()
        logger.info("agent_started", agent=self.name, stage=self.stage_number)

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

    async def call_llm(self, user_message: str, max_tokens: int = 4096) -> str:
        """Convenience: call the LLM with this agent's system prompt."""
        return await self.llm.generate(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
        )

    async def call_llm_json(self, user_message: str, max_tokens: int = 4096) -> dict:
        """Convenience: call LLM and parse JSON response."""
        raw = await self.llm.generate_structured(
            system_prompt=self.system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
        )
        # Strip any accidental markdown fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned.strip())
