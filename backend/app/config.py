"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def backend_root() -> Path:
    """Directory containing `app/` (the backend package root)."""
    return Path(__file__).resolve().parent.parent


def resolve_storage_path(path_str: str) -> Path:
    """Resolve a path from settings: absolute paths are kept; relative paths are under `backend_root()`."""
    p = Path(path_str)
    if p.is_absolute():
        return p
    return (backend_root() / p).resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hf_model_id: str = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
    # cuda | cpu | auto — use `auto` on Render (CPU) or GPU hosts (CUDA when available).
    device: str = "auto"
    default_resolution: str = "720p"
    default_aspect_ratio: str = "9:16"
    max_duration_seconds: int = 5
    generated_video_dir: str = "generated/videos"
    generated_thumbnail_dir: str = "generated/thumbnails"
    database_path: str = "generated/metadata/videos.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    default_fps: int = 16
    # When set, POST /videos/generate enqueues to Redis; run `arq app.worker_settings.WorkerSettings`
    # (or use deploy/start.sh which starts a worker when REDIS_URL is set). When unset, jobs run
    # in-process via asyncio (single-node demo).
    redis_url: str | None = None

    @field_validator("redis_url", mode="before")
    @classmethod
    def normalize_redis_url(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


@lru_cache
def get_settings() -> Settings:
    return Settings()


def generated_static_mount(settings: Settings) -> Path:
    """Directory mounted at URL prefix `/generated` (contains `videos/` and `thumbnails/`)."""
    video_dir = resolve_storage_path(settings.generated_video_dir)
    return video_dir.parent
