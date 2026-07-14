---
name: character-creator
description: Create or update a reusable, continuity-locked UGC character (a "creator" persona) or a product asset for the backlot content engine. Use this whenever the user wants to make a new persona/creator/avatar/model/face for ads, "a character for my brand", a spokesperson, or wants to register/lock a real product's photos as a reusable asset — and ALWAYS before making an ad or video that references a character or product that doesn't exist yet. Also use to evolve an existing character (new wardrobe, seasonal look, new expression) while keeping them the same person. Handles both generated-from-scratch personas and real uploaded photos.
---

# character-creator

Produce or update a **locked asset** — a Character (a reusable UGC creator identity)
or a Product — that every ad and video will composite from. This is the asset that
makes an account feel like a real person, so getting it right and locking it is the
whole foundation.

Read these shared references before working:
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md` — how to grill for a strong brief (do this first).
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/continuity.md` — why we lock refs and never regenerate identities.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/asset-library.md` — the on-disk format and `assets.py` commands.
- `${CLAUDE_PLUGIN_ROOT}/skills/_shared/nano-banana.md` — how origination prompts should read.

## Flow

### 1. Grill for the persona (or product)
Follow `interview.md`. For a **character**, pull out: niche/account angle, age &
vibe, look & wardrobe, what to avoid, and whether they're generated or a real person
(uploaded photos). For a **product**, you mainly need real photos + the descriptor +
any constraints (e.g. "printed text must stay legible"). Don't over-grill — stop when
you can picture them. Then reflect the brief back and get a yes.

From the confirmed brief, compose two things in-context (you are the planner):
- a **canonical descriptor** — the fixed text injected into every future prompt
  ("mid-20s woman, warm smile, soft makeup, cream knit sweater, gold hoops").
- a **seed prompt** — a photographic origination prompt for the front angle.

### 2. Originate (or ingest)

**Generated character** — build a multi-angle turnaround (front, 3/4, profile, full
body) from one seed. Angle 0 is generated first and chained into the rest so it's one
person from four angles (see `continuity.md`):
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py originate-character \
  --name "Maya" \
  --persona "mid-20s, warm, girl-next-door, casual-chic" \
  --descriptor "mid-20s woman, warm smile, soft makeup, cream knit sweater, gold hoops" \
  --seed-prompt "photo of a mid-20s woman, girl-next-door, soft natural window light, plain background" \
  --wardrobe "oversized cream knit, gold hoops" \
  --negative "no heavy makeup, no tattoos, no sunglasses"
```

**Real person (upload)** — lock provided photos instead of generating:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py ingest-character --name "Maya" \
  --descriptor "..." --refs /path/a.png /path/b.png /path/c.png
```

**Product** — always real photos:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py create-product --name "Heart Mug" \
  --descriptor "white ceramic mug, printed photo + name on front" \
  --constraints "print area must stay legible and undistorted; keep true white" \
  --refs /path/front.png /path/angle.png
```

The command prints the assigned **id** and the saved ref paths. It writes the
manifest and locks the refs under `assets/`.

### 3. Review loop
Show the user the ref sheet (the generated angles). Let them reject/regen individual
angles before they consider it locked. If they want changes:
- regenerate a single angle by re-running origination with an adjusted `--angles`
  JSON, or tweak the descriptor and re-originate.
- when a locked character is edited later (new wardrobe/season), **bump `version`**
  in the manifest — she should stay the same person in a new outfit, not a lookalike.

### 4. Lock a voice (characters that will speak)
If the character will do voice-over in videos, lock a voice now — it's the audio
half of continuity, the same trick as the face refs. Needs `ELEVENLABS_API_KEY`:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/voices.py list --search "warm" --category premade
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py set-voice --id maya-01 \
  --voice-id <voice_id> --voice-name Rachel
```

Share a couple of `preview_url`s so the user can audition before locking. Skip
for products and for characters that only appear in silent clips — the voice can
be locked later when the first VO is needed.

### 5. Confirm it's summonable
Report the id back plainly: "Locked as `maya-01` (4 refs, voice: Rachel)." That id
is how ad-image and ugc-video will summon her. Never let an ad silently invent a
throwaway identity — if an asset is missing, create it here first.

## Testing without spending
Prefix any command with `BACKLOT_IMAGE_PROVIDER=stub` to run the full flow with
placeholder images (no Replicate token, no cost) — useful to prove the wiring before
generating real refs. Drop the prefix (with `REPLICATE_API_TOKEN` set) for real pixels.
