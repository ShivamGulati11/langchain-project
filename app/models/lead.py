"""Lead and Batch SQLAlchemy models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Batch(Base):
    """Tracks an ingestion batch (file upload or API bulk-create)."""

    __tablename__ = "batches"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # csv | api | s3
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending | processing | completed | failed
    total_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invalid_rows: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("config_versions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leads: Mapped[list[Lead]] = relationship("Lead", back_populates="batch")


class Lead(Base):
    """Core lead record – immutable identity fields, mutable status projection."""

    __tablename__ = "leads"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("batches.batch_id"), nullable=True, index=True
    )
    # PII stored hashed where required; raw stored encrypted at rest
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Status as mutable projection from event store
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="new"
    )  # new | deduping | qualified | rejected | communicating | completed
    winning_nbfc_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    config_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("config_versions.id"), nullable=True
    )
    dnd: Mapped[bool] = mapped_column(default=False)
    consent_given: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    batch: Mapped[Batch | None] = relationship("Batch", back_populates="leads")
    dedupe_logs: Mapped[list] = relationship("DedupeLog", back_populates="lead")
    journey_instances: Mapped[list] = relationship("JourneyInstance", back_populates="lead")
    communication_logs: Mapped[list] = relationship("CommunicationLog", back_populates="lead")
