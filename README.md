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
cp .env.example .env                      # REPLICATE_API_TOKEN + ELEVENLABS_API_KEY
brew install ffmpeg                       # only needed for compose.py (video assembly)
# Node >= 18 (optional): Remotion overlays — karaoke captions, end cards.
# Without Node, compose.py's built-in PIL captions still work.
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
  assets.py        create/list/get characters & products (+ set-voice)
  run_ad.py        ad job JSON → composite → format export → text overlay (cached)
  run_video.py     video job JSON → image-to-video clips (cached, model-aware)
  run_production.py  production JSON → the FULL reel DAG (keyframes → clips →
                     VO/music → overlays → masters), every stage cached
  render_shot.py   regenerate one shot of a production, reuse everything else
  compose.py       timeline JSON → concat + audio mix + captions → master videos (ffmpeg)
  render_overlay.py  Remotion template + props → alpha overlay (.mov) or card clip (.mp4)
  audio_gen.py     VO (locked character voice, word timings) / music / SFX files
  voices.py        browse ElevenLabs voices to lock onto a character
  models.py        list / inspect / swap which model serves each capability
  text_overlay.py  deterministic PIL copy layer (never let the model draw text)
providers/       swappable model-host abstraction
  models.json      the capability registry — which model serves each capability
  config.py        env + registry resolver (resolve("video.i2v") → model/backend/profile)
  images.py        generate_reference(), composite()
  video.py         image_to_video(), capabilities()
  audio.py         tts() [+ word-timing sidecar], music(), sfx()  (ElevenLabs)
remotion/        motion-graphics templates (Node >= 18, optional)
  src/             KaraokeCaptions, HookCard, ProgressBar (alpha overlays), EndCard (clip)
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
- `/ugc-character` — create/lock a character or product (+ voice)
- `/ugc-ad` — build a set of ad creatives
- `/ugc-reel` — produce a complete video ad (shots, VO, music, captions, end card)
- `/ugc-assets` — list/inspect the library

## Not yet built
See `docs/backlot-v2-plan.md` for the roadmap. P1–P5 are done; what remains is
P6: more model profiles (kling / wan / veo / flux as registry entries — verify
each schema on Replicate first) and a `video.lipsync` capability for
talking-head beats.
