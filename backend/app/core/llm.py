"""Multi-provider LLM client.

Supports: Anthropic Claude, OpenAI GPT, DeepSeek, Google Gemini.
Uses synchronous httpx in a thread pool for Docker reliability.
Provider is selected per-request via the `provider` parameter.
"""

import asyncio
import structlog
import httpx

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# ── Provider Configurations ──

PROVIDERS = {
    "anthropic": {
        "label": "Claude (Anthropic)",
        "api_url": "https://api.anthropic.com/v1/messages",
        "models": [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
            {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5"},
        ],
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "label": "GPT (OpenAI)",
        "api_url": "https://api.openai.com/v1/chat/completions",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "o3-mini", "name": "o3-mini"},
        ],
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "label": "DeepSeek",
        "api_url": "https://api.deepseek.com/v1/chat/completions",
        "models": [
            {"id": "deepseek-chat", "name": "DeepSeek V3"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1"},
        ],
        "default_model": "deepseek-chat",
    },
    "gemini": {
        "label": "Gemini (Google)",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        "models": [
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        ],
        "default_model": "gemini-2.5-flash",
    },
    "minimax": {
        "label": "MiniMax",
        "api_url": "https://api.minimaxi.com/anthropic/v1/messages",
        "api_format": "anthropic",
        "models": [
            {"id": "MiniMax-M2.5", "name": "MiniMax M2.5"},
            {"id": "MiniMax-M2.7", "name": "MiniMax M2.7"},
            {"id": "MiniMax-M2.1", "name": "MiniMax M2.1"},
        ],
        "default_model": "MiniMax-M2.5",
    },
    "glm": {
        "label": "GLM (智谱)",
        "api_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "models": [
            {"id": "glm-4.7", "name": "GLM-4.7"},
            {"id": "glm-4-plus", "name": "GLM-4 Plus"},
            {"id": "glm-4-flash", "name": "GLM-4 Flash"},
        ],
        "default_model": "glm-4.7",
    },
}


def _get_api_key(provider: str) -> str:
    """Get API key for a provider from settings."""
    key_map = {
        "anthropic": settings.anthropic_api_key,
        "openai": settings.openai_api_key,
        "deepseek": settings.deepseek_api_key,
        "gemini": settings.gemini_api_key,
        "minimax": settings.minimax_api_key,
        "glm": settings.glm_api_key,
    }
    return key_map.get(provider, "")


def get_available_providers() -> list[dict]:
    """Return list of providers that have API keys configured."""
    result = []
    for pid, pconfig in PROVIDERS.items():
        key = _get_api_key(pid)
        result.append({
            "id": pid,
            "label": pconfig["label"],
            "models": pconfig["models"],
            "default_model": pconfig["default_model"],
            "available": bool(key),
        })
    return result


# ── API Call Functions ──

def _call_anthropic(api_key: str, model: str, system_prompt: str,
                    user_message: str, max_tokens: int, temperature: float,
                    api_url: str = "https://api.anthropic.com/v1/messages") -> dict:
    """Call Anthropic-compatible API (works for Anthropic, MiniMax)."""
    # MiniMax temperature must be > 0 and <= 1.0
    if temperature <= 0:
        temperature = 0.1
    if temperature > 1.0:
        temperature = 1.0
    response = httpx.post(
        api_url,
        headers={
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=httpx.Timeout(connect=30, read=600, write=30, pool=30),
    )
    if response.status_code == 200:
        data = response.json()
        # MiniMax/Claude can return multiple content blocks: text, thinking, tool_use
        # We need to extract the text content from the first text block
        content_blocks = data.get("content", [])
        text_parts = []
        for block in content_blocks:
            block_type = block.get("type", "")
            if block_type == "text":
                text_parts.append(block.get("text", ""))
        if not text_parts:
            return {"error": f"No text content in response: {str(data)[:300]}",
                    "status": 200, "retry_after": 0}
        return {"text": "\n".join(text_parts), "usage": data.get("usage", {})}
    return {"error": response.text[:500], "status": response.status_code,
            "retry_after": int(response.headers.get("retry-after", 30)) if response.status_code == 429 else 0}


def _call_openai_compatible(api_url: str, api_key: str, model: str, system_prompt: str,
                            user_message: str, max_tokens: int, temperature: float) -> dict:
    """Call OpenAI-compatible API (works for OpenAI, DeepSeek)."""
    response = httpx.post(
        api_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=httpx.Timeout(connect=30, read=600, write=30, pool=30),
    )
    if response.status_code == 200:
        data = response.json()
        return {"text": data["choices"][0]["message"]["content"], "usage": data.get("usage", {})}
    return {"error": response.text[:500], "status": response.status_code,
            "retry_after": int(response.headers.get("retry-after", 30)) if response.status_code == 429 else 0}


def _call_gemini(api_key: str, model: str, system_prompt: str,
                 user_message: str, max_tokens: int, temperature: float) -> dict:
    """Call Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    response = httpx.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_message}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        },
        timeout=httpx.Timeout(connect=30, read=600, write=30, pool=30),
    )
    if response.status_code == 200:
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"text": text, "usage": data.get("usageMetadata", {})}
    return {"error": response.text[:500], "status": response.status_code, "retry_after": 0}


def _call_api_sync(provider: str, api_key: str, model: str, system_prompt: str,
                   user_message: str, max_tokens: int, temperature: float) -> dict:
    """Route to the correct provider's API call function."""
    if provider == "anthropic":
        return _call_anthropic(api_key, model, system_prompt, user_message, max_tokens, temperature)
    elif provider == "minimax":
        api_url = PROVIDERS["minimax"]["api_url"]
        return _call_anthropic(api_key, model, system_prompt, user_message, max_tokens, temperature, api_url=api_url)
    elif provider in ("openai", "deepseek", "glm"):
        api_url = PROVIDERS[provider]["api_url"]
        return _call_openai_compatible(api_url, api_key, model, system_prompt, user_message, max_tokens, temperature)
    elif provider == "gemini":
        return _call_gemini(api_key, model, system_prompt, user_message, max_tokens, temperature)
    else:
        return {"error": f"Unknown provider: {provider}", "status": 400, "retry_after": 0}


# ── Main LLM Client ──

class LLMClient:
    """Multi-provider LLM client."""

    def __init__(self):
        self.default_provider = "anthropic"
        self.default_model = settings.llm_primary_model

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        provider: str = "",
        model: str = "",
    ) -> str:
        """Generate a completion using the specified provider and model."""
        use_provider = provider or self.default_provider
        use_model = model or (PROVIDERS.get(use_provider, {}).get("default_model", "") if provider else self.default_model)
        api_key = _get_api_key(use_provider)

        if not api_key:
            raise RuntimeError(f"No API key configured for provider: {use_provider}")

        last_error = None

        for attempt in range(3):
            try:
                result = await asyncio.to_thread(
                    _call_api_sync,
                    use_provider, api_key, use_model,
                    system_prompt, user_message, max_tokens, temperature,
                )

                if "text" in result:
                    logger.info(
                        "llm_success",
                        provider=use_provider,
                        model=use_model,
                        input_tokens=result.get("usage", {}).get("input_tokens")
                            or result.get("usage", {}).get("prompt_tokens"),
                        output_tokens=result.get("usage", {}).get("output_tokens")
                            or result.get("usage", {}).get("completion_tokens"),
                        attempt=attempt + 1,
                    )
                    return result["text"]

                # Error handling
                status = result.get("status", 0)
                if status == 429:
                    wait = result.get("retry_after", 30)
                    logger.warning("llm_rate_limited", provider=use_provider, retry_after=wait)
                    await asyncio.sleep(wait)
                    continue
                elif status == 529:
                    logger.warning("llm_overloaded", provider=use_provider)
                    await asyncio.sleep(30)
                    continue
                else:
                    last_error = f"[{use_provider}] API error {status}: {result.get('error', '')}"
                    logger.error("llm_api_error", provider=use_provider, status=status, error=result.get("error"))

            except Exception as e:
                error_msg = str(e)
                logger.error("llm_call_error", provider=use_provider, error=error_msg, attempt=attempt + 1)
                last_error = error_msg
                if "disconnected" in error_msg.lower():
                    await asyncio.sleep(15 * (attempt + 1))
                else:
                    await asyncio.sleep(5 * (attempt + 1))

        raise RuntimeError(f"LLM call failed after 3 attempts: {last_error}")

    async def generate_structured(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        provider: str = "",
        model: str = "",
    ) -> str:
        """Generate structured JSON output."""
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
            provider=provider,
            model=model,
        )


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
