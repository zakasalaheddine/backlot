---
name: ugc-video
description: Generate a short UGC / ad VIDEO clip for the backlot content engine by animating an existing locked keyframe (image-to-video) with Seedance. Use this whenever the user wants a UGC video, reel, video ad, or to "animate" / "bring to life" an ad image or keyframe. Requires an existing keyframe (from ad-image) as the start frame — if none exists, create the character/product and an ad keyframe first. Silent motion clips (no audio, no burned captions) in v1.
---

# ugc-video

Animate a **locked keyframe** into a short clip. Powerful because it starts from a
real composited frame — the character, product, and print are already correct in
pixels — so Seedance only adds motion, it never re-invents identity.

Read these shared references first:
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md` — grill for the motion brief.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/seedance-motion.md` — how the motion prompt should read.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/continuity.md` — the frame is locked; animate it, don't restage.

## Preconditions (enforce these)
A clip **requires an existing keyframe** as its start frame — a `keyframe_*.png`
produced by ad-image, or any locked composited image. If there is no suitable
keyframe, stop and route to **ad-image** (which itself requires a character/product
from **character-creator**). Never generate a throwaway frame to animate.

Check what keyframes exist, e.g.:
```bash
ls out/*/*/keyframe_*.png
```

## Flow

### 1. Grill for the motion brief
Follow `interview.md`, kept short: which keyframe, what single motion beat, duration
(5s default, 10s only if needed), and whether the camera should be fixed. The motion
prompt is drafted by you (the planner) from the keyframe's concept — like ad copy —
then confirmed. See `seedance-motion.md`.

### 2. Emit the video job JSON (you are the planner)
Write it to `out/<name>/job.json`:

```json
{
  "meta": { "brand": "backlot", "notes": "reels from the Sunny tee set" },
  "clips": [
    {
      "id": "c1",
      "concept": "mirror selfie comes alive — subtle sway + phone tilt",
      "frame": "out/job/v1/keyframe_9x16.png",
      "motion": "she sways slightly and tilts the phone, hair moves naturally, gentle breathing, subtle smile shift; realistic hand-held phone micro-motion",
      "duration": 5,
      "resolution": "1080p",
      "camera_fixed": false,
      "negative": "morphing face, warping shirt print, garbled text, extra fingers, jitter"
    }
  ]
}
```

Notes:
- `frame` is an existing keyframe path — the locked composite. Never re-composite.
- Do NOT set `aspect_ratio` — the clip inherits the frame's ratio.
- `negative` is appended to the motion prompt as "Avoid: …" by the runner.
- Multiple `clips` batch fine; each animates one frame.

### 3. Run it
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/run_video.py out/<name>/job.json
```
Writes `out/<name>/<clip-id>/clip.mp4` plus a `run_manifest.json`. Clips are
content-addressed — a re-run skips already-rendered clips. Add `--force` to
re-render.

### 4. Review & iterate
Show the user the `clip.mp4` outputs. Iterate the motion prompt (regenerates — video
is the expensive step, so change intentionally). Watch for identity drift or print
warping; tighten the `negative` if you see it.

## Testing without spending
`BACKLOT_VIDEO_PROVIDER=stub python ${CLAUDE_PLUGIN_ROOT}/scripts/run_video.py out/<name>/job.json`
runs the whole pipeline with a placeholder .mp4 — proves the job JSON, validation,
caching, and manifest before you spend. Drop the prefix (with `REPLICATE_API_TOKEN`
set) for real clips.
