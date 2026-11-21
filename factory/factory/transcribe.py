"""Transcriber adapters. Returns a transcript block, or None when no transcript can be made."""
from __future__ import annotations

import shutil
import subprocess
from typing import Callable

from factory.config import Config


def _block(path, source: str, trust: str, text: str) -> dict:
    return {"path": str(path), "source": source, "trust": trust, "text": text}


def transcribe(reel: dict, cfg: Config, runner: Callable = subprocess.run, which: Callable = shutil.which) -> dict | None:
    folder = cfg.reel_dir(reel["id"])
    manual = folder / "transcript.txt"
    # A person or the browser tool dropped it in: always wins, and is trusted.
    if manual.is_file() and manual.read_text(encoding="utf-8").strip():
        return _block(manual, "manual", "high", manual.read_text(encoding="utf-8").strip())
    if cfg.transcriber != "whisper":
        return None
    cli, ffmpeg = which("whisper-cli"), which("ffmpeg")
    videos = [f for f in reel["files"] if f["kind"] == "video"]
    if not (cli and ffmpeg and cfg.whisper_model.is_file() and videos):
        return None
    src = max(videos, key=lambda f: f.get("seconds") or 0)  # longest clip; first one on ties
    wav = folder / "audio-16k.wav"
    try:
        r = runner([ffmpeg, "-y", "-i", src["path"], "-ar", "16000", "-ac", "1", str(wav)],
                   capture_output=True, text=True)
        if r.returncode != 0:
            return None
        r = runner([cli, "-m", str(cfg.whisper_model), "-l", "mn", "-nt", "-f", str(wav)],
                   capture_output=True, text=True)
    finally:
        wav.unlink(missing_ok=True)
    text = (r.stdout or "").strip()
    if r.returncode != 0 or not text:
        return None
    manual.write_text(text + "\n", encoding="utf-8")
    # Mongolian whisper output is weak, so mark it low trust for every later step.
    return _block(manual, "whisper", "low", text)
