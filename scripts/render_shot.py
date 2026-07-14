#!/usr/bin/env python3
"""Regenerate ONE shot of a production — the cheap fix for one bad clip.

Re-runs the full production with only the named shot's keyframe + clip forced;
every other stage comes from cache, so you pay for one image + one clip (plus a
fast re-assemble). Video is the expensive stage — change intentionally.

Usage (from repo root):
    python scripts/render_shot.py production.json s3 [s5 ...] [--out out/<name>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import run_production


def main() -> None:
    p = argparse.ArgumentParser(description="Regenerate specific shots of a production")
    p.add_argument("production", help="path to production JSON")
    p.add_argument("shots", nargs="+", help="shot id(s) to regenerate, e.g. s3")
    p.add_argument("--out", default="", help="output dir (default out/<stem>)")
    a = p.parse_args()
    prod_path = Path(a.production)
    out_dir = Path(a.out) if a.out else Path.cwd() / "out" / prod_path.stem
    manifest = run_production.run(prod_path, out_dir, force=False,
                                  force_shots=set(a.shots))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
