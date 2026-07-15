"""Stub video backend — no token, no cost.

Selected with BACKLOT_VIDEO_PROVIDER=stub. With ffmpeg on PATH this renders a
REAL clip by holding the start frame for the requested duration — an animatic:
the full production pipeline (concat, audio, overlays, masters) runs end-to-end
and the result previews the actual keyframes, just without motion. Without
ffmpeg it falls back to a placeholder file that only proves job/caching wiring.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

# Minimal structurally-valid MP4 ftyp box — the no-ffmpeg fallback. Not playable.
_PLACEHOLDER_MP4 = bytes.fromhex(
    "0000001866747970" "69736f6d" "00000200" "69736f6d" "6d703431"
)

_HEIGHTS = {"480p": 480, "720p": 720, "1080p": 1080, "4k": 2160}


def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool, audio: bool,
                   out_path: Path, *, model=None, profile=None) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg") and frame.exists():
        h = _HEIGHTS.get(resolution, 1080)
        # Hold the keyframe; even dimensions required by yuv420p.
        vf = (f"scale=-2:{h},crop=trunc(iw/2)*2:trunc(ih/2)*2,"
              f"fps=24,format=yuv420p")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-loop", "1", "-i", str(frame), "-t", str(duration),
             "-vf", vf, "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
             str(out_path)],
            capture_output=True, text=True)
        if proc.returncode == 0:
            return out_path
    out_path.write_bytes(_PLACEHOLDER_MP4)
    return out_path


def lipsync(video: Path, audio_track: Path, out_path: Path, *, model=None,
            profile=None) -> Path:
    """Animatic-grade stub: mux the VO onto the clip without moving the mouth."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if shutil.which("ffmpeg"):
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video), "-i", str(audio_track),
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
             "-c:a", "aac", "-shortest", str(out_path)],
            capture_output=True, text=True)
        if proc.returncode == 0:
            return out_path
    shutil.copyfile(video, out_path)
    return out_path
