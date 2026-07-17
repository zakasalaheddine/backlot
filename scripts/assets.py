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

# The character sheet is the FIRST and only thing origination produces: one
# composite image (turnaround + head/expression grid on plain white, no text
# panels, no wardrobe/accessory/cinematic panels). Individual clean pose refs are
# generated later, on demand, from the sheet — see `add-pose`.
SHEET_ASPECT = "3:2"

DEFAULT_EXPRESSIONS = ["neutral", "happy", "sad", "angry", "surprised", "determined", "thoughtful"]

# Characters are PHOTOREAL by default — a real person, not an illustration. Pass
# --style "illustrated"/"anime"/etc only when the user explicitly asks for art.
PHOTOREAL_STYLE = (
    "Photorealistic — a real photograph of a real person, natural skin texture "
    "with pores and fine detail, realistic lighting, shot on a DSLR, sharp focus. "
    "This is a PHOTO, not an illustration, not a drawing, not a painting, not "
    "anime, not a cartoon, not a 3D render."
)
PHOTOREAL_NEGATIVE = ("illustration, drawing, painting, sketch, anime, cartoon, "
                      "comic, cgi, 3d render, digital art, painterly, stylized")

SHEET_TEMPLATE = (
    "{style}\n\n"
    "A single clean CHARACTER REFERENCE SHEET on a plain white background. "
    "No text, no labels, no color swatches, no wardrobe or accessory cut-outs, "
    "no cinematic scene, no props. One consistent person in every view, "
    "uniform even studio lighting, sharp detail.\n\n"
    "TOP ROW: a full-body turnaround of the SAME person — front view, side "
    "profile, and back view, neutral standing pose.\n"
    "BELOW: a grid of head-and-shoulders shots of the SAME person from multiple "
    "angles (front, 3/4 left, 3/4 right, profile left, profile right, tilted up, "
    "tilted down), cycling through a range of EXPRESSIONS: {expressions}.\n"
    "Plus one larger clean head-and-shoulders hero portrait.\n\n"
    "The person: {identity}"
)


# ---------- helpers ----------

def _style_clause(style: str) -> str:
    return PHOTOREAL_STYLE if style == "photoreal" else f"Art style: {style}."


def _merge_negative(negative: str, style: str) -> str:
    """Add anti-illustration terms for photoreal; leave art styles untouched."""
    if style != "photoreal":
        return negative
    return f"{negative}, {PHOTOREAL_NEGATIVE}".strip(", ") if negative else PHOTOREAL_NEGATIVE

def _expression_names(sheet: dict | None) -> list[str]:
    """Expression labels for the sheet grid. Reads sheet.character.expressions
    (list of names or {name, ...} dicts); falls back to a sensible default set."""
    exprs = ((sheet or {}).get("character", {}) or {}).get("expressions", [])
    names = [e.get("name", "") if isinstance(e, dict) else str(e) for e in exprs]
    names = [n for n in names if n]
    return names or DEFAULT_EXPRESSIONS


def _sheet_prompt(sheet: dict | None, descriptor: str, style: str) -> str:
    base = ((sheet or {}).get("prompt_config", {}) or {}).get("base_prompt", "") or descriptor
    return SHEET_TEMPLATE.format(
        style=_style_clause(style),
        expressions=", ".join(_expression_names(sheet)), identity=base)


def _prompt_cfg(sheet: dict | None) -> dict:
    return (sheet or {}).get("prompt_config", {}) or {}

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


def _parse_sheet(raw: str | None) -> dict | None:
    """Parse the optional --sheet JSON blob (the structured character sheet).
    Stored verbatim; assets.py stays schema-blind so the sheet can evolve in the
    skill without touching Python."""
    return json.loads(raw) if raw else None


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
    """Generate the CHARACTER SHEET (one composite image) and lock it. Individual
    pose refs are NOT generated here — add them later with `add-pose`."""
    from providers import images

    char_id = _next_id(CHARACTERS, args.name, args.id)
    char_dir = CHARACTERS / char_id
    char_dir.mkdir(parents=True, exist_ok=True)

    sheet = _parse_sheet(args.sheet)
    cfg = _prompt_cfg(sheet)
    base_prompt = cfg.get("base_prompt", "") or args.descriptor
    negative = _merge_negative(cfg.get("negative_prompt", "") or args.negative or "", args.style)
    seed_refs = list(args.seed_refs) if args.seed_refs else []

    sheet_path = char_dir / "character_sheet.png"
    images.composite(
        {"prompt": _sheet_prompt(sheet, args.descriptor, args.style), "negative": negative},
        seed_refs, aspect=args.aspect, out_path=sheet_path,
    )

    manifest = {
        "id": char_id,
        "name": args.name,
        "persona": args.persona or "",
        "appearance": {
            "descriptor": args.descriptor,
            "wardrobe_default": args.wardrobe or "",
            "negative": args.negative or "",
        },
        "style": args.style,
        "sheet_image": "character_sheet.png",
        "refs": [],  # poses are deferred — see `add-pose`
        "seed_prompt": base_prompt,
        "created_from": "generate",
        "version": 1,
    }
    if sheet is not None:
        manifest["sheet"] = sheet
    _write_manifest(char_dir / "character.json", manifest)
    print(json.dumps({"id": char_id, "dir": str(char_dir),
                      "sheet_image": "character_sheet.png", "refs": []}, indent=2))


def add_pose(args) -> None:
    """Generate ONE clean pose ref for an existing character, seeded from its
    sheet (or an earlier pose) so it stays the same person. This is how a
    compositing-ready ref comes into being — only when an ad/video needs it."""
    from providers import images

    d = _find_asset(args.id)
    if not d or not (d / "character.json").exists():
        print(f"No character with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    m = _load_manifest(d)
    refs_dir = d / "refs"
    refs_dir.mkdir(exist_ok=True)

    # Identity anchor: an existing pose ref if any, else the character sheet.
    anchor = None
    if m.get("refs"):
        anchor = (d / m["refs"][0]).resolve()
    elif m.get("sheet_image"):
        anchor = (d / m["sheet_image"]).resolve()

    cfg = _prompt_cfg(m.get("sheet"))
    style = m.get("style", "photoreal")
    base = cfg.get("base_prompt", "") or m["appearance"]["descriptor"]
    negative = _merge_negative(
        cfg.get("negative_prompt", "") or m["appearance"].get("negative", ""), style)
    prompt = (f"{_style_clause(style)}\n\n{base}\n\nSingle clean shot of this exact "
              f"same person — one figure only, no sheet, no grid, plain neutral "
              f"background.\nPose / framing: {args.pose}.")

    n = len(m.get("refs", []))
    out = refs_dir / f"pose_{n:02d}.png"
    images.composite({"prompt": prompt, "negative": negative},
                     [anchor] if anchor else [], aspect=args.aspect, out_path=out)

    rel = f"refs/{out.name}"
    m.setdefault("refs", []).append(rel)
    m["version"] = int(m.get("version", 1)) + 1
    _write_manifest(d / "character.json", m)
    print(json.dumps({"id": args.id, "pose": rel, "refs": m["refs"]}, indent=2))


def ingest_character(args) -> None:
    """Lock a character from real uploaded photos (no generation)."""
    char_id = _next_id(CHARACTERS, args.name, args.id)
    char_dir = CHARACTERS / char_id
    rels = _copy_refs(args.refs, char_dir / "refs")
    sheet = _parse_sheet(args.sheet)
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
    if sheet is not None:
        manifest["sheet"] = sheet
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
        sp.add_argument("--sheet", default="",
                        help="structured character sheet as JSON (stored verbatim; "
                             "its prompt_config.base_prompt drives origination)")

    o = sub.add_parser("originate-character",
                       help="generate the character SHEET (poses come later)")
    add_common_char(o)
    o.add_argument("--aspect", default=SHEET_ASPECT, help="sheet aspect (landscape)")
    o.add_argument("--style", default="photoreal",
                   help="'photoreal' (default, a real person) or an art style like "
                        "'illustrated', 'anime', '3d pixar' — only when asked")
    o.add_argument("--seed-refs", nargs="*", default=None,
                   help="optional images to seed identity (e.g. real photos)")
    o.set_defaults(func=originate_character)

    ap = sub.add_parser("add-pose",
                        help="generate one clean pose ref from a character's sheet")
    ap.add_argument("--id", required=True)
    ap.add_argument("--pose", required=True,
                    help="framing/pose, e.g. 'front, standing, arms relaxed'")
    ap.add_argument("--aspect", default="4:5")
    ap.set_defaults(func=add_pose)

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
