"""Public video API. Callers use ONLY these functions; the backend is chosen
from env (config.VIDEO_PROVIDER). To add a host, drop a module in backends/
with the same image_to_video() signature and register it in _backend().

v1: image-to-video from a locked keyframe via Seedance. Mirrors images.py.
"""
from __future__ import annotations

from pathlib import Path

from . import config


def _backend():
    name = config.VIDEO_PROVIDER
    if name == "replicate":
        from .backends import replicate_video as b
    elif name == "stub":
        from .backends import stub_video as b
    else:
        raise ValueError(
            f"Unknown BACKLOT_VIDEO_PROVIDER={name!r}. Known: replicate, stub."
        )
    return b


def image_to_video(frame: str | Path, motion: dict, duration: int = 5,
                   resolution: str = "1080p",
                   out_path: str | Path = "out/clip.mp4") -> Path:
    """Animate a single locked keyframe into a short clip.

    frame: path to the start-frame image (an existing composited keyframe).
    motion: {"prompt": str (required), "negative": str (optional),
             "seed": int (optional), "camera_fixed": bool (optional),
             "audio": bool (optional, default False)}.
    Returns the saved .mp4 path.
    """
    b = _backend()
    return b.image_to_video(
        Path(frame),
        motion["prompt"],
        motion.get("negative", ""),
        duration,
        resolution,
        motion.get("seed"),
        motion.get("camera_fixed", False),
        motion.get("audio", False),
        Path(out_path),
    )


def capabilities() -> dict:
    """Capability profile of the active Seedance model (from BACKLOT_SEEDANCE_MODEL).
    Lets callers introspect supported resolutions / audio without backend details."""
    from .backends.seedance_profiles import profile_for
    return profile_for(config.SEEDANCE_MODEL)
