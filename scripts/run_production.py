#!/usr/bin/env python3
"""Production runner — one production JSON -> a finished multi-shot reel.

The full DAG, every stage content-addressed (re-runs only redo what changed):

  1. keyframes   composite each shot's keyframe from LOCKED library refs
  2. clips       animate each keyframe (run_video, motion presets)
  3. audio       VO per shot in the character's locked voice (+ word timings),
                 one music bed for the whole reel
  4. overlays    karaoke captions per VO, hook cards, progress bar, end card
                 (Remotion; degrades to burned PIL captions without Node)
  5. assemble    compose.py -> master_<fmt>.mp4 per requested format

Production JSON:
{
  "meta": {
    "brand": "EluNoire",
    "character": "maya-01",              // owns identity refs + locked voice
    "product": "heart-mug-01",           // optional
    "aspect": "9:16", "formats": ["9:16"], "fps": 24,
    "music": { "mood": "cozy-upbeat lofi, warm", "gain_db": -8 },  // optional
    "accent_color": "#ffd400",
    "captions": "karaoke" | "pil" | "none",   // default: karaoke if Node, else pil
    "progress_bar": true
  },
  "shots": [
    {
      "id": "s1", "beat": "hook",
      "keyframe": { "prompt": "...", "use_refs": ["maya-01", "heart-mug-01"],
                    "negative": "..." },
      "motion":   { "camera": "dolly-in", "action": null, "motion": "",
                    "duration": 5 },     // same fields as a ugc-video clip
      "vo": "Okay so I panic-ordered this...",   // optional
      "hook": "POV: you forgot Valentine's"      // optional HookCard overlay
    }
  ],
  "end_card": { "headline": "...", "cta": "Shop now", "subhead": "",
                "duration_s": 3 }                // optional
}

Usage (from repo root):
    python scripts/run_production.py production.json [--out out/<name>] [--force]
    python scripts/run_production.py production.json --force-shot s2   # regen one shot

Zero-cost dry run of the WHOLE pipeline (animatic: held keyframes, silent audio):
    BACKLOT_IMAGE_PROVIDER=stub BACKLOT_VIDEO_PROVIDER=stub \
    BACKLOT_AUDIO_TTS_PROVIDER=stub BACKLOT_AUDIO_MUSIC_PROVIDER=stub \
    python scripts/run_production.py production.json
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

from providers import images, audio, config  # noqa: E402
import assets  # noqa: E402
import run_video  # noqa: E402
import compose as compose_mod  # noqa: E402
import render_overlay  # noqa: E402


def _say(msg: str) -> None:
    print(f"[production] {msg}", file=sys.stderr)


def _sha(*parts: str, files: list[Path] = ()) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode())
        h.update(b"\x00")
    for f in files:
        h.update(hashlib.sha256(Path(f).read_bytes()).digest())
    return h.hexdigest()[:16]


def _cached(artifact: Path, want: str, force: bool) -> bool:
    hash_path = artifact.parent / (artifact.name + ".hash")
    have = hash_path.read_text().strip() if hash_path.exists() else ""
    return not force and artifact.exists() and have == want


def _stamp(artifact: Path, want: str) -> None:
    (artifact.parent / (artifact.name + ".hash")).write_text(want)


def _duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {out.stderr.strip()}")
    return float(out.stdout.strip())


# ---------------------------------------------------------------- stages ----

def stage_keyframes(prod: dict, out_dir: Path, force_all: bool,
                    force_shots: set) -> dict:
    aspect = prod["meta"].get("aspect", "9:16")
    frames = {}
    for shot in prod["shots"]:
        sid = shot["id"]
        kf = shot["keyframe"]
        ref_paths = []
        for asset_id in kf.get("use_refs", []):
            ref_paths.extend(assets.resolve_refs(asset_id))
        out = out_dir / "shots" / sid / "keyframe.png"
        force = force_all or sid in force_shots
        want = _sha(kf["prompt"], kf.get("negative", ""), aspect,
                    files=ref_paths)
        if not _cached(out, want, force):
            _say(f"keyframe {sid}: compositing")
            images.composite({"prompt": kf["prompt"],
                              "negative": kf.get("negative", "")},
                             ref_paths, aspect=aspect, out_path=out)
            _stamp(out, want)
        else:
            _say(f"keyframe {sid}: cached")
        frames[sid] = out
    return frames


def stage_clips(prod: dict, frames: dict, out_dir: Path, force_all: bool,
                force_shots: set) -> dict:
    """Emit a run_video job for all shots and run it (its cache is per clip)."""
    clips_job = {"meta": {"brand": prod["meta"].get("brand", "")}, "clips": []}
    for shot in prod["shots"]:
        motion = dict(shot.get("motion") or {})
        clip = {"id": shot["id"], "frame": str(frames[shot["id"]].resolve())}
        for key in ("camera", "action", "motion", "negative", "duration",
                    "resolution", "seed", "camera_fixed", "audio"):
            if motion.get(key) is not None:
                clip[key] = motion[key]
        clips_job["clips"].append(clip)
    job_path = out_dir / "clips_job.json"
    job_path.write_text(json.dumps(clips_job, indent=2) + "\n")

    if force_shots and not force_all:
        # run_video's cache is hash-based: drop the targeted shots' hashes.
        for sid in force_shots:
            hp = out_dir / "clips" / sid / "clip.hash"
            if hp.exists():
                hp.unlink()
    _say("clips: rendering (cached clips skip)")
    manifest = run_video.run(job_path, out_dir / "clips", force_all)
    return {c["clip"]: Path(c["mp4"]) for c in manifest["outputs"]}


def stage_audio(prod: dict, total: float, out_dir: Path, vo_starts: dict,
                force: bool) -> dict:
    """VO per shot (locked character voice) + one music bed. Returns the
    compose `audio` block pieces + timing sidecar paths."""
    meta = prod["meta"]
    adir = out_dir / "audio"
    result = {"vo": [], "timings": {}, "music": None}

    voice = None
    char_id = meta.get("character", "")
    if char_id:
        voice = assets.resolve_voice(char_id)
    tts_res = config.resolve("audio.tts")
    vo_shots = [s for s in prod["shots"] if (s.get("vo") or "").strip()]
    if vo_shots and char_id and voice is None:
        _say(f"warning: character {char_id!r} has no locked voice — using the "
             f"model default. Lock one with assets.py set-voice for continuity.")

    for shot in vo_shots:
        sid, text = shot["id"], shot["vo"].strip()
        out = adir / f"vo_{sid}.mp3"
        want = _sha(text, json.dumps(voice or {}, sort_keys=True),
                    tts_res["slug"], tts_res["backend"])
        hash_path = adir / f"vo_{sid}.hash"  # backend picks .mp3/.wav — hash by stem
        have = hash_path.read_text().strip() if hash_path.exists() else ""
        existing = list(adir.glob(f"vo_{sid}.mp3")) + list(adir.glob(f"vo_{sid}.wav"))
        if force or have != want or not existing:
            _say(f"vo {sid}: speaking ({len(text.split())} words)")
            path = audio.tts(text, voice=voice, out_path=out)
            hash_path.write_text(want)
        else:
            path = existing[0]
            _say(f"vo {sid}: cached")
        timing = path.parent / (path.stem + ".timing.json")
        result["vo"].append({"src": str(path), "at": vo_starts[sid]})
        result["timings"][sid] = timing if timing.exists() else None

    music = meta.get("music")
    if music and music.get("mood"):
        mus_res = config.resolve("audio.music")
        out = adir / "music.mp3"
        want = _sha(music["mood"], f"{int(total)}", mus_res["slug"],
                    mus_res["backend"])
        hash_path = adir / "music.hash"
        have = hash_path.read_text().strip() if hash_path.exists() else ""
        existing = list(adir.glob("music.mp3")) + list(adir.glob("music.wav"))
        if force or have != want or not existing:
            _say(f"music: generating {int(total)}s bed")
            path = audio.music(music["mood"], duration=int(total) + 1, out_path=out)
            hash_path.write_text(want)
        else:
            path = existing[0]
            _say("music: cached")
        result["music"] = {"src": str(path),
                           "gain_db": music.get("gain_db", -8),
                           "duck": music.get("duck", True)}
    return result


def stage_overlays(prod: dict, dims: tuple, fps: int, total: float,
                   shot_starts: dict, vo_starts: dict, timings: dict,
                   out_dir: Path, force: bool) -> tuple[list, Path | None]:
    """Render Remotion overlays. Returns (compose overlays list, end card clip)."""
    meta = prod["meta"]
    odir = out_dir / "overlays"
    odir.mkdir(parents=True, exist_ok=True)
    accent = meta.get("accent_color", "#ffd400")
    w, h = dims
    overlays = []

    def render(name: str, job: dict) -> Path:
        job_path = odir / f"{name}_job.json"
        job_path.write_text(json.dumps(job, indent=2) + "\n")
        res = render_overlay.render(job_path, force)
        _say(f"overlay {name}: {'rendered' if res['rendered'] else 'cached'}")
        return Path(res["out"])

    for shot in prod["shots"]:
        sid = shot["id"]
        timing = timings.get(sid)
        if timing:
            out = render(f"captions_{sid}", {
                "template": "KaraokeCaptions",
                "timing": str(timing.resolve()),
                "width": w, "height": h, "fps": fps,
                "out": str(odir / f"captions_{sid}.mov"),
                "props": {"highlightColor": accent},
            })
            overlays.append({"src": str(out), "at": vo_starts[sid]})
        if (shot.get("hook") or "").strip():
            dur = min(2.2, float((shot.get("motion") or {}).get("duration", 5)))
            out = render(f"hook_{sid}", {
                "template": "HookCard",
                "width": w, "height": h, "fps": fps, "duration_s": dur,
                "out": str(odir / f"hook_{sid}.mov"),
                "props": {"text": shot["hook"].strip()},
            })
            overlays.append({"src": str(out), "at": shot_starts[sid]})

    if meta.get("progress_bar", True):
        out = render("progress", {
            "template": "ProgressBar",
            "width": w, "height": h, "fps": fps, "duration_s": round(total, 3),
            "out": str(odir / "progress.mov"),
            "props": {"color": accent},
        })
        overlays.append({"src": str(out), "at": 0.0})

    end_clip = None
    end = prod.get("end_card")
    if end:
        end_clip = render("endcard", {
            "template": "EndCard",
            "width": w, "height": h, "fps": fps,
            "duration_s": float(end.get("duration_s", 3)),
            "out": str(odir / "endcard.mp4"),
            "props": {"headline": end.get("headline", ""),
                      "subhead": end.get("subhead", ""),
                      "cta": end.get("cta", "Shop now"),
                      "brand": meta.get("brand", ""),
                      "accentColor": accent},
        })
    return overlays, end_clip


# ------------------------------------------------------------------ run ----

def run(prod_path: Path, out_dir: Path, force: bool,
        force_shots: set = frozenset()) -> dict:
    prod = json.loads(prod_path.read_text())
    meta = prod.get("meta", {})
    if not prod.get("shots"):
        raise ValueError("production has no shots")
    seen = set()
    for s in prod["shots"]:
        if s["id"] in seen:
            raise ValueError(f"duplicate shot id {s['id']!r}")
        seen.add(s["id"])
    unknown = force_shots - seen
    if unknown:
        raise ValueError(f"--force-shot: no such shot(s): {sorted(unknown)}")

    aspect = meta.get("aspect", "9:16")
    fps = int(meta.get("fps", 24))
    dims = compose_mod.FORMAT_DIMS[aspect]
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1-2. keyframes -> clips
    frames = stage_keyframes(prod, out_dir, force, force_shots)
    clips = stage_clips(prod, frames, out_dir, force, force_shots)

    # shot start times from the REAL rendered durations
    shot_starts, vo_starts, t = {}, {}, 0.0
    for shot in prod["shots"]:
        shot_starts[shot["id"]] = round(t, 3)
        vo_starts[shot["id"]] = round(t + 0.15, 3)  # small lead-in
        t += _duration(clips[shot["id"]])
    end_dur = float((prod.get("end_card") or {}).get("duration_s", 0) or 0)
    total = t + end_dur

    # 3. audio
    audio_block = stage_audio(prod, total, out_dir, vo_starts, force)

    # 4. overlays (Remotion) or PIL caption fallback
    captions_mode = meta.get("captions") or (
        "karaoke" if shutil.which("node") else "pil")
    pil_captions, overlays, end_clip = [], [], None
    if captions_mode == "karaoke" and shutil.which("node") is None:
        _say("captions: node not found — falling back to burned PIL captions")
        captions_mode = "pil"
    if captions_mode == "karaoke" or prod.get("end_card") \
            or meta.get("progress_bar", True):
        if shutil.which("node"):
            timings = audio_block["timings"] if captions_mode == "karaoke" else {}
            overlays, end_clip = stage_overlays(
                prod, dims, fps, total, shot_starts, vo_starts, timings,
                out_dir, force)
        elif prod.get("end_card"):
            _say("end card: skipped (needs node)")
    if captions_mode == "pil":
        for shot in prod["shots"]:
            timing = audio_block["timings"].get(shot["id"])
            if (shot.get("vo") or "").strip() and timing:
                dur = json.loads(Path(timing).read_text())["duration_s"]
                at = vo_starts[shot["id"]]
                pil_captions.append({"text": shot["vo"].strip(),
                                     "start": at, "end": round(at + dur, 3)})

    # 5. assemble
    timeline = {
        "meta": {"brand": meta.get("brand", ""), "aspect": aspect,
                 "formats": meta.get("formats", [aspect]), "fps": fps},
        "clips": [{"id": s["id"], "src": str(clips[s["id"]].resolve())}
                  for s in prod["shots"]],
    }
    if end_clip is not None:
        timeline["clips"].append({"id": "endcard", "src": str(end_clip.resolve())})
    if audio_block["vo"] or audio_block["music"]:
        timeline["audio"] = {"vo": audio_block["vo"], "keep_clip_audio": False}
        if audio_block["music"]:
            timeline["audio"]["music"] = audio_block["music"]
    if pil_captions:
        timeline["captions"] = pil_captions
    if overlays:
        timeline["overlays"] = overlays
    timeline_path = out_dir / "timeline.json"
    timeline_path.write_text(json.dumps(timeline, indent=2) + "\n")

    _say("assemble: composing masters")
    assembled = compose_mod.run(timeline_path, out_dir / "assemble", force)

    manifest = {
        "production": str(prod_path),
        "meta": meta,
        "duration_s": assembled["duration_s"],
        "captions": captions_mode,
        "shots": [{"id": s["id"], "beat": s.get("beat", ""),
                   "keyframe": str(frames[s["id"]]),
                   "clip": str(clips[s["id"]]),
                   "vo_at": vo_starts[s["id"]] if (s.get("vo") or "").strip() else None}
                  for s in prod["shots"]],
        "masters": assembled["masters"],
    }
    (out_dir / "production_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    p = argparse.ArgumentParser(description="Run a full reel production")
    p.add_argument("production", help="path to production JSON")
    p.add_argument("--out", default="", help="output dir (default out/<stem>)")
    p.add_argument("--force", action="store_true", help="rebuild everything")
    p.add_argument("--force-shot", action="append", default=[],
                   help="regenerate one shot's keyframe+clip (repeatable)")
    a = p.parse_args()
    prod_path = Path(a.production)
    out_dir = Path(a.out) if a.out else Path.cwd() / "out" / prod_path.stem
    manifest = run(prod_path, out_dir, a.force, set(a.force_shot))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
