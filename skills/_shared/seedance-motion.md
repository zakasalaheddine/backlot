# Seedance motion — image-to-video prompt patterns

Seedance (`bytedance/seedance-1-pro`) animates a **single start frame** into a
short clip. Our start frame is always a locked composited keyframe, so the
identity, product, and print are already correct in pixels — the motion prompt's
only job is to bring that exact frame to life without breaking it.

You never call Seedance directly. `providers/video.py` wraps it; you write the
`motion` string and pick the frame. Verified inputs: `image` (the frame),
`prompt` (motion, required), `duration` (5 or 10s), `resolution` (default 1080p),
optional `seed`, `camera_fixed`. `aspect_ratio` is ignored with an image — the
clip inherits the frame's ratio, so 9:16 keyframes stay 9:16.

## Compose from presets first

Motion is now authored from a **preset library** (`presets/motion.json`, listed via
`scripts/presets.py list`): named **camera** moves (dolly-in, crash-zoom, orbit-arc,
handheld-follow, …) and **subject actions** (show-product, mirror-selfie-alive,
walk-toward, …). A clip references a `camera` and/or `action` by id; the runner
composes them. Free-text `motion` is for fine-tuning on top — not the default.

Prefer a `verified` preset (tested to look good on Seedance). An `experimental`
preset may be mushy — warn the user before using one.

## Model selection & audio

The video model comes from the capability registry (`providers/models.json`),
default `bytedance/seedance-1-pro`. Inspect / swap with
`python ${CLAUDE_PLUGIN_ROOT}/scripts/models.py list|set video.i2v <model>`
(the legacy `BACKLOT_SEEDANCE_MODEL` env var still works). The backend adapts
per model:

- **seedance-1-pro** — silent clips; aspect inferred from the keyframe.
- **seedance-2.0** — can generate audio and needs an explicit aspect (handled for
  you). Audio is **off by default**; opt in per clip with `"audio": true` (adds
  synced ambient/SFX; quoted dialogue in the motion prompt can produce lip-synced
  speech). **2.0's moderation rejects photoreal PEOPLE in image-to-video**
  (error E005) — verified 2026-07: every frame with a human creator was flagged,
  including a plain character ref, while people-free product/b-roll scenes pass.
  In practice: 2.0 + audio is for b-roll and product scenes only; for character
  clips use `seedance-1-pro` (silent) with ElevenLabs VO on top.

## Authoring a new preset

When adding to `presets/motion.json`:
- `prompt`: one clause describing the move, written as a continuation ("the camera
  glides slowly toward the subject"; "she lifts the product toward the camera").
- `camera_fixed`: `true` only for locked-off camera presets; omit for actions.
- `duration`: the move's natural length (5 unless it needs 10).
- `negative`: the specific thing this move tends to break (e.g. a crash-zoom smears
  faces — put that here).
- `status`: start at `experimental`; promote to `verified` only after you render it
  on a real keyframe and confirm identity holds and the move reads cleanly.

## Motion that reads as real UGC

- **Describe small, human motion, not a new scene.** "She sways slightly, hair
  moves in a light breeze, subtle breathing, a small smile shift." The frame is
  already composed — you are adding life, not restaging.
- **Hand-held energy.** "Natural hand-held phone micro-motion, slight framing
  drift" reads as a real reel. For a mirror selfie, "the phone tilts a little as
  she shifts her weight."
- **One or two beats, not a story.** 5s holds one gesture well (a turn, a laugh
  landing, lifting the product toward camera). Don't script three actions.
- **`camera_fixed`.** Set `true` for a locked-off product-hero feel; leave
  `false` (default) for organic, moving-camera UGC.

## Protect the frame (put these in `negative`)

Seedance has no negative field — the runner appends `negative` to the prompt as
"Avoid: …". Always guard the things i2v tends to break:
`morphing face, identity drift, warping or distorting the shirt print, garbled
text, extra or melting fingers, flickering, heavy jitter, background warping`.

## What NOT to do

- Don't describe a different outfit, product, or place — that fights the frame
  and causes morphing. Animate what's there.
- Don't ask for on-screen text or captions — v1 clips are clean motion (copy is a
  later, separate layer, like the image side).
- Don't request long durations hoping for more — longer clips drift more. Prefer
  5s; use 10s only when the motion genuinely needs it.
