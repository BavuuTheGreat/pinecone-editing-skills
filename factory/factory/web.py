"""Local dashboard: a single-page admin console plus the JSON API behind it.

    python3 -m factory serve [--port 8765]

Why it exists: the manager's "yes" should be a button, not a command. The console (static files in factory/ui/) reads
the factory's files through a small JSON API and writes only three things: an approval decision, one `tick`, and a
review result. It binds to 127.0.0.1 only, and because approving a reel starts real work on this machine every POST
must pass four checks: a local Host, a local Origin (when one is sent), a JSON content type, and the per-process token
that is injected into index.html at serve time.
"""
from __future__ import annotations

import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from . import approval, state
from . import tick as tick_mod
from .config import Config

FACTORY_DIR = Path(__file__).resolve().parents[1]
UI_DIR = FACTORY_DIR / "ui"
LOCAL_HOSTS = ("localhost", "127.0.0.1", "[::1]")
ID_RE = re.compile(r"^[\w-]{1,200}$")  # what state.slugify can produce; no dots, slashes or separators
MAX_BODY = 64 * 1024
MAX_COMMENT = 2000
STATIC_TYPES = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".svg": "image/svg+xml"}
PAGES = ("/", "/reels", "/review", "/agents", "/themes", "/assets")  # plus /reels/<id>: the client draws them
WRITE_LOCK = threading.Lock()  # the handler is threaded; decisions, ticks and results must not interleave

# who acts on a reel in each status (from agents/README.md); proposed waits for a person, not an agent
STATUS_AGENT = {"new": "intake", "transcribing": "listener", "detecting": "listener", "approved": "planner",
                "changes": "planner", "editing": "editor", "in_review": "checker"}
NEXT = {  # one plain line per status: what is happening to the reel now
    "new": "Intake will read the files and the note.",
    "transcribing": "The Listener will transcribe it, or use transcript.txt if one is there.",
    "detecting": "The Listener will pick the theme.",
    "proposed": "Waiting for your yes.",
    "approved": "The Planner will write the edit brief.",
    "editing": "The Editor is working. Finished files are recorded with `factory done`.",
    "in_review": "Waiting for the reviewer's result.",
    "changes": "The Planner will write a new brief with the review comments.",
    "done": "Finished.",
    "rejected": "Rejected. Nothing will be made.",
}


# ---------------------------------------------------------------- decisions (also used by the tests)

def _decide(cfg: Config, reel_id: str, decision: str, comment: str) -> tuple[int, str]:
    if not ID_RE.match(reel_id or ""):
        return 400, "That is not a reel id."
    if decision not in ("approve", "reject"):
        return 400, "Decision must be approve or reject."
    if len(comment) > MAX_COMMENT:
        return 400, "The comment is too long."
    try:
        reel = state.load(cfg, reel_id)
    except state.UnknownReel:
        return 404, "That reel does not exist any more."
    if (why := approval.refusal(reel)):
        return 409, why
    if decision == "approve":
        approval.approve(cfg, reel, comment, by="dashboard")
        return 200, f"Approved: {reel['name']}. The next step picks it up."
    if not comment.strip():
        return 400, "To reject, write the reason first."
    approval.reject(cfg, reel, comment, by="dashboard")
    return 200, f"Rejected: {reel['name']}."


def decide(cfg: Config, reel_id: str, decision: str, comment: str) -> str:
    """Record the manager's decision. Returns the message to show. Rejecting needs a reason: the editor learns from it."""
    with WRITE_LOCK:
        return _decide(cfg, reel_id, decision, comment)[1]


def _record_review(cfg: Config, reel_id: str, result: str, comment: str) -> tuple[int, str]:
    if not ID_RE.match(reel_id or ""):
        return 400, "That is not a reel id."
    if result not in ("approved", "changes"):
        return 400, "Result must be approved or changes."
    if len(comment) > MAX_COMMENT:
        return 400, "The comment is too long."
    if result == "changes" and not comment.strip():
        return 400, "Say what must change."
    try:
        reel = state.load(cfg, reel_id)
    except state.UnknownReel:
        return 404, "That reel does not exist any more."
    if reel["status"] != "in_review":
        return 409, f"{reel['name']} is '{reel['status']}', not in review."
    reel["review"]["state"] = result
    if comment.strip():
        reel["review"]["comments"].append(comment.strip())
    state.save(cfg, reel)
    return 200, f"Review recorded: {result}. The next step moves {reel['name']} on."


# ---------------------------------------------------------------- read models

def _theme_table() -> dict[str, dict]:
    try:
        return json.loads((FACTORY_DIR / "themes.json").read_text(encoding="utf-8")).get("themes", {})
    except (OSError, ValueError):
        return {}


def _file_name(p: object) -> str:
    return str(p).replace("\\", "/").rsplit("/", 1)[-1]


def _decided(cfg: Config, r: dict) -> str:
    """A decision that is written but not yet picked up by the next tick: '', 'approved' or 'rejected'."""
    if r.get("status") != "proposed" or cfg.approval != "file":
        return ""
    d = approval.FileApproval(cfg).read_decision(r)
    return d["state"] if d else ""


def reel_summary(cfg: Config, r: dict, themes: dict | None = None) -> dict:
    themes = themes if themes is not None else _theme_table()
    det, ap = r.get("detection") or {}, r.get("approval") or {}
    theme, status = det.get("theme") or "", r.get("status", "new")
    decided = _decided(cfg, r)
    return {
        "id": r.get("id", ""), "name": r.get("name") or r.get("id", ""), "status": status,
        "theme": theme, "theme_label": (themes.get(theme) or {}).get("label", theme),
        "confidence": float(det.get("confidence") or 0), "updated": r.get("updated", ""), "created": r.get("created", ""),
        "needs": list(r.get("needs") or []), "approval": ap.get("state", "none"), "decided": decided,
        "awaiting_you": status == "proposed" and ap.get("state") == "pending" and not decided,
        "agent": STATUS_AGENT.get(status, ""),
    }


def reel_detail(cfg: Config, r: dict) -> dict:
    out = reel_summary(cfg, r)
    prop, note, ed, rv = r.get("proposal") or {}, r.get("note") or {}, r.get("edit") or {}, r.get("review") or {}
    det, tr = r.get("detection") or {}, r.get("transcript") or {}
    scores = sorted((det.get("scores") or {}).items(), key=lambda kv: -float(kv[1] or 0))[:3]
    out.update({
        "next": NEXT.get(out["status"], ""),
        "note": {k: note.get(k, "") for k in ("name", "team", "result", "handle")},
        "evidence": list(det.get("evidence") or []),
        "runners_up": [{"theme": k, "score": float(v or 0)} for k, v in scores],
        "proposal": {"hook": prop.get("hook", ""), "target_seconds": prop.get("target_seconds") or 0,
                     "music": prop.get("music", ""), "inserts": list(prop.get("inserts") or []),
                     "open_questions": list(prop.get("open_questions") or [])},
        "approval_detail": {k: (r.get("approval") or {}).get(k, "") for k in ("state", "by", "at", "comment")},
        "files": [{"name": _file_name(f.get("path", "")), "kind": f.get("kind", ""),
                   "seconds": f.get("seconds") or 0} for f in r.get("files") or [] if isinstance(f, dict)],
        "transcript": {"source": tr.get("source", ""), "trust": tr.get("trust", "")},  # the text itself stays on disk
        "outputs": [_file_name(o) for o in ed.get("outputs") or []],
        "review": {"state": rv.get("state", "none"), "comments": [str(c) for c in rv.get("comments") or []]},
        "history": [{"at": h.get("at", ""), "from": h.get("from", ""), "to": h.get("to", ""), "why": h.get("why", "")}
                    for h in r.get("history") or [] if isinstance(h, dict)],
    })
    return out


def review_model(cfg: Config) -> dict:
    """review.build() text cut into sections the page can draw. The text itself is the source of truth."""
    from . import review
    text = review.build(cfg)
    title, summary, sections, cur, group = "", "", [], None, None
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            cur, group = {"title": line[3:].strip(), "items": [], "groups": []}, None
            sections.append(cur)
        elif cur is None:
            if line.strip():
                summary = line.strip()
        elif line.startswith("**") and line.rstrip().endswith("**"):
            group = {"title": line.strip("* "), "items": []}
            cur["groups"].append(group)
        elif line.startswith("- "):
            (group if group is not None else cur)["items"].append(line[2:].strip())
    for s in sections:
        s["empty"] = not s["items"] and not any(g["items"] for g in s["groups"])
    return {"title": title, "summary": summary, "sections": sections, "text": text}


def _md_list(block: str) -> list[str]:
    return [m.strip().lstrip("-").strip() for m in block.splitlines() if m.strip().startswith("-")]


def _md_sections(text: str) -> dict[str, str]:
    out, cur = {}, ""
    for line in text.splitlines():
        if line.startswith("## "):
            cur = line[3:].strip()
            out[cur] = ""
        elif cur:
            out[cur] += line + "\n"
    return out


def agents_model(cfg: Config) -> list[dict]:
    """The role cards (factory/agents/*.md + the table in agents/README.md) and what each is doing right now."""
    adir = FACTORY_DIR / "agents"
    try:
        readme = (adir / "README.md").read_text(encoding="utf-8")
    except OSError:
        return []
    reels = [reel_summary(cfg, r) for r in state.list_reels(cfg)]
    agents = []
    for line in readme.splitlines():
        m = re.match(r"^\|\s*\[([^\]]+)\]\(([\w.-]+\.md)\)\s*\|(.*)$", line)
        if not m:
            continue
        name, fname = m.group(1), m.group(2)
        cells = [c.strip().replace("`", "") for c in m.group(3).strip().rstrip("|").split("|")]
        if len(cells) < 4:
            continue
        key = fname[:-3]
        try:
            secs = _md_sections((adir / fname).read_text(encoding="utf-8"))
        except OSError:
            secs = {}
        brief = lambda r: {"id": r["id"], "name": r["name"], "status": r["status"]}  # noqa: E731
        agents.append({
            "key": key, "name": name, "job": cells[0], "reads": cells[1], "writes": cells[2], "hands_to": cells[3],
            "built": "not built" not in cells[0].lower(),
            "does": (secs.get("What I do") or "").strip(),
            "must": _md_list(secs.get("I must", "")), "never": _md_list(secs.get("I must never", "")),
            "acting_on": [brief(r) for r in reels if r["agent"] == key],
            "waiting_on_you": [brief(r) for r in reels if key == "planner" and r["awaiting_you"]],
        })
    return agents


def themes_model() -> list[dict]:
    out = []
    for key, t in _theme_table().items():
        out.append({"key": key, "label": t.get("label", key), "status": t.get("status", ""), "card": t.get("card", ""),
                    "keywords": [{"term": k.get("term", ""), "weight": k.get("weight", 1)} for k in t.get("keywords") or []],
                    "questions": list(t.get("questions") or []), "footage": t.get("footage") or {},
                    "default_seconds": t.get("default_seconds") or []})
    return out


def assets_model(cfg: Config) -> dict:
    root = cfg.repo / "assets"
    try:
        man = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"items": [], "missing": True}
    items = []
    for kind in ("music", "images", "sfx"):
        for a in man.get(kind) or []:
            rel = str(a.get("file", ""))
            p = (root / rel).resolve()
            fetched = bool(rel) and root.resolve() in p.parents and p.is_file()
            items.append({"kind": kind, "id": a.get("id", ""), "title": a.get("title", ""), "artist": a.get("artist", ""),
                          "licence": a.get("licence", ""), "licence_url": a.get("licence_url", ""),
                          "credit": a.get("credit", ""), "bpm": a.get("bpm"), "mood": a.get("mood", ""),
                          "notes": a.get("notes", ""), "fetched": fetched})
    return {"items": items, "missing": False}


def run_tick(cfg: Config) -> list[str]:
    """No in-process lock: a step can run for hours. tick() holds its own cross-process lock and raises TickBusy."""
    return tick_mod.tick(cfg)


# ---------------------------------------------------------------- http

def _host_ok(value: str | None) -> bool:
    host = (value or "").strip().lower()
    if host.startswith("["):
        return host.split("]")[0] + "]" in LOCAL_HOSTS
    return host.rsplit(":", 1)[0] in LOCAL_HOSTS if ":" in host else host in LOCAL_HOSTS


def _origin_ok(value: str | None) -> bool:
    if value is None:
        return True  # a browser always sends Origin on a POST; non-browser callers still need the token
    u = urlparse(value)
    return u.scheme == "http" and _host_ok(u.netloc)


def make_handler(cfg: Config, token: str):
    class H(BaseHTTPRequestHandler):
        server_version = "FactoryUI"
        timeout = 30  # a slow or short request body must not pin a thread forever

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy",
                             "default-src 'self'; style-src 'self' https://fonts.googleapis.com; "
                             "font-src https://fonts.gstatic.com; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: object) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _error(self, code: int, message: str) -> None:
            self._json(code, {"ok": False, "error": message})

        def _index(self) -> None:
            html = (UI_DIR / "index.html").read_text(encoding="utf-8").replace("__FACTORY_TOKEN__", token)
            self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")

        def _static(self, rel: str) -> None:
            root = UI_DIR.resolve()
            p = (root / rel).resolve()
            if not rel or root not in p.parents or not p.is_file() or p.suffix not in STATIC_TYPES:
                return self._error(404, "Not found")
            self._send(200, p.read_bytes(), STATIC_TYPES[p.suffix])

        def do_GET(self) -> None:  # noqa: N802
            if not _host_ok(self.headers.get("Host")):
                return self._error(403, "Refused: not a local request.")
            path = unquote(urlparse(self.path).path)
            try:
                if path in PAGES or re.fullmatch(r"/reels/[\w-]{1,200}", path):
                    return self._index()
                if path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return
                if path.startswith("/ui/"):
                    return self._static(path[4:])
                if path == "/api/reels":
                    themes = _theme_table()
                    return self._json(200, [reel_summary(cfg, r, themes) for r in state.list_reels(cfg)])
                m = re.fullmatch(r"/api/reels/([^/]*)", path)
                if m:
                    if not ID_RE.match(m.group(1)):
                        return self._error(400, "That is not a reel id.")
                    return self._json(200, reel_detail(cfg, state.load(cfg, m.group(1))))
                if path == "/api/review":
                    return self._json(200, review_model(cfg))
                if path == "/api/agents":
                    return self._json(200, agents_model(cfg))
                if path == "/api/themes":
                    return self._json(200, themes_model())
                if path == "/api/assets":
                    return self._json(200, assets_model(cfg))
            except state.UnknownReel:
                return self._error(404, "That reel does not exist.")
            except (OSError, ValueError) as e:
                return self._error(500, f"Could not read the factory files: {e.__class__.__name__}")
            self._error(404, "Not found")

        def do_POST(self) -> None:  # noqa: N802
            if not _host_ok(self.headers.get("Host")) or not _origin_ok(self.headers.get("Origin")):
                return self._error(403, "Refused: this request did not come from the dashboard.")
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = -1
            if not 0 <= n <= MAX_BODY:  # refused unread; the connection is dropped so the body is never parsed as a request
                self.close_connection = True
                return self._error(400 if n < 0 else 413, "Bad length." if n < 0 else "Body too large.")
            supplied = self.headers.get("X-Factory-Token", "").encode("utf-8", "replace")
            if not hmac.compare_digest(supplied, token.encode()):
                return self._error(403, "Refused: this request did not come from the dashboard.")
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self._error(400, "Send JSON.")
            try:
                body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                return self._error(400, "Body is not valid JSON.")
            if not isinstance(body, dict):
                return self._error(400, "Body must be a JSON object.")
            path = urlparse(self.path).path

            def text(key: str) -> str:
                v = body.get(key, "")
                return v if isinstance(v, str) else ""
            try:
                if path == "/api/decide":
                    with WRITE_LOCK:
                        code, msg = _decide(cfg, text("id"), text("decision"), text("comment"))
                elif path == "/api/review-result":
                    with WRITE_LOCK:
                        code, msg = _record_review(cfg, text("id"), text("result"), text("comment"))
                elif path == "/api/tick":
                    try:
                        log = run_tick(cfg)
                    except tick_mod.TickBusy:
                        return self._error(409, "A step is already running. Try again when it finishes.")
                    return self._json(200, {"ok": True, "log": log, "message": "; ".join(log) or "Nothing changed."})
                else:
                    return self._error(404, "Not found")
            except OSError as e:
                return self._error(500, f"Could not write: {e.__class__.__name__}")
            if code == 200:
                return self._json(200, {"ok": True, "message": msg})
            self._error(code, msg)

        def log_message(self, *a: object) -> None:  # keep the terminal quiet
            pass
    return H


def serve(cfg: Config, port: int = 8765) -> None:
    import secrets
    cfg.ensure_dirs()
    token = secrets.token_urlsafe(16)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(cfg, token))
    print(f"Editing factory console: http://localhost:{port}  (folder {cfg.home}; Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
