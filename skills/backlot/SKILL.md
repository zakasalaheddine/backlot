---
name: backlot
description: UGC content engine — build reusable characters, static ad images, and (soon) image-to-video UGC reels from one continuity-locked asset library, using Nano-Banana for images behind a swappable provider layer. Use this as the entry point whenever the user wants to run an end-to-end UGC/ad workflow, build "a set of ads", set up a content engine or ad campaign for a brand, isn't sure which step they need, or asks what backlot can do. Routes to the right sub-skill (character-creator, ad-image, ugc-video) and enforces that ads/videos only ever reference assets that already exist.
---

# backlot — router

backlot makes UGC creatives from **reusable, continuity-locked assets**. Everything
is either an *asset* (created once, locked, reused forever) or an *output* built by
compositing those assets into a new scene. That reference-locking is the whole trick
— it's what makes an account feel like one real person across every post.

```
        ASSET LIBRARY  (assets/characters, assets/products — locked, versioned)
                 │ referenced by ID
     ┌───────────┼───────────┐
     ▼           ▼           ▼
character-creator  ad-image   ugc-video (v1)
(produces assets) (static ads)(image→video)
```

## Route by intent

| The user wants to… | Go to |
|---|---|
| create a character / creator / persona / avatar / spokesperson; register a real product; evolve a character's look | **character-creator** |
| make an ad image, product ad, static/feed/carousel creative, a set of test variants, "a set of ads" | **ad-image** |
| make a UGC video, reel, video ad, animate an image | **ugc-video** *(v1 — not built yet; tell the user it's coming and offer ads instead)* |

Invoke the matching sub-skill (they trigger on their own descriptions too; this
router is for multi-step campaigns or when the user is unsure).

## Hard rule: assets exist before outputs
ad-image and ugc-video **require** a character and/or product in the library. Before
generating, check:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list
```
If the referenced asset isn't there, route to **character-creator** first — never
silently generate a throwaway identity or a fake product. Regeneration is where
consistency dies.

## Typical end-to-end ("build me a set of ads")
1. **character-creator** → lock the creator persona (and product if not yet in the
   library). Get back their IDs.
2. **ad-image** → grill the ad brief, emit an ad job JSON referencing those IDs, run
   `scripts/run_ad.py`, review the variants.
3. Iterate copy (cheap) or scenes (regenerates) until the set is ready to ship.

## Setup & providers
- Copy `.env.example` → `.env`, add `REPLICATE_API_TOKEN`. Images run on Nano-Banana
  via Replicate.
- The host is isolated in `providers/` — swapping to fal / another API is a backend
  change, invisible to these skills. See `providers/__init__.py`.
- No token yet, or want a free dry run? Prefix any command with
  `BACKLOT_IMAGE_PROVIDER=stub` to exercise the whole pipeline with placeholder
  images at zero cost.

Deeper prompt-craft lives in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/` (interview, continuity, nano-banana,
ad-layout, asset-library) — read the relevant file when you enter a sub-skill.
