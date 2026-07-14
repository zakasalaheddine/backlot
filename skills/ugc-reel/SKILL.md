---
name: ugc-reel
description: Produce a COMPLETE UGC video ad from one brief — multi-shot keyframes, animated clips, voice-over in the character's locked voice, music bed, karaoke captions, hook card, progress bar, and CTA end card, assembled into publishable masters. Use this whenever the user wants a finished reel/video ad end-to-end ("make me a video ad for X", "a full reel", "a TikTok ad"), rather than a single silent clip (that's ugc-video). Requires a character and/or product in the library — route to character-creator first if missing. Supports single-shot regeneration for iteration.
---

# ugc-reel

One brief → a finished, publishable vertical video ad. You are the planner:
grill the brief, emit ONE production JSON, run ONE script. The runner owns the
whole DAG (keyframes → clips → audio → overlays → assembly), every stage cached.

Read these shared references first:
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md` — how to grill.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/assembly.md` — beat structure, pacing, VO writing.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/audio-direction.md` — voice tone, music moods.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/continuity.md` — refs carry identity, prompts don't.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/seedance-motion.md` — motion presets per shot.

## Preconditions (enforce)
- Character and/or product exist: `python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list`
  — missing → route to **character-creator** first. Never invent identities.
- VO planned? The character should have a **locked voice** (`assets.py get --id <char>`
  shows a `voice` block). Missing → lock one (character-creator step 4) or the
  reel falls back to a generic default voice.
- Binaries: `ffmpeg` required; Node optional (without it: burned PIL captions,
  no end card / hook / progress bar — say so instead of failing).

## Flow

### 1. Grill the brief
Product, character, angle, and the beats (default: hook → proof → CTA per
`assembly.md`). Confirm: number of shots (2–3 + end card is the sweet spot),
VO line per shot, hook text, music mood, brand accent color, formats
(9:16 default; 1:1 / 4:5 extra masters are free).

### 2. Emit the production JSON
Write `out/<name>/production.json`. Full schema in the runner's docstring
(`scripts/run_production.py`). Skeleton:

```json
{
  "meta": {
    "brand": "...", "character": "maya-01", "product": "mug-01",
    "aspect": "9:16", "formats": ["9:16"], "fps": 24,
    "music": {"mood": "cozy-upbeat lofi, warm", "gain_db": -8},
    "accent_color": "#ffd400", "progress_bar": true
  },
  "shots": [
    {"id": "s1", "beat": "hook",
     "keyframe": {"prompt": "scene only — refs carry identity", "use_refs": ["maya-01", "mug-01"]},
     "motion": {"camera": "dolly-in", "duration": 5},
     "vo": "okay so I panic ordered this...",
     "hook": "POV: you forgot Valentine's"},
    {"id": "s2", "beat": "proof",
     "keyframe": {"prompt": "close-up ...", "use_refs": ["mug-01"]},
     "motion": {"camera": "static-locked", "duration": 5},
     "vo": "look at the print, it came in two days"}
  ],
  "end_card": {"headline": "...", "cta": "Shop now", "duration_s": 3}
}
```

### 3. Dry-run as an animatic (strongly recommended, zero cost)
```bash
BACKLOT_IMAGE_PROVIDER=stub BACKLOT_VIDEO_PROVIDER=stub \
BACKLOT_AUDIO_TTS_PROVIDER=stub BACKLOT_AUDIO_MUSIC_PROVIDER=stub \
python ${CLAUDE_PLUGIN_ROOT}/scripts/run_production.py out/<name>/production.json
```
This assembles a REAL watchable master (held keyframes, silent audio, live
captions/overlays) — the user can approve pacing, captions, and card copy
before any provider spend.

### 4. Produce for real
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/run_production.py out/<name>/production.json
```
Show `assemble/master_*.mp4` plus the per-shot table from
`production_manifest.json`.

### 5. Iterate shot-by-shot (cheap by design)
- Bad shot → edit its prompt/motion, then regen JUST it:
  `python ${CLAUDE_PLUGIN_ROOT}/scripts/render_shot.py production.json s2`
- Copy tweaks (vo/hook/end card/captions) re-run only audio/overlays/assembly —
  clips are never re-paid for. Just re-run the production script.
- Watch for identity drift or print warping → tighten `negative`, regen the shot.
