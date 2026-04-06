"""Database models for the Logistics Presale system."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum as SAEnum, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


# ──────────────────────────────────────────────
# User & Team
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="consultant")  # admin / consultant / client
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    team = relationship("Team", back_populates="members")
    projects = relationship("Project", back_populates="created_by_user")


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    members = relationship("User", back_populates="team")


# ──────────────────────────────────────────────
# Project (one per tender/bid)
# ──────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    client_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    status = Column(String(50), default="created")  # created / in_progress / completed / archived
    tender_file_url = Column(String(1000), nullable=True)

    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # Project assumptions (stage 0)
    assumptions = Column(JSON, nullable=True)

    created_by_user = relationship("User", back_populates="projects")
    stages = relationship("ProjectStage", back_populates="project", order_by="ProjectStage.stage_number")
    quotations = relationship("Quotation", back_populates="project")
    documents = relationship("TenderDocument", back_populates="project")
    qa_issues = relationship("QAIssue", back_populates="project")


# ──────────────────────────────────────────────
# Pipeline Stages (stage 0-11)
# ──────────────────────────────────────────────

class ProjectStage(Base):
    __tablename__ = "project_stages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage_number = Column(Integer, nullable=False)  # 0-11
    stage_name = Column(String(100), nullable=False)
    agent_name = Column(String(100), nullable=False)

    status = Column(String(50), default="pending")  # pending / running / completed / failed / skipped
    output_data = Column(JSON, nullable=True)
    qa_result = Column(String(50), nullable=True)  # PASS / CONDITIONAL_PASS / FAIL
    error_message = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    execution_time_seconds = Column(Float, nullable=True)

    project = relationship("Project", back_populates="stages")


# ──────────────────────────────────────────────
# Quotation
# ──────────────────────────────────────────────

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    scheme_name = Column(String(100), default="方案A")  # 方案A / 方案B / 方案C

    # Cost breakdown
    cost_breakdown = Column(JSON, nullable=True)  # {labor, equipment, facility, operations, software}
    total_cost = Column(Float, nullable=True)
    total_price = Column(Float, nullable=True)
    margin_rate = Column(Float, nullable=True)

    # Financial indicators
    roi = Column(Float, nullable=True)
    irr = Column(Float, nullable=True)
    npv = Column(Float, nullable=True)
    payback_months = Column(Integer, nullable=True)

    status = Column(String(50), default="draft")  # draft / submitted / approved / rejected
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project = relationship("Project", back_populates="quotations")


# ──────────────────────────────────────────────
# Tender Document
# ──────────────────────────────────────────────

class TenderDocument(Base):
    __tablename__ = "tender_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    doc_type = Column(String(50), nullable=False)  # tender_response / ppt / quotation_sheet
    version = Column(Integer, default=1)
    file_url = Column(String(1000), nullable=False)
    file_name = Column(String(500), nullable=False)
    qa_status = Column(String(50), nullable=True)
    generated_at = Column(DateTime(timezone=True), default=utcnow)

    project = relationship("Project", back_populates="documents")


# ──────────────────────────────────────────────
# QA Issues
# ──────────────────────────────────────────────

class QAIssue(Base):
    __tablename__ = "qa_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    stage_number = Column(Integer, nullable=False)
    severity = Column(String(10), nullable=False)  # P0 / P1 / P2
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    status = Column(String(50), default="open")  # open / resolved / accepted / wontfix
    created_at = Column(DateTime(timezone=True), default=utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="qa_issues")


# ──────────────────────────────────────────────
# Knowledge Base
# ──────────────────────────────────────────────

class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    category = Column(String(50), nullable=False)  # automation_case / cost_model / logistics_case
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)  # ["warehouse", "AGV", "cold-chain"]
    metadata_ = Column("metadata", JSON, nullable=True)
    embedding_id = Column(String(255), nullable=True)  # vector DB reference
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
