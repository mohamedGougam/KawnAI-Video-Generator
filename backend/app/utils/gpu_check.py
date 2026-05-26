"""CUDA / GPU availability helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GpuInfo:
    cuda_available: bool
    device_name: str | None
    cuda_version: str | None
    message: str


def get_gpu_info() -> GpuInfo:
    try:
        import torch
    except ImportError:
        return GpuInfo(
            cuda_available=False,
            device_name=None,
            cuda_version=None,
            message="PyTorch is not installed; GPU detection skipped.",
        )

    cuda_ok = bool(torch.cuda.is_available())
    name = torch.cuda.get_device_name(0) if cuda_ok else None
    ver = getattr(torch.version, "cuda", None)
    if cuda_ok:
        msg = f"CUDA is available ({name})."
    else:
        msg = (
            "CUDA is not available; inference will run on CPU if DEVICE=auto or DEVICE=cpu. "
            "CPU video generation is very slow and may run out of memory for large models."
        )
    return GpuInfo(
        cuda_available=cuda_ok,
        device_name=name,
        cuda_version=str(ver) if ver else None,
        message=msg,
    )


def require_cuda_for_hf() -> None:
    """Raise RuntimeError if CUDA was explicitly requested but is missing."""
    info = get_gpu_info()
    if not info.cuda_available:
        raise RuntimeError(info.message)


def describe_device_mode(requested: str) -> str:
    """Effective device label for health checks (does not load the full pipeline)."""
    try:
        import torch
    except ImportError:
        return "unknown"

    req = (requested or "auto").strip().lower()
    if req == "cuda":
        return "cuda" if torch.cuda.is_available() else "cuda_unavailable"
    if req == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"
