---
description: Generate static UGC / product ad creatives (composited + copy overlay, multi-format, variants)
argument-hint: "[brief: product + character + angle, e.g. 'maya-01 holding heart-mug-01, Valentine's']"
---

Use the **ad-image** skill to build a set of ad creatives.

$ARGUMENTS

First confirm the referenced character/product exist (`python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list`)
— if not, route to character-creator. Then grill the ad brief per
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md`, emit an ad job JSON, and run `scripts/run_ad.py`.
Show the user the resulting `ad_*.png` variants.
