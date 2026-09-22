"""create paper lifecycle persistence

Revision ID: 0002_paper_lifecycle
Revises: 0001_system_metadata
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_paper_lifecycle"
down_revision: Union[str, Sequence[str], None] = "0001_system_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "paper_lifecycle_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lifecycle_result_digest", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_contract_version", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("reason_codes_json", sa.Text(), nullable=False),
        sa.Column("admission_digest", sa.String(length=64), nullable=False),
        sa.Column("decision_intent_digest", sa.String(length=64), nullable=True),
        sa.Column("simulation_input_digest", sa.String(length=64), nullable=True),
        sa.Column("fill_digest", sa.String(length=64), nullable=True),
        sa.Column("transition_digest", sa.String(length=64), nullable=True),
        sa.Column("ledger_digest", sa.String(length=64), nullable=True),
        sa.Column("reconciliation_digest", sa.String(length=64), nullable=True),
        sa.Column("paper_result_digest", sa.String(length=64), nullable=True),
        sa.Column("history_digest", sa.String(length=64), nullable=True),
        sa.Column("observation_digest", sa.String(length=64), nullable=True),
        sa.Column("artifact_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "artifact_count >= 0",
            name="ck_paper_lifecycle_runs_artifact_count_non_negative",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_paper_lifecycle_runs"),
        sa.UniqueConstraint(
            "lifecycle_result_digest",
            name="uq_paper_lifecycle_runs_lifecycle_result_digest",
        ),
    )
    op.create_index(
        "ix_paper_lifecycle_runs_lifecycle_result_digest",
        "paper_lifecycle_runs",
        ["lifecycle_result_digest"],
        unique=False,
    )
    op.create_table(
        "paper_lifecycle_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("artifact_digest", sa.String(length=64), nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("owner_contract_version", sa.String(length=128), nullable=False),
        sa.Column("canonical_payload", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ordinal > 0",
            name="ck_paper_lifecycle_artifacts_ordinal_positive",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["paper_lifecycle_runs.id"],
            name="fk_paper_lifecycle_artifacts_run_id_paper_lifecycle_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_paper_lifecycle_artifacts"),
        sa.UniqueConstraint(
            "run_id",
            "artifact_kind",
            name="uq_paper_artifact_run_kind",
        ),
        sa.UniqueConstraint(
            "run_id",
            "ordinal",
            name="uq_paper_artifact_run_ordinal",
        ),
    )
    op.create_index(
        "ix_paper_lifecycle_artifacts_run_id",
        "paper_lifecycle_artifacts",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_paper_lifecycle_artifacts_run_id",
        table_name="paper_lifecycle_artifacts",
    )
    op.drop_table("paper_lifecycle_artifacts")
    op.drop_index(
        "ix_paper_lifecycle_runs_lifecycle_result_digest",
        table_name="paper_lifecycle_runs",
    )
    op.drop_table("paper_lifecycle_runs")
