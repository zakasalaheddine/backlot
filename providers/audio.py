"""Public audio API — voice-over, music, and SFX. Callers use ONLY these
functions; the model + backend per capability are resolved from the registry
(providers/models.json) with env overrides — see config.resolve(). Mirrors
images.py / video.py.

P1 ships the seam with a stub backend (silent WAVs sized realistically) so the
assembly pipeline can be built and tested; real backends (ElevenLabs) are P3.
"""
from __future__ import annotations

from pathlib import Path

from . import config


def tts(text: str, voice: str | None = None,
        out_path: str | Path = "out/vo.wav") -> Path:
    """Speak `text` as a voice-over take.

    voice: provider voice id (a character's locked voice — see character.json).
    Returns the saved audio path.
    """
    res = config.resolve("audio.tts")
    b = config.load_backend(res)
    return b.tts(text, voice, Path(out_path),
                 model=res["slug"], profile=res["profile"])


def music(mood: str, duration: int = 15,
          out_path: str | Path = "out/music.wav") -> Path:
    """Generate a music bed for `mood` (e.g. "cozy-upbeat"), `duration` seconds."""
    res = config.resolve("audio.music")
    b = config.load_backend(res)
    return b.music(mood, duration, Path(out_path),
                   model=res["slug"], profile=res["profile"])


def sfx(desc: str, duration: int = 2,
        out_path: str | Path = "out/sfx.wav") -> Path:
    """Generate a sound effect described by `desc`, `duration` seconds."""
    res = config.resolve("audio.sfx")
    b = config.load_backend(res)
    return b.sfx(desc, duration, Path(out_path),
                 model=res["slug"], profile=res["profile"])
