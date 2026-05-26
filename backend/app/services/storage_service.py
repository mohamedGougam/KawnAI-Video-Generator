"""Filesystem paths for generated assets."""

from __future__ import annotations

from pathlib import Path

from app.config import Settings, resolve_storage_path


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self._video_dir = resolve_storage_path(settings.generated_video_dir)
        self._thumb_dir = resolve_storage_path(settings.generated_thumbnail_dir)
        self._video_dir.mkdir(parents=True, exist_ok=True)
        self._thumb_dir.mkdir(parents=True, exist_ok=True)

    def video_abs_path(self, video_id: str) -> Path:
        return self._video_dir / f"{video_id}.mp4"

    def thumbnail_abs_path(self, video_id: str) -> Path:
        return self._thumb_dir / f"{video_id}.png"

    def public_video_url(self, video_id: str) -> str:
        return f"/generated/videos/{video_id}.mp4"

    def public_thumbnail_url(self, video_id: str) -> str:
        return f"/generated/thumbnails/{video_id}.png"

    def delete_assets(self, video_id: str) -> None:
        for p in (self.video_abs_path(video_id), self.thumbnail_abs_path(video_id)):
            if p.exists():
                p.unlink()
