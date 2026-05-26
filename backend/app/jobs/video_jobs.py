"""Background/async helpers for long-running video jobs (reserved for future queue)."""

# Video jobs are currently scheduled via `asyncio.create_task` from
# `VideoGenerationService`. This module is a placeholder for a Redis/RQ/Celery
# migration without changing API routes.

__all__: list[str] = []
