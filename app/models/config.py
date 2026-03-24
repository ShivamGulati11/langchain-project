"""Configuration version model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConfigVersion(Base):
    """Versioned, audited configuration for NBFC priorities and communication sequences."""

    __tablename__ = "config_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft"
    )  # draft | published | archived
    # JSON blobs (stored as text; validate in service layer)
    nbfc_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    comm_sequence: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    journey_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Audit
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Rollback pointer
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("config_versions.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
