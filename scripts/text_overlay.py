#!/usr/bin/env python3
"""Deterministic ad text overlay (PIL).

Copy legibility is where AI ads look sloppy — so headline/subhead/CTA are NEVER
drawn by the image model. Claude writes the copy; this burns it in as a crisp
layer with a contrast scrim and a real CTA button, positioned inside per-format
safe zones. Same input -> same pixels, every time.

Used by run_ad.py, but also runnable standalone:
    python scripts/text_overlay.py base.png out.png \
        --headline "Forgot Valentine's?" --subhead "Sorted in 2 minutes." \
        --cta "Shop now" --aspect 9:16 --anchor bottom
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Common macOS/Linux font candidates. Real bold files first so headlines/CTA are
# actually bold (Helvetica.ttc loads its regular face by default under PIL).
_BOLD_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
_REG_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int, bold: bool):
    for path in (_BOLD_FONTS if bold else _REG_FONTS):
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _draw_block(draw, lines, font, x, y, fill, line_gap):
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y = bbox[3] + line_gap
    return y


def render_overlay(base_path, overlay: dict, out_path, aspect: str = "1:1",
                   anchor: str = "bottom") -> Path:
    """Burn headline/subhead/CTA onto base_path -> out_path.

    overlay: {"headline": str, "subhead": str, "cta": str}  (any may be empty)
    anchor:  "top" | "bottom" — which safe zone to place copy in.
    """
    img = Image.open(base_path).convert("RGB")
    W, H = img.size
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    margin = int(W * 0.06)
    max_w = W - 2 * margin
    head_font = _font(int(W * 0.075), bold=True)
    sub_font = _font(int(W * 0.040), bold=False)
    cta_font = _font(int(W * 0.045), bold=True)

    headline = overlay.get("headline", "").strip()
    subhead = overlay.get("subhead", "").strip()
    cta = overlay.get("cta", "").strip()

    head_lines = _wrap(draw, headline, head_font, max_w) if headline else []
    sub_lines = _wrap(draw, subhead, sub_font, max_w) if subhead else []

    # Measure block height for the scrim + placement.
    def block_h(lines, font, gap):
        if not lines:
            return 0
        h = 0
        for ln in lines:
            bb = draw.textbbox((0, 0), ln, font=font)
            h += (bb[3] - bb[1]) + gap
        return h

    head_gap, sub_gap = int(H * 0.012), int(H * 0.008)
    text_h = block_h(head_lines, head_font, head_gap) + block_h(sub_lines, sub_font, sub_gap)
    cta_h = int(H * 0.075) if cta else 0
    total_h = text_h + (int(H * 0.03) + cta_h if cta else 0)

    pad = int(H * 0.04)
    if anchor == "top":
        scrim_top, y = 0, margin
    else:
        scrim_top = H - total_h - pad * 2
        y = scrim_top + pad

    # Contrast scrim (gradient-ish: solid band) so any background stays readable.
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(scrim)
    if anchor == "top":
        sdraw.rectangle([0, 0, W, total_h + pad * 2], fill=(0, 0, 0, 140))
    else:
        sdraw.rectangle([0, scrim_top, W, H], fill=(0, 0, 0, 140))
    layer = Image.alpha_composite(layer, scrim)
    draw = ImageDraw.Draw(layer)

    y = _draw_block(draw, head_lines, head_font, margin, y, (255, 255, 255, 255), head_gap)
    if sub_lines:
        y += int(H * 0.01)
        y = _draw_block(draw, sub_lines, sub_font, margin, y, (235, 235, 235, 255), sub_gap)

    if cta:
        y += int(H * 0.02)
        tw = draw.textlength(cta, font=cta_font)
        bb = draw.textbbox((0, 0), cta, font=cta_font)
        th = bb[3] - bb[1]
        bx0, by0 = margin, y
        bx1, by1 = int(margin + tw + W * 0.08), int(y + th + H * 0.03)
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=int(H * 0.02),
                               fill=(255, 255, 255, 255))
        draw.text((bx0 + (bx1 - bx0 - tw) / 2, by0 + (by1 - by0 - th) / 2 - bb[1]),
                  cta, font=cta_font, fill=(15, 15, 15, 255))

    out = Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path, "PNG")
    return out_path


def render_caption(text: str, width: int, height: int, out_path) -> Path:
    """Render ONE video caption as a full-frame transparent PNG.

    Reel-style: bold white text in a dark rounded pill, centered, sitting at
    ~78% height so it clears both the subject and platform UI. compose.py
    overlays these onto the video for a caption's time window — same principle
    as the ad overlay: text is always drawn deterministically, never by a model.
    """
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    font = _font(int(height * 0.032), bold=True)
    max_w = int(width * 0.82)
    lines = _wrap(draw, text.strip(), font, max_w)

    line_gap = int(height * 0.006)
    sizes = [draw.textbbox((0, 0), ln, font=font) for ln in lines]
    line_hs = [bb[3] - bb[1] for bb in sizes]
    block_h = sum(line_hs) + line_gap * (len(lines) - 1)
    block_w = max((bb[2] - bb[0]) for bb in sizes) if lines else 0

    pad_x, pad_y = int(width * 0.03), int(height * 0.012)
    cx = width // 2
    block_bottom = int(height * 0.80)
    top = block_bottom - block_h - pad_y
    draw.rounded_rectangle(
        [cx - block_w // 2 - pad_x, top,
         cx + block_w // 2 + pad_x, block_bottom + pad_y],
        radius=int(height * 0.012), fill=(0, 0, 0, 170))

    y = block_bottom - block_h
    for ln, bb, lh in zip(lines, sizes, line_hs):
        lw = bb[2] - bb[0]
        draw.text((cx - lw / 2 - bb[0], y - bb[1]), ln, font=font,
                  fill=(255, 255, 255, 255))
        y += lh + line_gap

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    layer.save(out_path, "PNG")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(description="Burn ad copy onto an image")
    p.add_argument("base")
    p.add_argument("out")
    p.add_argument("--headline", default="")
    p.add_argument("--subhead", default="")
    p.add_argument("--cta", default="")
    p.add_argument("--aspect", default="1:1")
    p.add_argument("--anchor", default="bottom", choices=["top", "bottom"])
    a = p.parse_args()
    out = render_overlay(a.base, {"headline": a.headline, "subhead": a.subhead,
                                  "cta": a.cta}, a.out, a.aspect, a.anchor)
    print(str(out))


if __name__ == "__main__":
    main()
