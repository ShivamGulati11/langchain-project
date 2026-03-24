"""Journey schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JourneyInstanceRead(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    definition_version: str
    state: str
    current_step_index: int
    next_action_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
