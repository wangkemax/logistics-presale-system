"""Logistics Presale AI System — FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.rate_limiter import RateLimitMiddleware
from app.core.middleware import SecurityHeadersMiddleware, RequestLoggingMiddleware, InputSanitizationMiddleware
from app.core.logging import setup_logging
from app.core.metrics import MetricsMiddleware, register_metrics_endpoint
from app.api.routes import auth, projects
from app.api.routes import quotations as quotations_routes
from app.api.routes import knowledge as knowledge_routes
from app.api.routes import documents as documents_routes
from app.api.routes import editor as editor_routes
from app.api.routes import prompts as prompts_routes
from app.api.routes import export as export_routes
from app.api.routes import templates as templates_routes
from app.api.routes import batch as batch_routes
from app.api.routes import preferences as preferences_routes
from app.api.routes import approval as approval_routes
from app.api.routes import analytics as analytics_routes
from app.services.websocket_service import router as ws_router, manager as ws_manager

settings = get_settings()

# Initialize structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await ws_manager.init_redis()
    yield
    await ws_manager.shutdown_redis()
    await engine.dispose()


app = FastAPI(
    title="Logistics Presale AI System",
    description=(
        "物流售前解决方案及报价系统 — 基于多 Agent 协同的 AI 平台\n\n"
        "## Core Features\n"
        "- 招标文件智能解析\n"
        "- AI 多 Agent 协同方案设计\n"
        "- 自动化成本建模与报价\n"
        "- 标书/PPT/报价单一键生成\n"
        "- QA 质量门禁\n"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Middleware (order matters: last added = first executed)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(InputSanitizationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
)

# Routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(quotations_routes.router, prefix="/api/v1")
app.include_router(knowledge_routes.router, prefix="/api/v1")
app.include_router(documents_routes.router, prefix="/api/v1")
app.include_router(editor_routes.router, prefix="/api/v1")
app.include_router(prompts_routes.router, prefix="/api/v1")
app.include_router(export_routes.router, prefix="/api/v1")
app.include_router(templates_routes.router, prefix="/api/v1")
app.include_router(batch_routes.router, prefix="/api/v1")
app.include_router(preferences_routes.router, prefix="/api/v1")
app.include_router(approval_routes.router, prefix="/api/v1")
app.include_router(analytics_routes.router, prefix="/api/v1")
app.include_router(ws_router)


# ── LLM Providers API ──
@app.get("/api/v1/llm/providers")
async def list_providers():
    """List available LLM providers and their models."""
    from app.core.llm import get_available_providers
    return get_available_providers()

# Prometheus metrics
register_metrics_endpoint(app)


@app.get("/")
async def root():
    return {
        "name": "Logistics Presale AI System",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Enhanced health check — verifies DB, Redis, and core services."""
    import redis.asyncio as aioredis

    checks = {"api": "ok"}

    # Database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:50]}"

    # WebSocket manager
    checks["websocket_connections"] = ws_manager.active_connections

    # Cache stats
    try:
        from app.services.agent_cache import get_agent_cache
        cache = get_agent_cache()
        cache_stats = await cache.stats()
        checks["agent_cache_entries"] = cache_stats["total_entries"]
    except Exception:
        checks["agent_cache_entries"] = "unavailable"

    all_ok = all(v == "ok" for k, v in checks.items() if k in ("api", "database", "redis"))
    return {
        "status": "healthy" if all_ok else "degraded",
        "checks": checks,
    }
