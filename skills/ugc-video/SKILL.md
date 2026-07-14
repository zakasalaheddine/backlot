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

List the motion presets before authoring a clip, and warn the user before using
any preset whose `status` is `experimental` (unverified on Seedance):
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/presets.py list
```

## Flow

### 1. Grill for the motion brief
Pick a **camera move** and/or a **subject action** from the preset library
(`presets.py list`), plus duration (5s default, 10s only if needed). Free-text
`motion` is optional, for fine-tuning on top of the presets. Warn before using an
`experimental` preset. You (the planner) still confirm the brief before rendering.

### 2. Emit the video job JSON (you are the planner)
Write it to `out/<name>/job.json`:

```json
{
  "meta": { "brand": "backlot", "notes": "reels from the Sunny tee set" },
  "clips": [
    {
      "id": "c1",
      "concept": "crash zoom onto the tee while she shows it off",
      "frame": "out/job/v1/keyframe_9x16.png",
      "camera": "crash-zoom",
      "action": "show-product",
      "motion": "",
      "negative": "garbled text"
    }
  ]
}
```

Notes:
- `frame` is an existing keyframe path — the locked composite. Never re-composite.
- Do NOT set `aspect_ratio` — the clip inherits the frame's ratio.
- `negative` is appended to the motion prompt as "Avoid: …" by the runner.
- Multiple `clips` batch fine; each animates one frame.
- `camera` / `action` reference preset ids (`presets.py list`); the runner expands
  them into the motion prompt + params. Free-text `motion` is optional/additive.
- A clip must supply at least one of `camera`, `action`, or `motion`.
- Preset-derived `camera_fixed`/`duration` are overridden by explicit clip fields.
- `audio` (optional, default false) — request generated audio. Only supported on
  audio-capable models (e.g. seedance-2.0); requesting it on a silent model is a
  clip-named error. Check / swap the active model with
  `python ${CLAUDE_PLUGIN_ROOT}/scripts/models.py list` (`set video.i2v <model>`).

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

### 5. Stitch into one video (optional)
When the user wants the clips assembled into a single reel, emit a timeline job
and run compose (needs the `ffmpeg` binary):

```json
{
  "meta": { "aspect": "9:16", "formats": ["9:16"], "fps": 24 },
  "clips": [
    { "id": "c1", "src": "out/<name>/c1/clip.mp4" },
    { "id": "c2", "src": "out/<name>/c2/clip.mp4", "trim": { "start": 0, "end": 4.5 } }
  ],
  "audio": {
    "vo":    [{ "src": "vo.wav", "at": 0.3 }],
    "music": { "src": "bed.wav", "gain_db": -6, "duck": true }
  },
  "captions": [{ "text": "POV: ...", "start": 0.0, "end": 2.2 }]
}
```

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/compose.py out/<name>/timeline.json
```

Clips are cut hard (no transitions), captions are burned deterministically with
PIL (a model never draws text), the `audio` block is optional (omit it and clip
audio passes through), and VO/music can be generated silent-for-now with
`providers/audio.py` (stub) until real audio lands. Every stage is cached — a
caption tweak re-exports masters without re-encoding or re-mixing anything.

## Testing without spending
`BACKLOT_VIDEO_PROVIDER=stub python ${CLAUDE_PLUGIN_ROOT}/scripts/run_video.py out/<name>/job.json`
runs the whole pipeline with a placeholder .mp4 — proves the job JSON, validation,
caching, and manifest before you spend. Drop the prefix (with `REPLICATE_API_TOKEN`
set) for real clips.
