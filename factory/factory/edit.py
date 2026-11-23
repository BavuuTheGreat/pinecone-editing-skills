"""The edit hand-off: write the brief for the editing agent, run the editor adapter, record outputs."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable

from factory import state
from factory.config import Config

THEME_CARD = "plugins/pinecone-video/skills/edit-reel/references/themes/{theme}.md"
RULES = [
    "Never clip speech.",
    "Every answer ends on a finished sentence.",
    "No interviewer voice in the final audio.",
    "Use names only as given in the note; never take a name from speech.",
    "List unsure caption words in your final message.",
]


def theme_of(reel: dict) -> str:
    return reel["note"]["theme"] or reel["proposal"]["theme"] or reel["detection"]["theme"]


def _request_text(cfg: Config, reel: dict) -> str:
    rid, theme, folder = reel["id"], theme_of(reel), cfg.reel_dir(reel["id"])
    card = cfg.repo / THEME_CARD.format(theme=theme or "unknown")
    p, n, t = reel["proposal"], reel["note"], reel["transcript"]
    lines = []
    if reel["status"] == "changes" and reel["review"]["comments"]:
        lines += ["## Review comments (fix these first)", *[f"- {c}" for c in reel["review"]["comments"]], ""]
    lines += [f"# Edit request: {reel['name']}", "", f"Reel id: `{rid}`", "", "## Files"]
    for f in reel["files"]:
        dur = f"{f['seconds']:.1f} s" if f.get("seconds") is not None else "duration unknown"
        size = f", {f['width']}x{f['height']}" if f.get("width") else ""
        lines.append(f"- {f['path']} ({f['kind']}, {dur}{size})")
    lines += ["", "## Note", *[f"- {k}: {n[k] or '(empty)'}" for k in ("name", "team", "result", "handle", "theme")],
              f"- extra: {n['extra'] or '(none)'}", "",
              "## Theme", f"- Detected/used theme: {theme or '(none)'} (confidence {reel['detection']['confidence']:.2f})",
              f"- Theme card: {card}" + ("" if card.is_file() else " (file not found yet)"), "",
              "## Proposal (approved)", f"- Hook: {p['hook']}", f"- Target length: {p['target_seconds']} s",
              f"- Inserts: {', '.join(p['inserts']) or '(none)'}", f"- Music: {p['music']}",
              f"- Proposal file: {p['path'] or '(none)'}", "",
              "## Transcript", f"- Path: {t['path'] or '(none)'}",
              f"- Trust: {t['trust'] or '(unknown)'}" + (" - low trust, check every word by ear/energy analysis" if t["trust"] == "low" else ""),
              "", "## House rules", *[f"- {r}" for r in RULES], "",
              "## Outputs", f"Write finished files into `{folder / 'outputs'}`.", "",
              "## When finished, report back with exactly", "",
              f"    python3 -m factory done {rid} <output files...>", "",
              f"(run it from `{cfg.repo / 'factory'}`)", ""]
    return "\n".join(lines)


def write_request(cfg: Config, reel: dict) -> str:
    folder = cfg.reel_dir(reel["id"])
    (folder / "outputs").mkdir(parents=True, exist_ok=True)
    path = folder / "EDIT_REQUEST.md"
    path.write_text(_request_text(cfg, reel), encoding="utf-8")
    reel["edit"]["request_path"] = str(path)
    return str(path)


class HandoffEditor:
    name = "handoff"

    def run(self, reel: dict, cfg: Config) -> None:
        pass  # a person or an agent session picks up EDIT_REQUEST.md and runs `factory done`


class ClaudeEditor:
    """Headless editing. Opt-in: the caller (tick) holds the render lock around run()."""
    name = "claude"

    def __init__(self, runner: Callable = subprocess.run) -> None:
        self.runner = runner

    def run(self, reel: dict, cfg: Config) -> None:
        prompt = (f"Read {reel['edit']['request_path']} and do exactly what it says. "
                  "When the edit is finished, run the report-back command it gives.")
        self.runner(["claude", "-p", prompt], cwd=str(cfg.repo), capture_output=True, text=True, timeout=3 * 3600)


def get_editor(cfg: Config, runner: Callable | None = None) -> HandoffEditor | ClaudeEditor:
    if cfg.editor == "claude":
        return ClaudeEditor(runner) if runner else ClaudeEditor()
    return HandoffEditor()


def mark_done(cfg: Config, reel: dict, outputs: list[str]) -> None:
    if not outputs:
        raise ValueError("give at least one output file")
    paths = [Path(os.path.abspath(Path(o).expanduser())) for o in outputs]  # abspath: keep symlinked temp/volume paths as given
    for p in paths:
        if not p.is_file():
            raise FileNotFoundError(f"output file not found: {p}")
    reel["edit"]["outputs"] = [str(p) for p in paths]
    reel["edit"]["finished"] = state.now_iso()
    state.save(cfg, reel)
