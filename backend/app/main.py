"""Logistics Presale AI System — FastAPI Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.core.config import get_settings
from app.core.database import engine, Base
from app.api.routes import auth, projects
from app.api.routes import quotations as quotations_routes
from app.api.routes import knowledge as knowledge_routes
from app.api.routes import documents as documents_routes
from app.services.websocket_service import router as ws_router, manager as ws_manager

settings = get_settings()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Create tables on startup (dev only; use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Initialize WebSocket Redis pub/sub
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
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(quotations_routes.router, prefix="/api/v1")
app.include_router(knowledge_routes.router, prefix="/api/v1")
app.include_router(documents_routes.router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/")
async def root():
    return {
        "name": "Logistics Presale AI System",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
