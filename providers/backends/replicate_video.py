"""Replicate video backend — Seedance (bytedance/seedance-1-pro).

Verified image-to-video schema:
    prompt        string, required   -> the motion description
    image         string             -> start frame (uploaded from a local file)
    duration      integer, default 5 -> seconds (5 or 10)
    resolution    480p | 720p | 1080p (default 1080p)
    seed          integer, optional
    camera_fixed  boolean, optional
    aspect_ratio  IGNORED when image is passed -> clip inherits the frame's ratio
    -> output is a SINGLE .mp4 URI.

Seedance has no separate negative field, so a negative is appended to the
prompt as "Avoid: ..." (same convention as replicate_images.py).
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from .replicate_common import run_video


def _build_input(prompt: str, negative: str, duration: int, resolution: str,
                 seed, camera_fixed: bool) -> dict:
    full = prompt
    if negative:
        full = f"{prompt}\n\nAvoid: {negative}."
    inp = {
        "prompt": full,
        "duration": duration,
        "resolution": resolution,
        "camera_fixed": camera_fixed,
    }
    if seed is not None:
        inp["seed"] = seed
    return inp


def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool,
                   out_path: Path) -> Path:
    """Animate one start frame into a clip via Seedance. aspect_ratio is
    deliberately omitted — Seedance ignores it when an image is provided."""
    inp = _build_input(prompt, negative, duration, resolution, seed, camera_fixed)
    with open(frame, "rb") as fh:
        inp["image"] = fh
        return run_video(config.SEEDANCE_MODEL, inp, out_path)
