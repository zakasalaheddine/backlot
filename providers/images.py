"""Public image API. Callers use ONLY these functions; the backend is chosen
from env (config.IMAGE_PROVIDER). To add a host, drop a module in backends/
with the same two functions and register it in _BACKENDS.
"""
from __future__ import annotations

from pathlib import Path

from . import config


def _backend():
    name = config.IMAGE_PROVIDER
    if name == "replicate":
        from .backends import replicate_images as b
    elif name == "stub":
        from .backends import stub_images as b
    else:
        raise ValueError(
            f"Unknown BACKLOT_IMAGE_PROVIDER={name!r}. Known: replicate, stub."
        )
    return b


def generate_reference(prompt: str, angles, aspect: str = "4:5",
                       out_dir: str | Path = "out/refs", ref_imgs=None,
                       chain: bool = True) -> list[Path]:
    """Originate a character ref set — one image per angle from one seed prompt.

    angles: list of framing instructions, e.g.
        ["front, eye-level, neutral expression",
         "3/4 left, eye-level", "full body, standing"]

    chain (default True): once the first angle is generated, it is fed as a
    reference into every later angle so the turnaround stays the SAME person.
    This is the whole continuity trick — regenerating each angle independently
    from text alone drifts into different faces. Set False to disable.

    ref_imgs: optional seed images (e.g. real uploaded photos) used on angle 0.
    Returns the list of saved PNG paths, in angle order.
    """
    b = _backend()
    out_dir = Path(out_dir)
    paths: list[Path] = []
    for i, angle in enumerate(angles):
        out_path = out_dir / f"ref_{i:02d}.png"
        if i == 0:
            seed_refs = ref_imgs
        elif chain:
            seed_refs = [paths[0]] + list(ref_imgs or [])
        else:
            seed_refs = ref_imgs
        paths.append(b.generate_reference(prompt, angle, aspect, out_path, seed_refs))
    return paths


def composite(spec: dict, ref_imgs, aspect: str = "4:5",
              out_path: str | Path = "out/frame.png") -> Path:
    """Place locked reference images into a new scene.

    spec: {"prompt": str, "negative": str (optional)}
    ref_imgs: list of local reference image paths (character + product refs).
    Returns the saved PNG path.
    """
    b = _backend()
    return b.composite(
        spec["prompt"], spec.get("negative", ""), ref_imgs, aspect, Path(out_path)
    )
