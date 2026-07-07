---
description: List and inspect the backlot asset library (characters & products)
argument-hint: "[optional asset-id to inspect]"
---

Show the backlot asset library.

Run:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py list
```

If the user names a specific asset in "$ARGUMENTS", inspect it instead:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/assets.py get --id <id>
```

Summarize what characters and products exist, their ids, ref counts, and versions, so
the user knows what they can reference in an ad or video.
