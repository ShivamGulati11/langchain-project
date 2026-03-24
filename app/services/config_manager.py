"""Configuration version management service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import ConfigVersion

logger = structlog.get_logger(__name__)


class ConfigManagerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_draft(
        self,
        name: str,
        nbfc_config: Optional[dict] = None,
        comm_sequence: Optional[dict] = None,
        retry_config: Optional[dict] = None,
        journey_config: Optional[dict] = None,
        created_by: Optional[str] = None,
    ) -> ConfigVersion:
        config = ConfigVersion(
            name=name,
            status="draft",
            nbfc_config=json.dumps(nbfc_config) if nbfc_config else None,
            comm_sequence=json.dumps(comm_sequence) if comm_sequence else None,
            retry_config=json.dumps(retry_config) if retry_config else None,
            journey_config=json.dumps(journey_config) if journey_config else None,
            created_by=created_by,
        )
        self.db.add(config)
        await self.db.flush()
        logger.info("Config draft created", config_id=str(config.id), name=name)
        return config

    async def publish(
        self, config_id: uuid.UUID, published_by: Optional[str] = None
    ) -> ConfigVersion:
        config = await self._get_or_raise(config_id)
        if config.status != "draft":
            raise ValueError(f"Config {config_id} is not in draft status")
        config.status = "published"
        config.published_by = published_by
        config.published_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("Config published", config_id=str(config_id))
        return config

    async def rollback(
        self, config_id: uuid.UUID, target_version_id: uuid.UUID, rolled_back_by: Optional[str] = None
    ) -> ConfigVersion:
        target = await self._get_or_raise(target_version_id)
        new_config = ConfigVersion(
            name=target.name,
            nbfc_config=target.nbfc_config,
            comm_sequence=target.comm_sequence,
            retry_config=target.retry_config,
            journey_config=target.journey_config,
            status="draft",
            previous_version_id=target_version_id,
            created_by=rolled_back_by,
        )
        self.db.add(new_config)
        await self.db.flush()
        logger.info(
            "Config rolled back",
            new_config_id=str(new_config.id),
            from_version=str(target_version_id),
        )
        return new_config

    async def get_active_config(self) -> Optional[ConfigVersion]:
        result = await self.db.execute(
            select(ConfigVersion)
            .where(ConfigVersion.status == "published")
            .order_by(ConfigVersion.published_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_nbfc_priority(self, config_version_id: Optional[uuid.UUID] = None) -> list[str]:
        config = None
        if config_version_id:
            config = await self._get_or_raise(config_version_id)
        else:
            config = await self.get_active_config()

        if config and config.nbfc_config:
            data = json.loads(config.nbfc_config)
            return data.get("nbfc_priority", [])
        # Default fallback
        return ["NBFC_A", "NBFC_B", "NBFC_C"]

    async def _get_or_raise(self, config_id: uuid.UUID) -> ConfigVersion:
        result = await self.db.execute(
            select(ConfigVersion).where(ConfigVersion.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError(f"Config version {config_id} not found")
        return config
