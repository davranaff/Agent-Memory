"""backfill project schema tables and component line columns

Revision ID: a7e6c3f9d1b2
Revises: 6d9f8d0a4b1c
Create Date: 2026-02-18 03:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.models import Project, Component, CodePattern, Documentation


# revision identifiers
revision: str = "a7e6c3f9d1b2"
down_revision: Union[str, None] = "6d9f8d0a4b1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    # Ensure project-analysis tables exist in environments that were migrated
    # only through earlier Alembic revisions.
    Project.__table__.create(bind, checkfirst=True)
    Component.__table__.create(bind, checkfirst=True)
    CodePattern.__table__.create(bind, checkfirst=True)
    Documentation.__table__.create(bind, checkfirst=True)

    inspector = sa.inspect(bind)

    # Backfill columns used by indexer/registry APIs.
    if not _column_exists(inspector, "components", "line_start"):
        op.add_column("components", sa.Column("line_start", sa.Integer(), nullable=True))
    if not _column_exists(inspector, "components", "line_end"):
        op.add_column("components", sa.Column("line_end", sa.Integer(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _column_exists(inspector, "components", "line_end"):
        op.drop_column("components", "line_end")
    if _column_exists(inspector, "components", "line_start"):
        op.drop_column("components", "line_start")
