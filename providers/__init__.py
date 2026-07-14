"""backlot provider layer — a thin, swappable abstraction over model hosts.

Public API (import these, never a backend directly):

    from providers import images, video, audio

    images.generate_reference(prompt, angles, aspect, out_dir)  -> list[Path]
    images.composite(spec, ref_imgs, aspect, out_path)          -> Path
    video.image_to_video(frame, motion, duration, out_path)     -> Path
    audio.tts(text, voice, out_path)                            -> Path
    audio.music(mood, duration, out_path)                       -> Path
    audio.sfx(desc, duration, out_path)                         -> Path

Which model serves each capability lives in providers/models.json (the
capability registry); config.resolve() picks the model + backend, honouring
BACKLOT_<CAPABILITY>_MODEL / _PROVIDER env overrides. To move a capability to a
new host, add a backend in providers/backends/ and point the registry (or the
env var) at it. Nothing above this layer changes. Inspect or swap from the CLI:
scripts/models.py list|inspect|set.
"""
