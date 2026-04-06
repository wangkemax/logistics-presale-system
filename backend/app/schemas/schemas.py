"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────
# Auth
# ──────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6)
    role: str = "consultant"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
# Project
# ──────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    client_name: str | None = None
    industry: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    client_name: str | None
    industry: str | None
    status: str
    tender_file_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    assumptions: dict | None
    stages: list["StageResponse"]
    quotations: list["QuotationResponse"]


# ──────────────────────────────────────────────
# Pipeline Stage
# ──────────────────────────────────────────────

class StageResponse(BaseModel):
    id: UUID
    stage_number: int
    stage_name: str
    agent_name: str
    status: str
    output_data: dict | None
    qa_result: str | None
    confidence: float | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    execution_time_seconds: float | None

    model_config = {"from_attributes": True}


class StageExecuteRequest(BaseModel):
    """Request to manually trigger a specific stage."""
    stage_number: int = Field(ge=0, le=11)
    override_input: dict | None = None


# ──────────────────────────────────────────────
# Quotation
# ──────────────────────────────────────────────

class QuotationCreate(BaseModel):
    scheme_name: str = "方案A"
    cost_breakdown: dict | None = None


class QuotationResponse(BaseModel):
    id: UUID
    version: int
    scheme_name: str
    cost_breakdown: dict | None
    total_cost: float | None
    total_price: float | None
    margin_rate: float | None
    roi: float | None
    irr: float | None
    npv: float | None
    payback_months: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QuotationUpdate(BaseModel):
    cost_breakdown: dict | None = None
    total_price: float | None = None
    margin_rate: float | None = None
    status: str | None = None


# ──────────────────────────────────────────────
# QA Issue
# ──────────────────────────────────────────────

class QAIssueResponse(BaseModel):
    id: UUID
    stage_number: int
    severity: str
    category: str | None
    description: str
    suggestion: str | None
    resolution: str | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QAIssueResolve(BaseModel):
    resolution: str
    status: str = "resolved"  # resolved / accepted / wontfix


# ──────────────────────────────────────────────
# Agent Output (internal)
# ──────────────────────────────────────────────

class AgentOutput(BaseModel):
    """Standard output from every Agent execution."""
    stage_number: int
    agent_name: str
    status: str  # success / error
    data: dict
    confidence: float = Field(ge=0, le=1)
    issues: list[dict] = []
    execution_time_seconds: float = 0.0


# ──────────────────────────────────────────────
# WebSocket Messages
# ──────────────────────────────────────────────

class WSMessage(BaseModel):
    event: str  # stage_started / stage_completed / stage_failed / pipeline_completed
    project_id: str
    stage_number: int | None = None
    data: dict | None = None
