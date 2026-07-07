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
