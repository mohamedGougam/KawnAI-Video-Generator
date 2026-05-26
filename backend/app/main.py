"""FastAPI entrypoint for the Kawn Video Generation backend."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import video_routes
from app.config import backend_root, get_settings
from app.models.video_schema import HealthResponse
from app.utils.gpu_check import get_gpu_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kawn.backend")

app = FastAPI(
    title="Kawn Video Generation API",
    version="1.0.0",
    description="Text-to-video engine for Kawn — mock-first with pluggable HF/Diffusers providers.",
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


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    s = get_settings()
    gpu = get_gpu_info()
    return HealthResponse(
        status="ok",
        video_provider=s.video_provider,
        cuda_available=gpu.cuda_available,
        cuda_device=gpu.device_name,
        cuda_version=gpu.cuda_version,
        message=gpu.message,
    )


app.include_router(video_routes.router)

_gen_root = backend_root() / "generated"
_gen_root.mkdir(parents=True, exist_ok=True)
app.mount(
    "/generated",
    StaticFiles(directory=str(_gen_root)),
    name="generated",
)

logger.info("Kawn Video Generation API ready (provider=%s)", settings.video_provider)
