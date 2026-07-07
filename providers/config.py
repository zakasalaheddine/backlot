"""Provider configuration — the single place the host choice lives.

Everything model-host-specific is resolved from env here, so swapping Replicate
for fal / a direct API is a matter of adding a backend module and flipping
BACKLOT_IMAGE_PROVIDER. The skills never see any of this.
"""
from __future__ import annotations

import os
from pathlib import Path

# Plugin root = parent of the providers/ package. Used to locate .env and, by
# default, the asset library — so paths work regardless of the current CWD (an
# installed plugin runs from the user's project, not this directory).
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Populate os.environ from <plugin>/.env if present.

    Dependency-free so `pip install -r requirements.txt` isn't a prerequisite for
    reading the token. Existing env vars win — an explicit `export` overrides .env.
    """
    env_file = PLUGIN_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


_load_dotenv()


def _get(name: str, default: str) -> str:
    val = os.environ.get(name, "").strip()
    return val or default


# Which backend module serves each capability.
# "replicate" -> providers/backends/replicate_*.py
# "stub"      -> providers/backends/stub_*.py   (placeholder PNGs, no cost, no token)
IMAGE_PROVIDER = _get("BACKLOT_IMAGE_PROVIDER", "replicate")
VIDEO_PROVIDER = _get("BACKLOT_VIDEO_PROVIDER", "replicate")

# Model slugs — overridable so you can pin a version hash or point at a fork.
NANO_BANANA_MODEL = _get("BACKLOT_NANO_BANANA_MODEL", "google/nano-banana")
SEEDANCE_MODEL = _get("BACKLOT_SEEDANCE_MODEL", "bytedance/seedance-1-pro")

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()


def require_replicate_token() -> str:
    if not REPLICATE_API_TOKEN:
        raise RuntimeError(
            "REPLICATE_API_TOKEN is not set. Copy .env.example to .env and add your "
            "token, or run with BACKLOT_IMAGE_PROVIDER=stub to test without spending."
        )
    return REPLICATE_API_TOKEN
