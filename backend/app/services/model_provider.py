"""Pluggable video generation providers (mock + Hugging Face scaffold)."""

from __future__ import annotations

import shutil
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


class MockVideoProvider(VideoModelProvider):
    """Deterministic placeholder clip for UI and integration tests without a GPU."""

    name = "mock"

    def __init__(self, sample_video_path: str | None = None) -> None:
        self._sample = Path(sample_video_path) if sample_video_path else None

    async def generate(
        self,
        *,
        video_id: str,
        request: "VideoGenerateRequest",
        video_path: Path,
        thumbnail_path: Path,
        fps: int,
    ) -> None:
        if self._sample and self._sample.is_file():
            shutil.copy(self._sample, video_path)
            await _write_thumbnail_from_video(video_path, thumbnail_path)
            return

        await _synthesize_kawn_placeholder(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            duration_seconds=min(float(request.duration_seconds), 6.0),
            fps=fps,
            aspect_ratio=str(request.aspect_ratio.value),
        )


async def _write_thumbnail_from_video(video_path: Path, thumbnail_path: Path) -> None:
    """Extract first frame as PNG using imageio; fallback to solid color."""
    try:
        import imageio.v3 as iio
        import numpy as np
        from PIL import Image

        frames = iio.imread(video_path, index=0)
        if frames is None:
            raise RuntimeError("No frames")
        Image.fromarray(np.asarray(frames)).save(thumbnail_path, format="PNG")
    except Exception:
        await _solid_thumbnail(thumbnail_path)


async def _solid_thumbnail(thumbnail_path: Path) -> None:
    from PIL import Image

    img = Image.new("RGB", (720, 1280), color=(17, 17, 17))
    img.save(thumbnail_path, format="PNG")


async def _synthesize_kawn_placeholder(
    *,
    video_path: Path,
    thumbnail_path: Path,
    duration_seconds: float,
    fps: int,
    aspect_ratio: str,
) -> None:
    """Create a short branded MP4 using imageio (bundled ffmpeg)."""
    import numpy as np

    try:
        import imageio.v2 as imageio
    except ImportError as e:
        raise RuntimeError(
            "imageio is required for the mock provider when no MOCK_SAMPLE_VIDEO_PATH is set."
        ) from e

    # (height, width) in pixels — keep multiples of 16 for H.264 friendliness.
    if aspect_ratio == "16:9":
        h, w = 720, 1280
    elif aspect_ratio == "9:16":
        h, w = 1280, 720
    elif aspect_ratio == "1:1":
        h, w = 720, 720
    else:
        h, w = 720, 1280

    n = max(int(duration_seconds * fps), 8)
    orange = np.array([255, 107, 0], dtype=np.uint8)
    dark = np.array([17, 17, 17], dtype=np.uint8)
    frames: list[np.ndarray] = []
    for i in range(n):
        t = i / max(n - 1, 1)
        base = (dark * (1 - t) + orange * t).astype(np.uint8)
        frame = np.tile(base, (h, w, 1))
        frames.append(frame)

    try:
        imageio.mimsave(
            str(video_path),
            frames,
            fps=fps,
            codec="libx264",
            quality=8,
        )
    except Exception as e:
        raise RuntimeError(
            "Could not encode mock video. Install imageio[ffmpeg] or provide MOCK_SAMPLE_VIDEO_PATH."
        ) from e
    await _solid_thumbnail(thumbnail_path)


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

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        # TODO: Pin diffusers to a release that includes `WanPipeline` (see HF Wan2.1 docs).
        # TODO: Authenticate with Hugging Face if the repo is gated (`huggingface-cli login`).
        # TODO: Consider `torch.compile` / `enable_model_cpu_offload` for memory pressure.
        try:
            import torch
            from diffusers import AutoencoderKLWan, WanPipeline
            from diffusers.schedulers.scheduling_unipc_multistep import (
                UniPCMultistepScheduler,
            )
        except ImportError as e:
            raise RuntimeError(
                "diffusers/torch are not installed. Install backend/requirements.txt "
                "with the CUDA build of PyTorch appropriate for your GPU."
            ) from e

        from app.utils.gpu_check import require_cuda_for_hf

        if self._device.lower().startswith("cuda"):
            require_cuda_for_hf()

        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        if self._device.lower().startswith("cuda") and torch.cuda.is_available():
            torch_device = "cuda"
        else:
            torch_device = "cpu"

        # TODO: Tune `flow_shift`: 5.0 for 720p-style runs, 3.0 for 480p (per Wan docs).
        flow_shift = 3.0 if "1.3B" in self._model_id else 5.0

        # TODO: Replace manual scheduler wiring if Diffusers exposes a Wan default factory.
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
        pipe.to(torch_device)

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

    # Wan2.1-T2V-1.3B is commonly run at 480p-class resolutions; clamp if user asks higher.
    if "1.3B" in model_id and resolution == "720p":
        base = (480, 854) if tall else (854, 480)

    h, w = base
    # Many video models expect multiples of 8
    h = (h // 8) * 8
    w = (w // 8) * 8
    return h, w


def _frames_for_duration(duration_seconds: float, fps: int) -> int:
    n = int(duration_seconds * fps)
    return max(9, min(n, 120))
