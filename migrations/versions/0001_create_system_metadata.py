"""create system metadata

Revision ID: 0001_system_metadata
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_system_metadata"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_system_metadata"),
        sa.UniqueConstraint("key", name="uq_system_metadata_key"),
    )
    op.create_index("ix_system_metadata_key", "system_metadata", ["key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_system_metadata_key", table_name="system_metadata")
    op.drop_table("system_metadata")
