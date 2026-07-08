"""Replicate video backend — Seedance (bytedance/seedance-1-pro, seedance-2.0).

Each model version accepts a different input schema; the fields to send are
resolved from that model's capability profile (see seedance_profiles.py):

    prompt        required   -> motion description (+ "Avoid: <negative>." appended)
    image         start frame (uploaded from a local file)
    duration      integer seconds
    resolution    per-profile set (1-pro: 480p/720p/1080p; 2.0 adds 4k)
    seed          optional
    camera_fixed  1-pro only, and only when True
    aspect_ratio  2.0 only ("explicit" profile); probed from the frame. 1-pro
                  infers aspect from the image, so it is omitted there.
    generate_audio 2.0 only; the clip's audio flag (default False)
    -> output is a SINGLE .mp4 URI.

Seedance has no negative field, so a negative is appended to the prompt as
"Avoid: ..." (same convention as replicate_images.py).
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from .replicate_common import run_video
from .seedance_profiles import profile_for, nearest_aspect


def _build_input(profile: dict, prompt: str, negative: str, duration: int,
                 resolution: str, seed, camera_fixed: bool, audio: bool,
                 aspect: str | None) -> dict:
    full = f"{prompt}\n\nAvoid: {negative}." if negative else prompt
    inp = {"prompt": full, "duration": duration, "resolution": resolution}
    if profile["camera_fixed"] and camera_fixed:
        inp["camera_fixed"] = True
    if profile["aspect"] == "explicit" and aspect:
        inp["aspect_ratio"] = aspect
    if profile["audio"]:
        inp["generate_audio"] = bool(audio)
    if seed is not None:
        inp["seed"] = seed
    return inp


def _frame_aspect(frame: Path) -> str:
    """Probe the frame's pixel size and map it to the nearest supported aspect."""
    from PIL import Image
    with Image.open(frame) as im:
        w, h = im.size
    return nearest_aspect(w, h)


def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool, audio: bool,
                   out_path: Path) -> Path:
    """Animate one start frame into a clip via the configured Seedance model,
    sending only the fields that model's profile supports."""
    profile = profile_for(config.SEEDANCE_MODEL)
    aspect = _frame_aspect(frame) if profile["aspect"] == "explicit" else None
    inp = _build_input(profile, prompt, negative, duration, resolution, seed,
                       camera_fixed, audio, aspect)
    with open(frame, "rb") as fh:
        inp["image"] = fh
        return run_video(config.SEEDANCE_MODEL, inp, out_path)
