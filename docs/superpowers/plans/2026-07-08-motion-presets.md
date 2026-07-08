# Motion Presets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Higgsfield-style motion preset library (named camera + action recipes) that `run_video.py` composes onto a keyframe, referenced by id from a clip.

**Architecture:** A committed `presets/motion.json` holds recipes; `scripts/presets.py` loads/resolves/lists them and is imported by `run_video.py`, which composes `camera` + `action` + free-text `motion` into the final Seedance inputs. Free-text `motion` stays supported. Provider seam and the Seedance backend are untouched.

**Tech Stack:** Python 3.9+, standard library only (json, argparse, pathlib). Builds on the existing ugc-video pipeline.

## Global Constraints

- Presets live in `presets/motion.json` (committed), resolved from the plugin root (`REPO = scripts/..`), loaded regardless of CWD.
- Preset schema: `{id, category ("camera"|"action"), label, prompt, camera_fixed?(bool), duration?(int), negative?, status ("verified"|"experimental")}`.
- A clip may reference `camera` and/or `action` preset ids and/or free-text `motion`. It MUST supply at least one of the three.
- Composition: final motion = non-empty of `[action.prompt, camera.prompt, motion]` joined with `". "`; negative = non-empty of `[action.negative, camera.negative, clip.negative]` joined with `", "`; `camera_fixed` precedence clip > camera preset > `False`; `duration` precedence clip > camera preset > action preset > `5`; `resolution` = clip or `"1080p"`.
- The cache hash is computed on the RESOLVED values (final motion, merged negative, duration, resolution, seed, camera_fixed) + frame bytes — the existing `_clip_hash` signature already takes exactly these, so it is reused unchanged.
- Errors (all name the clip id): unknown preset id (list valid ids of that category); category mismatch; clip with none of camera/action/motion; missing `presets/motion.json`; malformed JSON.
- `resolution` must be in `{480p,720p,1080p}`; `duration` in `{5,10}` — existing guards, now applied to resolved values.
- Do NOT touch `providers/` or send `aspect_ratio`.
- Repo has NO pytest suite by design; verification is stub-based `python -c` blocks — not a defect.
- Initial `status` for every shipped preset is `"experimental"`; the curation pass (Task 4, paid) promotes the good ones to `"verified"`.

---

### Task 1: Preset library data + `presets.py` CLI/loader

**Files:**
- Create: `presets/motion.json`
- Create: `scripts/presets.py`

**Interfaces:**
- Produces (imported by Task 2): `presets.load_presets() -> dict[str, dict]` (id -> record); `presets.resolve(preset_id: str, expected_category: str, presets: dict | None = None) -> dict`.
- CLI: `python scripts/presets.py list [--category camera|action] [--status verified|experimental]`; `python scripts/presets.py get --id <id>`.

- [ ] **Step 1: Write `presets/motion.json` (starter catalog, all `status` = experimental)**

```json
[
  { "id": "static-locked", "category": "camera", "label": "Static locked-off",
    "prompt": "the camera stays completely still on a locked-off tripod, no camera movement",
    "camera_fixed": true, "duration": 5,
    "negative": "camera drift, handheld shake", "status": "experimental" },
  { "id": "dolly-in", "category": "camera", "label": "Slow dolly in",
    "prompt": "the camera glides slowly and smoothly toward the subject in a steady dolly-in",
    "camera_fixed": false, "duration": 5,
    "negative": "jerky motion, warping edges", "status": "experimental" },
  { "id": "crash-zoom", "category": "camera", "label": "Crash zoom in",
    "prompt": "the camera rapidly punches in toward the subject in a fast crash zoom, then holds steady",
    "camera_fixed": false, "duration": 5,
    "negative": "smearing the face during the zoom, warping", "status": "experimental" },
  { "id": "orbit-arc", "category": "camera", "label": "Slow orbit arc",
    "prompt": "the camera arcs slowly around the subject in a smooth partial orbit, keeping them centered",
    "camera_fixed": false, "duration": 5,
    "negative": "morphing the subject during the orbit, background warping", "status": "experimental" },
  { "id": "handheld-follow", "category": "camera", "label": "Handheld follow",
    "prompt": "natural hand-held camera with subtle organic drift, as if shot on a phone",
    "camera_fixed": false, "duration": 5,
    "negative": "heavy shake, nausea-inducing motion", "status": "experimental" },
  { "id": "fpv-swoop", "category": "camera", "label": "FPV swoop",
    "prompt": "a fast FPV-drone style swoop that sweeps in toward the subject and levels off",
    "camera_fixed": false, "duration": 5,
    "negative": "extreme distortion, melting geometry", "status": "experimental" },
  { "id": "whip-pan", "category": "camera", "label": "Whip pan",
    "prompt": "a quick whip-pan that snaps across and settles on the subject",
    "camera_fixed": false, "duration": 5,
    "negative": "unreadable blur, warping the face", "status": "experimental" },
  { "id": "mirror-selfie-alive", "category": "action", "label": "Mirror selfie comes alive",
    "prompt": "she holds her phone for a mirror selfie, sways slightly and tilts the phone, hair moving naturally, a subtle smile shift",
    "duration": 5,
    "negative": "morphing face, warping the phone", "status": "experimental" },
  { "id": "show-product", "category": "action", "label": "Show the product",
    "prompt": "she lifts and angles the product toward the camera to show it off, a natural proud gesture",
    "duration": 5,
    "negative": "warping the product, distorting printed text", "status": "experimental" },
  { "id": "walk-toward", "category": "action", "label": "Walk toward camera",
    "prompt": "she takes a couple of relaxed steps toward the camera, natural gait and arm sway",
    "duration": 5,
    "negative": "gliding feet, morphing legs", "status": "experimental" },
  { "id": "turn-reveal", "category": "action", "label": "Turn and reveal",
    "prompt": "she turns from three-quarters toward the camera in a smooth reveal, settling into a confident pose",
    "duration": 5,
    "negative": "face morphing mid-turn", "status": "experimental" },
  { "id": "laugh-react", "category": "action", "label": "Laugh / react",
    "prompt": "she is caught mid-laugh reacting to something off-camera, head tipping slightly, shoulders relaxing",
    "duration": 5,
    "negative": "frozen or rubbery expression", "status": "experimental" },
  { "id": "hair-tuck", "category": "action", "label": "Hair tuck",
    "prompt": "she tucks a strand of hair behind her ear and glances toward the light, a small natural motion",
    "duration": 5,
    "negative": "extra fingers, melting hand", "status": "experimental" }
]
```

- [ ] **Step 2: Write the failing test for the loader/resolver**

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
import presets
m = presets.load_presets()
assert 'crash-zoom' in m and m['crash-zoom']['category'] == 'camera'
assert 'show-product' in m and m['show-product']['category'] == 'action'
# resolve happy path
p = presets.resolve('crash-zoom', 'camera', m); assert p['id'] == 'crash-zoom'
# unknown id -> ValueError listing valid camera ids
try: presets.resolve('nope', 'camera', m); print('FAIL: no error')
except ValueError as e: assert 'unknown camera preset' in str(e) and 'crash-zoom' in str(e)
# category mismatch -> ValueError
try: presets.resolve('show-product', 'camera', m); print('FAIL: no mismatch error')
except ValueError as e: assert 'category' in str(e)
print('loader/resolver OK')
"
```

- [ ] **Step 3: Run it to verify it fails**

Run the block.
Expected: FAIL — `ModuleNotFoundError: No module named 'presets'`.

- [ ] **Step 4: Write `scripts/presets.py`**

```python
#!/usr/bin/env python3
"""Motion preset library — named camera/action recipes for ugc-video.

Curated, committed content (unlike the private asset library). Loaded from
presets/motion.json at the plugin root so it resolves regardless of CWD. Both
this CLI and scripts/run_video.py read presets through load_presets()/resolve().
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PRESETS_FILE = REPO / "presets" / "motion.json"


def load_presets() -> dict:
    """Return {id: preset_record}. Raises on a missing or malformed library."""
    if not PRESETS_FILE.exists():
        raise FileNotFoundError(f"preset library not found: {PRESETS_FILE}")
    try:
        data = json.loads(PRESETS_FILE.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"preset library {PRESETS_FILE} is malformed JSON: {e}")
    return {p["id"]: p for p in data}


def resolve(preset_id: str, expected_category: str, presets: dict | None = None) -> dict:
    """Look up a preset by id, enforcing its category. Raises ValueError otherwise."""
    presets = presets if presets is not None else load_presets()
    p = presets.get(preset_id)
    if p is None:
        valid = sorted(k for k, v in presets.items()
                       if v.get("category") == expected_category)
        raise ValueError(
            f"unknown {expected_category} preset {preset_id!r}; "
            f"valid: {', '.join(valid)}"
        )
    if p.get("category") != expected_category:
        raise ValueError(
            f"preset {preset_id!r} is category {p.get('category')!r}, "
            f"expected {expected_category!r}"
        )
    return p


def list_presets(args) -> None:
    presets = load_presets()
    rows = []
    for p in presets.values():
        if args.category and p.get("category") != args.category:
            continue
        if args.status and p.get("status") != args.status:
            continue
        rows.append({
            "id": p["id"], "category": p.get("category"),
            "label": p.get("label", ""), "status": p.get("status"),
            "prompt": p.get("prompt", "")[:80],
        })
    rows.sort(key=lambda r: (r["category"], r["id"]))
    print(json.dumps(rows, indent=2))


def get_preset(args) -> None:
    presets = load_presets()
    p = presets.get(args.id)
    if p is None:
        print(f"No preset with id {args.id!r}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(p, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="backlot motion preset library")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ls = sub.add_parser("list", help="list presets")
    ls.add_argument("--category", choices=["camera", "action"], default=None)
    ls.add_argument("--status", choices=["verified", "experimental"], default=None)
    ls.set_defaults(func=list_presets)

    g = sub.add_parser("get", help="print one preset record")
    g.add_argument("--id", required=True)
    g.set_defaults(func=get_preset)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the loader/resolver test to confirm it passes**

Run the Step 2 block. Expected: `loader/resolver OK`.

- [ ] **Step 6: Verify the CLI**

```bash
python scripts/presets.py list --category camera | python -c "import json,sys; r=json.load(sys.stdin); assert all(x['category']=='camera' for x in r) and len(r)==7; print('list camera OK', len(r))"
python scripts/presets.py list --status verified | python -c "import json,sys; r=json.load(sys.stdin); assert r==[]; print('list verified OK (none yet)')"
python scripts/presets.py get --id show-product | python -c "import json,sys; p=json.load(sys.stdin); assert p['category']=='action'; print('get OK')"
```
Expected: `list camera OK 7`, `list verified OK (none yet)`, `get OK`.

- [ ] **Step 7: Commit**

```bash
git add presets/motion.json scripts/presets.py
git commit -m "feat: add motion preset library and presets CLI"
```

---

### Task 2: Compose presets in `run_video.py`

**Files:**
- Modify: `scripts/run_video.py`

**Interfaces:**
- Consumes: `presets.resolve` / `presets.load_presets` (Task 1).
- Produces: `run_video._compose(clip: dict, preset_map: dict) -> tuple[str, str, int, str, object, bool]` returning `(motion, negative, duration, resolution, seed, camera_fixed)`.

- [ ] **Step 1: Write the failing composition test**

```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
import run_video
pm = {
  'crash-zoom': {'id':'crash-zoom','category':'camera','prompt':'CAM','camera_fixed':False,'duration':5,'negative':'camneg'},
  'show-product': {'id':'show-product','category':'action','prompt':'ACT','duration':10,'negative':'actneg'},
}
# action + camera + free motion; duration precedence camera(5) over action(10)
motion, neg, dur, res, seed, cf = run_video._compose(
  {'id':'c1','camera':'crash-zoom','action':'show-product','motion':'winks'}, pm)
assert motion == 'ACT. CAM. winks', motion
assert 'actneg' in neg and 'camneg' in neg
assert dur == 5 and res == '1080p' and cf is False
# clip overrides win
m2 = run_video._compose({'id':'c2','camera':'crash-zoom','duration':10,'camera_fixed':True}, pm)
assert m2[2] == 10 and m2[5] is True and m2[0] == 'CAM'
# backward compat: motion only
m3 = run_video._compose({'id':'c3','motion':'just sway'}, pm)
assert m3[0] == 'just sway'
# empty clip -> error
try: run_video._compose({'id':'c4'}, pm); print('FAIL: no error')
except ValueError as e: assert 'at least one' in str(e)
print('compose OK')
"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — `AttributeError: module 'run_video' has no attribute '_compose'`.

- [ ] **Step 3: Add the `scripts` path + import and the `_compose` helper**

In `scripts/run_video.py`, after the existing `sys.path.insert(0, str(REPO))` (line 24) add the scripts dir to the path, and import the preset library. Replace:

```python
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from providers import video  # noqa: E402
```

with:

```python
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from providers import video  # noqa: E402
import presets as preset_lib  # noqa: E402


def _compose(clip: dict, preset_map: dict):
    """Resolve a clip's camera/action presets + free-text motion into the final
    Seedance inputs. Returns (motion, negative, duration, resolution, seed, camera_fixed)."""
    cid = clip["id"]
    cam = preset_lib.resolve(clip["camera"], "camera", preset_map) if clip.get("camera") else None
    act = preset_lib.resolve(clip["action"], "action", preset_map) if clip.get("action") else None
    free = clip.get("motion", "").strip()

    parts = [x for x in [act["prompt"] if act else "",
                         cam["prompt"] if cam else "", free] if x]
    motion = ". ".join(parts)
    if not motion:
        raise ValueError(
            f"clip {cid!r}: needs at least one of camera/action/motion"
        )

    negs = [x for x in [act.get("negative", "") if act else "",
                        cam.get("negative", "") if cam else "",
                        clip.get("negative", "")] if x]
    negative = ", ".join(negs)

    if "camera_fixed" in clip:
        camera_fixed = bool(clip["camera_fixed"])
    elif cam and "camera_fixed" in cam:
        camera_fixed = bool(cam["camera_fixed"])
    else:
        camera_fixed = False

    if "duration" in clip:
        duration = int(clip["duration"])
    elif cam and "duration" in cam:
        duration = int(cam["duration"])
    elif act and "duration" in act:
        duration = int(act["duration"])
    else:
        duration = 5

    resolution = clip.get("resolution", "1080p")
    seed = clip.get("seed")
    return motion, negative, duration, resolution, seed, camera_fixed
```

- [ ] **Step 4: Rewrite the per-clip body of `run()` to use `_compose`**

In `run()`, load the preset map once before the loop, and replace the clip-field extraction + old motion guard with the composed values. Replace this block:

```python
    produced = []
    for clip in job["clips"]:
        cid = clip["id"]
        motion = clip.get("motion", "").strip()
        if not motion:
            raise ValueError(f"clip {cid!r}: 'motion' prompt is required")
        frame = _resolve_frame(clip["frame"], job_path)
        if not frame.exists():
            raise FileNotFoundError(
                f"clip {cid!r}: start frame not found: {clip['frame']}"
            )

        duration = int(clip.get("duration", 5))
        resolution = clip.get("resolution", "1080p")
        camera_fixed = bool(clip.get("camera_fixed", False))
        negative = clip.get("negative", "")
        seed = clip.get("seed")

        if resolution not in {"480p", "720p", "1080p"}:
```

with:

```python
    preset_map = preset_lib.load_presets()
    produced = []
    for clip in job["clips"]:
        cid = clip["id"]
        frame = _resolve_frame(clip["frame"], job_path)
        if not frame.exists():
            raise FileNotFoundError(
                f"clip {cid!r}: start frame not found: {clip['frame']}"
            )

        motion, negative, duration, resolution, seed, camera_fixed = _compose(
            clip, preset_map)

        if resolution not in {"480p", "720p", "1080p"}:
```

(The rest of the loop — the guard for duration, the hash, the render, and the manifest append — is unchanged.)

- [ ] **Step 5: Run the composition test to confirm it passes**

Run the Step 1 block. Expected: `compose OK`.

- [ ] **Step 6: End-to-end stub run (presets + backward compat) with a real keyframe**

```bash
rm -rf out/_pv; mkdir -p out/_pv
cat > out/_pv/job.json <<'JSON'
{ "meta": {}, "clips": [
  { "id": "c1", "frame": "out/job/v1/keyframe_9x16.png", "camera": "crash-zoom", "action": "show-product" },
  { "id": "c2", "frame": "out/job/v1/keyframe_9x16.png", "motion": "just a subtle sway" }
] }
JSON
BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py out/_pv/job.json --out out/_pv/run >/dev/null
python -c "
import json, pathlib
m = json.load(open('out/_pv/run/run_manifest.json'))
assert len(m['outputs']) == 2 and all(pathlib.Path(o['mp4']).exists() for o in m['outputs'])
assert all(o['rendered'] for o in m['outputs'])
print('preset clip + motion-only clip both render OK')
"
# unknown preset id -> error
python -c "import json; d=json.load(open('out/_pv/job.json')); d['clips']=[{'id':'x','frame':'out/job/v1/keyframe_9x16.png','camera':'nope'}]; json.dump(d, open('out/_pv/bad.json','w'))"
BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py out/_pv/bad.json --out out/_pv/r2 2>&1 | grep -q "unknown camera preset" && echo "unknown-preset guard OK"
rm -rf out/_pv
```
Expected: `preset clip + motion-only clip both render OK` and `unknown-preset guard OK`.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_video.py
git commit -m "feat: compose camera/action motion presets in run_video"
```

---

### Task 3: Skill + motion-reference updates

**Files:**
- Modify: `skills/ugc-video/SKILL.md`
- Modify: `skills/_shared/seedance-motion.md`

**Interfaces:**
- Consumes: the `presets.py` CLI and the job's `camera`/`action` fields (Tasks 1-2).
- Produces: user-facing guidance so the grill offers presets and warns on `experimental` ones.

- [ ] **Step 1: Update `skills/ugc-video/SKILL.md`**

In the flow, add preset usage. After the "Read these shared references first" list, add `skills/_shared/seedance-motion.md` already covers motion; ensure the grill + job schema reflect presets. Make these concrete edits:

(a) In the **Preconditions** section, add a line telling the skill to list presets:
```markdown
List the motion presets before authoring a clip, and warn the user before using
any preset whose `status` is `experimental` (unverified on Seedance):
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/presets.py list
```
```

(b) In **Flow step 1 (grill)**, replace the motion-brief guidance with:
```markdown
### 1. Grill for the motion brief
Pick a **camera move** and/or a **subject action** from the preset library
(`presets.py list`), plus duration (5s default, 10s only if needed). Free-text
`motion` is optional, for fine-tuning on top of the presets. Warn before using an
`experimental` preset. You (the planner) still confirm the brief before rendering.
```

(c) In **Flow step 2**, update the job JSON example clip to reference presets:
```json
{
  "id": "c1",
  "concept": "crash zoom onto the tee while she shows it off",
  "frame": "out/job/v1/keyframe_9x16.png",
  "camera": "crash-zoom",
  "action": "show-product",
  "motion": "",
  "negative": "garbled text"
}
```
and add these notes:
```markdown
- `camera` / `action` reference preset ids (`presets.py list`); the runner expands
  them into the motion prompt + params. Free-text `motion` is optional/additive.
- A clip must supply at least one of `camera`, `action`, or `motion`.
- Preset-derived `camera_fixed`/`duration` are overridden by explicit clip fields.
```

- [ ] **Step 2: Update `skills/_shared/seedance-motion.md`**

Add a section near the top that reframes motion authoring around presets, and an authoring-guidance section. Insert after the intro paragraph:

```markdown
## Compose from presets first

Motion is now authored from a **preset library** (`presets/motion.json`, listed via
`scripts/presets.py list`): named **camera** moves (dolly-in, crash-zoom, orbit-arc,
handheld-follow, …) and **subject actions** (show-product, mirror-selfie-alive,
walk-toward, …). A clip references a `camera` and/or `action` by id; the runner
composes them. Free-text `motion` is for fine-tuning on top — not the default.

Prefer a `verified` preset (tested to look good on Seedance). An `experimental`
preset may be mushy — warn the user before using one.

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
```

- [ ] **Step 3: Verify the docs are consistent**

```bash
grep -q "presets.py list" skills/ugc-video/SKILL.md && echo "skill references presets CLI OK"
grep -q "experimental" skills/ugc-video/SKILL.md && echo "skill warns on experimental OK"
grep -q "Compose from presets" skills/_shared/seedance-motion.md && echo "reference updated OK"
# ensure aspect_ratio still not documented as a job field
grep -q "Do NOT set .aspect_ratio." skills/ugc-video/SKILL.md && echo "aspect note intact OK"
```
Expected: all four OK lines.

- [ ] **Step 4: Commit**

```bash
git add skills/ugc-video/SKILL.md skills/_shared/seedance-motion.md
git commit -m "docs: author ugc-video motion from the preset library"
```

---

### Task 4: Curation pass (paid — real renders, run with user consent)

**Files:**
- Modify: `presets/motion.json` (flip `status` per results)

**Interfaces:** Consumes the whole pipeline + a real `REPLICATE_API_TOKEN`. This task spends Replicate credits; run it only with explicit user consent.

- [ ] **Step 1: Render each preset on the Sunny keyframe**

For each preset, author a one-clip job referencing it (camera presets paired with a neutral `handheld-follow`-free action like `mirror-selfie-alive`; action presets paired with `static-locked` camera) against `out/job/v1/keyframe_9x16.png`, and render for real:

```bash
python scripts/run_video.py out/curation/<preset-id>/job.json
```
Use ffmpeg to extract start/mid/end frames for review:
```bash
ffmpeg -y -v error -i out/curation/<preset-id>/c1/clip.mp4 -vf "select='eq(n,0)'" -frames:v 1 /tmp/<id>_s.png
ffmpeg -y -v error -ss 2.5 -i out/curation/<preset-id>/c1/clip.mp4 -frames:v 1 /tmp/<id>_m.png
ffmpeg -y -v error -sseof -0.3 -i out/curation/<preset-id>/c1/clip.mp4 -frames:v 1 /tmp/<id>_e.png
```

- [ ] **Step 2: Judge and set status**

For each preset, eyeball the frames + clip for: identity hold, believable movement, and no warping (especially the shirt print for `show-product`). Set `status` to `verified` if it reads cleanly, keep `experimental` if shaky, or drop the preset if it never works. Present the results (a table of preset -> verdict + a representative frame) to the user before finalizing.

- [ ] **Step 3: Commit the finalized statuses**

```bash
git add presets/motion.json
git commit -m "chore: set motion preset statuses from curation pass"
```

---

## Self-Review

**Spec coverage:**
- Preset schema + `presets/motion.json` (committed, plugin-root path) → Task 1. ✓
- `presets.py` load/resolve + CLI (list/get, category+status filters) → Task 1. ✓
- Referenced-by-id, runner expands; composition order + precedence + merged negatives → Task 2 `_compose`, Global Constraints. ✓
- Cache on resolved values (reuses `_clip_hash` with the same 7-field signature incl. seed) → Task 2 Step 4 (hash line unchanged). ✓
- Validation: unknown id (lists valid), category mismatch, empty clip, missing/malformed file → Task 1 (`resolve`, `load_presets`) + Task 2 (`_compose`). ✓
- resolution/duration guards on resolved values → Task 2 Step 4 (guards unchanged, now fed composed values). ✓
- Skill offers presets + warns on experimental; seedance-motion.md reframed + authoring guidance → Task 3. ✓
- Backward compat (motion-only jobs) → Task 2 Step 1 (m3) + Step 6 (c2). ✓
- Curation pass (paid, sets statuses; all ship experimental first) → Task 4 + Global Constraints. ✓
- Provider seam / aspect_ratio untouched → no `providers/` edits; Task 3 Step 3 asserts aspect note intact. ✓

**Placeholder scan:** No TBD/TODO; every code step has complete code; verifications show commands + expected output. Task 4 is inherently interactive (paid render + human judgment) — its steps are concrete actions, not placeholders. ✓

**Type consistency:** `presets.resolve(preset_id, expected_category, presets=None)` defined in Task 1, called in Task 2 `_compose`. `presets.load_presets() -> {id: record}` defined Task 1, called in Task 2 `run()`. `_compose(clip, preset_map) -> (motion, negative, duration, resolution, seed, camera_fixed)` defined + tested Task 2; its 6-tuple is unpacked into the existing `_clip_hash(frame, motion, negative, duration, resolution, seed, camera_fixed)` (7 args incl. frame) and `video.image_to_video` call — matches current run_video.py. ✓
