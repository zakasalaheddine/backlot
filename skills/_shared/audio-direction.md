# Audio direction — VO tone and music vocabulary

What to put in a production's `vo` fields and `meta.music.mood` so the audio
sounds like UGC, not like an ad read.

## Voice-over

- **The character's locked voice IS the narrator** (`character.json` voice —
  lock one via character-creator before the first VO reel).
- Tone: friend-on-facetime. Slightly imperfect beats polished. If a line reads
  like a billboard, rewrite it as a confession ("I genuinely didn't expect...").
- Keep per-shot lines ≤ ~12 words (5s shots). The timing sidecar syncs captions
  automatically — don't pad lines to fill time.

## Music mood prompts (`meta.music.mood`)

Describe genre + energy + texture in 3–6 words; the bed is generated
instrumental and ducked under the VO automatically.

| Reel vibe | Mood prompt |
|---|---|
| cozy / gift / home | "cozy-upbeat lofi, warm, soft keys" |
| energetic / fashion | "punchy pop, four on the floor, bright" |
| calm / skincare / morning | "gentle acoustic, airy, slow build" |
| techy / gadget | "minimal electronic, clean pulse" |

- Default `gain_db` -8 (music under VO). No VO in the reel? -4 and pick a
  bolder mood.
- One bed per reel. Mood switches mid-reel read as edits gone wrong.

## SFX (optional garnish)

One or two subtle diegetic hits max (`audio_gen.py sfx "soft kettle click"`),
placed via the timeline's `vo` list mechanics (an SFX is just another audio
take with an `at`). Skip unless a shot obviously calls for it.
