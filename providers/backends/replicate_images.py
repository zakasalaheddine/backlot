"""Replicate image backend — Nano-Banana (google/nano-banana).

Verified schema (google/nano-banana):
    prompt         string, required
    image_input    array of image URIs, default []  (supports MULTIPLE refs —
                   this is what lets us composite a locked character + product)
    aspect_ratio   one of: match_input_image, 1:1, 2:3, 3:2, 3:4, 4:3, 4:5,
                   5:4, 9:16, 16:9, 21:9
    output_format  jpg | png
    -> output is a SINGLE image URI.

Local reference files are passed as open file handles; the replicate client
uploads them and substitutes URLs.
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from .replicate_common import run_image

# Aspect ratios nano-banana accepts natively. Anything else must be produced by
# post-crop (the ad runner handles that) rather than asking the model.
NATIVE_ASPECTS = {
    "match_input_image", "1:1", "2:3", "3:2", "3:4", "4:3",
    "4:5", "5:4", "9:16", "16:9", "21:9",
}


def _aspect(aspect: str) -> str:
    return aspect if aspect in NATIVE_ASPECTS else "match_input_image"


def _run(prompt: str, ref_imgs, aspect: str, out_path: Path, output_format: str) -> Path:
    handles = [open(p, "rb") for p in (ref_imgs or [])]
    try:
        input_dict = {
            "prompt": prompt,
            "aspect_ratio": _aspect(aspect),
            "output_format": output_format,
        }
        if handles:
            input_dict["image_input"] = handles
        return run_image(config.NANO_BANANA_MODEL, input_dict, out_path)
    finally:
        for h in handles:
            h.close()


def generate_reference(prompt: str, angle: str, aspect: str, out_path: Path,
                       ref_imgs=None) -> Path:
    """Originate ONE angle of a character ref set from a seed prompt.

    The caller loops over angles; each call bakes the angle instruction into the
    prompt so the turnaround stays on-model. Optional ref_imgs seeds the identity
    from an existing image (e.g. angle 2+ referencing angle 1 for consistency).
    """
    full = f"{prompt}\n\nCamera / framing for this shot: {angle}."
    return _run(full, ref_imgs, aspect, out_path, output_format="png")


def composite(prompt: str, negative: str, ref_imgs, aspect: str, out_path: Path) -> Path:
    """Place locked reference images into a new scene described by prompt."""
    full = prompt
    if negative:
        full = f"{prompt}\n\nAvoid: {negative}."
    return _run(full, ref_imgs, aspect, out_path, output_format="png")
