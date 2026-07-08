# Seedance model profiles (multi-model video backend) — design

**Date:** 2026-07-08
**Status:** approved, ready for implementation plan

## Goal

Make backlot's video backend correctly drive **multiple Seedance model versions**
(currently `seedance-1-pro` and `seedance-2.0`), selected via
`BACKLOT_SEEDANCE_MODEL`, instead of hardcoding 1-pro's schema. The current backend
sends `camera_fixed` (which 2.0 rejects as an unknown field) and omits `aspect_ratio`
(so 2.0 clips default to 16:9 horizontal). This adds per-model capability profiles so
each model receives exactly the fields it supports, with correct aspect and audio
handling.

Decisions (from brainstorming):
- **Per-model capability profiles** — an explicit map keyed by model family, not
  runtime schema introspection. Simple, readable; a new model = one profile entry.
- **Audio default OFF, opt-in per clip** — 2.0 generates audio by default; backlot
  defaults `generate_audio=false` (silent, matching v1 UGC, avoiding random AI
  dialogue on ads). A clip opts in with `"audio": true`.

## Verified schema differences (from the Replicate model API)

| field | seedance-1-pro | seedance-2.0 |
|---|---|---|
| `prompt` (required) | yes | yes |
| `image` (start frame) | yes | yes |
| `camera_fixed` | yes (bool) | **absent** — sending it errors |
| `aspect_ratio` | ignored when `image` set | **honored**; default `16:9`; enum incl. `9:16`, `adaptive` |
| `generate_audio` | absent | present, **default true**; enum bool |
| `resolution` | `480p/720p/1080p` (default 1080p) | `480p/720p/1080p/4k` (default 720p) |
| `seed` | yes | yes |
| output | single `.mp4` | single `.mp4` |

Confirmed empirically: a 2.0 render with `{prompt, image, duration, resolution,
aspect_ratio}` (no `camera_fixed`) is **accepted** by 2.0 (it reached content
moderation, not a schema error). 2.0 also has **stricter content moderation** than
1-pro — a young-woman + bedroom + mirror-selfie scene was flagged (E005) twice.

## Capability profiles

New `providers/backends/seedance_profiles.py`:

```python
PROFILES = {
    "seedance-1-pro": {
        "camera_fixed": True,       # field supported
        "aspect": "infer",          # aspect read from the image; do NOT send aspect_ratio
        "audio": False,             # no audio support
        "resolutions": {"480p", "720p", "1080p"},
    },
    "seedance-2.0": {
        "camera_fixed": False,      # not a field
        "aspect": "explicit",       # MUST send aspect_ratio or it defaults to 16:9
        "audio": True,              # generate_audio supported (backlot default off)
        "resolutions": {"480p", "720p", "1080p", "4k"},
    },
}

def profile_for(slug: str) -> dict:
    # substring match on family so pinned "…:versionhash" still resolves
    if "seedance-2" in slug:   return PROFILES["seedance-2.0"]
    if "seedance-1" in slug:   return PROFILES["seedance-1-pro"]
    # unknown model: fall back to the conservative 1-pro profile (logged note)
    return PROFILES["seedance-1-pro"]
```

## Profile-aware input building

`replicate_video._build_input(...)` takes the active profile and builds only
supported fields:

- `prompt` = motion (+ `"\n\nAvoid: <negative>."` when negative present) — always.
- `image` (open file handle) — always (added in `image_to_video`, as today).
- `camera_fixed`: include **only if** `profile["camera_fixed"]` is True **and** the
  resolved `camera_fixed` is True. (Also removes the redundant `camera_fixed:false`
  we send to 1-pro today — a harmless improvement.)
- aspect: if `profile["aspect"] == "explicit"`, probe the frame with Pillow and send
  `aspect_ratio` = the matching supported ratio; if `"infer"`, send nothing.
- audio: if `profile["audio"]`, send `generate_audio` = the clip's `audio` flag
  (default `False`). If the profile has no audio, never send it.
- `seed` when not None.
- `resolution` validated against `profile["resolutions"]`.

**Aspect from the frame:** a helper probes width/height (Pillow, already a dep) and
maps the ratio to the nearest supported aspect from a small set
(`9:16, 3:4, 1:1, 4:3, 16:9`). Our 1088×1920 keyframes → `"9:16"`. (Only used when
the profile is `"explicit"`.)

## Provider API + runner wiring

- `providers/video.py` gains `capabilities() -> dict`, resolving
  `profile_for(config.SEEDANCE_MODEL)`, so the runner/skill can introspect the active
  model (its `resolutions` set and `audio` support) without touching backend internals.
- `image_to_video`'s `motion` dict gains an optional `"audio": bool` key (default
  False), threaded to the backend.
- `run_video.py`:
  - Reads a clip-level `"audio"` (default False) and threads it via `_compose` into
    the motion dict.
  - Replaces the hardcoded `{480p,720p,1080p}` resolution guard with
    `video.capabilities()["resolutions"]` (so 2.0 can use `4k`), still raising a
    **clip-named** error early.
  - If a clip sets `audio: true` but the active model's profile has no audio →
    clip-named `ValueError` (fail fast; never silently drop).
  - `audio` joins the cache-key inputs (`_clip_hash`) — toggling audio changes output.

## Skill / docs

- `skills/_shared/seedance-motion.md` and `skills/ugc-video/SKILL.md`: document the
  optional `audio` clip field (default off), that the model is chosen via
  `BACKLOT_SEEDANCE_MODEL` (env), and a note that **seedance-2.0 has stricter content
  moderation** — some people/bedroom UGC scenes get flagged (E005); prefer 1-pro for
  those.

## Error handling

- Unknown model slug → conservative 1-pro profile with a logged note (never a crash).
- `resolution` not in the active profile's set → clip-named `ValueError`.
- `audio: true` on a no-audio model → clip-named `ValueError`.
- Aspect probe on a missing/unreadable frame → the existing frame-existence guard
  fires first (in the runner), so `_build_input` only sees a valid frame.

## Testing

- **Unit (free, no network):**
  - `profile_for` resolves 1-pro, 2.0, pinned `…:hash`, and unknown → 1-pro.
  - `_build_input` for 2.0: omits `camera_fixed`, includes `aspect_ratio:"9:16"`
    (probed from a 9:16 test image written with Pillow), `generate_audio:false` by
    default and `true` on opt-in, accepts `4k`.
  - `_build_input` for 1-pro: `camera_fixed` present only when True, no
    `aspect_ratio`, no `generate_audio`.
  - aspect-from-frame helper maps sample dimensions to the right ratio.
- **Stub (free):** end-to-end `run_video` job renders; the `audio` flag and
  capability-based resolution/audio validation are exercised.
- **Real render:** schema acceptance for 2.0 is already confirmed (the one-off reached
  moderation). A real 2.0 clip is **best-effort** — gated by 2.0 moderation on our
  bedroom keyframes; attempt on the least-risky frame and, if flagged, report as a
  content limitation, not a code failure. 1-pro remains fully verifiable end-to-end.

## Backward compatibility

- Default model stays `seedance-1-pro`; existing jobs are unchanged (the only
  behavioral diff on 1-pro is that a redundant `camera_fixed:false` is no longer sent,
  which does not change output).
- No change to `video.image_to_video`'s existing positional args; `audio` rides inside
  the `motion` dict. The provider seam and `providers/images.py` are untouched.

## Out of scope (future)

- Runtime schema introspection (profiles are explicit for now).
- 2.0's `reference_images` / `reference_videos` / `last_frame_image` inputs.
- Spoken-dialogue prompting for 2.0 audio (double-quote dialogue) — the `audio` flag
  just toggles generation.
