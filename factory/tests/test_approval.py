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
