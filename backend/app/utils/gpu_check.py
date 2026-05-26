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
            "CUDA is not available. Install a CUDA-enabled PyTorch build and drivers, "
            "or set VIDEO_PROVIDER=mock for development without a GPU."
        )
    return GpuInfo(
        cuda_available=cuda_ok,
        device_name=name,
        cuda_version=str(ver) if ver else None,
        message=msg,
    )


def require_cuda_for_hf() -> None:
    """Raise RuntimeError if Hugging Face provider needs CUDA but it is missing."""
    info = get_gpu_info()
    if not info.cuda_available:
        raise RuntimeError(info.message)
