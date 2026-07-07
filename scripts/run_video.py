#!/usr/bin/env python3
"""Video runner — video job JSON -> image-to-video clips + manifest.

Pipeline per clip:
  1. Validate the start-frame keyframe exists and the motion prompt is non-empty.
  2. image_to_video() the frame into a short clip (Seedance).
  3. Content-address the clip so re-runs skip already-rendered clips.

Usage (from repo root):
    python scripts/run_video.py path/to/job.json [--out out/<name>] [--force]

Test the whole pipeline with no cost/token:
    BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py job.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from providers import video  # noqa: E402


def _clip_hash(frame: Path, motion: str, negative: str, duration: int, resolution: str,
               seed, camera_fixed: bool) -> str:
    h = hashlib.sha256()
    for part in (motion, negative, str(duration), resolution, str(seed), str(camera_fixed)):
        h.update(part.encode())
        h.update(b"\x00")
    h.update(hashlib.sha256(frame.read_bytes()).digest())
    return h.hexdigest()[:16]


def _resolve_frame(raw: str, job_path: Path) -> Path:
    p = Path(raw)
    if p.exists():
        return p
    alt = job_path.parent / raw
    return alt if alt.exists() else p  # return original for a clean error msg


def run(job_path: Path, out_dir: Path, force: bool) -> dict:
    job = json.loads(job_path.read_text())
    meta = job.get("meta", {})
    out_dir.mkdir(parents=True, exist_ok=True)

    produced = []
    for clip in job["clips"]:
        cid = clip["id"]
        motion = clip.get("motion", "").strip()
        if not motion:
            raise ValueError(f"clip {cid!r}: 'motion' prompt is required")
        frame = _resolve_frame(clip["frame"], job_path)
        if not frame.exists():
            raise FileNotFoundError(
                f"clip {cid!r}: start frame not found: {clip['frame']}"
            )

        duration = int(clip.get("duration", 5))
        resolution = clip.get("resolution", "1080p")
        camera_fixed = bool(clip.get("camera_fixed", False))
        negative = clip.get("negative", "")
        seed = clip.get("seed")

        if resolution not in {"480p", "720p", "1080p"}:
            raise ValueError(
                f"clip {cid!r}: resolution must be one of 480p/720p/1080p, got {resolution!r}"
            )
        if duration not in {5, 10}:
            raise ValueError(f"clip {cid!r}: duration must be 5 or 10, got {duration!r}")

        cdir = out_dir / cid
        cdir.mkdir(parents=True, exist_ok=True)
        clip_path = cdir / "clip.mp4"
        hash_path = cdir / "clip.hash"

        want = _clip_hash(frame, motion, negative, duration, resolution, seed, camera_fixed)
        have = hash_path.read_text().strip() if hash_path.exists() else ""

        if force or not clip_path.exists() or have != want:
            video.image_to_video(
                frame,
                {"prompt": motion, "negative": negative, "seed": seed,
                 "camera_fixed": camera_fixed},
                duration=duration, resolution=resolution, out_path=clip_path,
            )
            hash_path.write_text(want)
            rendered = True
        else:
            rendered = False

        produced.append({"clip": cid, "mp4": str(clip_path),
                         "frame": str(frame), "rendered": rendered})

    manifest = {"job": str(job_path), "meta": meta, "outputs": produced}
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Run a video job")
    p.add_argument("job", help="path to video job JSON")
    p.add_argument("--out", default="", help="output dir (default out/<job-stem>)")
    p.add_argument("--force", action="store_true", help="ignore cache, re-render all")
    a = p.parse_args()
    job_path = Path(a.job)
    out_dir = Path(a.out) if a.out else Path.cwd() / "out" / job_path.stem
    manifest = run(job_path, out_dir, a.force)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
