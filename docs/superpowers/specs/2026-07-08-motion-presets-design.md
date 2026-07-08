# Motion presets (Higgsfield-style) — design

**Date:** 2026-07-08
**Status:** approved, ready for implementation plan

## Goal

Make ugc-video motion **curated and cinematic** instead of hand-written free text —
a library of named, reusable motion presets (Higgsfield-style) that the runner
composes onto a keyframe. Two categories — **camera** moves and **subject actions** —
each a battle-tested recipe (prompt fragment + params + negative). A clip references
presets by id; free-text `motion` stays supported for fine-tuning.

Direction decisions (from brainstorming):
- **Both camera and action presets**, in one library.
- **Referenced by id, runner expands** — structured data, versionable, CLI-listable,
  same "reusable asset referenced by id" ethos as the character/product library.
- **Curate on Seedance now, keep the seam open** — build on the existing Seedance
  backend; empirically test each preset and ship only the good ones as `verified`;
  the provider seam already allows a dedicated camera-control model later without
  touching presets or skills.

## Preset library

**Storage:** `presets/motion.json` — a committed, versioned JSON list (curated content,
unlike the private/gitignored asset library). The file is resolved from the plugin
root (like `config.PLUGIN_ROOT`), so both `presets.py` and `run_video.py` load it
regardless of the current working directory. Schema per preset:

```json
{
  "id": "crash-zoom",
  "category": "camera",
  "label": "Crash zoom in",
  "prompt": "the camera rapidly punches in toward the subject in a fast crash zoom, then holds steady",
  "camera_fixed": false,
  "duration": 5,
  "negative": "warping, smearing the face during the zoom",
  "status": "verified"
}
```

Fields:
- `id` — unique slug, referenced from a clip.
- `category` — `"camera"` or `"action"`.
- `label` — human name for CLI listing.
- `prompt` — the motion fragment injected into the Seedance prompt.
- `camera_fixed` — camera presets set this (bool); action presets omit it.
- `duration` — preset's natural duration (int seconds); optional.
- `negative` — preset-specific things to avoid; merged into the clip's negative.
- `status` — `"verified"` (looks good on Seedance) or `"experimental"` (may be mushy).

**Starter catalog** (statuses finalized by the curation pass):
- *Camera:* `static-locked` (camera_fixed true), `dolly-in`, `crash-zoom`,
  `orbit-arc`, `handheld-follow`, `fpv-swoop` (experimental), `whip-pan` (experimental).
- *Action:* `mirror-selfie-alive`, `show-product`, `walk-toward`, `turn-reveal`,
  `laugh-react`, `hair-tuck`.

## Job integration & composition

A clip references presets by id; free-text `motion` remains optional:

```json
{
  "id": "c1",
  "frame": "out/job/v1/keyframe_9x16.png",
  "camera": "crash-zoom",
  "action": "show-product",
  "motion": "she winks at the end",
  "negative": "extra fingers"
}
```

The runner composes, in this order:
1. **Motion prompt** = join non-empty of `[action.prompt, camera.prompt, motion]`
   with ". " separators.
2. **Negative** = merge (dedup-join) of `action.negative`, `camera.negative`, and the
   clip's `negative`.
3. **camera_fixed** = clip value if present, else the camera preset's value, else `False`.
4. **duration** = precedence: clip value > camera preset > action preset > `5`.
5. **resolution** = clip value or `"1080p"` (presets do not set resolution).

Explicit clip fields always override preset-derived values. Validation: a clip must
supply at least one of `camera`, `action`, or `motion` (else it has no motion at all).

**Caching:** the content-address hash is computed on the **resolved** values (final
motion, merged negative, duration, resolution, camera_fixed, seed) + frame bytes — so
changing a referenced preset busts the cache exactly like editing `motion` does.
(This preserves the existing hash contract — same fields, including the `seed` added
in the earlier cache-key fix; only the values are now post-expansion.)

## CLI

`scripts/presets.py`, mirroring `assets.py`:
```bash
python scripts/presets.py list [--category camera|action] [--status verified]
python scripts/presets.py get --id crash-zoom
```
`list` prints id, label, category, status, one-line prompt. `get` prints the full
preset record.

## Skill / reference changes

- `skills/ugc-video/SKILL.md` — the grill offers presets ("pick a camera move + an
  action"); the job references them by id. New precondition: list the preset library
  first (`presets.py list`). **Warn before using an `experimental` preset.** Keep
  documenting free-text `motion` as the fine-tune/override path. Do NOT document
  `aspect_ratio` (unchanged).
- `skills/_shared/seedance-motion.md` — reframed from "write a free-text motion
  string" to "compose from presets; free-text is only for fine-tuning," plus
  **authoring guidance** for adding a preset: how to write a prompt fragment, how to
  pick `camera_fixed`/`duration`, and when to promote `experimental → verified`.

## Curation pass (empirical, spends credits)

Its own task, run with user consent. Render each candidate preset on the Sunny
keyframe (`out/job/v1/keyframe_9x16.png`), eyeball for identity hold + believable
movement + no warping, and set each preset's `status` to `verified` / `experimental`,
or drop it. This is what makes the moves genuinely "real." Batch of camera presets
first, then action presets. Report the resulting statuses.

## Error handling

- Unknown preset id -> `ValueError` naming the clip and listing valid ids for that
  category.
- Clip with none of `camera`/`action`/`motion` -> `ValueError` naming the clip.
- `presets/motion.json` missing or malformed -> clear error at load.
- Category mismatch (e.g. `camera` referencing an `action`-category preset) -> error.
- Using an `experimental` preset is allowed by the runner; the **skill** warns the
  user before authoring it (not a runner error).

## Testing

- **Stub-provable (free):** preset load, id resolution, composition/precedence,
  merged negatives, validation errors (unknown id, empty clip, category mismatch),
  cache correctness on resolved values, and backward-compat (old `motion`-only jobs).
- **Paid:** the curation pass (real renders) — the one step that needs credits.
- `scripts/presets.py list` output is deterministic and testable.

## Backward compatibility

Existing free-text `motion`-only jobs run unchanged — presets are purely additive.
The `video.image_to_video` API and the Seedance backend are untouched; all
composition happens in `run_video.py`. The provider seam is unchanged, leaving the
door open for a dedicated camera-control model later.

## Out of scope (future)

- A dedicated camera-control model / multi-model routing (the seam allows it later).
- Chaining presets across multiple clips into a sequenced reel.
- Audio, captions (still excluded, per ugc-video v1).
