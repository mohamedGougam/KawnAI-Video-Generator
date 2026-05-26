"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    video_provider: Literal["mock", "huggingface"] = "mock"
    hf_model_id: str = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
    device: str = "cuda"
    default_resolution: str = "720p"
    default_aspect_ratio: str = "9:16"
    max_duration_seconds: int = 10
    generated_video_dir: str = "generated/videos"
    generated_thumbnail_dir: str = "generated/thumbnails"
    database_path: str = "generated/metadata/videos.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    default_fps: int = 16
    mock_sample_video_path: str | None = None

    @field_validator("mock_sample_video_path", mode="before")
    @classmethod
    def _empty_mock_path_to_none(cls, v: object) -> object:
        if v == "":
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


def backend_root() -> Path:
    """Directory containing `app/` (the backend package root)."""
    return Path(__file__).resolve().parent.parent
