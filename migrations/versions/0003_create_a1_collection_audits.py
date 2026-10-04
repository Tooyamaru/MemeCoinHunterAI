"""Add an independent append-only A1 collection audit/link table.

Revision ID: 0003_a1_collection_audit
Revises: 0002_paper_lifecycle
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_a1_collection_audit"
down_revision = "0002_paper_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "a1_collection_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("lifecycle_result_digest", sa.String(64), nullable=False),
        sa.Column("collection_id", sa.String(128), nullable=False),
        sa.Column("packet_digest", sa.String(64), nullable=False),
        sa.Column("collection_digest", sa.String(64), nullable=False),
        sa.Column("selected_rti11_digest", sa.String(64), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("audit_digest", sa.String(64), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_a1_collection_audits"),
        sa.ForeignKeyConstraint(
            ["run_id"], ["paper_lifecycle_runs.id"], ondelete="RESTRICT",
            name="fk_a1_collection_audits_run_id_paper_lifecycle_runs",
        ),
        sa.UniqueConstraint("run_id", name="uq_a1_collection_audits_run_id"),
        sa.UniqueConstraint("lifecycle_result_digest",
                            name="uq_a1_collection_audits_lifecycle_result_digest"),
        sa.UniqueConstraint("audit_digest", name="uq_a1_collection_audits_audit_digest"),
    )


def downgrade() -> None:
    # Deliberate downgrade affects only the new attachment table.
    op.drop_table("a1_collection_audits")
