"""Daily review: what is failing, what works, what needs the manager, what changed, what is next."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

STUCK_HOURS = 24
CLOSED = ("done", "rejected")
EMPTY = "Nothing today."
GIT_GROUPS = [  # order matters: the engine folder sits inside the skills folder, so it is checked first
    ("plugins/pinecone-video/skills/edit-reel/references/themes/", "Themes"),
    ("plugins/pinecone-video/skills/testimonial-reel/engine/", "Engine"),
    ("plugins/pinecone-video/skills/", "Skills"),
    ("factory/", "Factory"),
    ("assets/", "Assets"),
]
NEXT_STEP = {
    "new": "will read the files and the note",
    "transcribing": "will transcribe it (or use transcript.txt if one is there)",
    "detecting": "will pick the theme",
    "approved": "will write EDIT_REQUEST.md",
    "editing": "is waiting for the finished files (`python3 -m factory done <id> <files>`)",
    "in_review": "is waiting for the review result",
    "changes": "will write a new EDIT_REQUEST.md with the review comments",
}


def _run_git(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30).stdout


def _load_reels(cfg: Any) -> list[dict]:
    root = Path(getattr(cfg, "state_dir", None) or Path(getattr(cfg, "home", ".")) / "state")
    reels = []
    for path in sorted(root.glob("*/reel.json")):
        try:
            reels.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue  # one broken record must not hide the others
    return reels


def _when(text: str, now: datetime) -> datetime | None:
    try:
        t = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return t.replace(tzinfo=now.tzinfo) if t.tzinfo is None else t.astimezone(now.tzinfo)


def _name(r: dict) -> str:
    return str(r.get("name") or r.get("id", "?"))


def _label(r: dict) -> str:
    status = r.get("status", "new")
    if status == "proposed":
        return "waiting for approval" if (r.get("approval") or {}).get("state") == "pending" else "proposed"
    return {"in_review": "in review", "changes": "needing changes"}.get(status, status)


def _summary(reels: list[dict]) -> str:
    counts: dict[str, int] = {}
    for r in reels:
        counts[_label(r)] = counts.get(_label(r), 0) + 1
    parts = ", ".join(f"{n} {label}" for label, n in counts.items())
    word = "reel" if len(reels) == 1 else "reels"
    return f"{len(reels)} {word}: {parts}" if parts else "0 reels"


def _last_change(r: dict, now: datetime) -> datetime | None:
    hist = r.get("history") or []
    return _when(hist[-1].get("at") if hist else r.get("updated"), now)


def _failing(reels: list[dict], now: datetime) -> list[str]:
    out = []
    for r in reels:
        out += [f"{_name(r)}: {need}" for need in r.get("needs") or []]
        last = _last_change(r, now)
        if r.get("status") not in CLOSED and last:
            hours = int((now - last).total_seconds() // 3600)
            if hours > STUCK_HOURS:
                out.append(f"{_name(r)}: stuck in '{r.get('status')}' for {hours} hours")
    return out


def _working(reels: list[dict], date: str, now: datetime) -> list[str]:
    out = []
    for r in reels:
        for step in r.get("history") or []:
            at = _when(step.get("at"), now)
            if at and at.date().isoformat() == date:
                out.append(f"{_name(r)}: {step.get('from') or 'start'} -> {step.get('to')}")
                if step.get("to") == "done":
                    out.append(f"{_name(r)}: finished")
    return out


def _needs_you(reels: list[dict]) -> list[str]:
    out = []
    for r in reels:
        if (r.get("approval") or {}).get("state") == "pending":
            out.append(f"{_name(r)}: waiting for your decision. Run `python3 -m factory approve {r.get('id')}`")
        if r.get("status") not in CLOSED:
            out += [f"{_name(r)}: {q}" for q in (r.get("proposal") or {}).get("open_questions") or []]
        if (r.get("review") or {}).get("state") == "changes":
            for c in (r["review"].get("comments") or ["changes requested"]):
                text = c.get("comment") or c.get("text") if isinstance(c, dict) else c
                out.append(f"{_name(r)}: review comment: {text}")
    return out


def _git_section(cfg: Any, date: str, runner: Callable[[list[str]], str]) -> list[str]:
    cmd = ["git", "-C", str(getattr(cfg, "repo", ".")), "log", f"--since={date} 00:00",
           "--pretty=format:%h%x09%s", "--name-only"]
    try:
        raw = runner(cmd)
    except Exception:  # a missing git or repo must not stop the review
        return ["Could not read git log."]
    groups: dict[str, list[str]] = {}
    commit, seen = "", set()
    for line in raw.splitlines():
        if "\t" in line:
            commit = line.replace("\t", " ", 1)
            seen = set()
        elif line.strip() and commit:
            group = next((g for prefix, g in GIT_GROUPS if line.startswith(prefix)), "Other")
            if group not in seen:
                seen.add(group)
                groups.setdefault(group, []).append(commit)
    out = []
    for name in [g for _, g in GIT_GROUPS] + ["Other"]:
        if name in groups and f"**{name}**" not in out:
            out += [f"**{name}**"] + [f"- {c}" for c in groups[name]]
    return out


def _tomorrow(reels: list[dict]) -> list[str]:
    out = []
    for r in reels:
        status = r.get("status")
        if status in CLOSED:
            continue
        if status == "proposed":
            step = ("is waiting for your approve or reject"
                    if (r.get("approval") or {}).get("state") == "pending" else "will write the proposal")
        else:
            step = NEXT_STEP.get(status, "will be checked again")
        out.append(f"{_name(r)}: {step.replace('<id>', str(r.get('id')))}")
    return out


def build(cfg: Any, date: str | None = None, now: datetime | None = None,
          git_runner: Callable[[list[str]], str] | None = None) -> str:
    now = now or datetime.now().astimezone()
    date = date or now.date().isoformat()
    reels = _load_reels(cfg)
    git = _git_section(cfg, date, git_runner or _run_git)
    sections = [
        ("Failing", _failing(reels, now)),
        ("Working", _working(reels, date, now)),
        ("Needs you", _needs_you(reels)),
        ("Added and updated", git),
        ("Tomorrow", _tomorrow(reels)),
    ]
    lines = [f"# Editing factory: daily review, {date}", "", _summary(reels), ""]
    for title, items in sections:
        body = items if items == git and items else [f"- {i}" for i in items]
        lines += [f"## {title}", ""] + (body or [EMPTY]) + [""]
    return "\n".join(lines)
