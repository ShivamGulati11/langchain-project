"""Event log (immutable append-only event store)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventLog(Base):
    """Immutable record of every observable event in the LOCE system."""

    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # comm_send_id may be null for system-level events (batch.created etc.)
    comm_send_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("communication_logs.comm_send_id"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    # dedupe key: (partner, partner_message_id, event_type)
    partner: Mapped[str | None] = mapped_column(String(50), nullable=True)
    partner_message_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(300), nullable=False, unique=True)
    payload_ref: Mapped[str | None] = mapped_column(Text, nullable=True)  # S3/Blob URL or JSON
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    comm_send: Mapped = relationship("CommunicationLog", back_populates="event_logs")
