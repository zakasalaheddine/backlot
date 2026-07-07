"""Stub image backend — deterministic placeholder PNGs, no token, no cost.

Selected with BACKLOT_IMAGE_PROVIDER=stub. Lets you exercise the entire
skill/script/runner pipeline (asset creation, ad jobs, format export, text
overlay) before spending a cent on Replicate. Swap back to `replicate` for
real pixels. Same signatures as replicate_images.py.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw

# Pixel dimensions per aspect for the placeholder canvas.
_DIMS = {
    "1:1": (1024, 1024), "4:5": (1024, 1280), "9:16": (1080, 1920),
    "16:9": (1920, 1080), "4:3": (1024, 768), "3:4": (768, 1024),
    "2:3": (768, 1152), "3:2": (1152, 768), "5:4": (1280, 1024),
    "21:9": (1680, 720), "match_input_image": (1024, 1024),
}


def _canvas(text: str, aspect: str, out_path: Path) -> Path:
    w, h = _DIMS.get(aspect, (1024, 1024))
    # Deterministic background colour from the text so different prompts differ.
    digest = hashlib.md5(text.encode()).hexdigest()
    bg = tuple(int(digest[i:i + 2], 16) // 2 + 60 for i in (0, 2, 4))
    img = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 8, w - 8, h - 8], outline=(255, 255, 255), width=4)
    label = (text[:120] + "...") if len(text) > 120 else text
    draw.multiline_text((24, 24), f"[STUB {aspect}]\n{label}", fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


def generate_reference(prompt: str, angle: str, aspect: str, out_path: Path,
                       ref_imgs=None) -> Path:
    return _canvas(f"REF {angle}: {prompt}", aspect, out_path)


def composite(prompt: str, negative: str, ref_imgs, aspect: str, out_path: Path) -> Path:
    refs = ", ".join(Path(p).name for p in (ref_imgs or []))
    return _canvas(f"COMPOSITE (refs: {refs})\n{prompt}", aspect, out_path)
