import tempfile
import unittest
from pathlib import Path

from factory import state, web
from factory.config import Config


class WebTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home")
        r = state.new_record("Reel <b>One</b>", "/in", "r-one")
        r["status"] = "proposed"
        r["approval"]["state"] = "pending"
        r["detection"] = {"theme": "pinequest-testimonial", "confidence": 0.52, "scores": {}, "evidence": ["'pinequest' x1"]}
        r["needs"] = ["Name is missing"]
        state.save(self.cfg, r)

    def test_page_shows_reel_escaped_with_buttons(self) -> None:
        h = web.page(self.cfg, "tok")
        self.assertIn("Reel &lt;b&gt;One&lt;/b&gt;", h)  # names are never trusted as HTML
        self.assertNotIn("<b>One</b>", h)
        self.assertIn("Yes, make it", h)
        self.assertIn("52% sure", h)
        self.assertIn("Name is missing", h)
        self.assertIn('value="tok"', h)

    def test_approve_writes_decision(self) -> None:
        msg = web.decide(self.cfg, "r-one", "approve", "go")
        self.assertIn("Approved", msg)
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
        self.assertNotIn("Yes, make it", web.page(self.cfg, "tok"))


if __name__ == "__main__":
    unittest.main()
