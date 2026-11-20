"""Command line: python3 -m factory <command>. Exit codes: 0 ok, 1 bad input, 2 unknown reel."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

from factory import approval, config, edit, state, tick as tick_mod
from factory.config import Config


def _age(iso: str) -> str:
    try:
        secs = max(0, int(datetime.now().astimezone().timestamp() - datetime.fromisoformat(iso).timestamp()))
    except ValueError:
        return "?"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit}"
    return f"{secs}s"


def cmd_status(cfg: Config, a: argparse.Namespace) -> int:
    reels = state.list_reels(cfg)
    if not reels:
        print("no reels yet")
        return 0
    rows = []
    for r in reels:
        d = r["detection"]
        theme = f"{d['theme']} ({d['confidence']:.2f})" if d["theme"] else "-"
        rows.append((r["id"], r["status"], theme, r["approval"]["state"], _age(r["updated"]), r["needs"]))
    w = [max(len(str(row[i])) for row in rows + [("id", "status", "theme", "approval", "age", [])]) for i in range(5)]
    print("  ".join(h.ljust(w[i]) for i, h in enumerate(("id", "status", "theme", "approval", "age"))))
    for row in rows:
        print("  ".join(str(row[i]).ljust(w[i]) for i in range(5)).rstrip())
        for need in row[5]:
            print(f"    {need}")
    return 0


def cmd_show(cfg: Config, a: argparse.Namespace) -> int:
    reel = state.load(cfg, a.id)
    print(json.dumps(reel, ensure_ascii=False, indent=2))
    if reel["proposal"]["path"]:
        try:
            print("\n--- proposal ---\n" + open(reel["proposal"]["path"], encoding="utf-8").read())
        except OSError:
            pass
    return 0


def cmd_approve(cfg: Config, a: argparse.Namespace) -> int:
    approval.approve(cfg, state.load(cfg, a.id), " ".join(a.comment))
    print(f"{a.id}: approved (the next tick moves it on)")
    return 0


def cmd_reject(cfg: Config, a: argparse.Namespace) -> int:
    approval.reject(cfg, state.load(cfg, a.id), " ".join(a.comment))
    print(f"{a.id}: rejected")
    return 0


def cmd_done(cfg: Config, a: argparse.Namespace) -> int:
    reel = state.load(cfg, a.id)
    if reel["status"] != "editing":
        # outputs reported at any other status would be wiped or ignored by the next step (found in the first walkthrough)
        print(f"{a.id} is '{reel['status']}', not editing: run `python3 -m factory tick` first, then report the files")
        return 1
    edit.mark_done(cfg, reel, a.files)
    print(f"{a.id}: {len(a.files)} output(s) recorded")
    return 0


def cmd_review_result(cfg: Config, a: argparse.Namespace) -> int:
    reel = state.load(cfg, a.id)
    if a.result not in ("approved", "changes"):
        print("result must be approved or changes", file=sys.stderr)
        return 1
    if reel["status"] != "in_review":
        print(f"{a.id} is '{reel['status']}', not in_review", file=sys.stderr)
        return 1
    reel["review"]["state"] = a.result
    if a.comment:
        reel["review"]["comments"].append(a.comment)
    state.save(cfg, reel)
    print(f"{a.id}: review {a.result}")
    return 0


def cmd_review(cfg: Config, a: argparse.Namespace) -> int:
    from factory import review
    date = a.date or datetime.now().date().isoformat()
    text = review.build(cfg, date)
    cfg.reviews.mkdir(parents=True, exist_ok=True)
    (cfg.reviews / f"{date}.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


def cmd_tick(cfg: Config, a: argparse.Namespace) -> int:
    for line in tick_mod.tick(cfg) or ["nothing changed"]:
        print(line)
    return 0


def cmd_loop(cfg: Config, a: argparse.Namespace) -> int:
    runs = 0
    while a.max_runs is None or runs < a.max_runs:
        cmd_tick(cfg, a)
        sys.stdout.flush()
        runs += 1
        if a.max_runs is None or runs < a.max_runs:
            time.sleep(a.every)
    return 0


def cmd_serve(cfg: Config, a: argparse.Namespace) -> int:
    from . import web  # lazy: the board is optional
    web.serve(cfg, a.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="factory", description="Editing factory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tick").set_defaults(fn=cmd_tick)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("show"); s.add_argument("id"); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("approve"); s.add_argument("id"); s.add_argument("comment", nargs="*"); s.set_defaults(fn=cmd_approve)
    s = sub.add_parser("reject"); s.add_argument("id"); s.add_argument("comment", nargs="+"); s.set_defaults(fn=cmd_reject)
    s = sub.add_parser("done"); s.add_argument("id"); s.add_argument("files", nargs="+"); s.set_defaults(fn=cmd_done)
    s = sub.add_parser("review-result"); s.add_argument("id")
    s.add_argument("result"); s.add_argument("comment", nargs="?", default="")
    s.set_defaults(fn=cmd_review_result)
    s = sub.add_parser("review"); s.add_argument("--date"); s.set_defaults(fn=cmd_review)
    s = sub.add_parser("serve", help="the board in a browser, with the approve / reject buttons (localhost only)")
    s.add_argument("--port", type=int, default=8765); s.set_defaults(fn=cmd_serve)
    s = sub.add_parser("loop"); s.add_argument("--every", type=float, default=300)
    s.add_argument("--max-runs", type=int, default=None, help=argparse.SUPPRESS)  # lets tests stop the loop
    s.set_defaults(fn=cmd_loop)
    return p


def main(argv: list[str] | None = None, cfg: Config | None = None) -> int:
    try:
        a = build_parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    cfg = cfg or config.load()
    try:
        return a.fn(cfg, a)
    except state.UnknownReel as e:
        print(f"unknown reel: {e.args[0]}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
