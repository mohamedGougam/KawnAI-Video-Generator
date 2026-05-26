"""FastAPI entrypoint for the Kawn Video Generation backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import video_routes
from app.config import generated_static_mount, get_settings, resolve_storage_path
from app.models.video_schema import HealthResponse
from app.utils.gpu_check import describe_device_mode, get_gpu_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kawn.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.services.job_queue import close_arq_pool

    await close_arq_pool()


app = FastAPI(
    title="Kawn Video Generation API",
    version="1.0.0",
    description="Text-to-video engine for Kawn — Hugging Face Diffusers (Wan2.1) with CPU/GPU auto selection.",
    lifespan=lifespan,
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict[str, str | dict[str, str]]:
    """Landing when someone opens the API base URL in a browser."""
    return {
        "service": "Kawn Video Generation API",
        "message": (
            "Unified stack: open / for the creator UI, /docs for the API playground, "
            "/health for status."
        ),
        "links": {
            "docs": "/docs",
            "health": "/health",
            "openapi": "/openapi.json",
            "api_v1": "/api/v1/models",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    s = get_settings()
    gpu = get_gpu_info()
    job_queue: Literal["inline", "redis"] = "redis" if (s.redis_url or "").strip() else "inline"
    return HealthResponse(
        status="ok",
        inference_backend="huggingface",
        device=describe_device_mode(s.device),
        cuda_available=gpu.cuda_available,
        cuda_device=gpu.device_name,
        cuda_version=gpu.cuda_version,
        message=gpu.message,
        job_queue=job_queue,
    )


app.include_router(video_routes.router)

_s = get_settings()
_gen_root = generated_static_mount(_s)
_gen_root.mkdir(parents=True, exist_ok=True)
resolve_storage_path(_s.generated_video_dir).mkdir(parents=True, exist_ok=True)
resolve_storage_path(_s.generated_thumbnail_dir).mkdir(parents=True, exist_ok=True)

app.mount(
    "/generated",
    StaticFiles(directory=str(_gen_root)),
    name="generated",
)

logger.info(
    "Kawn Video Generation API ready (inference=huggingface, device_mode=%s)",
    describe_device_mode(settings.device),
)
