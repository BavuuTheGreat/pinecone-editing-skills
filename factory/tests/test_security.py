"""Security regression tests for the local dashboard (JSON API + static console) and the state folder.

Threat model: SECURITY.md. The server is local only; a POST needs the page's token in a header; a reel id from the
network or the command line can never reach outside FACTORY_HOME/state; the console puts data in with textContent only.
"""
import contextlib
import http.client
import io
import json
import re
import socket
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from factory import cli, state, web
from factory.config import Config

PAYLOAD = '<script>alert(1)</script>'
API_GETS = ("/api/reels", "/api/reels/r-one", "/api/review", "/api/agents", "/api/themes", "/api/assets")


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = Config(home=self.root / "home")
        self.cfg.ensure_dirs()
        r = state.new_record(f"Reel {PAYLOAD}", "/in", "r-one")
        r["status"] = "proposed"
        r["approval"]["state"] = "pending"
        r["note"]["name"] = PAYLOAD
        r["needs"] = [PAYLOAD]
        r["review"]["comments"] = [PAYLOAD]
        r["proposal"]["hook"] = PAYLOAD
        state.save(self.cfg, r)
        self.token = "secret-token-value"
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(self.cfg, self.token))
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, args=(0.01,), daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def req(self, method: str, path: str, body: object = None, headers: dict | None = None, token: str | None = "",
            raw: bytes | None = None) -> tuple[int, str, dict]:
        """token="" sends the right token, None sends none, anything else sends that value."""
        h = {}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        if method == "POST":
            h["Content-Type"] = "application/json"
            if token is not None:
                h["X-Factory-Token"] = self.token if token == "" else token
        h.update(headers or {})
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        text = r.read().decode("utf-8", "replace")
        out = (r.status, text, dict(r.getheaders()))
        c.close()
        return out

    def decide(self, **kw) -> tuple[int, str, dict]:
        return self.req("POST", "/api/decide", {"id": "r-one", "decision": "approve", **kw.pop("body", {})}, **kw)

    def approval_exists(self, rid: str = "r-one") -> bool:
        return (self.cfg.reel_dir(rid) / "approval.json").exists()

    def snapshot(self) -> dict:
        return {str(p.relative_to(self.cfg.home)): p.read_bytes() for p in self.cfg.home.rglob("*") if p.is_file()}


class Binding(Base):
    def test_serve_binds_loopback_only(self) -> None:
        import inspect
        src = inspect.getsource(web.serve)
        self.assertIn('("127.0.0.1", port)', src)
        self.assertNotIn("0.0.0.0", inspect.getsource(web))

    def test_test_server_is_loopback(self) -> None:
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")


class PostNeedsToken(Base):
    def test_every_post_without_token_is_403_and_changes_nothing(self) -> None:
        before = self.snapshot()
        for path in ("/api/decide", "/api/review-result", "/api/tick", "/", "/anything", "/api/reels"):
            for token in (None, "", "wrong", self.token + "x", self.token[:-1], "\u00e9\u00e9"):
                if token == "":
                    continue  # "" means "send the right token" in req()
                code, body, _ = self.req("POST", path, {"id": "r-one", "decision": "approve"}, token=token)
                self.assertEqual(code, 403, (path, token))
                self.assertNotIn(self.token, body)
        # the empty-string token explicitly
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("POST", "/api/decide", body=b'{"id":"r-one","decision":"approve"}',
                  headers={"Content-Type": "application/json", "X-Factory-Token": ""})
        self.assertEqual(c.getresponse().status, 403)
        c.close()
        self.assertEqual(self.snapshot(), before)

    def test_right_token_still_works(self) -> None:
        code, body, _ = self.decide(body={"comment": "ok"})
        self.assertEqual(code, 200, body)
        self.assertTrue(self.approval_exists())

    def test_token_in_query_string_or_body_is_not_accepted(self) -> None:
        code, _, _ = self.req("POST", f"/api/decide?token={self.token}", {"id": "r-one", "decision": "approve"}, token=None)
        self.assertEqual(code, 403)
        code, _, _ = self.req("POST", "/api/decide", {"id": "r-one", "decision": "approve", "token": self.token}, token=None)
        self.assertEqual(code, 403)
        self.assertFalse(self.approval_exists())

    def test_old_form_endpoints_are_gone(self) -> None:
        for path in ("/decide", "/tick"):
            code, _, _ = self.req("POST", path, {"id": "r-one", "decision": "approve"})
            self.assertEqual(code, 404, path)
        self.assertFalse(self.approval_exists())

    def test_foreign_origin_is_refused_even_with_the_token(self) -> None:
        for origin in ("https://evil.example", "http://localhost.evil.example", "http://127.0.0.1.evil.example", "null"):
            code, _, _ = self.decide(headers={"Origin": origin})
            self.assertEqual(code, 403, origin)
        self.assertFalse(self.approval_exists())

    def test_form_content_type_is_refused(self) -> None:
        # a cross-site <form> can only send these three types without a CORS preflight
        for ctype in ("application/x-www-form-urlencoded", "text/plain", "multipart/form-data; boundary=x"):
            code, _, _ = self.req("POST", "/api/decide", headers={"Content-Type": ctype}, raw=b'{"id":"r-one","decision":"approve"}')
            self.assertEqual(code, 400, ctype)
        self.assertFalse(self.approval_exists())

    def test_malformed_content_length_is_400_and_changes_nothing(self) -> None:
        before = self.snapshot()
        for value in (b"abc", b"-5"):
            s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
            s.sendall(b"POST /api/decide HTTP/1.1\r\nHost: localhost\r\nContent-Length: " + value + b"\r\n\r\n")
            data = s.recv(300)
            s.close()
            self.assertIn(b" 400 ", data.split(b"\r\n")[0] + b" ", (value, data))
        self.assertEqual(self.snapshot(), before)

    def test_huge_body_is_413_and_not_read(self) -> None:
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(b"POST /api/decide HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                  b"Content-Length: 99999999999\r\n\r\n")
        data = s.recv(300)
        s.close()
        self.assertIn(b" 413 ", data.split(b"\r\n")[0] + b" ")

    def test_body_just_over_the_cap_is_413_with_a_real_token(self) -> None:
        big = json.dumps({"id": "r-one", "decision": "approve", "comment": "x" * web.MAX_BODY}).encode()
        code, _, _ = self.req("POST", "/api/decide", raw=big)
        self.assertEqual(code, 413)
        self.assertFalse(self.approval_exists())

    def test_foreign_host_header_is_refused(self) -> None:
        # DNS rebinding: a page on evil.example resolving to 127.0.0.1 must not be able to read the token page
        for method, path in (("GET", "/"), ("GET", "/review"), ("GET", "/api/reels"), ("GET", "/ui/app.js"), ("POST", "/api/decide")):
            for host in ("evil.example", "evil.example:80", "localhost.evil.example", "127.0.0.1.evil.example:1"):
                code, body, _ = self.req(method, path, {} if method == "POST" else None, headers={"Host": host})
                self.assertEqual(code, 403, (path, host))
                self.assertNotIn(self.token, body)

    def test_localhost_host_headers_are_fine(self) -> None:
        for host in ("localhost:8765", "127.0.0.1:1", "localhost", "[::1]:8765"):
            self.assertEqual(self.req("GET", "/api/reels", headers={"Host": host})[0], 200, host)


class NoLeaks(Base):
    def test_token_not_in_any_api_json_static_file_or_404(self) -> None:
        for path in API_GETS + ("/nope", "/api/nope", "/reels/..", "/ui/app.js", "/ui/app.css", "/ui/index.html"):
            _, body, headers = self.req("GET", path)
            self.assertNotIn(self.token, body, path)
            self.assertNotIn(self.token, json.dumps(headers), path)

    def test_token_only_in_the_injected_meta_of_the_pages(self) -> None:
        for path in ("/", "/review", "/agents", "/themes", "/assets", "/reels/r-one"):
            _, body, h = self.req("GET", path)
            self.assertEqual(body.count(self.token), 1, path)
            self.assertIn(f'<meta name="factory-token" content="{self.token}">', body)
            self.assertEqual(h.get("Cache-Control"), "no-store")

    def test_token_not_in_post_responses(self) -> None:
        for path, body in (("/api/decide", {"id": "r-one", "decision": "approve"}), ("/api/tick", {}),
                           ("/api/review-result", {"id": "r-one", "result": "approved"}), ("/api/decide", {"id": self.token})):
            _, text, h = self.req("POST", path, body)
            self.assertNotIn(self.token, text + json.dumps(h), path)

    def test_refusal_message_does_not_echo_token(self) -> None:
        for token in ("wrong", self.token + "x"):
            _, body, _ = self.req("POST", "/api/decide", {"id": self.token}, token=token)
            self.assertNotIn(self.token, body)

    def test_api_never_returns_transcript_text_or_folder_paths(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["transcript"] = {"path": "/private/place/t.txt", "source": "manual", "trust": "high", "text": "SECRET WORDS"}
        r["files"] = [{"path": "/private/place/clip.mp4", "kind": "video", "seconds": 1.0}]
        state.save(self.cfg, r)
        for path in ("/api/reels", "/api/reels/r-one"):
            _, body, _ = self.req("GET", path)
            self.assertNotIn("SECRET WORDS", body)
            self.assertNotIn("/private/place", body)
        self.assertIn("clip.mp4", self.req("GET", "/api/reels/r-one")[1])


class Escaping(Base):
    """The server sends data as JSON and the console draws it with textContent; no HTML page ever contains it."""

    def test_pages_never_contain_reel_data(self) -> None:
        for path in ("/", "/review", "/reels/r-one"):
            _, body, _ = self.req("GET", path)
            self.assertNotIn(PAYLOAD, body, path)
            self.assertNotIn("alert(1)", body, path)

    def test_api_is_json_not_html(self) -> None:
        for path in API_GETS:
            _, body, h = self.req("GET", path)
            self.assertTrue(h["Content-Type"].startswith("application/json"), path)
            json.loads(body)  # valid JSON; the payload is a plain string inside it
        self.assertIn("alert(1)", self.req("GET", "/api/reels/r-one")[1])
        self.assertEqual(self.req("GET", "/api/reels")[2]["X-Content-Type-Options"], "nosniff")

    def test_error_bodies_do_not_reflect_input(self) -> None:
        for path in (f"/api/reels/{PAYLOAD}", f"/nope{PAYLOAD}", "/reels/%3Cscript%3Ealert(1)%3C/script%3E"):
            _, body, h = self.req("GET", path)
            self.assertNotIn("<script>", body, path)
            self.assertNotIn("alert(1)", body, path)
        code, body, _ = self.req("POST", "/api/decide", {"id": PAYLOAD, "decision": PAYLOAD})
        self.assertEqual(code, 400)
        self.assertNotIn("<script>", body)

    def test_console_uses_textcontent_only(self) -> None:
        js = (web.UI_DIR / "app.js").read_text()
        self.assertEqual(js.count(".innerHTML"), 1)  # the icon helper, fed only by constants
        self.assertIn("s.innerHTML = PATHS[name] || ''", js)
        for bad in ("outerHTML", "insertAdjacentHTML", "document.write", "eval(", "new Function", "setAttribute('on", 'setAttribute("on', ".srcdoc"):
            self.assertNotIn(bad, js, bad)
        html = (web.UI_DIR / "index.html").read_text()
        for bad in (" onclick=", " onload=", " onerror=", "style=", "javascript:"):
            self.assertNotIn(bad, html, bad)
        self.assertEqual(len(re.findall(r"<script", html)), 1)  # one external script, nothing inline

    def test_security_headers_on_every_response(self) -> None:
        for path in ("/", "/api/reels", "/ui/app.js", "/nope"):
            _, _, h = self.req("GET", path)
            csp = h["Content-Security-Policy"]
            self.assertIn("default-src 'self'", csp, path)
            self.assertIn("frame-ancestors 'none'", csp, path)
            self.assertNotIn("unsafe-inline", csp, path)
            self.assertNotIn("unsafe-eval", csp, path)
            self.assertEqual(h["X-Content-Type-Options"], "nosniff")
            self.assertEqual(h["Referrer-Policy"], "no-referrer")
        self.assertTrue(self.req("GET", "/")[2]["Content-Type"].startswith("text/html; charset=utf-8"))


class RejectNeedsReason(Base):
    def test_reject_without_reason_over_http_changes_nothing(self) -> None:
        for comment in ("", "   ", "\t\n", None):
            code, body, _ = self.req("POST", "/api/decide", {"id": "r-one", "decision": "reject", "comment": comment})
            self.assertEqual(code, 400, comment)
            self.assertIn("reason", json.loads(body)["error"])
        self.assertFalse(self.approval_exists())
        self.assertEqual(state.load(self.cfg, "r-one")["status"], "proposed")

    def test_reject_with_reason_works(self) -> None:
        code, _, _ = self.req("POST", "/api/decide", {"id": "r-one", "decision": "reject", "comment": "wrong theme"})
        self.assertEqual(code, 200)
        self.assertTrue(self.approval_exists())

    def test_unknown_decision_is_not_an_approval(self) -> None:
        before = self.snapshot()
        for decision in ("maybe", "APPROVE", "approved", "", None, 1, ["approve"], {"a": 1}):
            code, _, _ = self.req("POST", "/api/decide", {"id": "r-one", "decision": decision, "comment": "hi"})
            self.assertEqual(code, 400, decision)
        self.assertEqual(self.snapshot(), before)

    def test_decide_function_refuses_unknown_decision(self) -> None:
        msg = web.decide(self.cfg, "r-one", "maybe", "hi")
        self.assertIn("approve or reject", msg)
        self.assertFalse(self.approval_exists())

    def test_wrong_status_is_409_and_changes_nothing(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        before = self.snapshot()
        self.assertEqual(self.req("POST", "/api/decide", {"id": "r-one", "decision": "approve"})[0], 409)
        self.assertEqual(self.req("POST", "/api/review-result", {"id": "r-one", "result": "approved"})[0], 409)
        self.assertEqual(self.snapshot(), before)

    def test_review_result_needs_a_reason_for_changes_and_a_known_result(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "in_review"
        state.save(self.cfg, r)
        before = self.snapshot()
        for body in ({"result": "changes", "comment": " "}, {"result": "wow"}, {"result": None}, {"result": "changes", "comment": 5}):
            self.assertEqual(self.req("POST", "/api/review-result", {"id": "r-one", **body})[0], 400, body)
        self.assertEqual(self.req("POST", "/api/review-result", {"id": "r-one", "result": "changes", "comment": "x" * 2001})[0], 400)
        self.assertEqual(self.snapshot(), before)


def quiet_main(argv, cfg):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return cli.main(argv, cfg=cfg)


class PathTraversal(Base):
    EVIL = ["../../etc", "..", "../home/state/r-one", "/etc", "a/../../x", "r-one/..", "", ".", "..%2f", "r one", "r-one\x00"]

    def plant_outside_reel(self) -> Path:
        """A reel.json OUTSIDE state/, reachable as ../outside from a state id."""
        out = self.cfg.home / "outside"
        out.mkdir()
        r = state.new_record("Outside", "/in", "outside")
        r["status"] = "proposed"
        r["approval"]["state"] = "pending"
        (out / "reel.json").write_text(json.dumps(r), encoding="utf-8")
        return out

    def test_state_load_rejects_bad_ids(self) -> None:
        self.plant_outside_reel()
        for rid in self.EVIL + ["../outside"]:
            with self.assertRaises(state.UnknownReel, msg=repr(rid)):
                state.load(self.cfg, rid)

    def test_http_api_cannot_reach_outside_state(self) -> None:
        out = self.plant_outside_reel()
        before = self.snapshot()
        for rid in ("../outside", "../../etc", "..", "a/b", "r-one/..", "..%2foutside", "", ".", "r one", "r-one\x00", "x" * 300):
            code, _, _ = self.req("POST", "/api/decide", {"id": rid, "decision": "approve", "comment": "x"})
            self.assertEqual(code, 400, rid)
            code, _, _ = self.req("POST", "/api/review-result", {"id": rid, "result": "approved"})
            self.assertEqual(code, 400, rid)
        for path in ("/api/reels/..", "/api/reels/..%2foutside", "/api/reels/%2e%2e", "/api/reels/a%2fb", "/api/reels/", "/api/reels/outside/x"):
            self.assertIn(self.req("GET", path)[0], (400, 404), path)
        self.assertEqual(self.req("GET", "/api/reels/ghost")[0], 404)
        for path in ("/reels/..", "/reels/outside/x", "/reels/a.b"):
            self.assertEqual(self.req("GET", path)[0], 404, path)
        self.assertFalse((out / "approval.json").exists())
        self.assertEqual(self.snapshot(), before)

    def test_cli_approve_and_show_cannot_reach_outside_state(self) -> None:
        out = self.plant_outside_reel()
        for argv in (["approve", "../outside"], ["reject", "../outside", "no"], ["show", "../outside"], ["done", "../outside", "/etc/hosts"]):
            self.assertEqual(quiet_main(argv, self.cfg), 2, argv)
        self.assertFalse((out / "approval.json").exists())

    def test_reel_dir_refuses_escaping_ids(self) -> None:
        for rid in ("..", "../x", "a/b", "/abs", ""):
            with self.assertRaises(ValueError, msg=repr(rid)):
                self.cfg.reel_dir(rid)

    def test_generated_ids_stay_valid(self) -> None:
        for name in ("../../etc", "Сурагч 1", "a/b\\c", "..", "  "):
            rid = state.unique_id(self.cfg, name)
            self.assertTrue(re.fullmatch(r"\w[\w-]*", rid), rid)
            self.cfg.reel_dir(rid)  # does not raise


class DoneCommand(Base):
    """`done` only records paths of files that exist; it never reads, copies or serves them."""

    def test_done_records_paths_but_api_shows_basenames_only(self) -> None:
        f = self.root / "deep" / "dir" / "out.mp4"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        self.assertEqual(quiet_main(["done", "r-one", str(f)], self.cfg), 0)
        _, body, _ = self.req("GET", "/api/reels/r-one")
        # the ONLY route that serves files does not exist: no path in the URL space returns file contents
        self.assertNotIn(str(f.parent), body)
        code, _, _ = self.req("GET", "/file?path=" + str(f))
        self.assertEqual(code, 404)

    def test_done_refuses_missing_files(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        self.assertEqual(quiet_main(["done", "r-one", str(self.root / "nope.mp4")], self.cfg), 1)


class FetchAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("fetch_assets", Path(__file__).resolve().parents[2] / "assets" / "fetch_assets.py")
        cls.fa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.fa)

    def test_manifest_path_cannot_escape_assets(self) -> None:
        for bad in ("../x.mp3", "music/../../x.mp3", "/etc/passwd"):
            with self.assertRaises(ValueError, msg=bad):
                self.fa.path_of({"file": bad})
        self.fa.path_of({"file": "music/ok.mp3"})  # fine

    def test_only_https_sources(self) -> None:
        for url in ("file:///etc/passwd", "http://example.com/a.mp3", "ftp://x/a.mp3"):
            with self.assertRaises(RuntimeError, msg=url):
                self.fa.download({"file": "music/ok.mp3", "source_url": url})

    def test_shipped_manifest_is_https_and_inside_assets(self) -> None:
        for _, e in self.fa.entries(self.fa.load()):
            if e.get("source_url"):
                self.assertTrue(e["source_url"].startswith("https://"), e["file"])
            self.fa.path_of(e)


if __name__ == "__main__":
    unittest.main()
