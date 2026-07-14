#!/usr/bin/env python3
"""Asset library — create / list / get characters & products.

The library is the spine of backlot: characters and products are created ONCE,
locked, and referenced by ID from every ad and video. This script owns the
on-disk conventions so the skills stay thin (they gather answers and call here).

Layout:
    assets/characters/<char-id>/character.json + refs/*.png
    assets/products/<product-id>/product.json  + refs/*.png

CLI (run from repo root):
    python scripts/assets.py originate-character --name Maya \
        --persona "mid-20s, warm, girl-next-door" \
        --descriptor "..." --seed-prompt "..." [--wardrobe ...] [--negative ...]
    python scripts/assets.py ingest-character  --name Maya --refs a.png b.png ...
    python scripts/assets.py create-product    --name "Heart Mug" \
        --descriptor "..." --constraints "..." --refs front.png angle.png
    python scripts/assets.py set-voice --id maya-01 --voice-id <elevenlabs-id> \
        [--voice-name Rachel] [--settings '{"stability": 0.5}']
    python scripts/assets.py list
    python scripts/assets.py get   --id maya-01
    python scripts/assets.py refs  --id maya-01     # print ref abs paths, one per line
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

# Make `providers` importable whether run from repo root or elsewhere.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Asset library location. Defaults to <plugin>/assets for in-repo dev; set
# BACKLOT_ASSETS_DIR to point it at the user's project when installed as a plugin.
ASSETS_DIR = Path(os.environ.get("BACKLOT_ASSETS_DIR", "").strip() or (REPO / "assets"))
CHARACTERS = ASSETS_DIR / "characters"
PRODUCTS = ASSETS_DIR / "products"

DEFAULT_ANGLES = [
    "front, eye-level, neutral friendly expression, plain background",
    "3/4 left, eye-level, plain background",
    "profile left, eye-level, plain background",
    "full body, standing, plain background",
]


# ---------- helpers ----------

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "asset"


def _next_id(base_dir: Path, name: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    slug = _slug(name)
    n = 1
    while (base_dir / f"{slug}-{n:02d}").exists():
        n += 1
    return f"{slug}-{n:02d}"


def _write_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def _load_manifest(asset_dir: Path) -> dict | None:
    for name in ("character.json", "product.json"):
        f = asset_dir / name
        if f.exists():
            return json.loads(f.read_text())
    return None


def _find_asset(asset_id: str) -> Path | None:
    for base in (CHARACTERS, PRODUCTS):
        d = base / asset_id
        if d.exists():
            return d
    return None


def _copy_refs(src_paths, dst_dir: Path) -> list[str]:
    dst_dir.mkdir(parents=True, exist_ok=True)
    rels = []
    for i, src in enumerate(src_paths):
        src = Path(src)
        dst = dst_dir / f"upload_{i:02d}{src.suffix.lower() or '.png'}"
        shutil.copy2(src, dst)
        rels.append(f"refs/{dst.name}")
    return rels


# ---------- public API (used by runners) ----------

def load_asset(asset_id: str) -> dict:
    """Return an asset manifest with an added _dir. Raises if missing."""
    d = _find_asset(asset_id)
    if not d:
        raise KeyError(
            f"Asset {asset_id!r} is not in the library. Create it first "
            f"(character-creator) — never silently generate a throwaway identity."
        )
    m = _load_manifest(d)
    m["_dir"] = str(d)
    return m


def resolve_refs(asset_id: str) -> list[Path]:
    """Absolute paths to an asset's locked reference images."""
    m = load_asset(asset_id)
    d = Path(m["_dir"])
    return [(d / r).resolve() for r in m.get("refs", [])]


def resolve_voice(asset_id: str) -> dict | None:
    """A character's locked voice block ({provider, voice_id, name, settings})
    or None if no voice has been locked yet (assets.py set-voice)."""
    return load_asset(asset_id).get("voice")


# ---------- commands ----------

def originate_character(args) -> None:
    """Generate a multi-angle ref set from one seed prompt, then lock it."""
    from providers import images

    char_id = _next_id(CHARACTERS, args.name, args.id)
    char_dir = CHARACTERS / char_id
    refs_dir = char_dir / "refs"
    angles = json.loads(args.angles) if args.angles else DEFAULT_ANGLES

    seed = args.seed_prompt or args.descriptor
    seed_refs = list(args.seed_refs) if args.seed_refs else None
    paths = images.generate_reference(
        seed, angles, aspect=args.aspect, out_dir=refs_dir, ref_imgs=seed_refs
    )
    rels = [f"refs/{p.name}" for p in paths]

    manifest = {
        "id": char_id,
        "name": args.name,
        "persona": args.persona or "",
        "appearance": {
            "descriptor": args.descriptor,
            "wardrobe_default": args.wardrobe or "",
            "negative": args.negative or "",
        },
        "refs": rels,
        "seed_prompt": seed,
        "created_from": "generate",
        "version": 1,
    }
    _write_manifest(char_dir / "character.json", manifest)
    print(json.dumps({"id": char_id, "dir": str(char_dir), "refs": rels}, indent=2))


def ingest_character(args) -> None:
    """Lock a character from real uploaded photos (no generation)."""
    char_id = _next_id(CHARACTERS, args.name, args.id)
    char_dir = CHARACTERS / char_id
    rels = _copy_refs(args.refs, char_dir / "refs")
    manifest = {
        "id": char_id,
        "name": args.name,
        "persona": args.persona or "",
        "appearance": {
            "descriptor": args.descriptor,
            "wardrobe_default": args.wardrobe or "",
            "negative": args.negative or "",
        },
        "refs": rels,
        "seed_prompt": args.descriptor,
        "created_from": "upload",
        "version": 1,
    }
    _write_manifest(char_dir / "character.json", manifest)
    print(json.dumps({"id": char_id, "dir": str(char_dir), "refs": rels}, indent=2))


def create_product(args) -> None:
    """Products are always real: lock uploaded photos + constraints."""
    prod_id = _next_id(PRODUCTS, args.name, args.id)
    prod_dir = PRODUCTS / prod_id
    rels = _copy_refs(args.refs, prod_dir / "refs")
    manifest = {
        "id": prod_id,
        "name": args.name,
        "descriptor": args.descriptor,
        "refs": rels,
        "constraints": args.constraints or "",
        "version": 1,
    }
    _write_manifest(prod_dir / "product.json", manifest)
    print(json.dumps({"id": prod_id, "dir": str(prod_dir), "refs": rels}, indent=2))


def set_voice(args) -> None:
    """Lock a voice onto a character — same continuity trick as the face refs:
    picked once, then every VO take sounds like the same person."""
    char_dir = CHARACTERS / args.id
    if not char_dir.exists():
        if _find_asset(args.id):
            print(f"{args.id!r} is a product — only characters have voices",
                  file=sys.stderr)
        else:
            print(f"No character with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    manifest = _load_manifest(char_dir)
    voice = {
        "provider": args.provider,
        "voice_id": args.voice_id,
        "name": args.voice_name or "",
    }
    if args.settings:
        voice["settings"] = json.loads(args.settings)
    manifest["voice"] = voice
    manifest["version"] = int(manifest.get("version", 1)) + 1
    _write_manifest(char_dir / "character.json", manifest)
    print(json.dumps({"id": args.id, "voice": voice,
                      "version": manifest["version"]}, indent=2))


def list_assets(args) -> None:
    def rows(base: Path, kind: str):
        out = []
        if base.exists():
            for d in sorted(base.iterdir()):
                m = _load_manifest(d)
                if m:
                    out.append({
                        "kind": kind, "id": m["id"], "name": m.get("name", ""),
                        "refs": len(m.get("refs", [])), "version": m.get("version", 1),
                    })
        return out

    data = rows(CHARACTERS, "character") + rows(PRODUCTS, "product")
    print(json.dumps(data, indent=2))


def get_asset(args) -> None:
    d = _find_asset(args.id)
    if not d:
        print(f"No asset with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    m = _load_manifest(d)
    m["_dir"] = str(d)
    m["_refs_abs"] = [str((d / r).resolve()) for r in m.get("refs", [])]
    print(json.dumps(m, indent=2))


def refs_of(args) -> None:
    d = _find_asset(args.id)
    if not d:
        print(f"No asset with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    m = _load_manifest(d)
    for r in m.get("refs", []):
        print(str((d / r).resolve()))


# ---------- CLI ----------

def main() -> None:
    p = argparse.ArgumentParser(description="backlot asset library")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common_char(sp):
        sp.add_argument("--name", required=True)
        sp.add_argument("--id", default=None, help="explicit id (else auto: name-01)")
        sp.add_argument("--persona", default="")
        sp.add_argument("--descriptor", required=True,
                        help="canonical text injected into every future prompt")
        sp.add_argument("--wardrobe", default="")
        sp.add_argument("--negative", default="")

    o = sub.add_parser("originate-character", help="generate a ref set from a seed")
    add_common_char(o)
    o.add_argument("--seed-prompt", default="")
    o.add_argument("--angles", default="", help="JSON list; default 4-angle turnaround")
    o.add_argument("--aspect", default="4:5")
    o.add_argument("--seed-refs", nargs="*", default=None,
                   help="optional images to seed identity on angle 0")
    o.set_defaults(func=originate_character)

    ic = sub.add_parser("ingest-character", help="lock a character from real photos")
    add_common_char(ic)
    ic.add_argument("--refs", nargs="+", required=True)
    ic.set_defaults(func=ingest_character)

    cp = sub.add_parser("create-product", help="lock a product from real photos")
    cp.add_argument("--name", required=True)
    cp.add_argument("--id", default=None)
    cp.add_argument("--descriptor", required=True)
    cp.add_argument("--constraints", default="")
    cp.add_argument("--refs", nargs="+", required=True)
    cp.set_defaults(func=create_product)

    sv = sub.add_parser("set-voice", help="lock a voice onto a character")
    sv.add_argument("--id", required=True)
    sv.add_argument("--voice-id", required=True, help="provider voice id")
    sv.add_argument("--voice-name", default="", help="human-readable voice name")
    sv.add_argument("--provider", default="elevenlabs")
    sv.add_argument("--settings", default="",
                    help='optional JSON, e.g. {"stability": 0.5, "similarity_boost": 0.75}')
    sv.set_defaults(func=set_voice)

    ls = sub.add_parser("list", help="list all assets")
    ls.set_defaults(func=list_assets)

    g = sub.add_parser("get", help="print one asset manifest + resolved ref paths")
    g.add_argument("--id", required=True)
    g.set_defaults(func=get_asset)

    r = sub.add_parser("refs", help="print ref abs paths (one per line)")
    r.add_argument("--id", required=True)
    r.set_defaults(func=refs_of)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
