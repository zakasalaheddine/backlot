# backlot v2 — from clip generator to full content engine

**North star:** one brief → a publishable multi-shot UGC video ad. Keyframes →
animated clips → voice-over + music → captions/motion-graphics → assembled
masters per aspect ratio — with every model swappable behind a capability
registry. Static ads keep working unchanged.

**Principles that don't change** (they're why v0/v1 work):
- Claude is the planner: skills emit job JSON, deterministic Python scripts do the pixels.
- Content-addressed caching at every stage; regen one artifact without rebuilding the batch.
- Every capability has a `stub` backend so the whole pipeline runs at zero cost.
- The asset library is the single source of continuity — now including *voice*.

---

## Workstream 1 — Capability registry (the foundation)

Generalize `providers/config.py` from two hardcoded providers to a capability
registry. This is what makes "easily swap models" real.

**Capabilities:**

| Capability        | v1 default                  | Alternates (later)              |
|-------------------|-----------------------------|---------------------------------|
| `image.reference` | nano-banana (Replicate)     | flux, seedream                  |
| `image.composite` | nano-banana (Replicate)     | seedream-edit                   |
| `video.i2v`       | seedance-1-pro (Replicate)  | kling, wan, hailuo, veo         |
| `audio.tts`       | ElevenLabs                  | Replicate TTS models            |
| `audio.music`     | ElevenLabs Music            | meta/musicgen (Replicate)       |
| `audio.sfx`       | ElevenLabs SFX              | —                               |
| `video.lipsync`   | — (v3)                      | latentsync / sync-labs          |

**Pieces:**
- `providers/models.json` — registry: capability → `{backend, model_slug, profile}`.
  (JSON, not YAML: the plugin is JSON everywhere and stays dependency-free.)
  Generalizes `seedance_profiles.py` into per-model **capability profiles**
  (max duration, resolutions, audio support, input-schema mapping) for every model,
  not just Seedance.
- Env overrides per capability: `BACKLOT_<CAP>_PROVIDER` / `BACKLOT_<CAP>_MODEL`
  (existing vars stay as aliases).
- `scripts/models.py list|inspect|set` — CLI so skills (and the user) can
  enumerate what's available and swap without editing code.
- Rule stays: adding a model = one profile entry (+ a backend module if it's a
  new host). Skills and runners never change.

## Workstream 2 — ffmpeg assembly (`scripts/compose.py`)

Highest immediate payoff: `run_video.py` already produces clips; nothing stitches them.

- Timeline job JSON: ordered clip refs + audio tracks + overlay refs → master video.
- Concat with uniform re-encode (fps/res/pix_fmt), per-aspect masters
  (9:16 native; 1:1 / 4:5 center-crop or reframe).
- Audio mix: VO + music with sidechain ducking, loudness-normalized to −14 LUFS.
- Caption fallback: burned ASS/SRT subtitles (works before Remotion exists).
- Overlay compositing: accepts alpha-channel overlay videos (from Workstream 4).
- Deterministic + content-addressed, same pattern as `run_video.py`.
- Dependency: `ffmpeg` binary — probe at start, fail with an install hint.

## Workstream 3 — Audio (ElevenLabs) + voice continuity

- `providers/audio.py`: `tts(text, voice, opts)`, `music(mood, duration)`, `sfx(desc)`.
- Backends: `elevenlabs_audio.py`, `replicate_audio.py`, `stub_audio.py`
  (silence + tone markers, keeps zero-cost testing).
- **Voice is part of character continuity:** `character.json` gains a `voice`
  block (`provider`, `voice_id`, settings). character-creator gets a
  "pick & lock a voice" step — same locking trick as faces.
- TTS returns word/character timestamps (ElevenLabs supports this) — saved next
  to the audio file; this drives karaoke captions in Workstream 4 with no
  transcription step.
- New env: `ELEVENLABS_API_KEY`.

## Workstream 4 — Remotion sidecar (animated assets)

- `remotion/` Node workspace inside the plugin (own `package.json`), driven by
  `scripts/render_overlay.py` (subprocess → `npx remotion render`).
- Props-driven templates: word-timed karaoke captions, hook text cards, CTA end
  card, logo sting, price/offer flash, progress bar.
- Remotion renders **transparent overlays** (ProRes 4444 / WebM alpha) and
  standalone cards; **ffmpeg remains the master assembler**. Remotion never
  touches the AI clips — assembly stays deterministic and cheap, and Node is an
  optional dependency (no Node → graceful degrade to ASS captions).
- `_shared/overlay-design.md` — template usage + brand-kit conventions
  (fonts/colors per brand, stored in the asset library as a `brand` asset — small
  json + logo files).

## Workstream 5 — Full production pipeline

- `scripts/run_production.py` — the blueprint §6 DAG, end to end:
  `production.json` (shots: keyframe+motion, VO lines, captions, music mood,
  end card) → keyframes ∥ → clips ∥ → audio ∥ → overlays → compose.
- Every stage content-addressed; `scripts/render_shot.py <production> s3`
  regenerates one shot only.
- New skill + command: **`ugc-reel`** / `/ugc-reel` — grills the brief
  (angle, beats, hook, CTA), emits `production.json`, runs the pipeline, presents
  the cut for shot-level review.
- New `_shared/` prompt-craft: `audio-direction.md` (VO tone, music mood
  vocabulary), `assembly.md` (pacing, beat structure: hook ≤2s, proof, CTA).
- Default format: VO-over-b-roll (no talking face) per the blueprint's lip-sync
  caveat; lip-sync becomes a `video.lipsync` capability in v3 for talking beats.

## Workstream 6 — Model breadth

After the registry exists, each addition is a profile entry:
- Video: kling, wan, hailuo/minimax, veo (whatever's live on Replicate) — plus a
  per-model motion-prompt dialect note in `_shared/seedance-motion.md`
  (renamed `motion-prompts.md`, sectioned per model).
- Images: flux / seedream profiles for `image.reference`; nano-banana stays the
  composite default.
- Verify each model's real Replicate schema before writing its profile (same
  rule as Seedance — don't guess).

## Companion service/app — decision: **not yet**

Everything above is files + deterministic CLIs; Claude Code is already the
orchestrator and Replicate is already the async render farm. A service adds ops
burden without new capability today.

Revisit when one of these becomes true: (a) a web UI for review/approval of
shots is wanted, (b) multi-user / multi-machine asset library, (c) scheduled or
queued campaign runs. The escape hatch is designed in now: manifests stay
URL-agnostic and scripts stay thin, so a small FastAPI+SQLite job/asset server
can slot behind them later without touching skills.

---

## Phasing (each phase is independently shippable)

| Phase | Deliverable | Unlocks |
|-------|------------|---------|
| **P1** | Capability registry + `models.json` + `models.py` CLI | Real model swapping; foundation for all audio/video additions |
| **P2** | `compose.py` (concat, crops, ASS captions) | Multi-shot silent reels from existing clips — immediately usable |
| **P3** | ElevenLabs TTS/music + voice locking + audio mix in compose | Reels with sound; characters gain voices |
| **P4** | Remotion workspace + karaoke captions + end cards | Branded, scroll-stopping polish |
| **P5** | `run_production.py` + `render_shot.py` + `/ugc-reel` skill | One brief → finished ad, shot-level regen |
| **P6** | Kling/wan/veo/flux profiles; lip-sync capability | Breadth + talking-head beats |

**New dependencies by phase:** P2 `ffmpeg` binary · P3 `ELEVENLABS_API_KEY` ·
P4 Node ≥ 18 (optional — degrade to ASS captions without it).
