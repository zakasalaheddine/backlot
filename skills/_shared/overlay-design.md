# Overlay design — Remotion templates for motion graphics

The polish layer: word-timed captions, hook cards, end cards, progress bars.
Rendered headlessly from `remotion/src/` via `scripts/render_overlay.py`;
ffmpeg (compose.py) stays the master assembler. Needs Node >= 18 — without it,
fall back to compose.py's built-in PIL captions and skip the rest.

## The templates

| Template | Kind | Use for |
|---|---|---|
| `KaraokeCaptions` | transparent `.mov` overlay | word-by-word captions synced to VO |
| `HookCard` | transparent `.mov` overlay | big hook text over the opening shot |
| `ProgressBar` | transparent `.mov` overlay | thin retention bar across the full reel |
| `EndCard` | opaque `.mp4` CLIP | branded closer: headline + CTA (+ logo) |

Transparent templates go in the compose timeline's `overlays` list; `EndCard`
is a normal clip — append it to `clips`. Props for each template are documented
in its `.tsx` file (`remotion/src/`).

## Karaoke captions from a VO — the whole flow

```bash
# 1. VO with word timings (audio_gen writes vo.timing.json next to the audio)
python ${CLAUDE_PLUGIN_ROOT}/scripts/audio_gen.py tts "the line" --character maya-01 --out out/reel/vo.mp3

# 2. Captions timed by that sidecar (duration comes from the timing file)
cat > out/reel/captions_job.json <<'EOF'
{
  "template": "KaraokeCaptions",
  "timing": "out/reel/vo.timing.json",
  "width": 1080, "height": 1920, "fps": 24,
  "out": "out/reel/overlays/captions.mov",
  "props": { "highlightColor": "#ffd400" }
}
EOF
python ${CLAUDE_PLUGIN_ROOT}/scripts/render_overlay.py out/reel/captions_job.json
```

**Alignment rule:** word times in the sidecar are relative to the VO's start —
give the overlay the SAME `at` as the VO in the compose timeline:

```json
"audio":   { "vo": [{ "src": "vo.mp3", "at": 0.3 }] },
"overlays": [{ "src": "overlays/captions.mov", "at": 0.3 }]
```

## Conventions

- **Match the overlay's width/height/fps to the compose master** (the `meta`
  of the timeline job) so nothing is rescaled at composite time.
- **ProgressBar's `duration_s` = the reel's total duration** so the bar
  completes exactly at the end. Duration comes from compose's manifest
  (`duration_s`) or the sum of clip lengths.
- **One brand, one look:** pass the same `accentColor`/`highlightColor` and CTA
  wording across every overlay in a campaign. Ask the user for brand colors
  once and reuse them; don't restyle per video.
- **Don't stack text layers**: karaoke captions OR PIL captions, never both;
  HookCard only while no caption page is showing (its beat usually precedes
  the VO).
- Re-renders are content-addressed (props + template source) — tweaking a
  color re-renders in seconds; `--force` to override.
