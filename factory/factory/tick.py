"""One pass over every reel: each reel moves at most one step. Safe to run again and again."""
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from factory import approval, edit, inbox, state, transcribe
from factory.config import Config

STALE_LOCK_SECONDS = 2 * 3600
NO_TRANSCRIPT = "No transcript: put transcript.txt in {folder} or install whisper-cli"


@contextmanager
def render_lock(cfg: Config) -> Iterator[bool]:
    """One render-heavy step at a time (a 16 GB Mac crash-loops otherwise). Yields False if someone holds it."""
    cfg.home.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(cfg.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                stale = time.time() - cfg.lock.stat().st_mtime > STALE_LOCK_SECONDS
            except FileNotFoundError:
                continue
            if not stale:
                yield False
                return
            cfg.lock.unlink(missing_ok=True)  # a crashed run left it behind
    else:
        yield False
        return
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        yield True
    finally:
        cfg.lock.unlink(missing_ok=True)


class _Ctx:
    def __init__(self, cfg: Config, probe: Callable | None, runner: Callable | None) -> None:
        self.cfg, self.probe, self.runner = cfg, probe, runner


def _new(reel: dict, c: _Ctx) -> None:
    if not inbox.is_settled(Path(reel["inbox_path"]), c.cfg.settle_seconds):
        return  # still being copied
    inbox.describe(reel, c.probe) if c.probe else inbox.describe(reel)
    if not any(f["kind"] == "video" for f in reel["files"]):
        state.add_need(reel, "No video file in the inbox folder: add one")
        return
    state.clear_needs(reel, "No video file")
    state.set_status(reel, "transcribing", "files probed, note read")


def _transcribing(reel: dict, c: _Ctx) -> None:
    kw = {"runner": c.runner} if c.runner else {}
    folder = c.cfg.reel_dir(reel["id"])
    if (folder / "transcript.txt").exists() or c.cfg.transcriber != "whisper":
        tr = transcribe.transcribe(reel, c.cfg, **kw)
    else:
        with render_lock(c.cfg) as got:
            if not got:
                return
            tr = transcribe.transcribe(reel, c.cfg, **kw)
    if tr is None:
        state.add_need(reel, NO_TRANSCRIPT.format(folder=folder))
        return
    state.clear_needs(reel, "No transcript")
    reel["transcript"] = tr
    state.set_status(reel, "detecting", f"transcript from {tr['source']}")


def _detecting(reel: dict, c: _Ctx) -> None:
    from factory import detect  # owned by another module; a missing one becomes a need
    reel["detection"] = detect.detect(reel, c.cfg)
    state.set_status(reel, "proposed", f"theme {reel['detection']['theme']}")


def _proposed(reel: dict, c: _Ctx) -> None:
    adapter = approval.get_adapter(c.cfg)
    if not reel["proposal"]["path"]:
        from factory import propose
        block, markdown = propose.build(reel, c.cfg)
        path = c.cfg.reel_dir(reel["id"]) / "proposal.md"
        path.write_text(markdown, encoding="utf-8")
        reel["proposal"] = {**block, "path": str(path)}
        reel["approval"] = {"state": "pending", "by": "", "at": "", "comment": ""}
        for q in block.get("open_questions", []):
            state.add_need(reel, q)
        adapter.post_proposal(reel)
        return
    d = adapter.read_decision(reel)
    if d is None:
        return
    reel["approval"] = d
    reel["needs"] = [n for n in reel["needs"] if n not in reel["proposal"].get("open_questions", [])]
    state.set_status(reel, d["state"], f"approval {d['state']} by {d['by']}")


def _approved(reel: dict, c: _Ctx) -> None:
    edit.write_request(c.cfg, reel)
    state.set_status(reel, "editing", "EDIT_REQUEST.md written")


def _editing(reel: dict, c: _Ctx) -> None:
    ed = reel["edit"]
    if not ed["outputs"]:
        editor = edit.get_editor(c.cfg, c.runner)
        if editor.name != "claude" or ed["started"]:
            return  # handoff, or claude already ran: wait for `factory done`
        with render_lock(c.cfg) as got:
            if not got:
                return
            ed["started"] = state.now_iso()
            state.save(c.cfg, reel)
            editor.run(reel, c.cfg)
        fresh = state.load(c.cfg, reel["id"])  # the editor reports back through the CLI, which writes the file
        reel.clear()
        reel.update(fresh)
        if not reel["edit"]["outputs"]:
            state.add_need(reel, f"Editor finished without outputs: run python3 -m factory done {reel['id']} <files>")
            return
    state.clear_needs(reel, "Editor finished without")
    reel["review"]["state"] = "waiting"
    state.set_status(reel, "in_review", f"{len(reel['edit']['outputs'])} output(s) recorded")


def _in_review(reel: dict, c: _Ctx) -> None:
    rs = reel["review"]["state"]
    if rs == "approved":
        approval.get_adapter(c.cfg).post_result(reel)
        state.set_status(reel, "done", "review approved")
    elif rs == "changes":
        state.set_status(reel, "changes", "reviewer asked for changes")


def _changes(reel: dict, c: _Ctx) -> None:
    edit.write_request(c.cfg, reel)  # status is still "changes", so the comments go on top
    reel["edit"].update(outputs=[], started="", finished="")
    reel["review"]["state"] = "none"
    state.set_status(reel, "editing", "new EDIT_REQUEST.md with review comments")


STEPS = {"new": _new, "transcribing": _transcribing, "detecting": _detecting, "proposed": _proposed,
         "approved": _approved, "editing": _editing, "in_review": _in_review, "changes": _changes}


def tick(cfg: Config, probe: Callable | None = None, runner: Callable | None = None) -> list[str]:
    """Scan the inbox, then advance every reel one step. Returns one log line per change."""
    cfg.ensure_dirs()
    ctx, log = _Ctx(cfg, probe, runner), []
    for r in inbox.scan(cfg):
        log.append(f"{r['id']}: found in inbox")
    for reel in state.list_reels(cfg):
        before, status = json.dumps(reel, sort_keys=True), reel["status"]
        step = STEPS.get(status)
        if step:
            try:
                step(reel, ctx)
                state.clear_needs(reel, "Error at")
            except Exception as e:  # one bad reel must not stop the others
                state.add_need(reel, f"Error at {status}: {e}")
        if json.dumps(reel, sort_keys=True) != before:
            state.save(cfg, reel)  # only write on change, so waiting reels stay byte-identical
            if reel["status"] != status:
                log.append(f"{reel['id']}: {status} -> {reel['status']}")
    return log
