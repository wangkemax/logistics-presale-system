"""Unified LLM client with primary/fallback model support."""

import structlog
from anthropic import AsyncAnthropic, APIConnectionError, APITimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class LLMClient:
    """Multi-provider LLM client with automatic fallback."""

    def __init__(self):
        self.anthropic = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=600.0,  # 10 minutes for long tender chapters
            max_retries=0,  # We handle retries ourselves
        )
        self.primary_model = settings.llm_primary_model
        self.fallback_model = settings.llm_fallback_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=3, min=5, max=60),
        retry=retry_if_exception_type((APIConnectionError, APITimeoutError)),
    )
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion using the primary LLM (Claude)."""
        try:
            response = await self.anthropic.messages.create(
                model=self.primary_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text

        except (APIConnectionError, APITimeoutError) as e:
            logger.error("llm_connection_error", error=str(e), model=self.primary_model)
            raise
        except Exception as e:
            logger.error("llm_primary_failed", error=str(e), model=self.primary_model)
            raise

    async def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
    ) -> str:
        """Generate structured JSON output from LLM."""
        structured_system = (
            f"{system_prompt}\n\n"
            "IMPORTANT: Respond ONLY with valid JSON. "
            "No markdown, no code fences, no explanation."
        )
        return await self.generate(
            system_prompt=structured_system,
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=0.1,
        )


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
