"""Public video API. Callers use ONLY these functions; the model + backend are
resolved from the registry (providers/models.json) with env overrides — see
config.resolve("video.i2v"). Mirrors images.py.

v1: image-to-video from a locked keyframe.
"""
from __future__ import annotations

from pathlib import Path

from . import config


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
    res = config.resolve("video.i2v")
    b = config.load_backend(res)
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
        model=res["slug"], profile=res["profile"],
    )


def lipsync(video: str | Path, audio_track: str | Path,
            out_path: str | Path = "out/lipsync.mp4") -> Path:
    """Re-sync a clip's mouth movements to a voice-over track — the
    talking-head path. video: an existing character clip; audio_track: the VO
    (.wav preferred). Returns the saved .mp4 path."""
    res = config.resolve("video.lipsync")
    b = config.load_backend(res)
    return b.lipsync(Path(video), Path(audio_track), Path(out_path),
                     model=res["slug"], profile=res["profile"])


def capabilities() -> dict:
    """Capability profile of the active video model, plus which model it is:
    the profile fields (resolutions, audio, durations, ...) merged with
    {"model": slug, "key": registry key, "backend": module}. Lets runners
    validate jobs and key caches without knowing backend details."""
    res = config.resolve("video.i2v")
    return {**res["profile"], "model": res["slug"], "key": res["key"],
            "backend": res["backend"]}
