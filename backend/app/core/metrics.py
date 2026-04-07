"""Prometheus metrics for monitoring.

Exposes /metrics endpoint with:
- HTTP request counts and latencies
- Active WebSocket connections
- Agent execution counts and durations
- Pipeline success/failure rates
- Cache hit/miss rates
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Simple in-memory metrics (production: use prometheus_client library)


class Metrics:
    """Lightweight in-memory metrics collector."""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

    def inc(self, name: str, labels: dict | None = None, value: int = 1):
        key = self._key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + value

    def observe(self, name: str, value: float, labels: dict | None = None):
        key = self._key(name, labels)
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        # Keep only last 1000 observations
        if len(self._histograms[key]) > 1000:
            self._histograms[key] = self._histograms[key][-500:]

    def set_gauge(self, name: str, value: float, labels: dict | None = None):
        key = self._key(name, labels)
        self._gauges[key] = value

    def format_prometheus(self) -> str:
        """Format metrics in Prometheus text exposition format."""
        lines = []

        # Counters
        for key, value in sorted(self._counters.items()):
            lines.append(f"{key} {value}")

        # Gauges
        for key, value in sorted(self._gauges.items()):
            lines.append(f"{key} {value}")

        # Histograms (simplified: just count, sum, avg)
        for key, values in sorted(self._histograms.items()):
            if values:
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_sum {sum(values):.4f}")
                lines.append(f"{key}_avg {sum(values)/len(values):.4f}")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _key(name: str, labels: dict | None = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global metrics instance
metrics = Metrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        method = request.method
        path = self._normalize_path(request.url.path)
        status = str(response.status_code)

        metrics.inc("http_requests_total", {"method": method, "path": path, "status": status})
        metrics.observe("http_request_duration_seconds", duration, {"method": method, "path": path})

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize paths to avoid high-cardinality labels."""
        parts = path.strip("/").split("/")
        normalized = []
        for i, part in enumerate(parts):
            # Replace UUIDs with placeholder
            if len(part) == 36 and part.count("-") == 4:
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/" + "/".join(normalized)


def register_metrics_endpoint(app: FastAPI):
    """Register the /metrics endpoint."""

    @app.get("/metrics", response_class=PlainTextResponse, tags=["monitoring"])
    async def get_metrics():
        """Prometheus-compatible metrics endpoint."""
        # Update gauges
        from app.services.websocket_service import manager
        metrics.set_gauge("websocket_connections_active", manager.active_connections)

        try:
            from app.services.agent_cache import get_agent_cache
            cache = get_agent_cache()
            stats = await cache.stats()
            metrics.set_gauge("agent_cache_entries", stats["total_entries"])
        except Exception:
            pass

        return metrics.format_prometheus()


# ── Convenience functions for agents/services ──

def record_agent_execution(agent_name: str, status: str, duration: float):
    """Record an agent execution event."""
    metrics.inc("agent_executions_total", {"agent": agent_name, "status": status})
    metrics.observe("agent_execution_duration_seconds", duration, {"agent": agent_name})


def record_pipeline_completion(verdict: str):
    """Record a pipeline completion."""
    metrics.inc("pipeline_completions_total", {"verdict": verdict})


def record_cache_event(hit: bool):
    """Record a cache hit or miss."""
    metrics.inc("agent_cache_total", {"result": "hit" if hit else "miss"})
