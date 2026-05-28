"""Host memory checks before loading diffusion weights."""

from __future__ import annotations


class InsufficientMemoryError(RuntimeError):
    """Raised when the host does not have enough free RAM to start inference."""


def available_ram_mb() -> float | None:
    """Free-ish RAM in MiB, or None if psutil is unavailable."""
    try:
        import psutil
    except ImportError:
        return None
    return float(psutil.virtual_memory().available) / (1024 * 1024)


def check_ram_for_generation(*, min_mb: int) -> None:
    """
    Fail fast with a clear error instead of letting the OS OOM-kill the container.

    Set `MIN_AVAILABLE_RAM_MB=0` to disable (not recommended on Render).
    """
    if min_mb <= 0:
        return
    avail = available_ram_mb()
    if avail is None:
        return
    if avail < min_mb:
        raise InsufficientMemoryError(
            f"Not enough free RAM to start video generation "
            f"({avail:.0f} MiB available, need at least {min_mb} MiB). "
            "On Render, upgrade the web service to Standard 4 GB or larger, "
            "or use a GPU instance with CUDA."
        )
