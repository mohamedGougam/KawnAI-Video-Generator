"""Pydantic request/response models for the video API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class VideoStyle(str, Enum):
    cinematic = "cinematic"
    realistic = "realistic"
    animation = "animation"
    social_media_reel = "social_media_reel"
    sports = "sports"
    nature = "nature"
    futuristic = "futuristic"


class Resolution(str, Enum):
    p480 = "480p"
    p720 = "720p"
    p1080 = "1080p"


class AspectRatio(str, Enum):
    r16_9 = "16:9"
    r9_16 = "9:16"
    r1_1 = "1:1"


class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    style: VideoStyle = VideoStyle.cinematic
    duration_seconds: float = Field(default=5.0, ge=1.0, le=5.0)
    resolution: Resolution = Resolution.p720
    aspect_ratio: AspectRatio = AspectRatio.r9_16
    negative_prompt: str | None = Field(
        default="blurry, low quality, distorted faces, watermark, text artifacts",
        max_length=2000,
    )

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v: str) -> str:
        return v.strip()


class VideoGenerateResponse(BaseModel):
    video_id: str
    status: Literal["processing"] = "processing"
    message: str


class VideoRecordResponse(BaseModel):
    video_id: str
    status: Literal["processing", "completed", "failed"]
    prompt: str | None = None
    style: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime | None = None
    error: str | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    inference_backend: Literal["huggingface"] = "huggingface"
    device: str
    cuda_available: bool
    cuda_device: str | None = None
    cuda_version: str | None = None
    message: str
    job_queue: Literal["inline", "redis"] = "inline"


class ModelInfo(BaseModel):
    id: str
    name: str
    license_notes: str
    huggingface_repo: str | None
    diffusers_support: bool
    approx_resolution: str
    notes: str


class ModelsListResponse(BaseModel):
    selected_model_id: str
    recommended_for_kawn: str
    research_summary: str
    models: list[ModelInfo]
