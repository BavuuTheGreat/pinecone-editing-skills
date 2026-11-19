"""Theme detection: the "keyword listener".

Scores every theme in themes.json from the transcript, the folder name and the footage facts,
and returns the best guess with the evidence behind it. Pure functions, no network.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FOOTAGE_BONUS = 1.5      # per matched footage rule (and the same penalty per violated one)
NAME_MULTIPLIER = 3      # a keyword in the folder name is a strong, human-written hint
QUESTION_WEIGHT = 2.0    # one interviewer question heard in the transcript
SCREEN_HINTS = ("screen recording", "screen_recording", "screenrecording", "дэлгэц")
DEFAULT_THEMES = Path(__file__).resolve().parent.parent / "themes.json"


def load_themes(cfg: Any) -> dict:
    """Return {theme stem: theme table}. `cfg.themes_path` overrides the shipped file."""
    path = Path(getattr(cfg, "themes_path", None) or DEFAULT_THEMES)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("themes", data)


def count_hits(text: str, term: str) -> int:
    """Count a term in lower-case text.

    Mongolian word endings change ("төсөл" -> "төслийн"), so 4+ letter terms and phrases match
    as plain substrings. Shorter terms must be whole words, or "баг" would fire inside "багш".
    """
    term = term.lower()
    if not term:
        return 0
    if len(term) >= 4 or " " in term:
        return text.count(term)
    return len(re.findall(rf"(?<!\w){re.escape(term)}(?!\w)", text))


def footage_facts(reel: dict) -> dict:
    """Summarise the video files: count, total seconds, orientation, screen recording."""
    videos = [f for f in reel.get("files") or [] if f.get("kind") == "video"]

    def is_screen(f: dict) -> bool:
        return any(h in str(f.get("path", "")).lower() for h in SCREEN_HINTS)

    cams = [f for f in videos if not is_screen(f)]
    vertical = sum(1 for f in cams if (f.get("height") or 0) > (f.get("width") or 0))
    horizontal = sum(1 for f in cams if (f.get("width") or 0) > (f.get("height") or 0))
    orientation = "vertical" if vertical > horizontal else "horizontal" if horizontal > vertical else ""
    return {
        "videos": len(videos),
        "seconds": sum(f.get("seconds") or 0 for f in videos),
        "orientation": orientation,
        "screen_recording": any(is_screen(f) for f in videos),
    }


def footage_score(rules: dict, facts: dict) -> tuple[float, list[str]]:
    """+bonus for each rule the footage meets, -bonus for each it breaks. Unknown facts are skipped."""
    score, matched = 0.0, []

    def judge(name: str, ok: bool) -> None:
        nonlocal score
        score += FOOTAGE_BONUS if ok else -FOOTAGE_BONUS
        if ok:
            matched.append(name)

    if "videos" in rules:
        judge("video count", rules["videos"][0] <= facts["videos"] <= rules["videos"][1])
    if "seconds" in rules:
        judge("total length", rules["seconds"][0] <= facts["seconds"] <= rules["seconds"][1])
    if rules.get("orientation") in ("vertical", "horizontal") and facts["orientation"]:
        judge(rules["orientation"] + " footage", facts["orientation"] == rules["orientation"])
    if "screen_recording" in rules:
        has = facts["screen_recording"]
        judge("has a screen recording" if has else "no screen recording", has == rules["screen_recording"])
    return score, matched


def footage_line(facts: dict) -> str:
    if not facts["videos"]:
        return "no video files"
    plural = "s" if facts["videos"] != 1 else ""
    kind = (facts["orientation"] + " ") if facts["orientation"] else ""
    return f"{facts['videos']} {kind}video{plural}, {round(facts['seconds'])} s"


def score_theme(theme: dict, text: str, name: str, words: int, trust: float, facts: dict) -> tuple[float, list[tuple[float, str]]]:
    """Return (raw score, [(weight for sorting, evidence line)])."""
    total, hits = 0.0, []
    for kw in theme.get("keywords", []):
        term, weight = kw["term"].lower(), kw.get("weight", 1)
        in_text, in_name = count_hits(text, term), count_hits(name, term)
        if not in_text and not in_name:
            continue
        gain = weight * (in_text / words * 100) * trust + weight * NAME_MULTIPLIER * in_name
        total += gain
        where = " + ".join(w for w, n in (("name", in_name), ("transcript", in_text)) if n)
        hits.append((gain, f"'{term}' x{in_text + in_name} ({where})"))
    for q in theme.get("questions", []):
        if count_hits(text, q):
            total += QUESTION_WEIGHT * trust
            hits.append((QUESTION_WEIGHT * trust, f"question: '{q}'"))
    bonus, matched = footage_score(theme.get("footage", {}), facts)
    total += bonus
    if matched:
        hits.append((abs(bonus), "footage fits: " + ", ".join(matched)))
    return max(total, 0.0), hits


def detect(reel: dict, cfg: Any) -> dict:
    themes = load_themes(cfg)
    wanted = str((reel.get("note") or {}).get("theme", "")).strip().lower()
    for stem, theme in themes.items():
        if wanted and wanted in (stem.lower(), str(theme.get("label", "")).lower()):
            # A person's choice beats any guess.
            return {"theme": stem, "confidence": 1.0, "scores": {stem: 1.0},
                    "evidence": [f"note.txt says theme: {wanted}"]}

    transcript = reel.get("transcript") or {}
    text = str(transcript.get("text", "")).lower()
    name = str(reel.get("name", "")).lower()
    trust = 0.5 if transcript.get("trust") == "low" else 1.0  # whisper is weak on Mongolian
    words = max(len(text.split()), 1)
    facts = footage_facts(reel)
    if not text.strip() and not name.strip() and not facts["videos"]:
        # Footage rules alone would crown "motion teaser" (it expects no video) for an empty folder.
        return {"theme": "", "confidence": 0.0, "scores": {s: 0.0 for s in themes}, "evidence": ["no signal"]}

    raw: dict[str, float] = {}
    evidence: dict[str, list[tuple[float, str]]] = {}
    for stem, theme in themes.items():
        raw[stem], evidence[stem] = score_theme(theme, text, name, words, trust, facts)

    total = sum(raw.values())
    if total <= 0:
        return {"theme": "", "confidence": 0.0, "scores": {s: 0.0 for s in raw}, "evidence": ["no signal"]}
    scores = {s: round(v / total, 4) for s, v in raw.items()}
    best = max(raw, key=raw.get)
    ranked = [line for _, line in sorted(evidence[best], reverse=True)]
    # Keep questions and footage visible even when keyword hits outweigh them.
    keywords = [l for l in ranked if l.startswith("'")][:4]
    others = [l for l in ranked if not l.startswith("'")][:3]
    lines = keywords + others
    if facts["videos"]:
        lines.append(footage_line(facts))
    if transcript.get("trust") == "low":
        lines.append("transcript is low trust: word weights halved")
    return {"theme": best, "confidence": scores[best], "scores": scores, "evidence": lines}
