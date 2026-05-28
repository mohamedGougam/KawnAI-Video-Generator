"""ARQ worker: pull video jobs from Redis and run inference (separate from FastAPI process)."""

from __future__ import annotations

import logging
import os
from typing import Any

from arq.connections import RedisSettings

from app.models.video_schema import VideoGenerateRequest
from app.services.video_generation_service import get_worker_video_service

logger = logging.getLogger(__name__)


async def process_video_job(ctx: dict[str, Any], video_id: str, request_payload: dict[str, Any]) -> None:
    req = VideoGenerateRequest.model_validate(request_payload)
    svc = get_worker_video_service()
    await svc.execute_job(video_id, req)


def _redis_settings() -> RedisSettings:
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "REDIS_URL must be set for the ARQ worker (same value as the API service)."
        )
    return RedisSettings.from_dsn(url)


class WorkerSettings:
    functions = [process_video_job]
    redis_settings = _redis_settings()
    # Video diffusion is GPU/CPU-bound; one job at a time per worker process is typical.
    max_jobs = 1
    job_timeout = 3600
