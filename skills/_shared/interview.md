# The Grill — extracting a great brief before touching pixels

Shared by every backlot skill. The output of a generation is only as good as the
brief behind it, and users almost never hand you a good brief unprompted. Your job
is to **grill** — ask sharp, specific questions, react to the answers, and keep
pushing until you have something a strong creative director would be happy to
build from. Then reflect it back and get a yes before you spend a single credit.

This is a conversation, not a form. Don't dump 15 questions at once. Ask a tight
salvo (2–4 questions), listen, follow the interesting thread, and stop when the
picture is sharp — not when a checklist is full.

## How to grill well

- **One salvo at a time.** 2–4 questions, then wait. A wall of questions gets
  skimmed and half-answered.
- **React, don't interrogate.** Reflect what you heard, then dig where it's thin.
  "Cozy and warm — got it. Is she talking to camera like a friend, or is this
  voiceover over B-roll of her hands and the product?"
- **Offer options when the user stalls.** People choose faster than they invent.
  "Vibe: (a) soft girl-next-door, (b) clean minimalist, (c) chaotic-funny UGC?"
- **Push for the specific.** "Nice product" is useless. "White ceramic mug, a
  couple's photo printed on the front, gift-for-partner angle" is a brief.
- **Know when to stop.** When you can picture the finished creative and write its
  copy without guessing, you're done. Over-grilling annoys people.
- **Always confirm.** Before generating, play the brief back in 3–5 lines and ask
  "build this, or adjust?" This is the last cheap moment to change direction.

## Question banks (pull what's relevant — don't ask all of them)

### For a character (a UGC "creator" persona)
- Niche / account angle — what does this person post about? What are they selling?
- Age range, gender, vibe (girl-next-door / polished / edgy / funny / expert)?
- Look: hair, build, signature style, wardrobe default, makeup level?
- Anything to **avoid**? (tattoos, sunglasses, heavy glam — becomes the negative)
- Real person (upload photos) or generated from scratch?
- One reference account or creator whose energy this should match?

### For an ad (static creative)
- Which product and which character? (both must already exist in the library)
- The angle/occasion — what's the hook? (Valentine's gift, "I was skeptical
  but…", problem→solution, unboxing)
- Character-led (creator using the product, organic-feeling) or product-hero
  (clean studio, no person)?
- Formats needed? (1:1 feed, 4:5 feed, 9:16 story/reel)
- Copy: headline, one-line subhead, CTA? Or should you draft options?
- How many variants for testing? What should differ between them (hook, setting,
  expression) so the A/B is actually informative?
- Brand rules — colours, tone, words to avoid?

## Turning the grill into a brief

Once confirmed, you produce a compact structured brief in-context (you are the
planner — no separate LLM call). That brief becomes:
- character-creator → args to `scripts/assets.py`
- ad-image → an **ad job JSON** for `scripts/run_ad.py` (schema in ad-image skill)

Keep the user's exact words for persona/angle/copy where you can — they know their
audience better than a paraphrase does.
