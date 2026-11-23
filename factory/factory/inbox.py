"""Find new folders in the inbox and describe their files and note."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Callable

from factory import state
from factory.config import Config

EXT = {
    "video": {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"},
    "audio": {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"},
    "image": {".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif"},
}
NOTE_KEYS = ("name", "team", "result", "handle", "theme")
NO_INFO = {"seconds": None, "width": None, "height": None}


def kind_of(path: str) -> str:
    ext = Path(path).suffix.lower()
    return next((k for k, v in EXT.items() if ext in v), "other")


def ffprobe(path: str, runner: Callable = subprocess.run) -> dict:
    """Duration and size, or all None when ffprobe is missing or cannot read the file."""
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        r = runner(cmd, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return dict(NO_INFO)
        data = json.loads(r.stdout)
        video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        dur = data.get("format", {}).get("duration")
        return {"seconds": float(dur) if dur is not None else None,
                "width": video.get("width"), "height": video.get("height")}
    except (OSError, ValueError, subprocess.SubprocessError):
        return dict(NO_INFO)


def parse_note(text: str) -> dict:
    note = {k: "" for k in (*NOTE_KEYS, "extra")}
    extra = []
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() in NOTE_KEYS:
            note[key.strip().lower()] = value.strip()
        elif line.strip():
            extra.append(line.strip())
    note["extra"] = "\n".join(extra)
    return note


def _content(folder: Path) -> list[Path]:
    # Dot files (.DS_Store, partial downloads) change on their own and are not footage.
    return sorted(p for p in folder.rglob("*") if p.is_file() and not p.name.startswith("."))


def is_settled(folder: Path, settle_seconds: int, now: float | None = None) -> bool:
    """False while anything in the folder (or the folder itself) changed recently: it is probably still copying."""
    now = time.time() if now is None else now
    paths = [folder, *_content(folder)]
    return all(now - p.stat().st_mtime >= settle_seconds for p in paths)


def describe(reel: dict, probe: Callable[[str], dict] = ffprobe) -> None:
    folder = Path(reel["inbox_path"])
    files = []
    for p in _content(folder):
        if p.name == "note.txt":
            reel["note"] = parse_note(p.read_text(encoding="utf-8", errors="replace"))
            continue
        kind = kind_of(str(p))
        info = probe(str(p)) if kind in ("video", "audio") else dict(NO_INFO)
        files.append({"path": str(p.resolve()), "kind": kind, **info})
    reel["files"] = files


def scan(cfg: Config, now: float | None = None) -> list[dict]:
    """Create a record for every settled folder not seen before; return the new records."""
    if not cfg.inbox.is_dir():
        return []
    known = {r["inbox_path"] for r in state.list_reels(cfg)}
    made = []
    for folder in sorted(cfg.inbox.iterdir()):
        if not folder.is_dir() or folder.name.startswith(".") or str(folder.resolve()) in known:
            continue
        if not is_settled(folder, cfg.settle_seconds, now):
            continue
        reel = state.new_record(folder.name, str(folder.resolve()), state.unique_id(cfg, folder.name))
        state.save(cfg, reel)
        made.append(reel)
    return made
