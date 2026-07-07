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
  _shared/         prompt-craft: interview, continuity, nano-banana, ad-layout, asset-library
scripts/         deterministic work
  assets.py        create/list/get characters & products
  run_ad.py        ad job JSON → composite → format export → text overlay (cached)
  text_overlay.py  deterministic PIL copy layer (never let the model draw text)
providers/       swappable model-host abstraction
  images.py        generate_reference(), composite()  → backends/{replicate,stub}_images.py
  video.py         image_to_video()  (v1 stub)
  config.py        the ONE place the host + model slugs live (env-driven)
assets/          the persisted library (contents gitignored)
```

## Swapping providers
The whole point of the provider layer: to move a capability off Replicate, add a
module in `providers/backends/` with the same functions and point the matching
`BACKLOT_*_PROVIDER` env var at it. Skills and scripts don't change.

## Slash commands
- `/ugc-character` — create/lock a character or product
- `/ugc-ad` — build a set of ad creatives
- `/ugc-assets` — list/inspect the library

## Not yet built (v1)
`ugc-video`, `run_video.py`, `compose.py`, `render_shot.py`, `providers/video.py`
implementation, `_shared/seedance-motion.md`. The seams exist; verify the Seedance
schema on Replicate before implementing (don't guess it).
