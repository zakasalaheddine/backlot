#!/usr/bin/env python3
"""Voice browser — list ElevenLabs voices so a character can lock one.

Voice is part of character continuity: browse here, audition the preview_url,
then lock the pick with `assets.py set-voice`. Needs ELEVENLABS_API_KEY.

Usage (from repo root):
    python scripts/voices.py list [--search warm] [--category premade] [--limit 30] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from providers.backends.elevenlabs_common import request_json  # noqa: E402


def cmd_list(search: str, category: str, limit: int, as_json: bool) -> None:
    data = request_json("/v2/voices", query={
        "page_size": min(limit, 100), "search": search, "category": category})
    voices = [{
        "voice_id": v["voice_id"],
        "name": v.get("name", ""),
        "category": v.get("category", ""),
        "labels": v.get("labels") or {},
        "preview_url": v.get("preview_url", ""),
    } for v in data.get("voices", [])]

    if as_json:
        print(json.dumps(voices, indent=2))
        return
    for v in voices:
        labels = ", ".join(f"{k}={val}" for k, val in v["labels"].items())
        print(f"{v['voice_id']}  {v['name']:<18} {v['category']:<12} {labels}")
        if v["preview_url"]:
            print(f"{'':22}  preview: {v['preview_url']}")
    print(f"\n{len(voices)} voices. Lock one onto a character:\n"
          f"  python scripts/assets.py set-voice --id <char-id> "
          f"--voice-id <voice_id> --voice-name <name>")


def main() -> None:
    p = argparse.ArgumentParser(description="Browse ElevenLabs voices")
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("list", help="list/search voices")
    lp.add_argument("--search", default="")
    lp.add_argument("--category", default="",
                    choices=["", "premade", "cloned", "generated", "professional"])
    lp.add_argument("--limit", type=int, default=30)
    lp.add_argument("--json", action="store_true")
    a = p.parse_args()
    cmd_list(a.search, a.category, a.limit, a.json)


if __name__ == "__main__":
    main()
