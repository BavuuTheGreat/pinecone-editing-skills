"""Security regression tests for the local dashboard and the state folder.

Threat model: SECURITY.md. The server is local only; a POST needs the page's token; a reel id from the
network or the command line can never reach outside FACTORY_HOME/state.
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

    def req(self, method: str, path: str, body: str = "", headers: dict | None = None) -> tuple[int, str, dict]:
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = {"Content-Type": "application/x-www-form-urlencoded", **(headers or {})}
        c.request(method, path, body=body or None, headers=h)
        r = c.getresponse()
        data = r.read().decode("utf-8", "replace")
        out = (r.status, data, dict(r.getheaders()))
        c.close()
        return out

    def reel_bytes(self) -> bytes:
        return (self.cfg.reel_dir("r-one") / "reel.json").read_bytes()

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
        bodies = ["", "id=r-one&decision=approve", "token=&id=r-one&decision=approve", "token=wrong&id=r-one&decision=approve",
                  f"token={self.token}x&id=r-one&decision=approve"]
        for path in ("/decide", "/tick", "/", "/anything", "/api/reels"):
            for body in bodies:
                code, _, _ = self.req("POST", path, body)
                self.assertEqual(code, 403, (path, body))
        self.assertEqual(self.snapshot(), before)

    def test_right_token_still_works(self) -> None:
        code, _, h = self.req("POST", "/decide", f"token={self.token}&id=r-one&decision=approve&comment=ok")
        self.assertEqual(code, 303)
        self.assertTrue((self.cfg.reel_dir("r-one") / "approval.json").exists())

    def test_token_in_query_string_is_not_accepted(self) -> None:
        code, _, _ = self.req("POST", f"/decide?token={self.token}", "id=r-one&decision=approve")
        self.assertEqual(code, 403)

    def test_malformed_content_length_does_not_crash_or_change_state(self) -> None:
        before = self.snapshot()
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(b"POST /decide HTTP/1.1\r\nHost: localhost\r\nContent-Length: abc\r\n\r\n")
        data = s.recv(200)
        s.close()
        self.assertTrue(data.startswith(b"HTTP/1.") and b" 4" in data.split(b"\r\n")[0], data)
        self.assertEqual(self.snapshot(), before)

    def test_huge_body_is_refused(self) -> None:
        s = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        s.sendall(b"POST /decide HTTP/1.1\r\nHost: localhost\r\nContent-Length: 99999999999\r\n\r\n")
        data = s.recv(200)
        s.close()
        self.assertIn(b" 413 ", data.split(b"\r\n")[0] + b" ")

    def test_foreign_host_header_is_refused(self) -> None:
        # DNS rebinding: a page on evil.example resolving to 127.0.0.1 must not be able to read the token page
        for method, path in (("GET", "/"), ("GET", "/api/reels"), ("POST", "/decide")):
            code, body, _ = self.req(method, path, headers={"Host": "evil.example"})
            self.assertEqual(code, 403, path)
            self.assertNotIn(self.token, body)

    def test_localhost_host_headers_are_fine(self) -> None:
        for host in ("localhost:8765", "127.0.0.1:1", "localhost"):
            self.assertEqual(self.req("GET", "/api/reels", headers={"Host": host})[0], 200, host)


class NoLeaks(Base):
    def test_token_not_in_api_or_review_or_404(self) -> None:
        for path in ("/api/reels", "/review", "/nope"):
            _, body, headers = self.req("GET", path)
            self.assertNotIn(self.token, body, path)
            self.assertNotIn(self.token, json.dumps(headers))

    def test_token_only_in_the_board_forms(self) -> None:
        _, body, h = self.req("GET", "/")
        self.assertIn(self.token, body)
        self.assertEqual(h.get("Cache-Control"), "no-store")

    def test_refusal_message_does_not_echo_token(self) -> None:
        _, body, _ = self.req("POST", "/decide", f"token=wrong&id={self.token}")
        self.assertNotIn(self.token, body)


class Escaping(Base):
    def test_board_escapes_every_field(self) -> None:
        _, body, _ = self.req("GET", "/")
        self.assertNotIn(PAYLOAD, body)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", body)

    def test_flash_message_is_escaped(self) -> None:
        from urllib.parse import quote
        _, body, _ = self.req("GET", "/?m=" + quote(PAYLOAD))
        self.assertNotIn(PAYLOAD, body)

    def test_review_page_escapes(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "in_review"
        state.save(self.cfg, r)
        _, body, _ = self.req("GET", "/review")
        self.assertNotIn(PAYLOAD, body)

    def test_attribute_context_is_escaped(self) -> None:
        r = state.new_record('x"><img src=x onerror=alert(1)>', "/in", "r-two")
        r["status"] = "proposed"
        r["approval"]["state"] = "pending"
        state.save(self.cfg, r)
        _, body, _ = self.req("GET", "/")
        self.assertNotIn('"><img', body)

    def test_html_response_is_utf8_not_sniffed_as_script(self) -> None:
        _, _, h = self.req("GET", "/")
        self.assertTrue(h["Content-Type"].startswith("text/html; charset=utf-8"))


class RejectNeedsReason(Base):
    def test_reject_without_reason_over_http_changes_nothing(self) -> None:
        for comment in ("", "   ", "%20%09"):
            code, _, h = self.req("POST", "/decide", f"token={self.token}&id=r-one&decision=reject&comment={comment}")
            self.assertEqual(code, 303)
            self.assertIn("reason", __import__("urllib.parse", fromlist=["unquote"]).unquote(h["Location"]))
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())

    def test_unknown_decision_is_not_an_approval(self) -> None:
        self.req("POST", "/decide", f"token={self.token}&id=r-one&decision=maybe&comment=hi")
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())


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

    def test_http_decide_cannot_reach_outside_state(self) -> None:
        out = self.plant_outside_reel()
        before = self.snapshot()
        for rid in ("../outside", "../../etc", ".."):
            code, _, _ = self.req("POST", "/decide", f"token={self.token}&id={rid}&decision=approve&comment=x")
            self.assertEqual(code, 303)
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

    def test_done_records_paths_but_board_shows_basenames_only(self) -> None:
        f = self.root / "deep" / "dir" / "out.mp4"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"x")
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        self.assertEqual(quiet_main(["done", "r-one", str(f)], self.cfg), 0)
        _, body, _ = self.req("GET", "/")
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
