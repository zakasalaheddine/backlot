#!/usr/bin/env python3
"""Compose runner — timeline job JSON -> assembled master video(s) via ffmpeg.

Takes the clips run_video.py produced and assembles a publishable video:
  1. Normalize every clip to a uniform intermediate (fps, primary-format size,
     yuv420p, 48 kHz stereo — silent track padded in if the clip has none).
  2. Concat the normalized clips (hard cuts; transitions are a later feature).
  3. Mix the audio track: VO takes placed at offsets + music bed with sidechain
     ducking under the VO, loudness-normalized to -14 LUFS (audio block optional
     — without one, clip audio passes through).
  4. Burn captions: each caption is a deterministic PIL transparent PNG
     (text_overlay.render_caption — a model never draws text) overlaid for its
     time window. Alpha overlay videos (Remotion, P4) composite the same way.
  5. Export a master per requested format (9:16 native; others center-cropped).

Every stage is content-addressed (hash of inputs + params) so re-runs skip
finished work — a copy tweak re-burns captions without re-encoding clips.

Timeline job JSON:
{
  "meta": {"brand": "...", "aspect": "9:16", "formats": ["9:16", "1:1"], "fps": 24},
  "clips": [
    {"id": "c1", "src": "out/reel/c1/clip.mp4"},
    {"id": "c2", "src": "out/reel/c2/clip.mp4", "trim": {"start": 0, "end": 4.5}}
  ],
  "audio": {                                  // optional
    "vo":    [{"src": "vo_hook.wav", "at": 0.0}],
    "music": {"src": "bed.wav", "gain_db": -6, "duck": true},
    "keep_clip_audio": false
  },
  "captions": [{"text": "POV: ...", "start": 0.0, "end": 2.2}],   // optional
  "overlays": [{"src": "captions.mov", "at": 0.0}]                // optional, alpha video
}

Usage (from repo root):
    python scripts/compose.py path/to/timeline.json [--out out/<name>] [--force]

Requires the ffmpeg + ffprobe binaries (brew install ffmpeg / apt install ffmpeg).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from text_overlay import render_caption  # noqa: E402

# Canonical export dimensions per format.
FORMAT_DIMS = {
    "9:16": (1080, 1920), "1:1": (1080, 1080),
    "4:5": (1080, 1350), "16:9": (1920, 1080),
}


def _require_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            raise RuntimeError(
                f"{tool} not found on PATH. Install it first: brew install ffmpeg "
                f"(macOS) or apt install ffmpeg (Linux)."
            )


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        raise RuntimeError(f"ffmpeg failed ({' '.join(cmd[:6])} ...):\n{tail}")


def _probe(path: Path, *entries: str) -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", *entries, "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {out.stderr.strip()}")
    return out.stdout.strip()


def _duration(path: Path) -> float:
    return float(_probe(path, "-show_entries", "format=duration"))


def _has_audio(path: Path) -> bool:
    return bool(_probe(path, "-select_streams", "a",
                       "-show_entries", "stream=codec_type"))


def _sha(*parts: str, files: list[Path] = ()) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\x00")
    for f in files:
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()[:16]


def _fresh(artifact: Path, want: str, force: bool) -> bool:
    """True if `artifact` exists and was built from the same inputs."""
    hash_path = artifact.with_suffix(artifact.suffix + ".hash")
    have = hash_path.read_text().strip() if hash_path.exists() else ""
    return not force and artifact.exists() and have == want


def _stamp(artifact: Path, want: str) -> None:
    artifact.with_suffix(artifact.suffix + ".hash").write_text(want)


def _resolve(raw: str, job_path: Path) -> Path:
    p = Path(raw)
    if p.exists():
        return p
    alt = job_path.parent / raw
    return alt if alt.exists() else p  # return original for a clean error msg


def _crop_chain(src_w: int, src_h: int, fmt: str) -> str:
    """Center-crop the primary-format frame to `fmt`, then scale to canonical."""
    fw, fh = FORMAT_DIMS[fmt]
    r = fw / fh
    if src_w / src_h > r:
        cw, ch = int(src_h * r) // 2 * 2, src_h
    else:
        cw, ch = src_w, int(src_w / r) // 2 * 2
    return f"crop={cw}:{ch},scale={fw}:{fh}"


# ---------------------------------------------------------------- stages ----

def normalize_clip(src: Path, clip: dict, dims: tuple, fps: int,
                   out: Path, force: bool) -> str:
    """Re-encode one clip to the uniform intermediate. Returns its hash."""
    trim = clip.get("trim") or {}
    start, end = trim.get("start"), trim.get("end")
    if start is not None and end is not None and end <= start:
        raise ValueError(f"clip {clip['id']!r}: trim end must be > start")
    want = _sha(json.dumps([dims, fps, start, end]), files=[src])
    if _fresh(out, want, force):
        return want

    w, h = dims
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},fps={fps},format=yuv420p")
    cmd = ["ffmpeg", "-y", "-i", str(src)]
    if not _has_audio(src):
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        audio_map, shortest = "1:a:0", True
    else:
        audio_map, shortest = "0:a:0", False
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]
    cmd += ["-vf", vf, "-map", "0:v:0", "-map", audio_map,
            "-c:v", "libx264", "-crf", "18", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    if shortest:
        cmd += ["-shortest"]
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd + [str(out)])
    _stamp(out, want)
    return want


def concat_clips(norm_paths: list[Path], norm_hashes: list[str],
                 out: Path, force: bool) -> str:
    """Concat the uniform intermediates (stream copy — same encode params)."""
    want = _sha(*norm_hashes)
    if _fresh(out, want, force):
        return want
    lst = out.parent / "concat_list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in norm_paths))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
          "-c", "copy", str(out)])
    _stamp(out, want)
    return want


def mix_audio(audio: dict, concat: Path, total: float, job_path: Path,
              out: Path, force: bool) -> str:
    """Build the mixed audio track (VO + ducked music [+ clip audio]) -> wav."""
    vo = audio.get("vo") or []
    music = audio.get("music")
    keep_clip = bool(audio.get("keep_clip_audio", False))

    vo_paths = [_resolve(v["src"], job_path) for v in vo]
    music_path = _resolve(music["src"], job_path) if music else None
    for p in vo_paths + ([music_path] if music_path else []):
        if not p.exists():
            raise FileNotFoundError(f"audio source not found: {p}")

    want = _sha(json.dumps(audio, sort_keys=True), f"{total:.3f}",
                files=vo_paths + ([music_path] if music_path else [])
                + ([concat] if keep_clip else []))
    if _fresh(out, want, force):
        return want

    cmd, filters, idx = ["ffmpeg", "-y"], [], 0
    fmt = "aresample=48000,aformat=channel_layouts=stereo"

    vo_labels = []
    for v, p in zip(vo, vo_paths):
        cmd += ["-i", str(p)]
        ms = int(round(float(v.get("at", 0)) * 1000))
        filters.append(f"[{idx}:a]{fmt},adelay={ms}:all=1[vo{idx}]")
        vo_labels.append(f"[vo{idx}]")
        idx += 1
    vo_label = None
    if vo_labels:
        if len(vo_labels) > 1:
            filters.append(f"{''.join(vo_labels)}amix=inputs={len(vo_labels)}:"
                           f"duration=longest:normalize=0[vomix]")
            vo_label = "[vomix]"
        else:
            vo_label = vo_labels[0]
        filters.append(f"{vo_label}apad=whole_dur={total:.3f},"
                       f"atrim=0:{total:.3f}[vop]")
        vo_label = "[vop]"

    music_label = None
    if music_path:
        cmd += ["-stream_loop", "-1", "-i", str(music_path)]
        gain = float(music.get("gain_db", -6))
        filters.append(f"[{idx}:a]{fmt},atrim=0:{total:.3f},"
                       f"volume={gain}dB[mus]")
        music_label = "[mus]"
        idx += 1
        if vo_label and music.get("duck", True):
            filters.append(f"{vo_label}asplit=2[vok][vosc]")
            filters.append(f"[mus][vosc]sidechaincompress=threshold=0.03:"
                           f"ratio=8:attack=20:release=400[musd]")
            vo_label, music_label = "[vok]", "[musd]"

    clip_label = None
    if keep_clip:
        cmd += ["-i", str(concat)]
        filters.append(f"[{idx}:a]{fmt}[clipa]")
        clip_label = "[clipa]"
        idx += 1

    tracks = [x for x in (vo_label, music_label, clip_label) if x]
    if not tracks:
        raise ValueError("audio block given but has no vo/music/keep_clip_audio")
    if len(tracks) > 1:
        filters.append(f"{''.join(tracks)}amix=inputs={len(tracks)}:"
                       f"duration=first:normalize=0[premix]")
        final_in = "[premix]"
    else:
        final_in = tracks[0]
    filters.append(f"{final_in}loudnorm=I=-14:TP=-1.5:LRA=11,"
                   f"aresample=48000[aout]")

    out.parent.mkdir(parents=True, exist_ok=True)
    _run(cmd + ["-filter_complex", ";".join(filters), "-map", "[aout]",
                "-c:a", "pcm_s16le", "-t", f"{total:.3f}", str(out)])
    _stamp(out, want)
    return want


def export_master(concat: Path, concat_hash: str, mix: Path | None,
                  mix_hash: str, captions: list, overlays: list, fmt: str,
                  total: float, job_path: Path, work: Path, out: Path,
                  force: bool) -> bool:
    """Crop/scale to `fmt`, overlay captions + alpha videos, mux audio.
    Returns True if (re)rendered, False if cached."""
    overlay_paths = [_resolve(o["src"], job_path) for o in overlays]
    for p in overlay_paths:
        if not p.exists():
            raise FileNotFoundError(f"overlay source not found: {p}")

    want = _sha(concat_hash, mix_hash, fmt,
                json.dumps(captions, sort_keys=True),
                json.dumps([o.get("at", 0) for o in overlays]),
                files=overlay_paths)
    if _fresh(out, want, force):
        return False

    fw, fh = FORMAT_DIMS[fmt]
    src_w, src_h = (int(x) for x in _probe(
        concat, "-select_streams", "v:0",
        "-show_entries", "stream=width,height").split(","))

    cmd = ["ffmpeg", "-y", "-i", str(concat)]
    filters = [f"[0:v]{_crop_chain(src_w, src_h, fmt)}[v0]"]
    idx, vlabel = 1, "[v0]"

    cap_dir = work / "captions" / fmt.replace(":", "x")
    for n, cap in enumerate(captions):
        png = render_caption(cap["text"], fw, fh, cap_dir / f"cap_{n:02d}.png")
        cmd += ["-loop", "1", "-t", f"{float(cap['end']):.3f}", "-i", str(png)]
        filters.append(
            f"{vlabel}[{idx}:v]overlay=0:0:eof_action=pass:"
            f"enable='between(t,{float(cap['start']):.3f},"
            f"{float(cap['end']):.3f})'[v{idx}]")
        vlabel = f"[v{idx}]"
        idx += 1

    for o, p in zip(overlays, overlay_paths):
        at = float(o.get("at", 0))
        cmd += ["-itsoffset", f"{at:.3f}"]
        # ffmpeg's native VP9 decoder silently drops the alpha plane; WebM
        # overlays must be decoded with libvpx to stay transparent.
        if p.suffix.lower() == ".webm":
            cmd += ["-c:v", "libvpx-vp9"]
        cmd += ["-i", str(p)]
        filters.append(f"{vlabel}[{idx}:v]overlay=0:0:eof_action=pass:"
                       f"enable='gte(t,{at:.3f})'[v{idx}]")
        vlabel = f"[v{idx}]"
        idx += 1

    if mix is not None:
        cmd += ["-i", str(mix)]
        audio_args = ["-map", f"{idx}:a", "-c:a", "aac", "-b:a", "192k"]
    else:
        audio_args = ["-map", "0:a", "-c:a", "copy"]

    _run(cmd + ["-filter_complex", ";".join(filters), "-map", vlabel,
                *audio_args, "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-t", f"{total:.3f}", str(out)])
    _stamp(out, want)
    return True


# ------------------------------------------------------------------ run ----

def run(job_path: Path, out_dir: Path, force: bool) -> dict:
    _require_ffmpeg()
    job = json.loads(job_path.read_text())
    meta = job.get("meta", {})
    aspect = meta.get("aspect", "9:16")
    formats = meta.get("formats", [aspect])
    fps = int(meta.get("fps", 24))
    for f in [aspect] + formats:
        if f not in FORMAT_DIMS:
            raise ValueError(f"unknown format {f!r}; known: {list(FORMAT_DIMS)}")
    if not job.get("clips"):
        raise ValueError("timeline has no clips")

    work = out_dir / "work"
    dims = FORMAT_DIMS[aspect]

    norm_paths, norm_hashes = [], []
    for clip in job["clips"]:
        src = _resolve(clip["src"], job_path)
        if not src.exists():
            raise FileNotFoundError(f"clip {clip['id']!r}: source not found: {clip['src']}")
        out = work / "norm" / f"{clip['id']}.mp4"
        norm_hashes.append(normalize_clip(src, clip, dims, fps, out, force))
        norm_paths.append(out)

    concat = work / "concat.mp4"
    concat_hash = concat_clips(norm_paths, norm_hashes, concat, force)
    total = _duration(concat)

    audio = job.get("audio") or {}
    has_mix = bool(audio.get("vo") or audio.get("music")
                   or audio.get("keep_clip_audio"))
    mix, mix_hash = None, "passthrough"
    if has_mix:
        mix = work / "mix.wav"
        mix_hash = mix_audio(audio, concat, total, job_path, mix, force)

    masters = []
    for fmt in formats:
        out = out_dir / f"master_{fmt.replace(':', 'x')}.mp4"
        rendered = export_master(concat, concat_hash, mix, mix_hash,
                                 job.get("captions") or [],
                                 job.get("overlays") or [], fmt, total,
                                 job_path, work, out, force)
        masters.append({"format": fmt, "mp4": str(out), "rendered": rendered})

    manifest = {"job": str(job_path), "meta": meta,
                "duration_s": round(total, 3), "masters": masters}
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Assemble clips into master video(s)")
    p.add_argument("job", help="path to timeline job JSON")
    p.add_argument("--out", default="", help="output dir (default out/<job-stem>)")
    p.add_argument("--force", action="store_true", help="ignore cache, rebuild all")
    a = p.parse_args()
    job_path = Path(a.job)
    out_dir = Path(a.out) if a.out else Path.cwd() / "out" / job_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = run(job_path, out_dir, a.force)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
