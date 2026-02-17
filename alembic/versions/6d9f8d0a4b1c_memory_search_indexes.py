"""memory search indexes

Revision ID: 6d9f8d0a4b1c
Revises: 2f3bc0531b0d
Create Date: 2026-02-17 20:25:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers
revision: str = "6d9f8d0a4b1c"
down_revision: Union[str, None] = "2f3bc0531b0d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_memories_metadata_gin",
        "memories",
        ["metadata"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_memories_active_created",
        "memories",
        ["is_active", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memories_active_created", table_name="memories")
    op.drop_index("ix_memories_metadata_gin", table_name="memories")
