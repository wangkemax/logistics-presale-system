"""Unified LLM client using synchronous httpx in a thread pool.

The Anthropic async SDK and httpx AsyncClient both have connection
issues in Docker containers with uvicorn. Using sync httpx.post()
in asyncio.to_thread() is the most reliable approach — proven by
manual testing in the container.
"""

import asyncio
import json
import structlog
import httpx

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def _call_api_sync(
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    """Synchronous API call — runs in thread pool via asyncio.to_thread()."""
    headers = {
        "x-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": API_VERSION,
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    # Use a fresh client per call — avoids connection pool issues in Docker
    response = httpx.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=httpx.Timeout(
            connect=30.0,
            read=600.0,  # 10 min read timeout for long generations
            write=30.0,
            pool=30.0,
        ),
    )

    return {
        "status_code": response.status_code,
        "body": response.json() if response.status_code == 200 else None,
        "error_text": response.text[:500] if response.status_code != 200 else None,
        "retry_after": int(response.headers.get("retry-after", 30)) if response.status_code == 429 else 0,
    }


class LLMClient:
    """LLM client using sync httpx in thread pool for maximum reliability."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.primary_model = settings.llm_primary_model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion using Claude API."""
        last_error = None

        for attempt in range(3):
            try:
                # Run sync httpx in thread pool — proven reliable
                result = await asyncio.to_thread(
                    _call_api_sync,
                    self.api_key,
                    self.primary_model,
                    system_prompt,
                    user_message,
                    max_tokens,
                    temperature,
                )

                if result["status_code"] == 200:
                    data = result["body"]
                    text = data["content"][0]["text"]
                    logger.info(
                        "llm_success",
                        model=self.primary_model,
                        input_tokens=data.get("usage", {}).get("input_tokens"),
                        output_tokens=data.get("usage", {}).get("output_tokens"),
                        attempt=attempt + 1,
                    )
                    return text

                elif result["status_code"] == 429:
                    wait = result["retry_after"]
                    logger.warning("llm_rate_limited", retry_after=wait, attempt=attempt + 1)
                    await asyncio.sleep(wait)
                    continue

                elif result["status_code"] == 529:
                    logger.warning("llm_overloaded", attempt=attempt + 1)
                    await asyncio.sleep(30)
                    continue

                else:
                    logger.error(
                        "llm_api_error",
                        status=result["status_code"],
                        body=result["error_text"],
                        attempt=attempt + 1,
                    )
                    last_error = f"API error {result['status_code']}: {result['error_text']}"

            except Exception as e:
                logger.error("llm_call_error", error=str(e), attempt=attempt + 1)
                last_error = str(e)
                await asyncio.sleep(5 * (attempt + 1))

        raise RuntimeError(f"LLM call failed after 3 attempts: {last_error}")

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
