"""Public audio API — voice-over, music, and SFX. Callers use ONLY these
functions; the model + backend per capability are resolved from the registry
(providers/models.json) with env overrides — see config.resolve(). Mirrors
images.py / video.py. Default backend is ElevenLabs (needs ELEVENLABS_API_KEY);
BACKLOT_AUDIO_*_PROVIDER=stub runs at zero cost.

Backends pick the container (ElevenLabs .mp3, stub .wav) — the caller's suffix
is adjusted, so ALWAYS use the returned path. tts also writes a
`<stem>.timing.json` word-timing sidecar next to the audio.
"""
from __future__ import annotations

from pathlib import Path

from . import config


def tts(text: str, voice=None, out_path: str | Path = "out/vo.mp3") -> Path:
    """Speak `text` as a voice-over take.

    voice: a provider voice_id string, or a character.json voice block
    ({"voice_id": ..., "settings": {...}} — see assets.py set-voice). None uses
    the model profile's default voice. Returns the saved audio path.
    """
    res = config.resolve("audio.tts")
    b = config.load_backend(res)
    return b.tts(text, voice, Path(out_path),
                 model=res["slug"], profile=res["profile"])


def music(mood: str, duration: int = 15,
          out_path: str | Path = "out/music.mp3") -> Path:
    """Generate a music bed for `mood` (e.g. "cozy-upbeat"), `duration` seconds."""
    res = config.resolve("audio.music")
    b = config.load_backend(res)
    return b.music(mood, duration, Path(out_path),
                   model=res["slug"], profile=res["profile"])


def sfx(desc: str, duration: int = 2,
        out_path: str | Path = "out/sfx.mp3") -> Path:
    """Generate a sound effect described by `desc`, `duration` seconds."""
    res = config.resolve("audio.sfx")
    b = config.load_backend(res)
    return b.sfx(desc, duration, Path(out_path),
                 model=res["slug"], profile=res["profile"])
