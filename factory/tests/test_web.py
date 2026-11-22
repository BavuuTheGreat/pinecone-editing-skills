import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from factory import state, web
from factory.config import Config

TOKEN = "tok-123"


class WebTest(unittest.TestCase):
    """The decision logic, then the real HTTP server on a random local port."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home")
        r = state.new_record("Reel <b>One</b>", "/in", "r-one")
        r["status"] = "proposed"
        r["approval"]["state"] = "pending"
        r["detection"] = {"theme": "pinequest-testimonial", "confidence": 0.52, "scores": {"podcast-clip": 0.1}, "evidence": ["'pinequest' x1"]}
        r["transcript"] = {"path": "/x", "source": "manual", "trust": "high", "text": "SECRET WORDS"}
        r["files"] = [{"path": "/Users/someone/Downloads/clip.mp4", "kind": "video", "seconds": 12.5}]
        r["needs"] = ["Name is missing"]
        state.save(self.cfg, r)
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(self.cfg, TOKEN))
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def call(self, method: str, path: str, body=None, headers=None, token=TOKEN, raw: bytes | None = None, host: str | None = None):
        h = {"Host": host or f"127.0.0.1:{self.port}"}
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
        if method == "POST":
            h.setdefault("Content-Type", "application/json")
            if token is not None:
                h["X-Factory-Token"] = token
        h.update(headers or {})
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def jcall(self, *a, **k):
        code, _, body = self.call(*a, **k)
        return code, json.loads(body)

    # ---- decide()
    def test_approve_writes_decision(self) -> None:
        self.assertIn("Approved", web.decide(self.cfg, "r-one", "approve", "go"))
        self.assertTrue((self.cfg.reel_dir("r-one") / "approval.json").exists())

    def test_reject_needs_a_reason(self) -> None:
        self.assertIn("reason", web.decide(self.cfg, "r-one", "reject", "  "))
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())
        self.assertIn("Rejected", web.decide(self.cfg, "r-one", "reject", "wrong theme"))

    def test_nothing_to_decide_when_not_proposed(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        self.assertIn("nothing to decide", web.decide(self.cfg, "r-one", "approve", ""))

    # ---- reads
    def test_reels_list_and_detail(self) -> None:
        code, reels = self.jcall("GET", "/api/reels")
        self.assertEqual(code, 200)
        self.assertEqual(reels[0]["id"], "r-one")
        self.assertTrue(reels[0]["awaiting_you"])
        self.assertEqual(reels[0]["theme_label"], "PineQuest impression (participant / judge)")
        code, d = self.jcall("GET", "/api/reels/r-one")
        self.assertEqual(code, 200)
        self.assertEqual(d["name"], "Reel <b>One</b>")  # raw JSON: the client escapes, the server does not rewrite names
        self.assertEqual(d["files"][0]["name"], "clip.mp4")  # a basename, never the folder path
        self.assertNotIn("SECRET WORDS", json.dumps(d))  # transcript text stays on disk
        self.assertEqual(d["transcript"], {"source": "manual", "trust": "high"})

    def test_unknown_and_bad_reel_ids(self) -> None:
        self.assertEqual(self.call("GET", "/api/reels/nope")[0], 404)
        for bad in ("..", "%2e%2e", "a.b", "%00"):
            self.assertEqual(self.call("GET", f"/api/reels/{bad}")[0], 400, bad)
        self.assertEqual(self.call("GET", "/api/reels/a%2Fb")[0], 404)  # a slash is a different path, never an id
        self.assertEqual(self.call("GET", "/api/reels/" + "x" * 300)[0], 400)

    def test_review_agents_themes_assets(self) -> None:
        code, rv = self.jcall("GET", "/api/review")
        self.assertEqual(code, 200)
        self.assertEqual([s["title"] for s in rv["sections"]], ["Failing", "Working", "Needs you", "Added and updated", "Tomorrow"])
        self.assertTrue(any("Name is missing" in i for i in rv["sections"][0]["items"]))
        code, ag = self.jcall("GET", "/api/agents")
        self.assertEqual(code, 200)
        self.assertEqual([a["key"] for a in ag][:3], ["intake", "listener", "planner"])
        planner = next(a for a in ag if a["key"] == "planner")
        self.assertEqual(planner["waiting_on_you"][0]["id"], "r-one")  # a proposed reel waits for the person, not an agent
        self.assertFalse(next(a for a in ag if a["key"] == "analyst")["built"])
        code, th = self.jcall("GET", "/api/themes")
        self.assertEqual(code, 200)
        self.assertIn("pinequest-testimonial", [t["key"] for t in th])
        code, assets = self.jcall("GET", "/api/assets")
        self.assertEqual(code, 200)
        self.assertTrue(assets["items"])
        self.assertIn("credit", assets["items"][0])

    def test_agents_show_reels_in_their_hands(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        ag = self.jcall("GET", "/api/agents")[1]
        self.assertEqual(next(a for a in ag if a["key"] == "editor")["acting_on"][0]["id"], "r-one")

    # ---- writes: the security properties
    def test_post_without_token_is_refused(self) -> None:
        body = {"id": "r-one", "decision": "approve"}
        self.assertEqual(self.call("POST", "/api/decide", body, token=None)[0], 403)
        self.assertEqual(self.call("POST", "/api/decide", body, token="wrong")[0], 403)
        self.assertEqual(self.call("POST", "/api/tick", {}, token=None)[0], 403)
        self.assertEqual(self.call("POST", "/api/review-result", {}, token="")[0], 403)
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())

    def test_cross_origin_and_foreign_host_are_refused(self) -> None:
        body = {"id": "r-one", "decision": "approve"}
        self.assertEqual(self.call("POST", "/api/decide", body, headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/decide", body, headers={"Origin": "http://localhost.evil.example"})[0], 403)
        self.assertEqual(self.call("POST", "/api/decide", body, host="evil.example")[0], 403)
        self.assertEqual(self.call("GET", "/api/reels", host="evil.example:80")[0], 403)  # DNS rebinding
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())
        ok = self.call("POST", "/api/decide", body, headers={"Origin": f"http://localhost:{self.port}"})
        self.assertEqual(ok[0], 200)

    def test_post_needs_json(self) -> None:
        self.assertEqual(self.call("POST", "/api/decide", raw=b"id=r-one&decision=approve", headers={"Content-Type": "application/x-www-form-urlencoded"})[0], 400)
        self.assertEqual(self.call("POST", "/api/decide", raw=b"{nope")[0], 400)
        self.assertEqual(self.call("POST", "/api/decide", raw=b"[1]")[0], 400)

    def test_decide_endpoint(self) -> None:
        self.assertEqual(self.call("POST", "/api/decide", {"id": "r-one", "decision": "reject", "comment": " "})[0], 400)
        self.assertEqual(self.call("POST", "/api/decide", {"id": "../x", "decision": "approve"})[0], 400)
        self.assertEqual(self.call("POST", "/api/decide", {"id": "ghost", "decision": "approve"})[0], 404)
        self.assertEqual(self.call("POST", "/api/decide", {"id": "r-one", "decision": "maybe"})[0], 400)
        code, out = self.jcall("POST", "/api/decide", {"id": "r-one", "decision": "reject", "comment": "wrong theme"})
        self.assertEqual((code, out["ok"]), (200, True))
        d = json.loads((self.cfg.reel_dir("r-one") / "approval.json").read_text())
        self.assertEqual((d["state"], d["comment"], d["by"]), ("rejected", "wrong theme", "dashboard"))
        self.assertEqual(self.jcall("GET", "/api/reels")[1][0]["decided"], "rejected")

    def test_decide_conflict_when_not_proposed(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        self.assertEqual(self.call("POST", "/api/decide", {"id": "r-one", "decision": "approve"})[0], 409)

    def test_review_result_endpoint(self) -> None:
        self.assertEqual(self.call("POST", "/api/review-result", {"id": "r-one", "result": "approved"})[0], 409)  # not in review
        r = state.load(self.cfg, "r-one")
        r["status"] = "in_review"
        state.save(self.cfg, r)
        self.assertEqual(self.call("POST", "/api/review-result", {"id": "r-one", "result": "changes", "comment": ""})[0], 400)
        self.assertEqual(self.call("POST", "/api/review-result", {"id": "r-one", "result": "wow"})[0], 400)
        self.assertEqual(self.call("POST", "/api/review-result", {"id": "nope", "result": "approved"})[0], 404)
        self.assertEqual(self.call("POST", "/api/review-result", {"id": "r-one", "result": "changes", "comment": "cut at 0:12"})[0], 200)
        rec = state.load(self.cfg, "r-one")
        self.assertEqual((rec["review"]["state"], rec["review"]["comments"]), ("changes", ["cut at 0:12"]))

    def test_tick_endpoint(self) -> None:
        code, out = self.jcall("POST", "/api/tick", {})
        self.assertEqual(code, 200)
        self.assertIn("message", out)
        self.assertIsInstance(out["log"], list)

    def test_unknown_post_path(self) -> None:
        self.assertEqual(self.call("POST", "/api/nothing", {})[0], 404)
        self.assertEqual(self.call("POST", "/decide", {})[0], 404)

    # ---- static + pages
    def test_index_gets_the_token_and_deep_links_work(self) -> None:
        for path in ("/", "/review", "/agents", "/themes", "/assets", "/reels/r-one", "/reels/r-one?tab=history"):
            code, hdr, body = self.call("GET", path)
            self.assertEqual(code, 200, path)
            self.assertIn("text/html", hdr["Content-Type"])
            self.assertIn(f'name="factory-token" content="{TOKEN}"', body.decode())
            self.assertNotIn("__FACTORY_TOKEN__", body.decode())
        self.assertEqual(self.call("GET", "/reels/a.b")[0], 404)
        self.assertEqual(self.call("GET", "/ui/index.html")[0], 404)  # only served through the token-injecting route

    def test_static_files_and_traversal(self) -> None:
        code, hdr, _ = self.call("GET", "/ui/app.css")
        self.assertEqual((code, hdr["Content-Type"]), (200, "text/css; charset=utf-8"))
        code, hdr, _ = self.call("GET", "/ui/app.js")
        self.assertEqual((code, hdr["Content-Type"]), (200, "text/javascript; charset=utf-8"))
        for bad in ("/ui/../factory/web.py", "/ui/%2e%2e/factory/web.py", "/ui/..%2fcli.py", "/ui/", "/ui/nope.css", "/ui//etc/passwd"):
            self.assertEqual(self.call("GET", bad)[0], 404, bad)

    def test_ui_never_puts_data_in_innerhtml(self) -> None:
        js = (web.UI_DIR / "app.js").read_text()
        self.assertEqual(js.count(".innerHTML"), 1)  # the icon helper, fed only by constants
        html = (web.UI_DIR / "index.html").read_text()
        self.assertNotIn(" onclick=", html)
        self.assertNotIn("style=", html)

    def test_binds_to_loopback_only(self) -> None:
        self.assertEqual(self.srv.server_address[0], "127.0.0.1")


if __name__ == "__main__":
    unittest.main()
