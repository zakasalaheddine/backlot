#!/usr/bin/env python3
"""Audio generator — VO / music / SFX files for compose.py timelines.

Thin CLI over providers/audio.py. VO uses a character's LOCKED voice
(assets.py set-voice) so every take sounds like the same person — the audio
half of continuity. Prints JSON with the real output path (the backend picks
the container) and, for tts, the word-timing sidecar.

Usage (from repo root):
    python scripts/audio_gen.py tts "the VO line" --character maya-01 [--out out/vo.mp3]
    python scripts/audio_gen.py tts "the VO line" --voice <voice-id>
    python scripts/audio_gen.py music "cozy-upbeat lofi, warm" --duration 15
    python scripts/audio_gen.py sfx "kettle click, soft" [--duration 2]

Zero-cost test: BACKLOT_AUDIO_TTS_PROVIDER=stub (music/sfx likewise) writes
silent placeholders with the same timing sidecar.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from providers import audio  # noqa: E402
import assets  # noqa: E402


def cmd_tts(a) -> dict:
    voice = a.voice or None
    if a.character:
        voice = assets.resolve_voice(a.character)
        if voice is None:
            raise SystemExit(
                f"character {a.character!r} has no locked voice. Browse with "
                f"`python scripts/voices.py list`, then lock one with "
                f"`python scripts/assets.py set-voice --id {a.character} "
                f"--voice-id <id>` — or pass --voice <id> for a one-off."
            )
    out = audio.tts(a.text, voice=voice, out_path=a.out or "out/vo.mp3")
    timing = out.parent / (out.stem + ".timing.json")
    return {"audio": str(out),
            "timing": str(timing) if timing.exists() else None}


def cmd_music(a) -> dict:
    out = audio.music(a.text, duration=a.duration, out_path=a.out or "out/music.mp3")
    return {"audio": str(out)}


def cmd_sfx(a) -> dict:
    out = audio.sfx(a.text, duration=a.duration, out_path=a.out or "out/sfx.mp3")
    return {"audio": str(out)}


def main() -> None:
    p = argparse.ArgumentParser(description="Generate VO / music / SFX")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tts", help="speak a VO line")
    t.add_argument("text")
    t.add_argument("--character", default="", help="character id with a locked voice")
    t.add_argument("--voice", default="", help="one-off provider voice id")
    t.add_argument("--out", default="")
    t.set_defaults(func=cmd_tts)

    m = sub.add_parser("music", help="generate a music bed")
    m.add_argument("text", help="mood / style prompt")
    m.add_argument("--duration", type=int, default=15, help="seconds")
    m.add_argument("--out", default="")
    m.set_defaults(func=cmd_music)

    s = sub.add_parser("sfx", help="generate a sound effect")
    s.add_argument("text", help="sound description")
    s.add_argument("--duration", type=float, default=2, help="seconds")
    s.add_argument("--out", default="")
    s.set_defaults(func=cmd_sfx)

    a = p.parse_args()
    print(json.dumps(a.func(a), indent=2))


if __name__ == "__main__":
    main()
