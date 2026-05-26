"""Redis (ARQ) enqueue helpers. When `REDIS_URL` is unset, jobs stay in-process."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

logger = logging.getLogger(__name__)

_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_arq_pool() -> ArqRedis | None:
    """Lazily create a shared ARQ Redis pool when `REDIS_URL` is configured."""
    global _pool
    url = (get_settings().redis_url or "").strip()
    if not url:
        return None
    async with _pool_lock:
        if _pool is None:
            _pool = await create_pool(RedisSettings.from_dsn(url))
            logger.info("ARQ Redis pool created for job queue")
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose(close_connection_pool=True)
        _pool = None
        logger.info("ARQ Redis pool closed")


async def enqueue_video_job(*, video_id: str, request_payload: dict[str, Any]) -> None:
    """Push a generation job to Redis. Worker function name must match `worker_settings`."""
    pool = await get_arq_pool()
    if pool is None:
        raise RuntimeError("enqueue_video_job requires REDIS_URL to be set")
    await pool.enqueue_job("process_video_job", video_id, request_payload)
