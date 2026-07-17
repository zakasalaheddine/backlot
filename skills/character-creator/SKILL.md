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
- a **character sheet** — the full structured identity spec (see below). Fill
  every field by *inference* from the light brief plus coherent choices; do NOT
  turn it into a 25-question questionnaire. If the brief says "girl-next-door,
  mid-20s", you already know the jawline is soft and the makeup is minimal —
  decide it. Reflect the finished sheet back and get a yes.
- a **canonical descriptor** — a short one-line summary of the sheet, injected as
  `--descriptor` ("mid-20s woman, warm smile, cream knit sweater, gold hoops").

The sheet's `prompt_config.base_prompt` is the identity prompt; assets.py wraps it
in a fixed reference-sheet layout to produce the sheet image, so a locked sheet
keeps the same look.

**Photoreal by default.** Characters are real people — write `base_prompt`
photographically ("a real mid-20s woman…, natural skin texture, soft natural
light"), NOT "illustration/painterly/cinematic render". assets.py forces photoreal
and negatives out illustration automatically. Only when the user explicitly asks
for art (cartoon, anime, 3D, illustrated) pass `--style "anime"` (etc) to
`originate-character` — that switches the render medium and drops the anti-art
negatives.

### The character sheet
Compose this JSON and pass it verbatim via `--sheet`. It's the source of truth
for the identity; assets.py stores it as-is (schema-blind). Shape:
```json
{
  "character": {
    "name": "", "archetype": "",
    "identity": { "age_range": "", "gender_presentation": "", "ethnicity": "", "skin_tone": "" },
    "face": {
      "shape": "", "jawline": "", "cheekbones": "",
      "eyes": { "color": "", "shape": "", "spacing": "", "brows": "" },
      "nose": "", "lips": "", "distinct_markers": []
    },
    "hair": { "color": "", "undertone": "", "length": "", "texture": "", "part": "", "default_style": "" },
    "body": { "build": "", "height": "", "notable_features": [] },
    "expressions": [ { "name": "", "description": "" } ],
    "wardrobe": { "default_outfit": "", "variants": [], "color_palette": [] }
  },
  "prompt_config": {
    "base_prompt": "", "negative_prompt": "", "seed": null, "model": "", "style_tags": []
  }
}
```
`expressions` drives the emotion grid on the sheet — list ~6-8 emotions with a
short facial cue each (falls back to a default set if omitted). Keep the sheet a
plausible, internally-consistent person; that consistency is the whole point.

### 2. Generate the character SHEET (poses come later)

The sheet is the **first and only** thing you generate: ONE composite image — a
full-body turnaround (front / side / back) + a head-and-shoulders grid cycling
through the `expressions`, plus a hero portrait, on plain white. No text panels,
no wardrobe/accessory cut-outs, no cinematic scene. Individual clean pose refs are
NOT made here — you add them later, only when an ad/video needs one (step 2b).

**Generated character:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py originate-character \
  --name "Maya" \
  --persona "mid-20s, warm, girl-next-door, casual-chic" \
  --descriptor "mid-20s woman, warm smile, soft makeup, cream knit sweater, gold hoops" \
  --wardrobe "oversized cream knit, gold hoops" \
  --negative "no heavy makeup, no tattoos, no sunglasses" \
  --sheet "$SHEET_JSON"
```
Writes `character_sheet.png` + the manifest, with `refs: []`. Pass
`--seed-refs a.png b.png` to anchor the identity on existing images (real photos,
or a prior version's face).

**Real person (upload)** — lock provided photos instead of generating a sheet:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py ingest-character --name "Maya" \
  --descriptor "..." --refs /path/a.png /path/b.png /path/c.png \
  --sheet "$SHEET_JSON"   # compose the sheet by reading the uploaded photos
```
For an upload the photos ARE the refs — fill the sheet by describing what you see.

### 2b. Add poses on demand (only when needed)
When an ad or video actually needs a compositing-ready ref, generate one clean
pose from the sheet (it seeds the identity off the sheet, so it stays her):
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py add-pose --id maya-01 \
  --pose "front, standing, arms relaxed, plain background"
```
Each call appends a `refs/pose_NN.png`. Don't pre-generate poses you don't need.

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
Show the user `character_sheet.png`. If they want changes, tweak the sheet JSON
(expressions, face, wardrobe) and re-run `originate-character` — pass `--id <same>`
to overwrite, and `--seed-refs <old character_sheet.png>` to keep her the same
person while adjusting. When a locked character is edited later (new wardrobe/
season), **bump `version`** — same person, new look, not a lookalike.

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
Report the id back plainly: "Locked as `maya-01` (sheet ready, voice: Rachel)."
That id is how ad-image and ugc-video summon her. They composite from `refs` —
which start empty, so the first ad/video adds the poses it needs via `add-pose`
(or you pre-add them here). Never let an ad silently invent a throwaway identity —
if an asset is missing, create it here first.

## Testing without spending
Prefix any command with `BACKLOT_IMAGE_PROVIDER=stub` to run the full flow with
placeholder images (no Replicate token, no cost) — useful to prove the wiring before
generating real refs. Drop the prefix (with `REPLICATE_API_TOKEN` set) for real pixels.
