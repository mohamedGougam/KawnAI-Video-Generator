"""Video generation jobs.

- **Inline mode** (no `REDIS_URL`): `VideoGenerationService` schedules `execute_job` via asyncio.
- **Redis mode** (`REDIS_URL` set): the API enqueues via `app.services.job_queue`; workers run
  `process_video_job` in `app.worker_settings` (see `deploy/start.sh` for same-container worker).
"""

__all__: list[str] = []
