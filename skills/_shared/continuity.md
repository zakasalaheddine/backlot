# Continuity — keeping a character identical across every generation

The single reason backlot exists: an account only feels like a real person if the
person is the *same* in every post. Consistency dies the moment you regenerate an
identity from text. So the rule is absolute:

**Never regenerate an identity. Always composite locked reference images into a
new scene.**

## Where continuity comes from

1. **Locked reference set.** A character is created once as a multi-angle
   turnaround (front, 3/4, profile, full body) saved in `assets/characters/<id>/refs/`.
   Every downstream generation passes these images as `image_input` to Nano-Banana
   so the model is *editing/compositing a known face*, not inventing one.

2. **Canonical descriptor.** `appearance.descriptor` in `character.json` is a fixed
   text description injected verbatim into every prompt. It backs up the pixels with
   words ("mid-20s, warm smile, cream knit, gold hoops") so drift has less room.

3. **Chained origination.** When creating the turnaround, angle 0 (front) is
   generated first, then fed as a reference into every later angle. This is handled
   by `providers.images.generate_reference(..., chain=True)`. Independent per-angle
   text-only generation produces four different people — chaining produces one
   person from four angles.

4. **The negative.** `appearance.negative` lists what this person never has
   (heavy makeup, sunglasses, tattoos). Pass it through on every generation.

## When extending a character (new wardrobe, expression, season)

Composite from the existing refs + descriptor — don't start over. Bump `version` in
the manifest. She should read as the same person in a new outfit, not a lookalike.

## Optional: cross-shot continuity (video, v1)

For seamless video flow you can feed clip N's last frame as an extra reference into
keyframe N+1. Off by default — distinct shots usually beat a morph. Left as a hook
for `_shared/seedance-motion.md`.
