# Nano-Banana — compositing & editing prompt patterns

Nano-Banana (google/nano-banana on Replicate) is an **image editing / compositing**
model, not a plain text-to-image model. Its power for us: given `image_input` (up to
several reference images) + a `prompt`, it places those *real* references into a new
scene. That's how we get a consistent character and the actual product into an ad.

Verified input schema (see `providers/backends/replicate_images.py`):
- `prompt` (required) — the scene + instruction.
- `image_input` — array of reference image URIs (multiple supported).
- `aspect_ratio` — one of `1:1 4:5 9:16 16:9 4:3 3:4 2:3 3:2 5:4 21:9 match_input_image`.
- `output_format` — `png` (what we use).
- Output: a single image.

**You never call this directly.** `providers/images.py` wraps it. You write the
`prompt` and pick refs; the provider layer handles the API. Swapping to fal/another
host is a backend change with no effect on your prompts.

## Prompt patterns that work

- **Name the references by role, then describe the scene.**
  "Using the provided person and the provided white mug: she sits at a sunlit
  kitchen counter holding the mug, looking at it and smiling."
- **Describe the light and camera, not just the subject.** "warm morning window
  light, shot on a phone, slightly candid framing" reads as organic UGC; "even
  studio softbox, centered" reads as a catalog. Pick on purpose.
- **Protect the product.** For products with print/text, add "keep the mug's
  printed photo and text sharp, legible, and undistorted; true white ceramic."
  Carry `product.constraints` through verbatim.
- **Keep the identity locked in words too.** Append the character's canonical
  `descriptor` so pixels and text agree.
- **Use the negative.** Pass character `negative` + scene-specific don'ts (e.g.
  "no extra logos, no watermark, no warped text").

## Make it feel alive — pose, energy, candor (scene keyframes only)

The #1 reason a composited ad reads as "AI" is a **stiff, centered, standing-there**
subject staring at the lens like a catalog model. Real UGC is caught *mid-moment*.
For every ad/scene keyframe, direct a specific action and a specific camera — never
let the subject just stand and pose. (This is for ad **scenes**, not the character's
ref turnaround, which stays neutral for clean compositing.)

- **Give her a verb, not a pose.** Caught mid-laugh, glancing over her shoulder,
  turning toward the window, tucking hair behind her ear, walking through the
  doorway, flopping onto the bed, reaching for the product, mid-sip, mid-sentence
  talking to camera. "She *does* X" beats "she stands."
- **Selfie & mirror framing read as real.** Arm extended holding the phone (front-
  camera, slight wide-angle closeness), or a **mirror selfie** with the phone visible
  in her hand and the room reflected. Front-camera imperfection sells authenticity.
- **Loosen the body.** Weight on one hip, a hand gesturing, leaning on a wall or
  doorframe, sitting cross-legged, one knee up — asymmetry and contrapposto, not
  feet-together-arms-at-sides.
- **Loosen the camera.** Slightly off-center or tilted framing, a candid crop that
  cuts a little awkwardly, shot-on-phone grain, natural motion. "Snapshot" not
  "portrait session." Still leave the copy safe zone clear (see `ad-layout.md`).
- **Micro-expression over neutral smile.** A real laugh, a smirk, surprise,
  concentration — a specific feeling, not a held grin.

Bake the anti-stiffness into the **negative** too, e.g.:
`stiff posture, catalog pose, standing straight facing camera, arms at sides,
centered symmetrical framing, lookbook, studio catalog look, frozen expression`.

## What NOT to do

- Don't ask the model to render headline/subhead/CTA copy — it warps text. Copy is
  a separate deterministic layer (`scripts/text_overlay.py`). See `ad-layout.md`.
- Don't regenerate the character from a text prompt to "save a step." That breaks
  continuity — always pass the locked refs. See `continuity.md`.
- Don't default to "she stands in the room and smiles at the camera." That's the
  static look we're explicitly avoiding — give her an action and a candid camera.
