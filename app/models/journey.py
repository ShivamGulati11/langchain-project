"""Journey instance model – state machine per lead."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JourneyInstance(Base):
    """Tracks a single communication journey for a lead."""

    __tablename__ = "journey_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.lead_id"), nullable=False, index=True
    )
    definition_version: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default="started"
    )  # started | running | completed | stopped | failed
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_action_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    config_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped = relationship("Lead", back_populates="journey_instances")
    communication_logs: Mapped[list] = relationship(
        "CommunicationLog", back_populates="journey_instance"
    )
