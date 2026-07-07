# Ad layout — composition, copy hierarchy, and why text is a separate layer

An ad is "powerful" instead of "AI-sloppy" for two reasons: the *real* product and
a *consistent* character are composited in (not hallucinated), and the copy is
**burned in deterministically** rather than drawn by the model. This file holds the
rules the ad-image skill and `scripts/run_ad.py` follow.

## Text is never drawn by the model

Image models warp letters. So headline/subhead/CTA come from Claude (you) as clean
strings and are rendered as a crisp layer by `scripts/text_overlay.py` — real fonts,
a contrast scrim, a real CTA button. Deterministic: same copy → same pixels. The
keyframe the model makes should leave *room* for copy (see safe zones), not contain
any.

## Copy hierarchy

1. **Headline** — the hook. Short, high-contrast, top of the reading order. This is
   what stops the scroll. 3–7 words.
2. **Subhead** — the supporting line. One sentence, the payoff or proof.
3. **CTA** — the action, as a button. "Shop now", "Get yours", "Try it".

Write the headline to earn attention, the subhead to earn the click, the CTA to make
it easy. Keep it tight — reels and feeds are skimmed.

## Safe zones per format

`text_overlay.py` anchors copy to `top` or `bottom`. Choose so copy doesn't cover the
subject's face or the product, and stays clear of platform UI:
- **1:1 / 4:5 (feed):** bottom anchor is usually safest; keep clear of the very
  bottom where captions/handles sit.
- **9:16 (story/reel):** keep copy in the **middle band** — the top ~15% and bottom
  ~20% are covered by platform UI (profile, caption, buttons). Prefer bottom anchor
  but not flush to the edge; the overlay's margins handle most of this.

## Composition

- **Candid and in-motion, not posed.** Default to a caught-mid-moment feel — a verb
  (laughing, turning, reaching, mirror-selfie, walking) and a loose, slightly
  off-center phone-camera crop. Stiff, centered, standing-and-smiling frames read as
  AI. See "Make it feel alive" in `nano-banana.md` for the direction to bake into
  each keyframe prompt.
- Give the subject/product clear negative space where the copy will land — a busy
  frame edge-to-edge leaves nowhere for the headline to breathe. A candid pose can
  still leave the anchored copy zone (top/bottom) open.
- Contrast: the scrim guarantees legibility, but a keyframe that's already dark or
  bright where the copy sits looks more intentional than relying on the scrim alone.
- One idea per variant. If you're testing hooks, change the hook and keep the scene;
  if testing scenes, keep the hook. Don't change everything at once or the A/B tells
  you nothing.

## Two ad modes

- **Character-led (UGC):** the creator holding/using the product — feels like an
  organic post. Pass both character and product refs.
- **Product-hero (studio):** clean product on a set, no character. Pass only the
  product ref; prompt for studio light and a simple surface.
