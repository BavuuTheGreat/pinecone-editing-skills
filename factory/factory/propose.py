"""First proposal for a reel, from rules only (no LLM, no network).

The editing agent refines it; the manager approves or rejects it in about 20 seconds.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from . import detect as detector

CAP_SHARE = 0.6        # never plan more than 60 % of the raw footage: the rest is retakes and dead air
INTRO_SHARE = 0.10     # the first 10 % of a transcript is greetings, a weak hook
MIN_WORDS, MAX_WORDS = 4, 14
DEFAULT_TARGET = 45    # used only when no theme could be chosen


def _target_seconds(theme: dict, total: float) -> int:
    lo, hi = theme.get("default_seconds") or [DEFAULT_TARGET, DEFAULT_TARGET]
    target = (lo + hi) / 2
    if total and total < target / CAP_SHARE:
        target = total * CAP_SHARE
    return int(target)


def pick_hook(text: str, theme: dict) -> str:
    """Best opening sentence: 4-14 words, has a theme keyword or a number, not a question, not the intro."""
    keywords = theme.get("keywords", [])
    best, best_score = "", 0.0
    for m in re.finditer(r"[^.!?…]+[.!?…]*", text):
        raw = m.group(0)
        sentence = raw.strip(" .!?…\n\t\"'")
        if "?" in raw or m.start() < len(text) * INTRO_SHARE:
            continue
        if not MIN_WORDS <= len(sentence.split()) <= MAX_WORDS:
            continue
        low = sentence.lower()
        score = sum(k.get("weight", 1) for k in keywords if detector.count_hits(low, k["term"]))
        score += 2 if re.search(r"\d", sentence) else 0
        if score > best_score:  # strict: earlier sentence wins a tie
            best, best_score = sentence, score
    return best


def _inserts(files: list[dict]) -> list[dict]:
    videos = [f for f in files if f.get("kind") == "video"]
    main = max(videos, key=lambda f: f.get("seconds") or 0, default=None)
    out = []
    for f in files:
        if f is main or f.get("kind") not in ("video", "image"):
            continue
        path = str(f.get("path", ""))
        vertical = (f.get("height") or 0) > (f.get("width") or 0)
        screen = any(h in path.lower() for h in detector.SCREEN_HINTS)
        kind = "image" if f["kind"] == "image" else "screen recording" if screen else "video"
        use = "phone" if kind == "video" and vertical else "framed"  # a vertical clip is shown as a phone
        out.append({"file": Path(path).name, "kind": kind, "use": use})
    return out


def _music(cfg: Any, theme: str) -> str:
    repo = Path(getattr(cfg, "repo", "."))
    try:
        entries = json.loads((repo / "assets" / "MANIFEST.json").read_text(encoding="utf-8")).get("music", [])
        entries = [e for e in entries if isinstance(e, dict)]
        for e in entries:
            if theme and theme in (e.get("themes") or []):
                return str(e.get("id") or e.get("file"))
        for e in entries:
            if "default" in (e.get("tags") or []):
                return str(e.get("id") or e.get("file"))
    except (OSError, ValueError, AttributeError, TypeError):
        pass  # no or broken manifest: a generated track is always possible
    return "generated"


def build(reel: dict, cfg: Any) -> tuple[dict, str]:
    stored = reel.get("detection") or {}
    det = stored if stored.get("theme") else detector.detect(reel, cfg)
    themes = detector.load_themes(cfg)
    stem = det.get("theme", "")
    theme = themes.get(stem, {})
    files = reel.get("files") or []
    total = sum(f.get("seconds") or 0 for f in files if f.get("kind") == "video")
    transcript = reel.get("transcript") or {}
    low_trust = transcript.get("trust") == "low"
    text = str(transcript.get("text", ""))

    hook = "" if low_trust or not text.strip() else pick_hook(text, theme)
    questions = []
    if not str((reel.get("note") or {}).get("name", "")).strip():
        questions.append("Name is missing: add `name:` to note.txt, spelled exactly")
    if det.get("confidence", 0) < 0.5:
        questions.append(f"Theme is a guess ({round(det.get('confidence', 0) * 100)}%): confirm or add `theme:` to note.txt")
    if low_trust:
        questions.append("Transcript is from whisper (weak on Mongolian): captions need a human check")
    if not hook:
        questions.append("No hook line found: pick the opening sentence by hand")
    if theme and theme.get("status") != "ready":
        questions.append(f"Theme '{stem}' is not ready yet (status: {theme.get('status')}): expect manual work")

    block = {
        "theme": stem, "hook": hook, "target_seconds": _target_seconds(theme, total),
        "inserts": _inserts(files), "music": _music(cfg, stem), "open_questions": questions,
    }
    return block, _markdown(reel, block, theme, det)


def _markdown(reel: dict, block: dict, theme: dict, det: dict) -> str:
    rid = reel.get("id", "<id>")
    inserts = ", ".join(f"{i['file']} ({i['use']})" for i in block["inserts"]) or "none"
    label = theme.get("label", "no theme chosen")
    rows = [
        ("Theme", f"{label} ({round(det.get('confidence', 0) * 100)}% sure)"),
        ("Hook", block["hook"] or "none found"),
        ("Length", f"about {block['target_seconds']} s"),
        ("Inserts", inserts),
        ("Music", block["music"]),
    ]
    lines = [f"# {reel.get('name', rid)}", "", "| | |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in rows]
    lines += ["", "## Why this theme", ""] + [f"- {e}" for e in det.get("evidence", [])]
    lines += ["", "## Open questions", ""]
    lines += [f"- {q}" for q in block["open_questions"]] or ["- None."]
    lines += ["", "## Decide", "", "```", f"python3 -m factory approve {rid}",
              f'python3 -m factory reject {rid} "<reason>"', "```", ""]
    return "\n".join(lines)
