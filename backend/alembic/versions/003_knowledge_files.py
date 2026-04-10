"""Add file_path and file_name to knowledge_entries."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003_knowledge_files"
down_revision: Union[str, None] = "002_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_entries", sa.Column("file_path", sa.String(500), nullable=True))
    op.add_column("knowledge_entries", sa.Column("file_name", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("knowledge_entries", "file_name")
    op.drop_column("knowledge_entries", "file_path")
