"""Orchestrates moderation, persistence, and provider execution."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from app.config import Settings, backend_root, get_settings, resolve_storage_path
from app.models.video_schema import VideoGenerateRequest, VideoRecordResponse
from app.services.metadata_store import VideoMetadataStore, VideoRow
from app.services.model_provider import HuggingFaceVideoProvider
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(backend_root()))
    except ValueError:
        return str(path)


class VideoGenerationService:
    def __init__(
        self,
        *,
        settings: Settings,
        store: VideoMetadataStore,
        storage: StorageService,
        provider: HuggingFaceVideoProvider,
    ) -> None:
        self._settings = settings
        self._store = store
        self._storage = storage
        self._provider = provider

    @classmethod
    def from_settings(cls, settings: Settings) -> "VideoGenerationService":
        db_path = resolve_storage_path(settings.database_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = VideoMetadataStore(db_path)
        storage = StorageService(settings)
        provider = HuggingFaceVideoProvider(
            model_id=settings.hf_model_id,
            device=settings.device,
        )
        return cls(settings=settings, store=store, storage=storage, provider=provider)

    async def start_generation(self, request: VideoGenerateRequest) -> str:
        video_id = self._store.create_pending(
            prompt=request.prompt,
            style=request.style.value,
            resolution=request.resolution.value,
            aspect_ratio=request.aspect_ratio.value,
            duration_seconds=float(request.duration_seconds),
            negative_prompt=request.negative_prompt,
        )
        if (self._settings.redis_url or "").strip():
            from app.services.job_queue import enqueue_video_job

            try:
                await enqueue_video_job(
                    video_id=video_id,
                    request_payload=request.model_dump(mode="json"),
                )
            except Exception as e:
                logger.exception("Redis enqueue failed for %s", video_id)
                self._store.mark_failed(video_id, f"Queue enqueue failed: {e}")
                raise
        else:
            task = asyncio.create_task(self.execute_job(video_id, request))
            task.add_done_callback(self._log_task_exception)
        return video_id

    def _log_task_exception(self, task: asyncio.Task[None]) -> None:
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.exception("Background video job failed: %s", exc)

    async def execute_job(self, video_id: str, request: VideoGenerateRequest) -> None:
        video_path = self._storage.video_abs_path(video_id)
        thumb_path = self._storage.thumbnail_abs_path(video_id)
        try:
            await self._provider.generate(
                video_id=video_id,
                request=request,
                video_path=video_path,
                thumbnail_path=thumb_path,
                fps=self._settings.default_fps,
            )
            self._store.mark_completed(
                video_id,
                video_path=_relative_or_absolute(video_path),
                thumbnail_path=_relative_or_absolute(thumb_path),
            )
        except Exception as e:
            logger.exception("Generation failed for %s", video_id)
            self._store.mark_failed(video_id, str(e))
            if video_path.exists():
                video_path.unlink()
            if thumb_path.exists():
                thumb_path.unlink()

    def get_video(self, video_id: str) -> VideoRecordResponse | None:
        row = self._store.get(video_id)
        if row is None:
            return None
        return self._row_to_response(row)

    def list_videos(self, limit: int = 50) -> list[VideoRecordResponse]:
        return [self._row_to_response(r) for r in self._store.list_recent(limit)]

    def delete_video(self, video_id: str) -> bool:
        row = self._store.get(video_id)
        if row is None:
            return False
        self._storage.delete_assets(video_id)
        return self._store.delete(video_id)

    def _row_to_response(self, row: VideoRow) -> VideoRecordResponse:
        msg: str | None = None
        if row.status == "processing":
            msg = "Video generation in progress."
        elif row.status == "failed":
            msg = row.error or "Generation failed."

        video_url = (
            self._storage.public_video_url(row.video_id)
            if row.status == "completed"
            else None
        )
        thumb_url = (
            self._storage.public_thumbnail_url(row.video_id)
            if row.status == "completed"
            else None
        )
        created = None
        try:
            created = datetime.fromisoformat(row.created_at)
        except ValueError:
            created = None

        return VideoRecordResponse(
            video_id=row.video_id,
            status=row.status,  # type: ignore[arg-type]
            prompt=row.prompt,
            style=row.style,
            video_url=video_url,
            thumbnail_url=thumb_url,
            created_at=created,
            error=row.error,
            message=msg,
        )


_service: VideoGenerationService | None = None


def get_video_service() -> VideoGenerationService:
    global _service
    if _service is None:
        _service = VideoGenerationService.from_settings(get_settings())
    return _service
