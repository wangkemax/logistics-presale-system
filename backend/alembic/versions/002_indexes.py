"""Add performance indexes.

Revision ID: 002_indexes
Revises: 001_initial
Create Date: 2026-04-08
"""
from typing import Sequence, Union
from alembic import op

revision: str = "002_indexes"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Project queries: list by user, filter by status
    op.create_index("ix_projects_created_by_status", "projects", ["created_by", "status"])
    op.create_index("ix_projects_updated_at", "projects", ["updated_at"])

    # Stage queries: get all stages for a project, ordered by number
    op.create_index("ix_stages_project_status", "project_stages", ["project_id", "status"])

    # QA issues: filter by severity and status
    op.create_index("ix_qa_issues_severity_status", "qa_issues", ["project_id", "severity", "status"])

    # Quotations: lookup by project and status
    op.create_index("ix_quotations_project_status", "quotations", ["project_id", "status"])

    # Knowledge: search by category + active
    op.create_index("ix_knowledge_category_active", "knowledge_entries", ["category", "is_active"])

    # Tender documents: list by project
    op.create_index("ix_tender_docs_project", "tender_documents", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_tender_docs_project")
    op.drop_index("ix_knowledge_category_active")
    op.drop_index("ix_quotations_project_status")
    op.drop_index("ix_qa_issues_severity_status")
    op.drop_index("ix_stages_project_status")
    op.drop_index("ix_projects_updated_at")
    op.drop_index("ix_projects_created_by_status")
