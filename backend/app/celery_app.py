"""Celery application factory.

Uses Redis as broker/backend.  Falls back to synchronous execution
if Redis is unavailable (useful for local development without Docker).
"""

from __future__ import annotations

import logging
import os

from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"))

celery_app = Celery(
    "ledgerpilot",
    broker=REDIS_URL,
    backend=REDIS_URL,
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
    # Retry configuration
    task_default_retry_delay=30,
    task_max_retries=3,
    # Result expiry
    result_expires=3600,
)

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])
