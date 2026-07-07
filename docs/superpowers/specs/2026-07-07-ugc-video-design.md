# ugc-video (v1) — design

**Date:** 2026-07-07
**Status:** approved, ready for implementation plan

## Goal

Build the missing v1 capability: turn an existing, locked ad **keyframe** into a
short UGC **video clip** (image-to-video) via Seedance on Replicate, behind the same
swappable provider seam the image pipeline uses. Ships the smallest useful thing —
one silent motion clip per keyframe — reusing everything already built.

Scope decisions (from brainstorming):
- **Single clip from an existing keyframe.** Not a multi-shot stitched reel, not a
  combined generate+animate command. You make several clips by listing several in one
  job. Multi-shot stitching and fresh-generate-then-animate are explicitly out of v1.
- **Interface = a small video job JSON**, mirroring `run_ad.py`. Versioned,
  re-runnable, supports multiple clips per file.
- **No burned copy and no audio in v1** — clips are silent motion, consistent with
  the keyframe-only (no text overlay) direction. Captions/audio are future.

## Verified Seedance schema (bytedance/seedance-1-pro)

Pulled from the Replicate model API, not guessed:

| field | type | notes |
|---|---|---|
| `prompt` | string | **required** — the motion/text prompt |
| `image` | string | start frame for image-to-video |
| `aspect_ratio` | enum | **ignored when `image` is passed** — clip inherits the frame's ratio |
| `duration` | int | seconds, default `5` (supports 5 or 10) |
| `resolution` | enum | `480p` / `720p` / `1080p` (default `1080p`) |
| `fps` | enum | `24` only |
| `seed` | int | optional, for reproducibility |
| `camera_fixed` | bool | optional, pin camera position |
| `last_frame_image` | string | optional — enables future last-frame continuity chaining |
| **output** | string (uri) | a single `.mp4` URL |

Consequence: because we always pass `image` (the 9:16 keyframe), we do **not** send
`aspect_ratio` — the clip inherits the keyframe's ratio automatically.

## Architecture — mirror of the image stack

```
skills/ugc-video/SKILL.md              grill motion brief -> emit video job JSON -> run it
scripts/run_video.py                   runner (mirror of run_ad.py): job JSON -> clip(s) + manifest
providers/video.py                     public API: image_to_video()  (replaces NotImplementedError)
providers/backends/replicate_video.py  Seedance backend (verified schema above)
providers/backends/stub_video.py       writes a tiny placeholder .mp4 (zero cost, no token)
providers/backends/replicate_common.py add run_video() reusing _save_output
skills/_shared/seedance-motion.md      motion-prompt craft (the video analogue of nano-banana.md)
```

Only change to the existing image path: a small refactor in `replicate_common.py`
to share the "run model -> save single output" helper (`_save_output` already handles
both `FileOutput` and URL, so `.mp4` works unchanged). `config.py` already has
`VIDEO_PROVIDER` and `SEEDANCE_MODEL`.

## Video job JSON

```json
{
  "meta": { "brand": "backlot", "source_job": "out/job", "notes": "reels from the Sunny tee set" },
  "clips": [
    {
      "id": "c1",
      "concept": "mirror selfie comes alive — subtle sway + phone tilt",
      "frame": "out/job/v1/keyframe_9x16.png",
      "motion": "she sways slightly and tilts the phone, hair moves naturally, gentle breathing, subtle smile shift; realistic hand-held phone micro-motion",
      "duration": 5,
      "resolution": "1080p",
      "camera_fixed": false,
      "negative": "morphing face, warping shirt print, extra fingers, jitter, text distortion"
    }
  ]
}
```

- `frame` is any existing keyframe path (the locked composite — identity/product are
  already correct in pixels; we never re-composite identity for video).
- `motion` is drafted by the planner from the keyframe's concept (like ad copy is),
  editable by the user.
- `negative`: Seedance has no separate negative field, so the runner appends it to the
  prompt as "Avoid: …" (same trick `replicate_images.py` uses).

## Data flow (per clip)

1. Read and validate `frame` exists (fail early, name the clip id — never call Seedance
   with a bad or missing frame).
2. `video.image_to_video(frame, {prompt, negative, seed, camera_fixed}, duration, resolution)`
   -> `replicate_video.py` calls Seedance with `image=frame`, `prompt=motion`,
   `duration`, `resolution` (no `aspect_ratio`).
3. Save `out/<job>/<clip-id>/clip.mp4`; write `run_manifest.json`.

### Caching
Content-address each clip on `sha256(frame bytes + motion + duration + resolution +
camera_fixed)`. Re-runs skip already-rendered clips; `--force` overrides. Video is the
expensive step, so caching matters more than on the image side.

## Error handling

- Missing/invalid `frame` -> clear error naming the clip id, before any spend.
- Empty `motion` -> rejected up front (Seedance requires `prompt`), not sent as a 400.
- No token -> reuse `config.require_replicate_token()` (same message, points at stub).
- Transient API errors (we hit a 500 this session) -> surface the failing clip id;
  a re-run resumes since cached clips are skipped, so only failed clips re-render.
  The manifest marks each clip rendered / skipped / failed — no silent partial success.
- Unknown provider -> same `ValueError` ("Known: replicate, stub") as `images.py`.

## Testing

- `stub_video.py` writes a tiny valid placeholder `.mp4` so
  `BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py job.json` exercises job
  parsing, frame resolution, caching, and manifest at zero cost / no token.
- First real render: one 5s clip from a single existing Sunny keyframe, eyeballed for
  identity hold and no shirt-print warping, before batching more.
- Manual verification is the bar for v1 (generative media tool); no unit suite beyond
  the stub smoke run — matches how the image side is validated.

## Out of scope (future)

- Multi-shot stitched reels (needs ffmpeg + ordering).
- Combined generate-keyframe-then-animate command.
- Audio and burned-on captions.
- Last-frame continuity chaining (`last_frame_image`) for seamless multi-clip flow.
