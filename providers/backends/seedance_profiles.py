"""Per-model capability profiles for the Seedance video backend.

Each Seedance version accepts a different input schema. Rather than guess or
introspect at runtime, we keep an explicit profile per model family and send
only the fields that model supports. Adding a future model = one profile entry.
"""
from __future__ import annotations

PROFILES = {
    "seedance-1-pro": {
        "camera_fixed": True,          # field supported
        "aspect": "infer",             # aspect read from the image; don't send aspect_ratio
        "audio": False,                # no audio support
        "resolutions": frozenset({"480p", "720p", "1080p"}),
    },
    "seedance-2.0": {
        "camera_fixed": False,         # not a field (sending it errors)
        "aspect": "explicit",          # MUST send aspect_ratio or it defaults to 16:9
        "audio": True,                 # generate_audio supported (backlot default off)
        "resolutions": frozenset({"480p", "720p", "1080p", "4k"}),
    },
}


def profile_for(slug: str) -> dict:
    """Resolve a model slug to its capability profile. Substring match on the
    family so a pinned '<slug>:<versionhash>' still resolves. Unknown models
    fall back to the conservative 1-pro profile."""
    if "seedance-2" in slug:
        return PROFILES["seedance-2.0"]
    if "seedance-1" in slug:
        return PROFILES["seedance-1-pro"]
    return PROFILES["seedance-1-pro"]


# Supported aspect ratios we map a frame to (subset of Seedance's enum).
_ASPECTS = {"9:16": 9 / 16, "3:4": 3 / 4, "1:1": 1.0, "4:3": 4 / 3, "16:9": 16 / 9}


def nearest_aspect(w: int, h: int) -> str:
    """Map a frame's pixel dimensions to the closest supported aspect ratio."""
    ratio = w / h
    return min(_ASPECTS, key=lambda k: abs(_ASPECTS[k] - ratio))
