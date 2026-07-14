# Assembly — beat structure and pacing for UGC reels

How to plan the shots of a production so the reel converts. The runner
assembles whatever you give it; this is what to give it.

## Beat structure (15–30s total)

| Beat | Length | Job | Shot notes |
|---|---|---|---|
| **hook** | ≤ 2.5s of attention, one 5s shot | stop the scroll | strongest visual + a `hook` card; VO opens mid-thought ("okay so...") |
| **problem/context** | one 5s shot | make it relatable | optional — small productions skip straight to proof |
| **proof** | 1–2 × 5s shots | show the product working | close-up of the product/print; hands > faces here |
| **CTA** | 3s end card | tell them what to do | `end_card` with one short imperative ("Shop now") |

- **Default to VO-over-b-roll** — no talking faces (lip-sync artifacts kill
  trust). Hands, product, lifestyle; the locked character appears but doesn't
  mouth words.
- **5s shots by default**; 10s only when one continuous action needs it. More,
  shorter shots beats fewer, longer ones.
- 2 shots + end card ≈ 13s is a perfectly good ad. Don't pad to 30s.

## VO writing

- Conversational, first person, mid-thought openings; contractions always.
- ~2.5 words/second: a 5s shot fits ~12 words. Write each shot's `vo` to fit
  its shot — spillover into the next shot is fine ONLY if the next shot has no
  `vo` of its own (VO takes are placed at each shot's start and will overlap).
- The words become karaoke captions verbatim — write for the eye too: no
  parentheses, no numbers that read badly ("two days", not "2d").

## Continuity rules (same as everywhere in backlot)

- Every keyframe composites LOCKED refs (`use_refs`) — character and/or
  product. Never describe the character in the prompt; the refs carry identity.
- One reel = one wardrobe, one location vibe, unless the beat demands a change.
- Motion comes from the preset library (`presets.py list`) — free-text motion
  is seasoning, not the base.
