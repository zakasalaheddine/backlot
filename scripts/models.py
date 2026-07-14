#!/usr/bin/env python3
"""Model registry CLI — inspect and swap which model serves each capability.

The registry lives in providers/models.json; per-capability env overrides
(BACKLOT_<CAPABILITY>_MODEL / _PROVIDER) are honoured and shown. `set` persists
an override into the plugin .env so it applies to every later run.

Usage (from repo root):
    python scripts/models.py list [--json]
    python scripts/models.py inspect <capability|model-key>
    python scripts/models.py set <capability> <model-key-or-slug>
    python scripts/models.py set <capability> --provider stub|auto|<backend>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from providers import config  # noqa: E402


def _alternates(capability: str) -> list[str]:
    return [k for k, m in config.models().items()
            if capability in m["capabilities"]]


def _snapshot() -> list[dict]:
    rows = []
    for cap in config.capabilities():
        res = config.resolve(cap)
        rows.append({
            "capability": cap,
            "model": res["key"],
            "slug": res["slug"],
            "backend": res["backend"],
            "provider": res["provider"],
            "alternates": [k for k in _alternates(cap) if k != res["key"]],
        })
    return rows


def cmd_list(as_json: bool) -> None:
    rows = _snapshot()
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    cols = ["capability", "model", "slug", "backend", "provider"]
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        line = "  ".join(str(r[c]).ljust(widths[c]) for c in cols)
        alt = ", ".join(r["alternates"])
        print(line + (f"  (alternates: {alt})" if alt else ""))
    print("\nswap: python scripts/models.py set <capability> <model>   "
          "(or --provider stub for zero-cost runs)")


def cmd_inspect(name: str) -> None:
    if name in config.capabilities():
        print(json.dumps(config.resolve(name), indent=2))
        return
    entry = config.models().get(name)
    if entry is None:
        raise SystemExit(
            f"unknown capability or model {name!r}. Capabilities: "
            f"{config.capabilities()}; models: {list(config.models())}"
        )
    print(json.dumps({"model": name, **entry}, indent=2))


def _write_env(env_file: Path, key: str, value: str) -> None:
    """Set key=value in the env file, replacing an existing assignment."""
    lines = env_file.read_text().splitlines() if env_file.exists() else []
    out, replaced = [], False
    for line in lines:
        if line.split("=", 1)[0].strip() == key and "=" in line:
            out.append(f"{key}={value}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"{key}={value}")
    env_file.write_text("\n".join(out) + "\n")


def cmd_set(capability: str, model: str | None, provider: str | None,
            env_file: Path) -> None:
    if capability not in config.capabilities():
        raise SystemExit(
            f"unknown capability {capability!r}. Known: {config.capabilities()}"
        )
    if not model and not provider:
        raise SystemExit("nothing to set: give a model, --provider, or both")

    if model:
        valid = _alternates(capability)
        if model not in valid and "/" not in model:
            raise SystemExit(
                f"unknown model {model!r} for {capability!r}. Registry models: "
                f"{valid} (or pass a raw host slug like 'owner/name[:version]')"
            )
        if model not in valid:
            print(f"note: {model!r} is not in the registry — it will run under "
                  f"the default model's backend and conservative profile")
        _write_env(env_file, config.env_var(capability, "MODEL"), model)
        print(f"{config.env_var(capability, 'MODEL')}={model}  -> {env_file}")

    if provider:
        known = {"stub", "auto", "replicate"}
        if provider not in known and not (
                config.PLUGIN_ROOT / "providers" / "backends" / f"{provider}.py").exists():
            raise SystemExit(
                f"unknown provider {provider!r}: use stub/auto or a module name "
                f"that exists in providers/backends/"
            )
        _write_env(env_file, config.env_var(capability, "PROVIDER"), provider)
        print(f"{config.env_var(capability, 'PROVIDER')}={provider}  -> {env_file}")

    print("(exported env vars still win over .env; unset them if a change "
          "doesn't seem to apply)")


def main() -> None:
    p = argparse.ArgumentParser(description="Inspect / swap capability models")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("list", help="active model per capability")
    lp.add_argument("--json", action="store_true")

    ip = sub.add_parser("inspect", help="full detail for a capability or model")
    ip.add_argument("name")

    sp = sub.add_parser("set", help="persist a model/provider override to .env")
    sp.add_argument("capability")
    sp.add_argument("model", nargs="?", default=None,
                    help="registry key or raw host slug")
    sp.add_argument("--provider", default=None,
                    help="stub | auto | backend module name")
    sp.add_argument("--env-file", default=str(config.PLUGIN_ROOT / ".env"),
                    help="env file to write (default: plugin .env)")

    a = p.parse_args()
    if a.cmd == "list":
        cmd_list(a.json)
    elif a.cmd == "inspect":
        cmd_inspect(a.name)
    else:
        cmd_set(a.capability, a.model, a.provider, Path(a.env_file))


if __name__ == "__main__":
    main()
