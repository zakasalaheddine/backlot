"""Public video API — v1, not built yet.

The seam is defined so ugc-video can be dropped in without touching skills.
When you build it:
  1. Verify the Seedance slug + input schema on Replicate (start-frame image,
     motion prompt, duration, aspect) — do NOT guess it; the schema is where
     scripted integrations break.
  2. Add providers/backends/replicate_video.py implementing image_to_video().
  3. Register it below, mirroring images.py.
"""
from __future__ import annotations

from pathlib import Path


def image_to_video(frame: str | Path, motion: dict, duration_s: int = 6,
                   out_path: str | Path = "out/clip.mp4") -> Path:
    raise NotImplementedError(
        "ugc-video is v1. Implement providers/backends/replicate_video.py against "
        "the verified Seedance schema, then register it here."
    )
