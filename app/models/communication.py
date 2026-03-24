"""Communication log model."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CommunicationLog(Base):
    """Every send attempt across any channel/partner."""

    __tablename__ = "communication_logs"

    comm_send_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.lead_id"), nullable=False, index=True
    )
    journey_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journey_instances.id"),
        nullable=True,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(30), nullable=False)  # whatsapp | sms | email | ivr
    partner: Mapped[str] = mapped_column(String(50), nullable=False)
    partner_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="requested"
    )  # requested | accepted | failed | delivered | read | clicked | bounced
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped = relationship("Lead", back_populates="communication_logs")
    journey_instance: Mapped = relationship(
        "JourneyInstance", back_populates="communication_logs"
    )
    event_logs: Mapped[list] = relationship("EventLog", back_populates="comm_send")
