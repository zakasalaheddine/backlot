#!/usr/bin/env python3
"""Motion preset library — named camera/action recipes for ugc-video.

Curated, committed content (unlike the private asset library). Loaded from
presets/motion.json at the plugin root so it resolves regardless of CWD. Both
this CLI and scripts/run_video.py read presets through load_presets()/resolve().
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRESETS_FILE = REPO / "presets" / "motion.json"


def load_presets() -> dict:
    """Return {id: preset_record}. Raises on a missing or malformed library."""
    if not PRESETS_FILE.exists():
        raise FileNotFoundError(f"preset library not found: {PRESETS_FILE}")
    try:
        data = json.loads(PRESETS_FILE.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"preset library {PRESETS_FILE} is malformed JSON: {e}")
    presets: dict = {}
    for p in data:
        pid = p.get("id")
        if not pid:
            raise ValueError(f"preset library {PRESETS_FILE} has a record missing 'id': {p}")
        if pid in presets:
            raise ValueError(f"preset library {PRESETS_FILE} has duplicate id {pid!r}")
        presets[pid] = p
    return presets


def resolve(preset_id: str, expected_category: str, presets: dict | None = None) -> dict:
    """Look up a preset by id, enforcing its category. Raises ValueError otherwise."""
    presets = presets if presets is not None else load_presets()
    p = presets.get(preset_id)
    if p is None:
        valid = sorted(k for k, v in presets.items()
                       if v.get("category") == expected_category)
        raise ValueError(
            f"unknown {expected_category} preset {preset_id!r}; "
            f"valid: {', '.join(valid)}"
        )
    if p.get("category") != expected_category:
        raise ValueError(
            f"preset {preset_id!r} is category {p.get('category')!r}, "
            f"expected {expected_category!r}"
        )
    return p


def list_presets(args) -> None:
    presets = load_presets()
    rows = []
    for p in presets.values():
        if args.category and p.get("category") != args.category:
            continue
        if args.status and p.get("status") != args.status:
            continue
        rows.append({
            "id": p["id"], "category": p.get("category"),
            "label": p.get("label", ""), "status": p.get("status"),
            "prompt": p.get("prompt", "")[:80],
        })
    rows.sort(key=lambda r: (r["category"], r["id"]))
    print(json.dumps(rows, indent=2))


def get_preset(args) -> None:
    presets = load_presets()
    p = presets.get(args.id)
    if p is None:
        print(f"No preset with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(p, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="backlot motion preset library")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="list presets")
    ls.add_argument("--category", choices=["camera", "action"], default=None)
    ls.add_argument("--status", choices=["verified", "experimental"], default=None)
    ls.set_defaults(func=list_presets)

    g = sub.add_parser("get", help="print one preset record")
    g.add_argument("--id", required=True)
    g.set_defaults(func=get_preset)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
