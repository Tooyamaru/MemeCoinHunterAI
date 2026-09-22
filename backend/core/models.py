"""Minimal infrastructure-only SQLAlchemy metadata."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class SystemMetadata(Base):
    """Key/value metadata reserved for infrastructure, not trading data."""

    __tablename__ = "system_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PaperLifecycleRun(Base):
    """Append-only root identity for one persisted P01-RTI-02 result."""

    __tablename__ = "paper_lifecycle_runs"
    __table_args__ = (
        CheckConstraint("artifact_count >= 0", name="artifact_count_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lifecycle_result_digest: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )
    lifecycle_contract_version: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(64))
    reason_codes_json: Mapped[str] = mapped_column(Text)
    admission_digest: Mapped[str] = mapped_column(String(64))
    decision_intent_digest: Mapped[str | None] = mapped_column(String(64))
    simulation_input_digest: Mapped[str | None] = mapped_column(String(64))
    fill_digest: Mapped[str | None] = mapped_column(String(64))
    transition_digest: Mapped[str | None] = mapped_column(String(64))
    ledger_digest: Mapped[str | None] = mapped_column(String(64))
    reconciliation_digest: Mapped[str | None] = mapped_column(String(64))
    paper_result_digest: Mapped[str | None] = mapped_column(String(64))
    history_digest: Mapped[str | None] = mapped_column(String(64))
    observation_digest: Mapped[str | None] = mapped_column(String(64))
    artifact_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PaperLifecycleArtifact(Base):
    """Append-only canonical artifact snapshot owned by one lifecycle run."""

    __tablename__ = "paper_lifecycle_artifacts"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_kind", name="uq_paper_artifact_run_kind"),
        UniqueConstraint("run_id", "ordinal", name="uq_paper_artifact_run_ordinal"),
        CheckConstraint("ordinal > 0", name="ordinal_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("paper_lifecycle_runs.id", ondelete="RESTRICT"), index=True
    )
    artifact_kind: Mapped[str] = mapped_column(String(64))
    artifact_digest: Mapped[str] = mapped_column(String(64))
    payload_digest: Mapped[str] = mapped_column(String(64))
    owner_contract_version: Mapped[str] = mapped_column(String(128))
    canonical_payload: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
