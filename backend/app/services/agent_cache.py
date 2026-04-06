"""Redis-based Agent output cache.

Caches LLM responses by hashing the (agent_name, input_data, project_context)
tuple. Avoids redundant API calls when re-running stages with identical input.
"""

import hashlib
import json
from typing import Any

import structlog
import redis.asyncio as aioredis

from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Cache TTL: 24 hours (agent outputs don't change for same input)
DEFAULT_TTL = 60 * 60 * 24


class AgentCache:
    """Redis cache for Agent execution results."""

    def __init__(self, redis_url: str | None = None, ttl: int = DEFAULT_TTL):
        self.redis_url = redis_url or settings.redis_url
        self.ttl = ttl
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=5,
            )
        return self._redis

    @staticmethod
    def _make_key(agent_name: str, input_data: dict, project_context: dict) -> str:
        """Create a deterministic cache key from agent input."""
        payload = json.dumps(
            {"agent": agent_name, "input": input_data, "context": project_context},
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"agent_cache:{agent_name}:{digest}"

    async def get(
        self,
        agent_name: str,
        input_data: dict,
        project_context: dict,
    ) -> dict | None:
        """Look up a cached agent output.

        Returns:
            Cached output dict, or None if not found / expired.
        """
        try:
            r = await self._get_redis()
            key = self._make_key(agent_name, input_data, project_context)
            raw = await r.get(key)
            if raw:
                logger.info("agent_cache_hit", agent=agent_name, key=key[:30])
                return json.loads(raw)
            return None
        except Exception as e:
            logger.warning("agent_cache_get_error", error=str(e))
            return None

    async def set(
        self,
        agent_name: str,
        input_data: dict,
        project_context: dict,
        output: dict,
        ttl: int | None = None,
    ) -> None:
        """Store an agent output in cache.

        Args:
            agent_name: Agent identifier.
            input_data: Input that produced this output.
            project_context: Project assumptions context.
            output: The output to cache.
            ttl: Custom TTL in seconds (default: 24h).
        """
        try:
            r = await self._get_redis()
            key = self._make_key(agent_name, input_data, project_context)
            raw = json.dumps(output, ensure_ascii=False, default=str)
            await r.setex(key, ttl or self.ttl, raw)
            logger.info("agent_cache_set", agent=agent_name, key=key[:30])
        except Exception as e:
            logger.warning("agent_cache_set_error", error=str(e))

    async def invalidate(self, agent_name: str, input_data: dict, project_context: dict) -> None:
        """Remove a specific cache entry."""
        try:
            r = await self._get_redis()
            key = self._make_key(agent_name, input_data, project_context)
            await r.delete(key)
        except Exception:
            pass

    async def invalidate_agent(self, agent_name: str) -> int:
        """Remove all cache entries for a specific agent.

        Returns:
            Number of keys deleted.
        """
        try:
            r = await self._get_redis()
            pattern = f"agent_cache:{agent_name}:*"
            keys = []
            async for key in r.scan_iter(match=pattern, count=100):
                keys.append(key)
            if keys:
                await r.delete(*keys)
                logger.info("agent_cache_invalidated", agent=agent_name, count=len(keys))
            return len(keys)
        except Exception as e:
            logger.warning("agent_cache_invalidate_error", error=str(e))
            return 0

    async def flush_all(self) -> None:
        """Clear entire agent cache (all agents)."""
        try:
            r = await self._get_redis()
            keys = []
            async for key in r.scan_iter(match="agent_cache:*", count=200):
                keys.append(key)
            if keys:
                await r.delete(*keys)
                logger.info("agent_cache_flushed", count=len(keys))
        except Exception as e:
            logger.warning("agent_cache_flush_error", error=str(e))

    async def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        try:
            r = await self._get_redis()
            agents: dict[str, int] = {}
            total = 0
            async for key in r.scan_iter(match="agent_cache:*", count=200):
                total += 1
                parts = key.split(":")
                if len(parts) >= 2:
                    agent = parts[1]
                    agents[agent] = agents.get(agent, 0) + 1
            return {"total_entries": total, "by_agent": agents}
        except Exception:
            return {"total_entries": 0, "by_agent": {}}

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()
            self._redis = None


# ── Singleton ──

_agent_cache: AgentCache | None = None


def get_agent_cache() -> AgentCache:
    global _agent_cache
    if _agent_cache is None:
        _agent_cache = AgentCache()
    return _agent_cache
