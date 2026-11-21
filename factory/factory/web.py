"""Local dashboard: the factory board in a browser, with the approve / reject buttons.

    python3 -m factory serve [--port 8765]

Why it exists: the manager's "yes" should be a button, not a command. Until the Marketing Planner has an API this page
is that button. It binds to 127.0.0.1 only and refuses requests that do not come from the page itself, because approving
a reel starts real work on this machine.
"""
from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import approval, state
from . import tick as tick_mod
from .config import Config

LANES = [  # status -> (lane title, who acts)
    ("Arriving", ("new", "transcribing", "detecting")),
    ("Needs your yes", ("proposed",)),
    ("Editing", ("approved", "editing", "changes")),
    ("With the reviewer", ("in_review",)),
    ("Finished", ("done", "rejected")),
]

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#17181a;--mute:#6b6f76;--line:#e3e1da;--ok:#1f8a4c;--warn:#b25c00;--bad:#b3261e;--accent:#0f6b46;--chip:#eeece6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#121314;--card:#1b1d1f;--ink:#eceae4;--mute:#9aa0a6;--line:#2b2e31;--ok:#5fd38d;--warn:#f0a94b;--bad:#ff8a80;--accent:#5fd38d;--chip:#26292c}}
:root[data-theme="dark"]{--bg:#121314;--card:#1b1d1f;--ink:#eceae4;--mute:#9aa0a6;--line:#2b2e31;--ok:#5fd38d;--warn:#f0a94b;--bad:#ff8a80;--accent:#5fd38d;--chip:#26292c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1500px;margin:0 auto;display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;justify-content:space-between}
h1{font-size:22px;margin:0}.sub{color:var(--mute);font-size:13px}
.bar{display:flex;gap:8px;flex-wrap:wrap}
button,.btn{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);padding:7px 12px;border-radius:8px;cursor:pointer;text-decoration:none}
button.yes{background:var(--accent);border-color:var(--accent);color:#fff}button.no{color:var(--bad)}
@media (prefers-color-scheme:dark){button.yes{color:#0b1410}}
main{max-width:1500px;margin:0 auto;padding:8px 16px 40px;display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));align-items:start}
.lane h2{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);margin:8px 2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px;overflow-wrap:anywhere}
.card h3{margin:0 0 6px;font-size:16px}.chip{display:inline-block;background:var(--chip);border-radius:999px;padding:2px 9px;font-size:12px;margin:0 4px 4px 0}
.need{color:var(--warn);font-size:13.5px;margin:6px 0 0;padding-left:16px}.empty{color:var(--mute);font-size:13.5px;padding:6px 2px}
dl{display:grid;grid-template-columns:auto 1fr;gap:3px 10px;margin:8px 0;font-size:13.5px}dt{color:var(--mute)}dd{margin:0}
details{margin-top:8px;font-size:13.5px}summary{cursor:pointer;color:var(--mute)}
form{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}input[type=text]{flex:1 1 140px;font:inherit;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)}
.flash{max-width:1500px;margin:0 auto;padding:0 16px}.flash div{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:8px 12px}
"""


def _e(x: object) -> str:
    return html.escape(str(x if x is not None else ""))


def _card(r: dict, token: str) -> str:
    det, prop, ap = r.get("detection", {}), r.get("proposal", {}), r.get("approval", {})
    chips = [f'<span class="chip">{_e(r["status"])}</span>']
    if det.get("theme"):
        chips.append(f'<span class="chip">{_e(det["theme"])} · {round(float(det.get("confidence", 0)) * 100)}% sure</span>')
    rows = []
    if prop.get("hook"):
        rows.append(("Hook", prop["hook"]))
    if prop.get("target_seconds"):
        rows.append(("Length", f'about {prop["target_seconds"]} s'))
    if prop.get("music"):
        rows.append(("Music", prop["music"]))
    for k in ("name", "team", "result"):
        if r.get("note", {}).get(k):
            rows.append((k.capitalize(), r["note"][k]))
    if r.get("edit", {}).get("outputs"):
        rows.append(("Files", ", ".join(o.rsplit("/", 1)[-1] for o in r["edit"]["outputs"])))
    if r.get("review", {}).get("comments"):
        rows.append(("Review", " / ".join(map(str, r["review"]["comments"]))))
    out = [f'<div class="card"><h3>{_e(r["name"])}</h3>{"".join(chips)}']
    if rows:
        out.append("<dl>" + "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in rows) + "</dl>")
    if det.get("evidence"):
        out.append("<details><summary>Why this theme</summary><ul>" + "".join(f"<li>{_e(x)}</li>" for x in det["evidence"]) + "</ul></details>")
    out.extend(f'<p class="need">{_e(n)}</p>' for n in r.get("needs", []))
    if r["status"] == "proposed" and ap.get("state") == "pending":
        out.append(f'<form method="post" action="/decide"><input type="hidden" name="token" value="{_e(token)}">'
                   f'<input type="hidden" name="id" value="{_e(r["id"])}"><input type="text" name="comment" placeholder="Comment (needed to reject)">'
                   '<button class="yes" name="decision" value="approve">Yes, make it</button>'
                   '<button class="no" name="decision" value="reject">No</button></form>')
    out.append("</div>")
    return "".join(out)


def page(cfg: Config, token: str, flash: str = "") -> str:
    reels = state.list_reels(cfg)
    lanes = []
    for title, statuses in LANES:
        cards = "".join(_card(r, token) for r in reels if r["status"] in statuses) or '<div class="empty">Nothing here.</div>'
        lanes.append(f'<section class="lane"><h2>{_e(title)}</h2>{cards}</section>')
    pending = sum(1 for r in reels if r["status"] == "proposed")
    note = f'<div class="flash"><div>{_e(flash)}</div></div>' if flash else ""
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Editing factory</title><style>{CSS}</style></head><body><header><div><h1>Editing factory</h1>'
            f'<div class="sub">{len(reels)} reel(s) · {pending} waiting for your yes · folder {_e(cfg.home)}</div></div>'
            f'<div class="bar"><form method="post" action="/tick" style="margin:0"><input type="hidden" name="token" value="{_e(token)}">'
            f'<button>Run one step now</button></form><a class="btn" href="/review">Daily review</a><a class="btn" href="/">Refresh</a></div></header>'
            f'{note}<main>{"".join(lanes)}</main></body></html>')


def review_page(cfg: Config) -> str:
    from . import review  # lazy: the report module is optional for the board
    text = review.build(cfg)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Daily review</title><style>{CSS}pre{{white-space:pre-wrap;max-width:900px;margin:16px auto;padding:16px;'
            f'background:var(--card);border:1px solid var(--line);border-radius:12px;font:14px/1.5 ui-monospace,Menlo,monospace}}</style></head>'
            f'<body><header><h1>Daily review</h1><a class="btn" href="/">Back to the board</a></header><pre>{_e(text)}</pre></body></html>')


def decide(cfg: Config, reel_id: str, decision: str, comment: str) -> str:
    """Record the manager's decision. Returns the message to show. Rejecting needs a reason: the editor learns from it."""
    reel = state.load(cfg, reel_id)
    if reel["status"] != "proposed":
        return f"{reel['name']} is '{reel['status']}', so there is nothing to decide."
    if decision == "approve":
        approval.approve(cfg, reel, comment, by="dashboard")
        return f"Approved: {reel['name']}. The next step picks it up."
    if not comment.strip():
        return "To reject, write the reason in the comment box first."
    approval.reject(cfg, reel, comment, by="dashboard")
    return f"Rejected: {reel['name']}."


def make_handler(cfg: Config, token: str):
    class H(BaseHTTPRequestHandler):
        def _send(self, body: str, code: int = 200) -> None:
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            u = urlparse(self.path)
            if u.path == "/":
                self._send(page(cfg, token, parse_qs(u.query).get("m", [""])[0]))
            elif u.path == "/review":
                self._send(review_page(cfg))
            elif u.path == "/api/reels":
                self._send(json.dumps(state.list_reels(cfg), ensure_ascii=False))
            else:
                self._send("Not found", 404)

        def do_POST(self) -> None:  # noqa: N802
            n = int(self.headers.get("Content-Length") or 0)
            form = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode("utf-8")).items()}
            if form.get("token") != token:  # only this page's own forms may change state
                return self._send("Refused: this request did not come from the dashboard.", 403)
            try:
                if self.path == "/decide":
                    msg = decide(cfg, form.get("id", ""), form.get("decision", ""), form.get("comment", ""))
                elif self.path == "/tick":
                    msg = "; ".join(tick_mod.tick(cfg)) or "Nothing changed."
                else:
                    return self._send("Not found", 404)
            except state.UnknownReel:
                msg = "That reel does not exist any more."
            from urllib.parse import quote
            self.send_response(303)
            self.send_header("Location", "/?m=" + quote(msg))
            self.end_headers()

        def log_message(self, *a: object) -> None:  # keep the terminal quiet
            pass
    return H


def serve(cfg: Config, port: int = 8765) -> None:
    import secrets
    cfg.ensure_dirs()
    token = secrets.token_urlsafe(16)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(cfg, token))
    print(f"Editing factory board: http://localhost:{port}  (folder {cfg.home}; Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
