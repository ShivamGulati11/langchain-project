"""Celery application and task definitions."""
from __future__ import annotations

import asyncio
import uuid

import structlog
from celery import Celery

from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)

celery_app = Celery(
    "loce",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="loce.process_batch", bind=True, max_retries=3)
def process_batch_task(self, batch_id: str):
    """Process a CSV batch asynchronously."""
    from app.workers.dedupe_worker import _process_batch

    try:
        _run_async(_process_batch(uuid.UUID(batch_id)))
    except Exception as exc:
        logger.error("Batch processing failed", batch_id=batch_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(name="loce.run_dedupe", bind=True, max_retries=3)
def run_dedupe_task(self, lead_id: str):
    """Run NBFC waterfall dedupe for a single lead."""
    from app.workers.dedupe_worker import _run_dedupe

    try:
        _run_async(_run_dedupe(uuid.UUID(lead_id)))
    except Exception as exc:
        logger.error("Dedupe task failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="loce.start_journey", bind=True, max_retries=3)
def start_journey_task(self, lead_id: str, winning_nbfc_id: str):
    """Start a communication journey for a qualified lead."""
    from app.workers.journey_worker import _start_journey

    try:
        _run_async(_start_journey(uuid.UUID(lead_id), winning_nbfc_id))
    except Exception as exc:
        logger.error("Journey start failed", lead_id=lead_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="loce.advance_journey", bind=True, max_retries=3)
def advance_journey_task(self, journey_id: str):
    """Advance a journey to the next step (triggered by timer)."""
    from app.workers.journey_worker import _advance_journey

    try:
        _run_async(_advance_journey(uuid.UUID(journey_id)))
    except Exception as exc:
        logger.error("Journey advance failed", journey_id=journey_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)
