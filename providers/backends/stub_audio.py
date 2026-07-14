"""Stub audio backend — valid silent WAVs, no token, no cost.

Selected with BACKLOT_AUDIO_*_PROVIDER=stub. Mirrors the real backend's
contract: files are written as .wav (caller's suffix adjusted — use the
RETURNED path), durations are sized realistically (TTS length from word count
at speaking pace), and tts writes the same `<stem>.timing.json` word-timing
sidecar (evenly spaced) so caption/assembly work runs at zero cost.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

_RATE = 24000  # 24 kHz mono 16-bit


def _wav(out_path: Path) -> Path:
    out_path = Path(out_path)
    if out_path.suffix.lower() != ".wav":
        out_path = out_path.parent / (out_path.stem + ".wav")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def _silence(seconds: float, out_path: Path) -> Path:
    frames = max(1, int(seconds * _RATE))
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_RATE)
        w.writeframes(b"\x00\x00" * frames)
    return out_path


def tts(text: str, voice, out_path: Path, *, model=None, profile=None) -> Path:
    # ~2.5 words/second is a natural VO pace; timings evenly spaced.
    words = text.split() or ["..."]
    duration = max(1.0, len(words) / 2.5)
    per = duration / len(words)
    out = _wav(out_path)
    _silence(duration, out)
    timing = out.parent / (out.stem + ".timing.json")
    timing.write_text(json.dumps({
        "text": text, "duration_s": round(duration, 3),
        "words": [{"word": w, "start": round(i * per, 3),
                   "end": round((i + 0.9) * per, 3)}
                  for i, w in enumerate(words)],
    }, indent=2) + "\n")
    return out


def music(mood: str, duration: int, out_path: Path, *, model=None, profile=None) -> Path:
    return _silence(max(1, duration), _wav(out_path))


def sfx(desc: str, duration: int, out_path: Path, *, model=None, profile=None) -> Path:
    return _silence(max(1, duration), _wav(out_path))
