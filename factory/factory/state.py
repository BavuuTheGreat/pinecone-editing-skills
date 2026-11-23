"""The reel record (reel.json): create, load, save atomically, status history, needs."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from typing import Any

from factory.config import Config


class UnknownReel(KeyError):
    pass


def now_iso() -> str:
    # Local offset on purpose: the reviewer reads these times on the same machine.
    return datetime.now().astimezone().isoformat(timespec="seconds")


def slugify(name: str) -> str:
    # \w is Unicode-aware, so Cyrillic letters survive; everything else collapses to one "-".
    return re.sub(r"[\W_]+", "-", name.lower()).strip("-") or "reel"


def unique_id(cfg: Config, name: str) -> str:
    base, n = slugify(name), 1
    # Test for reel.json, not the folder: a transcript may be dropped into the folder before the record exists.
    while (cfg.reel_dir(base if n == 1 else f"{base}-{n}") / "reel.json").exists():
        n += 1
    return base if n == 1 else f"{base}-{n}"


def new_record(name: str, inbox_path: str, reel_id: str) -> dict[str, Any]:
    t = now_iso()
    return {
        "id": reel_id, "name": name, "inbox_path": inbox_path, "status": "new", "created": t, "updated": t,
        "files": [],
        "note": {"name": "", "team": "", "result": "", "handle": "", "theme": "", "extra": ""},
        "transcript": {"path": "", "source": "", "trust": "", "text": ""},
        "detection": {"theme": "", "confidence": 0.0, "scores": {}, "evidence": []},
        "proposal": {"path": "", "theme": "", "hook": "", "target_seconds": 0, "inserts": [], "music": "",
                     "open_questions": []},
        "approval": {"state": "none", "by": "", "at": "", "comment": ""},
        "edit": {"request_path": "", "job_path": "", "outputs": [], "started": "", "finished": ""},
        "review": {"state": "none", "comments": []},
        "needs": [],
        "history": [{"at": t, "from": "", "to": "new", "why": "found in inbox"}],
    }


def save(cfg: Config, reel: dict) -> None:
    """Write via temp file + rename so a crash never leaves half a record."""
    folder = cfg.reel_dir(reel["id"])
    folder.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".reel-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(reel, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, folder / "reel.json")
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load(cfg: Config, reel_id: str) -> dict[str, Any]:
    try:
        path = cfg.reel_dir(reel_id) / "reel.json"
    except ValueError:  # not a possible reel id (e.g. "../..")
        raise UnknownReel(reel_id) from None
    if not path.is_file():
        raise UnknownReel(reel_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_reels(cfg: Config) -> list[dict[str, Any]]:
    """All readable records, sorted by id. A corrupt file is skipped so it cannot stop the loop."""
    out = []
    if not cfg.state.is_dir():
        return out
    for d in sorted(cfg.state.iterdir()):
        try:
            out.append(json.loads((d / "reel.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def set_status(reel: dict, to: str, why: str) -> None:
    t = now_iso()
    reel["history"].append({"at": t, "from": reel["status"], "to": to, "why": why})
    reel["status"], reel["updated"] = to, t


def add_need(reel: dict, text: str) -> bool:
    if text in reel["needs"]:
        return False
    reel["needs"].append(text)
    return True


def clear_needs(reel: dict, prefix: str | None = None) -> None:
    reel["needs"] = [] if prefix is None else [n for n in reel["needs"] if not n.startswith(prefix)]
