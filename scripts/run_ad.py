#!/usr/bin/env python3
"""Ad runner — ad job JSON -> composited, text-overlaid ad creatives.

Pipeline per variant per format:
  1. Resolve locked refs (character + product) from the library by ID.
  2. composite() them into the variant's scene at the target aspect (Nano-Banana).
  3. Optional: if the variant has an `overlay`, burn headline/subhead/CTA as a
     deterministic layer (text_overlay.py). No overlay -> the clean keyframe is
     the final asset.
  4. Batch every variant x format for Meta testing.

Keyframes are content-addressed (hash of prompt + refs + aspect): re-runs skip
already-generated frames so a rerun after a copy tweak only re-burns text — it
does NOT pay for the image again.

Usage (from repo root):
    python scripts/run_ad.py path/to/job.json [--out out/<name>] [--force]

Test the whole pipeline with no cost:
    BACKLOT_IMAGE_PROVIDER=stub python scripts/run_ad.py job.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from providers import images  # noqa: E402
import assets  # noqa: E402
from text_overlay import render_overlay  # noqa: E402


def _keyframe_hash(prompt: str, negative: str, ref_paths, aspect: str) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode())
    h.update(b"\x00")
    h.update(negative.encode())
    h.update(b"\x00")
    h.update(aspect.encode())
    for p in ref_paths:
        h.update(b"\x00")
        h.update(str(p).encode())
        # include file bytes so swapping a ref regenerates
        h.update(hashlib.sha256(Path(p).read_bytes()).digest())
    return h.hexdigest()[:16]


def run(job_path: Path, out_dir: Path, force: bool) -> dict:
    job = json.loads(job_path.read_text())
    meta = job.get("meta", {})
    formats = meta.get("formats", ["1:1"])
    out_dir.mkdir(parents=True, exist_ok=True)

    produced = []
    for variant in job["variants"]:
        vid = variant["id"]
        kf = variant["keyframe"]
        prompt = kf["prompt"]
        negative = kf.get("negative", "")
        overlay = variant.get("overlay", {})
        anchor = variant.get("anchor", "bottom")

        # Resolve refs once per variant (same across formats).
        ref_paths = []
        for asset_id in kf.get("use_refs", []):
            ref_paths.extend(assets.resolve_refs(asset_id))

        vdir = out_dir / vid
        vdir.mkdir(parents=True, exist_ok=True)

        for fmt in formats:
            fmt_tag = fmt.replace(":", "x")
            keyframe_path = vdir / f"keyframe_{fmt_tag}.png"
            hash_path = vdir / f"keyframe_{fmt_tag}.hash"
            final_path = vdir / f"ad_{fmt_tag}.png"

            want_hash = _keyframe_hash(prompt, negative, ref_paths, fmt)
            have_hash = hash_path.read_text().strip() if hash_path.exists() else ""

            if force or not keyframe_path.exists() or have_hash != want_hash:
                images.composite(
                    {"prompt": prompt, "negative": negative},
                    ref_paths, aspect=fmt, out_path=keyframe_path,
                )
                hash_path.write_text(want_hash)
                regenerated = True
            else:
                regenerated = False

            # Copy overlay is optional. With an `overlay` block it's cheap +
            # deterministic, so (re)burn it from the keyframe. Without one, the
            # clean keyframe IS the deliverable — no text layer.
            if overlay:
                render_overlay(keyframe_path, overlay, final_path, aspect=fmt, anchor=anchor)
                ad_path = final_path
            else:
                ad_path = keyframe_path
            produced.append({
                "variant": vid, "format": fmt, "ad": str(ad_path),
                "keyframe": str(keyframe_path), "regenerated": regenerated,
            })

    manifest = {"job": str(job_path), "meta": meta, "outputs": produced}
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Run an ad job")
    p.add_argument("job", help="path to ad job JSON")
    p.add_argument("--out", default="", help="output dir (default out/<job-stem>)")
    p.add_argument("--force", action="store_true", help="ignore cache, regenerate all")
    a = p.parse_args()
    job_path = Path(a.job)
    # Default outputs next to where the user is working, not inside the plugin.
    out_dir = Path(a.out) if a.out else Path.cwd() / "out" / job_path.stem
    manifest = run(job_path, out_dir, a.force)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
