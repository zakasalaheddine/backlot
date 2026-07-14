"""Shared ElevenLabs plumbing: authenticated requests via urllib (no SDK dep).

Endpoints verified against https://elevenlabs.io/docs/api-reference (2026-07):
  POST /v1/text-to-speech/{voice_id}/with-timestamps  -> JSON (audio_base64 + alignment)
  POST /v1/music                                      -> raw audio bytes
  POST /v1/sound-generation                           -> raw audio bytes
  GET  /v2/voices                                     -> JSON voice list
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from .. import config

BASE = "https://api.elevenlabs.io"


def request(path: str, payload: dict | None = None, query: dict | None = None) -> bytes:
    """POST `payload` (or GET if None) to an ElevenLabs endpoint, return raw body."""
    key = config.require_elevenlabs_token()
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in query.items() if v not in (None, "")})
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method="POST" if data is not None else "GET",
        headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"ElevenLabs API error {e.code} on {path}: {body}") from None


def request_json(path: str, payload: dict | None = None,
                 query: dict | None = None) -> dict:
    return json.loads(request(path, payload, query))
