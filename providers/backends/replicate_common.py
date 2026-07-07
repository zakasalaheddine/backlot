"""Shared Replicate plumbing: run a model and save its output image(s) to disk.

Isolated here so both the image and (future) video backends share one code path
for auth, invocation, and downloading FileOutput/URL results.
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

from .. import config


def _client():
    import replicate  # imported lazily so `stub` mode needs no dependency

    config.require_replicate_token()
    # replicate reads REPLICATE_API_TOKEN from env automatically.
    return replicate


def _save_output(output, out_path: Path) -> Path:
    """Persist one Replicate image output to out_path.

    Replicate returns either a FileOutput object (has .read()/.url) or a plain
    URL string, depending on client version — handle both.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(output, "read"):  # FileOutput
        out_path.write_bytes(output.read())
    elif isinstance(output, str):  # URL
        urllib.request.urlretrieve(output, out_path)
    else:
        raise TypeError(f"Unexpected Replicate output type: {type(output)!r}")
    return out_path


def _run_and_save(model: str, input_dict: dict, out_path: Path) -> Path:
    """Run a Replicate model and save its single output to out_path."""
    replicate = _client()
    output = replicate.run(model, input=input_dict)
    # Some models return a list even for a single output.
    if isinstance(output, (list, tuple)):
        if not output:
            raise RuntimeError(f"{model} returned no output")
        output = output[0]
    return _save_output(output, out_path)


def run_image(model: str, input_dict: dict, out_path: Path) -> Path:
    """Run a single-image model and save the first output to out_path."""
    return _run_and_save(model, input_dict, out_path)


def run_video(model: str, input_dict: dict, out_path: Path) -> Path:
    """Run a video model and save its single output (.mp4) to out_path."""
    return _run_and_save(model, input_dict, out_path)
