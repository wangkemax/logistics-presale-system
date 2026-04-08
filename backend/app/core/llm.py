"""Unified LLM client using httpx directly.

Bypasses the Anthropic Python SDK which has async timeout issues
in Docker containers. Uses raw HTTP calls to the Messages API.
"""

import json
import structlog
import httpx

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


class LLMClient:
    """LLM client using direct httpx calls to Anthropic API."""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.primary_model = settings.llm_primary_model
        self.fallback_model = settings.llm_fallback_model
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=600.0,   # 10 min read for long generations
                    write=30.0,
                    pool=30.0,
                ),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
            )
        return self._client

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Generate a completion using Claude API via httpx."""
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": API_VERSION,
        }

        payload = {
            "model": self.primary_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }

        last_error = None

        for attempt in range(3):
            try:
                client = self._get_client()
                response = await client.post(API_URL, headers=headers, json=payload)

                if response.status_code == 200:
                    data = response.json()
                    text = data["content"][0]["text"]
                    logger.info(
                        "llm_success",
                        model=self.primary_model,
                        input_tokens=data.get("usage", {}).get("input_tokens"),
                        output_tokens=data.get("usage", {}).get("output_tokens"),
                        attempt=attempt + 1,
                    )
                    return text

                elif response.status_code == 429:
                    # Rate limited — wait and retry
                    retry_after = int(response.headers.get("retry-after", 30))
                    logger.warning("llm_rate_limited", retry_after=retry_after, attempt=attempt + 1)
                    import asyncio
                    await asyncio.sleep(retry_after)
                    continue

                elif response.status_code == 529:
                    # Overloaded — wait longer
                    logger.warning("llm_overloaded", attempt=attempt + 1)
                    import asyncio
                    await asyncio.sleep(30)
                    continue

                else:
                    error_body = response.text[:500]
                    logger.error(
                        "llm_api_error",
                        status=response.status_code,
                        body=error_body,
                        attempt=attempt + 1,
                    )
                    last_error = f"API error {response.status_code}: {error_body}"

            except httpx.TimeoutException as e:
                logger.error("llm_timeout", error=str(e), attempt=attempt + 1)
                last_error = f"Timeout: {str(e)}"
                import asyncio
                await asyncio.sleep(5 * (attempt + 1))

            except httpx.ConnectError as e:
                logger.error("llm_connect_error", error=str(e), attempt=attempt + 1)
                last_error = f"Connection error: {str(e)}"
                import asyncio
                await asyncio.sleep(5 * (attempt + 1))

            except Exception as e:
                logger.error("llm_unexpected_error", error=str(e), attempt=attempt + 1)
                last_error = f"Unexpected: {str(e)}"
                break

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

    async def close(self):
        """Close the httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
