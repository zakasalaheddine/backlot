"""Stub audio backend — valid silent WAVs, no token, no cost.

Selected with BACKLOT_AUDIO_*_PROVIDER=stub (or as the registry default until a
real audio backend lands). Durations are sized realistically — TTS length from
word count at speaking pace — so downstream assembly/mixing can be built and
tested against plausible timelines. Same signatures as a real audio backend.
"""
from __future__ import annotations

import wave
from pathlib import Path

_RATE = 24000  # 24 kHz mono 16-bit


def _silence(seconds: float, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(seconds * _RATE))
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(b"\x00\x00" * frames)
    return out_path


def tts(text: str, voice, out_path: Path, *, model=None, profile=None) -> Path:
    # ~2.5 words/second is a natural VO pace.
    words = max(1, len(text.split()))
    return _silence(max(1.0, words / 2.5), out_path)


def music(mood: str, duration: int, out_path: Path, *, model=None, profile=None) -> Path:
    return _silence(max(1, duration), out_path)


def sfx(desc: str, duration: int, out_path: Path, *, model=None, profile=None) -> Path:
    return _silence(max(1, duration), out_path)
