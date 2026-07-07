---
description: Create or update a reusable, continuity-locked UGC character or product asset
argument-hint: "[persona/product description, or 'update <asset-id>']"
---

Use the **character-creator** skill to create or update a backlot asset.

$ARGUMENTS

Grill the user for the persona (or product) per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/interview.md`, then
originate a locked, multi-angle character with `scripts/assets.py` (or ingest real
photos / register a product). Report the assigned asset id when done.
