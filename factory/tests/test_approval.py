import json
import tempfile
import unittest
from pathlib import Path

from factory import approval, state
from factory.config import Config


class ApprovalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name))
        self.reel = state.new_record("R", "/in", "r")
        state.save(self.cfg, self.reel)
        self.adapter = approval.get_adapter(self.cfg)

    def test_pending_until_decided(self) -> None:
        self.adapter.post_proposal(self.reel)
        self.assertIsNone(self.adapter.read_decision(self.reel))

    def test_approve(self) -> None:
        approval.approve(self.cfg, self.reel, "go", by="boss")
        d = self.adapter.read_decision(self.reel)
        self.assertEqual((d["state"], d["by"], d["comment"]), ("approved", "boss", "go"))
        self.assertRegex(d["at"], r"[+-]\d\d:\d\d$")

    def test_reject_overwrites(self) -> None:
        approval.approve(self.cfg, self.reel)
        approval.reject(self.cfg, self.reel, "no thanks")
        self.assertEqual(self.adapter.read_decision(self.reel)["state"], "rejected")

    def test_garbage_file_is_no_decision(self) -> None:
        (self.cfg.reel_dir("r") / "approval.json").write_text("{bad")
        self.assertIsNone(self.adapter.read_decision(self.reel))

    def test_decision_older_than_the_proposal_is_ignored(self) -> None:
        approval.approve(self.cfg, self.reel, "early")
        p = self.cfg.reel_dir("r") / "approval.json"
        d = json.loads(p.read_text())
        d["at"] = "2020-01-01T00:00:00+00:00"
        p.write_text(json.dumps(d))
        self.reel["proposal"]["at"] = "2026-11-20T10:00:00+08:00"
        self.assertIsNone(self.adapter.read_decision(self.reel))
        self.reel["proposal"]["at"] = "2019-01-01T00:00:00+00:00"
        self.assertEqual(self.adapter.read_decision(self.reel)["state"], "approved")

    def test_refusal_needs_proposed_pending_and_a_proposal(self) -> None:
        r = state.new_record("R", "/in", "r2")
        self.assertIn("nothing to decide", approval.refusal(r))
        r.update(status="proposed")
        self.assertIn("nothing to decide", approval.refusal(r))
        r["approval"]["state"] = "pending"
        self.assertIn("nothing to decide", approval.refusal(r))  # no proposal.md yet
        r["proposal"]["path"] = "/x/p.md"
        self.assertIsNone(approval.refusal(r))

    def test_decide_leaves_no_fixed_tmp_file(self) -> None:
        approval.approve(self.cfg, self.reel)
        self.assertFalse((self.cfg.reel_dir("r") / "approval.json.tmp").exists())
        self.assertEqual([p.name for p in self.cfg.reel_dir("r").glob("*.tmp")], [])

    def test_planner_stub(self) -> None:
        cfg = Config(home=self.cfg.home, approval="planner")
        p = approval.get_adapter(cfg)
        for call in (p.post_proposal, p.read_decision, p.post_result):
            with self.assertRaisesRegex(NotImplementedError, "Marketing Planner API not available yet"):
                call(self.reel)

    def test_post_result_noop(self) -> None:
        self.adapter.post_result(self.reel)


if __name__ == "__main__":
    unittest.main()
