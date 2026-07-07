---
name: ad-image
description: Generate static UGC / product ad creatives for the backlot content engine — composite a locked character and/or real product into a scene, then burn on headline/subhead/CTA copy as a deterministic layer, exported in multiple formats (1:1, 4:5, 9:16) and batched into variants for Meta/A-B testing. Use this whenever the user wants an ad image, static creative, product ad, carousel/feed image, "a post of my creator holding the product", a set of ad variants to test, or wants Claude to build them "a set of ads". Requires a character and/or product to already exist in the library — if not, create it with character-creator first. This is the fastest path to shippable ad creatives.
---

# ad-image

Turn a brief into a batch of **shippable ad creatives**: the real product and/or a
consistent character composited into a scene, with controlled copy burned on top,
in every format you need. Powerful because it composites *real* locked assets and
renders copy deterministically — not because it hopes a text-to-image model gets it
right.

Read these shared references first:
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md` — grill for the ad brief.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/ad-layout.md` — copy hierarchy, safe zones, why text is a layer.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/nano-banana.md` — how the keyframe prompt should read.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/continuity.md` — refs are locked; never regenerate the character.

## Preconditions (enforce these)
The ad **requires** a character and/or product already in the library. Check:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list
```
If the referenced character or product isn't there, stop and route to
**character-creator** to create it — never silently generate a throwaway identity or
a fake product.

## Flow

### 1. Grill for the brief
Follow `interview.md`: which product + character, the angle/hook, character-led vs
product-hero, formats, and how many variants + what differs between them so the A/B
is informative. Confirm before generating.

**Copy is optional.** The default deliverable is the clean composited keyframe. Only
grill for headline/subhead/CTA if the user actually wants burned-on copy — then add
an `overlay` block (below). If they don't, omit `overlay` entirely and the keyframe
is the final asset.

### 2. Emit the ad job JSON (you are the planner)
Compose the job in-context and write it to a file (e.g. `out/<name>/job.json`). The
`overlay` (and its `anchor`) is **optional** — include it only for burned-on copy;
omit it for a clean keyframe deliverable. When present, copy comes from you —
headline/subhead/CTA as clean strings. Schema:

```json
{
  "meta": {
    "brand": "EluNoire",
    "product": "heart-mug-01",
    "character": "maya-01",
    "angle": "Valentine's gift",
    "formats": ["1:1", "4:5", "9:16"]
  },
  "variants": [
    {
      "id": "v1",
      "concept": "Maya surprised, holding mug, morning light",
      "keyframe": {
        "prompt": "Using the provided person and the provided white heart mug: she's caught mid-laugh turning toward the window, one hand raising the mug like a cheers, weight on one hip, taken as a candid phone snapshot at a slightly tilted off-center angle, warm morning window light, natural shot-on-phone feel",
        "use_refs": ["maya-01", "heart-mug-01"],
        "negative": "studio lighting, watermark, warped text on the mug, stiff posture, catalog pose, standing straight facing camera, arms at sides, centered symmetrical framing, frozen expression"
      },
      "overlay": { "headline": "Forgot Valentine's again?", "subhead": "Panic-ordered. Arrived in time.", "cta": "Shop now" },
      "anchor": "bottom"
    }
  ]
}
```

Notes:
- `use_refs` are **library IDs**; the runner resolves them to locked ref images.
- **Direct a candid, in-motion moment — never a static pose.** Each keyframe prompt
  gives the character a specific action (mid-laugh, mirror-selfie, turning, reaching,
  walking) and a loose phone-camera angle. Push the anti-stiffness terms into
  `negative`. See "Make it feel alive" in `nano-banana.md` — this is the difference
  between a real-looking UGC post and an AI-stiff catalog shot.
- Keep the keyframe prompt free of any on-image text — copy is the overlay layer.
- For **product-hero** (no character), put only the product ID in `use_refs` and
  prompt for a clean studio set.
- For A/B: multiple `variants`, changing ONE thing (hook or scene, not both).
- `overlay` + `anchor` are optional. Omit both for a clean keyframe (no text). When
  included, `anchor` is `top` or `bottom` — pick per `ad-layout.md` safe zones.

### 3. Run it
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/run_ad.py out/<name>/job.json
```
This composites each variant × format (Nano-Banana), burns the copy layer only for
variants that have an `overlay` (`text_overlay.py`), and writes a `run_manifest.json`.
Each output's `ad` points to the copy-burned `ad_<format>.png` when there's an
overlay, or to the clean `keyframe_<format>.png` when there isn't. Keyframes are
content-addressed, so re-running after a copy tweak only re-burns text — it won't pay
to regenerate the image.

### 4. Review & iterate
Show the user the produced outputs (`ad`/`keyframe` paths from the manifest). Iterate
on copy (cheap — cached keyframe) or on the scene (regenerates). To force a fresh
keyframe, add `--force`.

## Testing without spending
`BACKLOT_IMAGE_PROVIDER=stub python ${CLAUDE_PLUGIN_ROOT}/scripts/run_ad.py out/<name>/job.json` runs the
entire pipeline with placeholder images — proves the job JSON and overlays before you
spend. Drop the prefix (with `REPLICATE_API_TOKEN` set) for real creatives.
