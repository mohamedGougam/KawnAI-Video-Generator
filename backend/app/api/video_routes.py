"""Versioned HTTP API for video generation."""

from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response

from app.config import get_settings
from app.models.video_schema import (
    ModelInfo,
    ModelsListResponse,
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoRecordResponse,
)
from app.services.moderation import moderate_prompt
from app.services.video_generation_service import (
    VideoGenerationService,
    get_video_service,
)

router = APIRouter(prefix="/api/v1", tags=["videos"])


def _render_requires_redis_queue() -> bool:
    """Render web instances are too small for inline Wan inference."""
    if not os.environ.get("RENDER"):
        return False
    return not (get_settings().redis_url or "").strip()


def get_video_generation_service() -> VideoGenerationService:
    return get_video_service()


@router.get("/models", response_model=ModelsListResponse)
def list_models() -> ModelsListResponse:
    settings = get_settings()
    models = [
        ModelInfo(
            id="Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
            name="Wan2.1 Text-to-Video 1.3B (Diffusers)",
            license_notes="Apache-2.0 style open weights; verify HF model card for your use case.",
            huggingface_repo="https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
            diffusers_support=True,
            approx_resolution="480p primary (720p requests are clamped in this backend for 1.3B)",
            notes="Default pick for practical GPU runs; strong motion and open weights.",
        ),
        ModelInfo(
            id="Wan-AI/Wan2.1-T2V-14B-Diffusers",
            name="Wan2.1 Text-to-Video 14B (Diffusers)",
            license_notes="Open weights; heavy VRAM requirements.",
            huggingface_repo="https://huggingface.co/Wan-AI/Wan2.1-T2V-14B-Diffusers",
            diffusers_support=True,
            approx_resolution="720p / 480p",
            notes="Higher fidelity and true 720p support; needs large GPU memory.",
        ),
        ModelInfo(
            id="tencent/HunyuanVideo",
            name="HunyuanVideo",
            license_notes="Check Tencent / HF card for commercial terms.",
            huggingface_repo="https://huggingface.co/tencent/HunyuanVideo",
            diffusers_support=True,
            approx_resolution="Up to 720p+ depending on recipe",
            notes="Strong open-ish research model; integration is provider-specific.",
        ),
        ModelInfo(
            id="THUDM/CogVideoX-5b",
            name="CogVideoX",
            license_notes="Check THUDM license on HF.",
            huggingface_repo="https://huggingface.co/THUDM/CogVideoX-5b",
            diffusers_support=True,
            approx_resolution="720p class",
            notes="Mature Diffusers pipelines; good alternative if Wan is too heavy.",
        ),
        ModelInfo(
            id="Lightricks/LTX-Video",
            name="LTX-Video",
            license_notes="Verify Lightricks HF license for commercial use.",
            huggingface_repo="https://huggingface.co/Lightricks/LTX-Video",
            diffusers_support=True,
            approx_resolution="720p+ depending on variant",
            notes="Efficiency-focused open video stack; good for iterative prototypes.",
        ),
        ModelInfo(
            id="genmo/mochi-1-preview",
            name="Mochi 1",
            license_notes="Apache-2.0 (preview); confirm current card.",
            huggingface_repo="https://huggingface.co/genmo/mochi-1-preview",
            diffusers_support=True,
            approx_resolution="480p class in many recipes",
            notes="Interesting quality/speed trade-offs; pipeline APIs evolve quickly.",
        ),
    ]
    return ModelsListResponse(
        selected_model_id=settings.hf_model_id,
        recommended_for_kawn="Wan2.1 T2V via Diffusers (1.3B for dev GPUs, 14B for quality)",
        research_summary=(
            "Wan2.1 ships official Diffusers checkpoints (`WanPipeline`, `WanImageToVideoPipeline`) "
            "with clear 480p/720p guidance, making it the best default for this scaffold. "
            "CogVideoX and LTX-Video are strong alternates if you need different VRAM curves."
        ),
        models=models,
    )


@router.post("/videos/generate", response_model=VideoGenerateResponse)
async def generate_video(
    body: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    service: VideoGenerationService = Depends(get_video_generation_service),
) -> VideoGenerateResponse:
    settings = get_settings()
    if body.duration_seconds > settings.max_duration_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"duration_seconds must be <= {settings.max_duration_seconds}",
        )

    moderation = moderate_prompt(body.prompt)
    if not moderation.allowed:
        raise HTTPException(status_code=400, detail=moderation.reason)

    if _render_requires_redis_queue():
        raise HTTPException(
            status_code=503,
            detail=(
                "Video generation on Render requires REDIS_URL (Key Value + ARQ worker). "
                "Sync render.yaml in the Render dashboard, or create a Key Value store and set "
                "REDIS_URL on this service to its internal connection string, then redeploy."
            ),
        )

    video_id = await service.start_generation(body, background_tasks=background_tasks)
    return VideoGenerateResponse(
        video_id=video_id,
        status="processing",
        message="Video generation started",
    )


@router.get("/videos/{video_id}", response_model=VideoRecordResponse)
def get_video(
    video_id: str,
    service: VideoGenerationService = Depends(get_video_generation_service),
) -> VideoRecordResponse:
    record = service.get_video(video_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return record


@router.get("/videos", response_model=list[VideoRecordResponse])
def list_videos(
    service: VideoGenerationService = Depends(get_video_generation_service),
) -> list[VideoRecordResponse]:
    return service.list_videos()


@router.delete("/videos/{video_id}", status_code=204, response_class=Response)
def delete_video(
    video_id: str,
    service: VideoGenerationService = Depends(get_video_generation_service),
) -> Response:
    deleted = service.delete_video(video_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Video not found")
    return Response(status_code=204)
