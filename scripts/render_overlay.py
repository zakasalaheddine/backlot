#!/usr/bin/env python3
"""Overlay renderer — Remotion template + props JSON -> overlay video.

Renders the plugin's motion-graphics templates (remotion/src/) headlessly:
transparent templates (KaraokeCaptions, HookCard, ProgressBar) come out as
ProRes 4444 .mov with alpha, ready for compose.py's `overlays` list; opaque
templates (EndCard) come out as .mp4, ready to append as a timeline CLIP.
ffmpeg stays the master assembler — Remotion never touches the AI clips.

Overlay job JSON:
{
  "template": "KaraokeCaptions",          // see TEMPLATES below
  "props": { ... },                        // template props (see the .tsx files)
  "timing": "out/vo.timing.json",         // optional: tts sidecar -> props.words
                                           //   + durationS (word times are VO-
                                           //   relative: composite the overlay
                                           //   at the VO's `at` offset)
  "width": 1080, "height": 1920, "fps": 30,
  "duration_s": 6.2,                       // optional when `timing` supplies it
  "out": "out/overlays/captions.mov"
}

Usage (from repo root):
    python scripts/render_overlay.py job.json [--force]

Requires Node >= 18 (first run auto-installs remotion/node_modules). Without
Node, skip overlays — compose.py's PIL captions cover the basics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REMOTION_DIR = REPO / "remotion"

# template -> transparent? (transparent = ProRes 4444 .mov overlay;
# opaque = h264 .mp4 standalone clip)
TEMPLATES = {
    "KaraokeCaptions": True,
    "HookCard": True,
    "ProgressBar": True,
    "EndCard": False,
}


def _require_node() -> None:
    if shutil.which("node") is None or shutil.which("npx") is None:
        raise RuntimeError(
            "node/npx not found — Remotion overlays need Node >= 18 "
            "(brew install node). Without Node, use compose.py's built-in PIL "
            "captions instead."
        )


def _ensure_deps() -> None:
    if not (REMOTION_DIR / "node_modules" / "remotion").exists():
        print("installing remotion dependencies (first run only)...",
              file=sys.stderr)
        proc = subprocess.run(["npm", "install", "--no-fund", "--no-audit"],
                              cwd=REMOTION_DIR, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"npm install failed:\n{proc.stderr[-800:]}")


def _src_hash() -> str:
    h = hashlib.sha256()
    # This script is part of the hash too: it owns the render flags, and a flag
    # change (e.g. pixel format) changes the output bytes.
    files = sorted((REMOTION_DIR / "src").glob("*.ts*"))
    files += [REMOTION_DIR / "package.json", Path(__file__)]
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def _build_props(job: dict, job_path: Path) -> dict:
    props = dict(job.get("props") or {})
    if job.get("timing"):
        timing_path = Path(job["timing"])
        if not timing_path.exists():
            timing_path = job_path.parent / job["timing"]
        timing = json.loads(timing_path.read_text())
        props.setdefault("words", timing["words"])
        job.setdefault("duration_s", timing["duration_s"] + 0.4)  # hold last page
    if "duration_s" not in job:
        raise ValueError("job needs duration_s (or a timing file that supplies it)")
    props["width"] = int(job.get("width", 1080))
    props["height"] = int(job.get("height", 1920))
    props["fps"] = int(job.get("fps", 30))
    props["durationS"] = float(job["duration_s"])
    return props


def render(job_path: Path, force: bool) -> dict:
    job = json.loads(job_path.read_text())
    template = job.get("template", "")
    if template not in TEMPLATES:
        raise ValueError(f"unknown template {template!r}; known: {list(TEMPLATES)}")
    transparent = TEMPLATES[template]

    props = _build_props(job, job_path)
    out = Path(job.get("out") or f"out/overlays/{template.lower()}")
    suffix = ".mov" if transparent else ".mp4"
    if out.suffix.lower() != suffix:
        out = out.parent / (out.stem + suffix)
    out.parent.mkdir(parents=True, exist_ok=True)

    want = hashlib.sha256(
        (json.dumps({"t": template, "p": props}, sort_keys=True) + _src_hash())
        .encode()).hexdigest()[:16]
    hash_path = out.parent / (out.name + ".hash")
    have = hash_path.read_text().strip() if hash_path.exists() else ""
    if not force and out.exists() and have == want:
        return {"out": str(out), "template": template, "rendered": False}

    _require_node()
    _ensure_deps()

    props_file = out.parent / (out.stem + ".props.json")
    props_file.write_text(json.dumps(props, indent=2) + "\n")

    cmd = ["npx", "remotion", "render", "src/index.ts", template,
           str(out.resolve()), f"--props={props_file.resolve()}",
           "--log=error", "--overwrite"]
    if transparent:
        # all three are required for alpha: png frames, the 4444 profile, AND
        # the alpha pixel format (without it Remotion silently emits ProRes 422)
        cmd += ["--codec=prores", "--prores-profile=4444",
                "--image-format=png", "--pixel-format=yuva444p10le"]
    else:
        cmd += ["--codec=h264"]
    proc = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"remotion render failed for {template}:\n{proc.stderr[-1200:]}")

    hash_path.write_text(want)
    return {"out": str(out), "template": template, "rendered": True}


def main() -> None:
    p = argparse.ArgumentParser(description="Render a Remotion overlay/card")
    p.add_argument("job", help="path to overlay job JSON")
    p.add_argument("--force", action="store_true", help="ignore cache, re-render")
    a = p.parse_args()
    print(json.dumps(render(Path(a.job), a.force), indent=2))


if __name__ == "__main__":
    main()
