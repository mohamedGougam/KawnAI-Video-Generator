"""Pluggable video generation providers (Hugging Face / Diffusers)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.video_schema import VideoGenerateRequest


class VideoModelProvider(ABC):
    """Abstract model backend. Swap implementations without changing API routes."""

    name: str

    @abstractmethod
    async def generate(
        self,
        *,
        video_id: str,
        request: "VideoGenerateRequest",
        video_path: Path,
        thumbnail_path: Path,
        fps: int,
    ) -> None:
        """Write an MP4 to `video_path` and a PNG thumbnail to `thumbnail_path`."""


class HuggingFaceVideoProvider(VideoModelProvider):
    """
    Wan2.1 (and compatible) text-to-video via Hugging Face Diffusers.

    The 1.3B T2V checkpoint is optimized for 480p; the 14B checkpoint supports 720p/480p.
    See README model matrix before requesting 720p on the small checkpoint.
    """

    name = "huggingface"

    def __init__(self, model_id: str, device: str) -> None:
        self._model_id = model_id
        self._device = device
        self._pipe = None
        self._loaded = False
        self._torch_device: str = "cpu"

    def _resolve_torch_device(self) -> str:
        import torch

        from app.utils.gpu_check import require_cuda_for_hf

        mode = (self._device or "auto").strip().lower()
        if mode == "cuda":
            require_cuda_for_hf()
            return "cuda"
        if mode == "cpu":
            return "cpu"
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        # TODO: Pin diffusers to a release that includes `WanPipeline` (see HF Wan2.1 docs).
        # TODO: Authenticate with Hugging Face if the repo is gated (`HF_TOKEN` / `huggingface-cli login`).
        # TODO: Consider `enable_model_cpu_offload` / `enable_sequential_cpu_offload` on low-RAM hosts.
        try:
            import torch
            from diffusers import AutoencoderKLWan, WanPipeline
            from diffusers.schedulers.scheduling_unipc_multistep import (
                UniPCMultistepScheduler,
            )
        except ImportError as e:
            raise RuntimeError(
                "diffusers/torch are not installed. Install backend/requirements.txt "
                "with the PyTorch build appropriate for your environment."
            ) from e

        self._torch_device = self._resolve_torch_device()
        dtype = torch.bfloat16 if self._torch_device == "cuda" else torch.float32

        # TODO: Tune `flow_shift`: 5.0 for 720p-style runs, 3.0 for 480p (per Wan docs).
        flow_shift = 3.0 if "1.3B" in self._model_id else 5.0

        vae = AutoencoderKLWan.from_pretrained(
            self._model_id,
            subfolder="vae",
            torch_dtype=torch.float32,
        )
        scheduler = UniPCMultistepScheduler(
            prediction_type="flow_prediction",
            use_flow_sigmas=True,
            num_train_timesteps=1000,
            flow_shift=flow_shift,
        )
        pipe = WanPipeline.from_pretrained(
            self._model_id,
            vae=vae,
            torch_dtype=dtype,
        )
        pipe.scheduler = scheduler
        pipe.to(self._torch_device)

        self._pipe = pipe
        self._loaded = True

    async def generate(
        self,
        *,
        video_id: str,
        request: "VideoGenerateRequest",
        video_path: Path,
        thumbnail_path: Path,
        fps: int,
    ) -> None:
        import asyncio

        self._ensure_loaded()

        height, width = _pixels_for_resolution(
            str(request.resolution.value),
            str(request.aspect_ratio.value),
            model_id=self._model_id,
        )
        num_frames = _frames_for_duration(request.duration_seconds, fps)

        neg = request.negative_prompt or ""

        def _run() -> None:
            import numpy as np
            from diffusers.utils import export_to_video
            from PIL import Image

            assert self._pipe is not None
            prompt = _apply_style(request.prompt, str(request.style.value))
            out = self._pipe(
                prompt=prompt,
                negative_prompt=neg,
                height=height,
                width=width,
                num_frames=num_frames,
                guidance_scale=5.0,
            )
            # TODO: Validate `out.frames` structure for your diffusers version.
            frames0 = out.frames[0]
            export_to_video(frames0, str(video_path), fps=fps)
            first = frames0[0]
            arr = np.asarray(first)
            Image.fromarray(arr).save(thumbnail_path)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run)


def _apply_style(prompt: str, style: str) -> str:
    hints: dict[str, str] = {
        "cinematic": "cinematic lighting, film grain, dramatic composition, wide lens",
        "realistic": "photorealistic, natural lighting, highly detailed, lifelike",
        "animation": "stylized 3D animation, vibrant colors, smooth motion",
        "social_media_reel": "vertical social media aesthetic, punchy colors, dynamic cuts energy",
        "sports": "dynamic sports broadcast look, motion blur on action, stadium energy",
        "nature": "natural documentary style, organic textures, golden hour light",
        "futuristic": "futuristic sci-fi aesthetic, neon accents, sleek modern design",
    }
    suffix = hints.get(style, "")
    return f"{prompt}. {suffix}" if suffix else prompt


def _pixels_for_resolution(resolution: str, aspect: str, model_id: str) -> tuple[int, int]:
    """Return (height, width) for the diffusion call."""
    tall = aspect == "9:16"
    if resolution == "1080p":
        base = (1920, 1080) if not tall else (1080, 1920)
    elif resolution == "720p":
        base = (1280, 720) if not tall else (720, 1280)
    else:
        base = (854, 480) if not tall else (480, 854)

    if "1.3B" in model_id and resolution == "720p":
        base = (480, 854) if tall else (854, 480)

    h, w = base
    h = (h // 8) * 8
    w = (w // 8) * 8
    return h, w


def _frames_for_duration(duration_seconds: float, fps: int) -> int:
    """Map requested duration to a frame count (capped for memory / pipeline stability)."""
    n = int(duration_seconds * fps)
    # Product max is 5s; ~120 frames @ 24fps.
    return max(9, min(n, 120))
