"""ElevenLabs audio backend — TTS (with word timestamps), music beds, SFX.

Verified schemas (see elevenlabs_common.py):
  tts   -> POST /v1/text-to-speech/{voice_id}/with-timestamps
           {text, model_id, voice_settings?} -> {audio_base64, alignment}
  music -> POST /v1/music {prompt, music_length_ms (3000-600000), model_id,
           force_instrumental} -> mp3 bytes
  sfx   -> POST /v1/sound-generation {text, duration_seconds (0.5-30),
           model_id} -> mp3 bytes

All three write .mp3 — if the caller asked for another suffix the path is
adjusted, so always use the RETURNED path. TTS additionally writes a
`<stem>.timing.json` sidecar with word-level timings (derived from the
character alignment) — this is what drives karaoke captions with no
transcription step.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from .elevenlabs_common import request, request_json


def _mp3(out_path: Path) -> Path:
    out_path = Path(out_path)
    if out_path.suffix.lower() != ".mp3":
        out_path = out_path.parent / (out_path.stem + ".mp3")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return out_path


def _words_from_alignment(alignment: dict) -> list[dict]:
    """Collapse character-level alignment into word timings."""
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    words, cur, w_start, w_end = [], "", 0.0, 0.0
    for c, cs, ce in zip(chars, starts, ends):
        if c.isspace():
            if cur:
                words.append({"word": cur, "start": round(w_start, 3),
                              "end": round(w_end, 3)})
                cur = ""
        else:
            if not cur:
                w_start = cs
            cur += c
            w_end = ce
    if cur:
        words.append({"word": cur, "start": round(w_start, 3),
                      "end": round(w_end, 3)})
    return words


def write_timing(out: Path, text: str, words: list[dict]) -> Path:
    timing = out.parent / (out.stem + ".timing.json")
    duration = words[-1]["end"] if words else 0.0
    timing.write_text(json.dumps(
        {"text": text, "duration_s": duration, "words": words}, indent=2) + "\n")
    return timing


def tts(text: str, voice, out_path: Path, *, model: str, profile: dict) -> Path:
    """Speak `text`. voice: a voice_id string, or a character.json voice block
    ({"voice_id": ..., "settings": {...}}); falls back to the profile default."""
    if isinstance(voice, dict):
        voice_id = voice.get("voice_id", "")
        settings = voice.get("settings")
    else:
        voice_id, settings = voice or "", None
    voice_id = voice_id or profile.get("default_voice", "")
    if not voice_id:
        raise ValueError("tts: no voice_id given and the profile has no default_voice")

    payload = {"text": text, "model_id": model}
    if settings:
        payload["voice_settings"] = settings
    data = request_json(f"/v1/text-to-speech/{voice_id}/with-timestamps", payload)

    out = _mp3(out_path)
    out.write_bytes(base64.b64decode(data["audio_base64"]))
    write_timing(out, text, _words_from_alignment(data.get("alignment") or {}))
    return out


def music(mood: str, duration: int, out_path: Path, *, model: str,
          profile: dict) -> Path:
    lo, hi = profile.get("duration_s", [3, 600])
    ms = int(min(max(float(duration), lo), hi) * 1000)
    payload = {"prompt": mood, "music_length_ms": ms, "model_id": model,
               "force_instrumental": bool(profile.get("instrumental", True))}
    out = _mp3(out_path)
    out.write_bytes(request("/v1/music", payload))
    return out


def sfx(desc: str, duration: int, out_path: Path, *, model: str,
        profile: dict) -> Path:
    lo, hi = profile.get("duration_s", [0.5, 30])
    payload = {"text": desc, "model_id": model,
               "duration_seconds": min(max(float(duration), lo), hi)}
    out = _mp3(out_path)
    out.write_bytes(request("/v1/sound-generation", payload))
    return out
