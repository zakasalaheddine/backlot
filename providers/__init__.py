"""backlot provider layer — a thin, swappable abstraction over model hosts.

Public API (import these, never a backend directly):

    from providers import images, video

    images.generate_reference(prompt, angles, aspect, out_dir)  -> list[Path]
    images.composite(spec, ref_imgs, aspect, out_path)          -> Path
    video.image_to_video(frame, motion, duration_s, out_path)   -> Path   # v1

The host (Replicate today) is selected in config.py from env. To move a
capability to a new host, add a backend in providers/backends/ and point the
corresponding BACKLOT_*_PROVIDER at it. Nothing above this layer changes.
"""
