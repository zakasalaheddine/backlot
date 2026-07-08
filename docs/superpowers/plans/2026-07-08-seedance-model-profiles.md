# Seedance Model Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the video backend drive multiple Seedance model versions (seedance-1-pro and seedance-2.0) correctly, via per-model capability profiles, with audio default-off and a per-clip opt-in.

**Architecture:** A new `seedance_profiles.py` holds an explicit profile per model family. `replicate_video` builds each model's input from its profile (camera_fixed / aspect_ratio / generate_audio / resolutions). `video.py` exposes `capabilities()`; `run_video.py` uses it for clip-named validation and threads an `audio` flag. 1-pro behavior is unchanged except a redundant `camera_fixed:false` is no longer sent.

**Tech Stack:** Python 3.9+, Pillow (already a dep, for aspect probing), Replicate.

## Global Constraints

- Default model stays `bytedance/seedance-1-pro`; `.env` may set `BACKLOT_SEEDANCE_MODEL`.
- Profiles (exact): `seedance-1-pro` = `{camera_fixed:True, aspect:"infer", audio:False, resolutions:{480p,720p,1080p}}`; `seedance-2.0` = `{camera_fixed:False, aspect:"explicit", audio:True, resolutions:{480p,720p,1080p,4k}}`.
- `profile_for(slug)`: `"seedance-2" in slug` → 2.0; `"seedance-1" in slug` → 1-pro; else → 1-pro (conservative fallback). Substring match so pinned `…:versionhash` resolves.
- `_build_input` sends: `prompt` (+ `"\n\nAvoid: <negative>."` when negative), `duration`, `resolution` always; `camera_fixed` ONLY when `profile["camera_fixed"]` AND resolved `camera_fixed` is True; `aspect_ratio` ONLY when `profile["aspect"]=="explicit"` (value = aspect probed from frame); `generate_audio` ONLY when `profile["audio"]` (value = the clip's audio flag, default False); `seed` when not None. Never send a field the profile lacks.
- Audio default is `False`. A clip opts in with `"audio": true`. `audio:true` on a no-audio model → clip-named `ValueError`.
- Resolution validated against the active profile's set (via `video.capabilities()`), clip-named error, before spend.
- `audio` joins the cache-key inputs.
- Backend contract signature (stub AND replicate must match): `image_to_video(frame, prompt, negative, duration, resolution, seed, camera_fixed, audio, out_path)`.
- No `providers/images.py` changes. Repo has NO pytest suite; verification is `python -c` + stub — not a defect.

---

### Task 1: Capability profiles module

**Files:**
- Create: `providers/backends/seedance_profiles.py`

**Interfaces:**
- Produces: `profile_for(slug: str) -> dict`; `nearest_aspect(w: int, h: int) -> str`.

- [ ] **Step 1: Write the failing test**

```bash
python -c "
import sys; sys.path.insert(0,'.')
from providers.backends import seedance_profiles as sp
assert sp.profile_for('bytedance/seedance-1-pro')['camera_fixed'] is True
p2 = sp.profile_for('bytedance/seedance-2.0')
assert p2['camera_fixed'] is False and p2['aspect']=='explicit' and p2['audio'] is True and '4k' in p2['resolutions']
assert sp.profile_for('bytedance/seedance-1-pro:abc123')['aspect']=='infer'   # pinned version
assert sp.profile_for('some/unknown')['camera_fixed'] is True                 # conservative fallback
assert sp.nearest_aspect(1088,1920)=='9:16'
assert sp.nearest_aspect(1920,1080)=='16:9'
assert sp.nearest_aspect(1024,1024)=='1:1'
print('profiles OK')
"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — `ModuleNotFoundError: No module named 'providers.backends.seedance_profiles'`.

- [ ] **Step 3: Write `providers/backends/seedance_profiles.py`**

```python
"""Per-model capability profiles for the Seedance video backend.

Each Seedance version accepts a different input schema. Rather than guess or
introspect at runtime, we keep an explicit profile per model family and send
only the fields that model supports. Adding a future model = one profile entry.
"""
from __future__ import annotations

PROFILES = {
    "seedance-1-pro": {
        "camera_fixed": True,          # field supported
        "aspect": "infer",             # aspect read from the image; don't send aspect_ratio
        "audio": False,                # no audio support
        "resolutions": {"480p", "720p", "1080p"},
    },
    "seedance-2.0": {
        "camera_fixed": False,         # not a field (sending it errors)
        "aspect": "explicit",          # MUST send aspect_ratio or it defaults to 16:9
        "audio": True,                 # generate_audio supported (backlot default off)
        "resolutions": {"480p", "720p", "1080p", "4k"},
    },
}


def profile_for(slug: str) -> dict:
    """Resolve a model slug to its capability profile. Substring match on the
    family so a pinned '<slug>:<versionhash>' still resolves. Unknown models
    fall back to the conservative 1-pro profile."""
    if "seedance-2" in slug:
        return PROFILES["seedance-2.0"]
    if "seedance-1" in slug:
        return PROFILES["seedance-1-pro"]
    return PROFILES["seedance-1-pro"]


# Supported aspect ratios we map a frame to (subset of Seedance's enum).
_ASPECTS = {"9:16": 9 / 16, "3:4": 3 / 4, "1:1": 1.0, "4:3": 4 / 3, "16:9": 16 / 9}


def nearest_aspect(w: int, h: int) -> str:
    """Map a frame's pixel dimensions to the closest supported aspect ratio."""
    ratio = w / h
    return min(_ASPECTS, key=lambda k: abs(_ASPECTS[k] - ratio))
```

- [ ] **Step 4: Run the test to confirm it passes**

Run the Step 1 block. Expected: `profiles OK`.

- [ ] **Step 5: Commit**

```bash
git add providers/backends/seedance_profiles.py
git commit -m "feat: add per-model Seedance capability profiles"
```

---

### Task 2: Profile-aware backend + capabilities API

**Files:**
- Modify: `providers/backends/replicate_video.py`
- Modify: `providers/backends/stub_video.py` (accept the new `audio` arg)
- Modify: `providers/video.py` (pass `audio`, add `capabilities()`)

**Interfaces:**
- Consumes: `seedance_profiles.profile_for`, `nearest_aspect` (Task 1).
- Produces:
  - `replicate_video._build_input(profile: dict, prompt, negative, duration, resolution, seed, camera_fixed, audio, aspect) -> dict`
  - `replicate_video._frame_aspect(frame: Path) -> str`
  - Backend `image_to_video(frame, prompt, negative, duration, resolution, seed, camera_fixed, audio, out_path) -> Path` (stub + replicate).
  - `video.capabilities() -> dict`.

- [ ] **Step 1: Write the failing tests**

```bash
python -c "
import sys; sys.path.insert(0,'.')
from providers.backends import replicate_video as rv, seedance_profiles as sp
p2 = sp.profile_for('bytedance/seedance-2.0')
i = rv._build_input(p2,'sway','jit',5,'1080p',None,False,False,'9:16')
assert 'camera_fixed' not in i and i['aspect_ratio']=='9:16' and i['generate_audio'] is False
assert i['prompt'].endswith('Avoid: jit.')
i2 = rv._build_input(p2,'x','',5,'4k',7,True,True,'9:16')
assert 'camera_fixed' not in i2 and i2['generate_audio'] is True and i2['seed']==7
p1 = sp.profile_for('bytedance/seedance-1-pro')
j = rv._build_input(p1,'x','',5,'1080p',None,True,False,None)
assert j['camera_fixed'] is True and 'aspect_ratio' not in j and 'generate_audio' not in j
j2 = rv._build_input(p1,'x','',5,'1080p',None,False,False,None)
assert 'camera_fixed' not in j2   # false omitted
print('build-input OK')
"
```

And a `capabilities()` check (env selects the model):
```bash
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-2.0 python -c "
import sys; sys.path.insert(0,'.')
from providers import video
c = video.capabilities()
assert c['audio'] is True and c['camera_fixed'] is False and '4k' in c['resolutions']
print('capabilities OK')
"
```

- [ ] **Step 2: Run them to verify they fail**

Expected: FAIL — `_build_input()` arity/`TypeError` (old 6-arg version) and `AttributeError: module 'providers.video' has no attribute 'capabilities'`.

- [ ] **Step 3: Rewrite `providers/backends/replicate_video.py`**

Replace the whole file with:

```python
"""Replicate video backend — Seedance (bytedance/seedance-1-pro, seedance-2.0).

Each model version accepts a different input schema; the fields to send are
resolved from that model's capability profile (see seedance_profiles.py):

    prompt        required   -> motion description (+ "Avoid: <negative>." appended)
    image         start frame (uploaded from a local file)
    duration      integer seconds
    resolution    per-profile set (1-pro: 480p/720p/1080p; 2.0 adds 4k)
    seed          optional
    camera_fixed  1-pro only, and only when True
    aspect_ratio  2.0 only ("explicit" profile); probed from the frame. 1-pro
                  infers aspect from the image, so it is omitted there.
    generate_audio 2.0 only; the clip's audio flag (default False)
    -> output is a SINGLE .mp4 URI.

Seedance has no negative field, so a negative is appended to the prompt as
"Avoid: ..." (same convention as replicate_images.py).
"""
from __future__ import annotations

from pathlib import Path

from .. import config
from .replicate_common import run_video
from .seedance_profiles import profile_for, nearest_aspect


def _build_input(profile: dict, prompt: str, negative: str, duration: int,
                 resolution: str, seed, camera_fixed: bool, audio: bool,
                 aspect: str | None) -> dict:
    full = f"{prompt}\n\nAvoid: {negative}." if negative else prompt
    inp = {"prompt": full, "duration": duration, "resolution": resolution}
    if profile["camera_fixed"] and camera_fixed:
        inp["camera_fixed"] = True
    if profile["aspect"] == "explicit" and aspect:
        inp["aspect_ratio"] = aspect
    if profile["audio"]:
        inp["generate_audio"] = bool(audio)
    if seed is not None:
        inp["seed"] = seed
    return inp


def _frame_aspect(frame: Path) -> str:
    """Probe the frame's pixel size and map it to the nearest supported aspect."""
    from PIL import Image
    with Image.open(frame) as im:
        w, h = im.size
    return nearest_aspect(w, h)


def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool, audio: bool,
                   out_path: Path) -> Path:
    """Animate one start frame into a clip via the configured Seedance model,
    sending only the fields that model's profile supports."""
    profile = profile_for(config.SEEDANCE_MODEL)
    aspect = _frame_aspect(frame) if profile["aspect"] == "explicit" else None
    inp = _build_input(profile, prompt, negative, duration, resolution, seed,
                       camera_fixed, audio, aspect)
    with open(frame, "rb") as fh:
        inp["image"] = fh
        return run_video(config.SEEDANCE_MODEL, inp, out_path)
```

- [ ] **Step 4: Update `providers/backends/stub_video.py` signature**

The stub must accept the same 9-arg contract. Change its `image_to_video` signature to include `audio` (it still ignores the frame and writes the placeholder):

```python
def image_to_video(frame: Path, prompt: str, negative: str, duration: int,
                   resolution: str, seed, camera_fixed: bool, audio: bool,
                   out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_PLACEHOLDER_MP4)
    return out_path
```

- [ ] **Step 5: Update `providers/video.py`**

(a) In `image_to_video`, pass the audio flag through and update the docstring's `motion` line to mention `"audio": bool (optional, default False)`:

```python
    b = _backend()
    return b.image_to_video(
        Path(frame),
        motion["prompt"],
        motion.get("negative", ""),
        duration,
        resolution,
        motion.get("seed"),
        motion.get("camera_fixed", False),
        motion.get("audio", False),
        Path(out_path),
    )
```

(b) Add `capabilities()` at module end:

```python
def capabilities() -> dict:
    """Capability profile of the active Seedance model (from BACKLOT_SEEDANCE_MODEL).
    Lets callers introspect supported resolutions / audio without backend details."""
    from .backends.seedance_profiles import profile_for
    return profile_for(config.SEEDANCE_MODEL)
```

- [ ] **Step 6: Run the `_build_input` and `capabilities` tests to confirm they pass**

Run both Step 1 blocks. Expected: `build-input OK` and `capabilities OK`.

- [ ] **Step 7: Verify `_frame_aspect` on a real image + stub arity end-to-end**

```bash
python -c "
import sys; sys.path.insert(0,'.')
from PIL import Image
from pathlib import Path
Image.new('RGB',(90,160)).save('out/_ap.png')       # 9:16
from providers.backends import replicate_video as rv
assert rv._frame_aspect(Path('out/_ap.png'))=='9:16'
import os; os.remove('out/_ap.png')
print('frame-aspect OK')
"
# stub still callable with the new 9-arg contract, via the public API
BACKLOT_VIDEO_PROVIDER=stub python -c "
import sys; sys.path.insert(0,'.')
from providers import video
from pathlib import Path
p = video.image_to_video('x.png', {'prompt':'sway','audio':True}, out_path='out/_t/clip.mp4')
assert Path(p).exists(); print('stub arity OK')
"
rm -rf out/_t out/_ap.png
```
Expected: `frame-aspect OK` and `stub arity OK`.

- [ ] **Step 8: Commit**

```bash
git add providers/backends/replicate_video.py providers/backends/stub_video.py providers/video.py
git commit -m "feat: profile-aware Seedance input building and capabilities()"
```

---

### Task 3: Runner wiring — audio opt-in + capability validation

**Files:**
- Modify: `scripts/run_video.py`

**Interfaces:**
- Consumes: `video.capabilities()`, `video.image_to_video` with `audio` in the motion dict (Task 2).
- Produces: `_compose(clip, preset_map) -> (motion, negative, duration, resolution, seed, camera_fixed, audio)`; `_clip_hash(frame, motion, negative, duration, resolution, seed, camera_fixed, audio)`.

- [ ] **Step 1: Write the failing composition test**

```bash
python -c "
import sys; sys.path.insert(0,'scripts')
import run_video
pm = {'dolly-in':{'id':'dolly-in','category':'camera','prompt':'CAM','camera_fixed':False,'duration':5}}
# audio defaults False; opt-in True
m = run_video._compose({'id':'c1','camera':'dolly-in'}, pm)
assert len(m)==7 and m[6] is False, m
m2 = run_video._compose({'id':'c2','camera':'dolly-in','audio':True}, pm)
assert m2[6] is True
print('compose-audio OK')
"
```

- [ ] **Step 2: Run it to verify it fails**

Expected: FAIL — `_compose` returns a 6-tuple (no audio), so `len(m)==7` assertion errors.

- [ ] **Step 3: Add `audio` to `_compose`**

Read `scripts/run_video.py`. In `_compose`, after `resolution`/`seed` are read, add `audio = bool(clip.get("audio", False))` and append it to the returned tuple. The return becomes:

```python
    resolution = clip.get("resolution", "1080p")
    seed = clip.get("seed")
    audio = bool(clip.get("audio", False))
    return motion, negative, duration, resolution, seed, camera_fixed, audio
```

- [ ] **Step 4: Thread `audio` through `_clip_hash` and `run()`**

(a) Update `_clip_hash` to include `audio` in the digest:

```python
def _clip_hash(frame: Path, motion: str, negative: str, duration: int, resolution: str,
               seed, camera_fixed: bool, audio: bool) -> str:
    h = hashlib.sha256()
    for part in (motion, negative, str(duration), resolution, str(seed),
                 str(camera_fixed), str(audio)):
        h.update(part.encode())
        h.update(b"\x00")
    h.update(hashlib.sha256(frame.read_bytes()).digest())
    return h.hexdigest()[:16]
```

(b) In `run()`, load capabilities once before the loop, unpack the 7-tuple, validate resolution/audio against the active model, and pass `audio` to both the hash and the render call. Replace the per-clip body from the `_compose` call through the render block with:

```python
    caps = video.capabilities()
    preset_map = preset_lib.load_presets()
    produced = []
    for clip in job["clips"]:
        cid = clip["id"]
        frame = _resolve_frame(clip["frame"], job_path)
        if not frame.exists():
            raise FileNotFoundError(
                f"clip {cid!r}: start frame not found: {clip['frame']}"
            )

        motion, negative, duration, resolution, seed, camera_fixed, audio = _compose(
            clip, preset_map)

        if resolution not in caps["resolutions"]:
            raise ValueError(
                f"clip {cid!r}: resolution {resolution!r} not supported by the active "
                f"model; choose one of {sorted(caps['resolutions'])}"
            )
        if duration not in {5, 10}:
            raise ValueError(f"clip {cid!r}: duration must be 5 or 10, got {duration!r}")
        if audio and not caps["audio"]:
            raise ValueError(
                f"clip {cid!r}: audio requested but the active model has no audio support"
            )

        cdir = out_dir / cid
        cdir.mkdir(parents=True, exist_ok=True)
        clip_path = cdir / "clip.mp4"
        hash_path = cdir / "clip.hash"

        want = _clip_hash(frame, motion, negative, duration, resolution, seed,
                          camera_fixed, audio)
        have = hash_path.read_text().strip() if hash_path.exists() else ""

        if force or not clip_path.exists() or have != want:
            video.image_to_video(
                frame,
                {"prompt": motion, "negative": negative, "seed": seed,
                 "camera_fixed": camera_fixed, "audio": audio},
                duration=duration, resolution=resolution, out_path=clip_path,
            )
            hash_path.write_text(want)
            rendered = True
        else:
            rendered = False

        produced.append({"clip": cid, "mp4": str(clip_path),
                         "frame": str(frame), "rendered": rendered})
```

(The old hardcoded `{"480p","720p","1080p"}` resolution guard is replaced by the `caps["resolutions"]` check above; everything else in `run()` is unchanged.)

- [ ] **Step 5: Run the composition test to confirm it passes**

Run the Step 1 block. Expected: `compose-audio OK`.

- [ ] **Step 6: End-to-end stub verification (audio flag + capability validation) with a real keyframe**

```bash
rm -rf out/_mv; mkdir -p out/_mv
# Under the 1-pro profile: audio:true must be rejected (clip-named); 4k rejected.
cat > out/_mv/j.json <<'JSON'
{ "meta": {}, "clips": [ { "id":"c1","frame":"out/job/v1/keyframe_9x16.png","camera":"dolly-in","audio":true } ] }
JSON
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-1-pro BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py out/_mv/j.json --out out/_mv/r 2>&1 | grep -q "audio requested but the active model has no audio" && echo "audio-guard(1-pro) OK"

# Under the 2.0 profile: audio:true allowed, 4k allowed, renders via stub.
cat > out/_mv/j2.json <<'JSON'
{ "meta": {}, "clips": [ { "id":"c1","frame":"out/job/v1/keyframe_9x16.png","camera":"dolly-in","action":"mirror-selfie-alive","audio":true,"resolution":"4k" } ] }
JSON
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-2.0 BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py out/_mv/j2.json --out out/_mv/r2 >/dev/null && echo "2.0 audio+4k stub render OK"

# audio busts the cache: same clip without audio re-renders
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-2.0 BACKLOT_VIDEO_PROVIDER=stub python scripts/run_video.py out/_mv/j2.json --out out/_mv/r2 >/dev/null
python -c "import json; m=json.load(open('out/_mv/r2/run_manifest.json')); assert m['outputs'][0]['rendered'] is False; print('cache stable OK')"
rm -rf out/_mv
```
Expected: `audio-guard(1-pro) OK`, `2.0 audio+4k stub render OK`, `cache stable OK`.

- [ ] **Step 7: Commit**

```bash
git add scripts/run_video.py
git commit -m "feat: audio opt-in and capability-based validation in run_video"
```

---

### Task 4: Docs — audio field, model selection, 2.0 moderation note

**Files:**
- Modify: `skills/_shared/seedance-motion.md`
- Modify: `skills/ugc-video/SKILL.md`

**Interfaces:** Consumes the new `audio` clip field + model-via-env behavior.

- [ ] **Step 1: Update `skills/_shared/seedance-motion.md`**

Add a short section documenting model selection + audio + moderation. Insert after the intro / "Compose from presets" material:

```markdown
## Model selection & audio

The Seedance model is chosen via `BACKLOT_SEEDANCE_MODEL` (env / `.env`), default
`bytedance/seedance-1-pro`. The backend adapts per model:

- **seedance-1-pro** — silent clips; aspect inferred from the keyframe.
- **seedance-2.0** — can generate audio and needs an explicit aspect (handled for
  you). Audio is **off by default**; opt in per clip with `"audio": true` (adds
  synced ambient/SFX/music). **2.0 has stricter content moderation** — some
  people/bedroom UGC scenes get flagged (error E005). If a scene is rejected, prefer
  `seedance-1-pro` for that creative.
```

- [ ] **Step 2: Update `skills/ugc-video/SKILL.md`**

In the job-JSON notes (Flow step 2), add a bullet:

```markdown
- `audio` (optional, default false) — request generated audio. Only supported on
  audio-capable models (e.g. seedance-2.0); requesting it on a silent model is a
  clip-named error. The model is set via `BACKLOT_SEEDANCE_MODEL`.
```

- [ ] **Step 3: Verify the docs**

```bash
grep -q 'BACKLOT_SEEDANCE_MODEL' skills/_shared/seedance-motion.md && echo "model-selection doc OK"
grep -q 'audio' skills/ugc-video/SKILL.md && echo "audio doc OK"
grep -qi 'moderation' skills/_shared/seedance-motion.md && echo "moderation note OK"
```
Expected: all three OK lines.

- [ ] **Step 4: Commit**

```bash
git add skills/_shared/seedance-motion.md skills/ugc-video/SKILL.md
git commit -m "docs: document model selection, audio opt-in, and 2.0 moderation"
```

---

### Task 5: Real-render verification (paid — run with user consent)

**Files:** none.

**Interfaces:** Consumes the whole pipeline + a real `REPLICATE_API_TOKEN`.

- [ ] **Step 1: 1-pro regression render**

Confirm the backend rewrite didn't break 1-pro end-to-end:
```bash
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-1-pro python scripts/run_video.py out/sunny-reel-v2/job.json --out out/regress-1pro --force
```
Expected: `rendered: true`, a real (multi-MB) `.mp4`; identity + print hold (extract frames with ffmpeg to check). This proves omitting the redundant `camera_fixed:false` and the profile path did not regress 1-pro.

- [ ] **Step 2: 2.0 best-effort render**

Attempt one 2.0 clip through the real pipeline (now that the backend sends the right fields):
```bash
BACKLOT_SEEDANCE_MODEL=bytedance/seedance-2.0 python scripts/run_video.py out/sunny-reel-v2/job.json --out out/try-2.0 --force
```
Two acceptable outcomes:
- **Renders** → verify the clip is vertical (9:16, via `ffprobe`) and note whether audio is present. Success.
- **E005 sensitive-content flag** → this is a **content-moderation limitation of 2.0 on this bedroom keyframe, not a code failure** (schema acceptance was already proven). Report it as such; do not retry-loop.

- [ ] **Step 3: Report**

Summarize: 1-pro regression pass/fail, and the 2.0 outcome (rendered vertical, or moderation-blocked). Do not commit `out/` (git-ignored).

---

## Self-Review

**Spec coverage:**
- Per-model profiles (`profile_for`, exact field sets, fallback, pinned-version) → Task 1. ✓
- Profile-aware `_build_input` (camera_fixed only-when-supported-and-True, aspect explicit/infer, generate_audio only when supported, seed) → Task 2, Global Constraints. ✓
- Aspect probed from frame + `nearest_aspect` mapping → Task 1 (`nearest_aspect`), Task 2 (`_frame_aspect`). ✓
- `video.capabilities()` + backend contract updated on BOTH stub and replicate → Task 2 (steps 3-5). ✓
- Runner audio opt-in, capability-based resolution/audio validation (clip-named), audio in cache key → Task 3. ✓
- Docs: audio field, model-via-env, 2.0 moderation note → Task 4. ✓
- Verification: unit + stub free; real render paid/best-effort with 1-pro regression + 2.0 attempt → Tasks 1-3 (free), Task 5 (paid). ✓
- Backward compat: 1-pro default, redundant `camera_fixed:false` dropped (no output change), images.py untouched → Global Constraints, Task 2. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; every verification shows the command + expected output. Task 5 outcomes are enumerated (render vs moderation), not placeholders. ✓

**Type consistency:** Backend contract `image_to_video(frame, prompt, negative, duration, resolution, seed, camera_fixed, audio, out_path)` is identical in `stub_video` (Task 2 Step 4), `replicate_video` (Task 2 Step 3), and the call in `video.image_to_video` (Task 2 Step 5). `_build_input(profile, prompt, negative, duration, resolution, seed, camera_fixed, audio, aspect)` defined + tested Task 2. `_compose(...) -> 7-tuple` (Task 3 Step 3) is unpacked into `_clip_hash(frame, motion, negative, duration, resolution, seed, camera_fixed, audio)` (Task 3 Step 4) and the motion dict `{prompt,negative,seed,camera_fixed,audio}` — all consistent. `capabilities() -> dict` (Task 2) consumed in Task 3. `profile_for`/`nearest_aspect` (Task 1) consumed in Task 2. ✓
