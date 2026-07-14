---
description: Produce a complete UGC video ad — shots, VO, music, captions, end card — from one brief
argument-hint: "[brief: character + product + angle, e.g. 'maya-01 with heart-mug-01, Valentine's panic gift']"
---

Use the **ugc-reel** skill to produce a finished reel end-to-end.

$ARGUMENTS

First confirm the referenced character/product exist
(`python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list`) — if not, route to
character-creator (lock a voice too if the reel has VO). Then grill the brief
per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/assembly.md`, emit a production JSON,
dry-run it as a zero-cost animatic for approval, and run
`scripts/run_production.py` for real. Iterate single shots with
`scripts/render_shot.py`.
