"""Provider configuration — env loading + the capability registry resolver.

Which model serves which capability lives in providers/models.json. This module
resolves a capability (e.g. "video.i2v") to {model key, slug, backend module,
profile}, honouring env overrides, so swapping a model or host is a registry
edit or an env var — the skills and runners never see any of this.

Env overrides, most specific wins:
    BACKLOT_<CAPABILITY>_MODEL     e.g. BACKLOT_VIDEO_I2V_MODEL=seedance-2.0
                                   (a registry key, or a raw host slug — pinned
                                   '<slug>:<versionhash>' works)
    BACKLOT_<CAPABILITY>_PROVIDER  "stub", "auto", or a backend module name
Legacy aliases (kept working): BACKLOT_IMAGE_PROVIDER / BACKLOT_VIDEO_PROVIDER,
BACKLOT_NANO_BANANA_MODEL / BACKLOT_SEEDANCE_MODEL.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Plugin root = parent of the providers/ package. Used to locate .env, the
# registry and, by default, the asset library — so paths work regardless of the
# current CWD (an installed plugin runs from the user's project, not here).
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

REGISTRY_PATH = PLUGIN_ROOT / "providers" / "models.json"
_REGISTRY = json.loads(REGISTRY_PATH.read_text())

# Legacy env aliases, applied when no BACKLOT_<CAPABILITY>_* var is set.
# Keyed by full capability or by family (the part before the dot).
_LEGACY_MODEL_ENV = {"image": "BACKLOT_NANO_BANANA_MODEL",
                     "video.i2v": "BACKLOT_SEEDANCE_MODEL"}
_LEGACY_PROVIDER_ENV = {"image": "BACKLOT_IMAGE_PROVIDER",
                        "video": "BACKLOT_VIDEO_PROVIDER"}

# The stub backend for each capability family — every family has one so the
# whole pipeline runs at zero cost with <FAMILY>_PROVIDER=stub.
_STUB_BACKENDS = {"image": "stub_images", "video": "stub_video", "audio": "stub_audio"}

REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN", "").strip()


def capabilities() -> list[str]:
    """All capabilities the registry knows, in registry order."""
    return list(_REGISTRY["capabilities"])


def models() -> dict:
    """The raw model entries from the registry (read-only use)."""
    return _REGISTRY["models"]


def env_var(capability: str, suffix: str) -> str:
    """The env var that overrides a capability's MODEL or PROVIDER."""
    return "BACKLOT_" + capability.replace(".", "_").upper() + "_" + suffix


def _env(capability: str, suffix: str, legacy: dict) -> str:
    """Read a capability override: specific var first, then its legacy alias."""
    val = os.environ.get(env_var(capability, suffix), "").strip()
    if val:
        return val
    family = capability.split(".", 1)[0]
    alias = legacy.get(capability) or legacy.get(family)
    return os.environ.get(alias, "").strip() if alias else ""


def _pick_model(raw: str, capability: str, default_key: str) -> tuple[str, str]:
    """Resolve the model override `raw` to (registry key, slug to run).

    Empty -> the capability's default. A registry key -> that entry. A raw host
    slug -> the entry whose `match` substring hits (so a pinned version keeps
    its profile); an unknown slug runs as-is under the default entry's
    backend/profile (conservative, mirrors the old profile_for fallback).
    """
    entries = _REGISTRY["models"]
    if not raw:
        return default_key, entries[default_key]["slug"]
    if raw in entries:
        if capability not in entries[raw]["capabilities"]:
            valid = [k for k, m in entries.items() if capability in m["capabilities"]]
            raise ValueError(
                f"model {raw!r} does not serve {capability!r}; registry models "
                f"for it: {valid}"
            )
        return raw, entries[raw]["slug"]
    for key, entry in entries.items():
        if capability in entry["capabilities"] and any(m and m in raw for m in entry["match"]):
            return key, raw
    return default_key, raw


def resolve(capability: str) -> dict:
    """Resolve a capability to its active model + backend.

    Returns {"capability", "key", "slug", "backend", "provider", "profile"}.
    `slug` is what the backend runs; `profile` is that model's capability
    profile (validate against it, build inputs from it).
    """
    defaults = _REGISTRY["capabilities"]
    if capability not in defaults:
        raise ValueError(
            f"Unknown capability {capability!r}. Known: {list(defaults)}"
        )
    family = capability.split(".", 1)[0]

    key, slug = _pick_model(_env(capability, "MODEL", _LEGACY_MODEL_ENV),
                            capability, defaults[capability])
    entry = _REGISTRY["models"][key]

    provider = _env(capability, "PROVIDER", _LEGACY_PROVIDER_ENV) or "auto"
    if provider == "stub":
        backend = _STUB_BACKENDS[family]
    elif provider in ("auto", "replicate"):  # "replicate" kept as a legacy alias
        backend = entry["backend"]
    else:
        backend = provider  # an explicit backend module name in providers/backends/

    return {"capability": capability, "key": key, "slug": slug,
            "backend": backend, "provider": provider,
            "profile": dict(entry.get("profile", {}))}


def load_backend(resolved: dict):
    """Import the backend module a resolve() result points at."""
    import importlib

    name = resolved["backend"]
    try:
        return importlib.import_module(f".backends.{name}", package=__package__)
    except ModuleNotFoundError as e:
        raise ValueError(
            f"Backend module {name!r} not found in providers/backends/ "
            f"(capability {resolved['capability']!r}; check "
            f"{env_var(resolved['capability'], 'PROVIDER')} or the registry)"
        ) from e


def require_replicate_token() -> str:
    if not REPLICATE_API_TOKEN:
        raise RuntimeError(
            "REPLICATE_API_TOKEN is not set. Copy .env.example to .env and add your "
            "token, or run with BACKLOT_IMAGE_PROVIDER=stub / BACKLOT_VIDEO_PROVIDER"
            "=stub to test without spending."
        )
    return REPLICATE_API_TOKEN
