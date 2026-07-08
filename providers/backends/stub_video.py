"""Stub video backend — writes a tiny valid placeholder .mp4, no token, no cost.

Selected with BACKLOT_VIDEO_PROVIDER=stub. Exercises the whole ugc-video
pipeline (job parsing, caching, manifest) before spending on Replicate. Same
signature as replicate_video.py. The stub does not read the frame — start-frame
validation is the runner's job.
"""
from __future__ import annotations

from pathlib import Path

# Minimal structurally-valid MP4 ftyp box — enough for existence/container
# checks. Not a playable video (this is a stub).
_PLACEHOLDER_MP4 = bytes.fromhex(
    "0000001866747970" "69736f6d" "00000200" "69736f6d" "6d703431"
)


def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool, audio: bool,
                   out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_PLACEHOLDER_MP4)
    return out_path
