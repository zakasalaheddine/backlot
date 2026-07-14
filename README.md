# backlot

A Claude Code plugin: a UGC content engine that builds **reusable characters**, **ad
images**, and (v1) **UGC videos** from one continuity-locked asset library.

- **Images / compositing:** Nano-Banana (`google/nano-banana`) via Replicate, behind
  a swappable provider layer.
- **Planning, copy, orchestration:** Claude (the skill-running agent).
- **v0 ships:** characters + ads. Video is v1 (seam is stubbed).

See `blueprint.md` for the full design.

## Setup
```bash
pip install -r requirements.txt          # replicate, Pillow
cp .env.example .env                      # then add your REPLICATE_API_TOKEN
```

## Try it with zero cost (no token)
Every command honours `BACKLOT_IMAGE_PROVIDER=stub`, which returns labelled
placeholder PNGs so you can exercise the whole pipeline before spending:
```bash
BACKLOT_IMAGE_PROVIDER=stub python scripts/assets.py originate-character \
  --name Maya --descriptor "mid-20s, warm smile, cream knit, gold hoops" \
  --seed-prompt "photo of a mid-20s girl-next-door, soft window light, plain background"
BACKLOT_IMAGE_PROVIDER=stub python scripts/run_ad.py out/<name>/job.json
```
Drop the prefix (with a real token) for real pixels.

## How it fits together
```
skills/          orchestrate (Claude is the planner; emits JSON, calls scripts)
  backlot/         router — routes to sub-skills, enforces "assets exist first"
  character-creator/  grill → originate/lock a character or product
  ad-image/           grill → ad job JSON → run_ad.py
  ugc-video/          grill → video job JSON → run_video.py
  _shared/         prompt-craft: interview, continuity, nano-banana, ad-layout, asset-library
scripts/         deterministic work
  assets.py        create/list/get characters & products
  run_ad.py        ad job JSON → composite → format export → text overlay (cached)
  run_video.py     video job JSON → image-to-video clips (cached, model-aware)
  models.py        list / inspect / swap which model serves each capability
  text_overlay.py  deterministic PIL copy layer (never let the model draw text)
providers/       swappable model-host abstraction
  models.json      the capability registry — which model serves each capability
  config.py        env + registry resolver (resolve("video.i2v") → model/backend/profile)
  images.py        generate_reference(), composite()
  video.py         image_to_video(), capabilities()
  audio.py         tts(), music(), sfx()   (stub backend for now; ElevenLabs is P3)
assets/          the persisted library (contents gitignored)
```

## Swapping models (the capability registry)
Which model serves each capability (`image.reference`, `image.composite`,
`video.i2v`, `audio.tts`, …) lives in `providers/models.json`, each with a
**capability profile** (supported resolutions, durations, audio, aspects) that
runners validate against and backends build inputs from.

```bash
python scripts/models.py list                      # active model per capability
python scripts/models.py inspect video.i2v         # full profile
python scripts/models.py set video.i2v seedance-2.0   # persist a swap to .env
python scripts/models.py set video.i2v --provider stub # zero-cost placeholder runs
```

Adding a model = one registry entry (+ a backend module in `providers/backends/`
only if it's a new host). Per-capability env overrides
(`BACKLOT_<CAPABILITY>_MODEL` / `_PROVIDER`) and the legacy
`BACKLOT_IMAGE_PROVIDER` / `BACKLOT_VIDEO_PROVIDER` /
`BACKLOT_NANO_BANANA_MODEL` / `BACKLOT_SEEDANCE_MODEL` vars are honoured.
Skills and scripts never change.

## Slash commands
- `/ugc-character` — create/lock a character or product
- `/ugc-ad` — build a set of ad creatives
- `/ugc-assets` — list/inspect the library

## Not yet built
See `docs/backlot-v2-plan.md` for the roadmap. Next up: `compose.py` (ffmpeg
multi-clip assembly, P2), real audio backends (ElevenLabs, P3), Remotion overlays
(P4), and the full production DAG (`run_production.py`, P5). The audio seam
(`providers/audio.py`) already exists with a stub backend.
