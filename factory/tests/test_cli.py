import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from factory import cli, state
from factory.config import Config

FACTORY_DIR = Path(__file__).resolve().parents[1]


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home")
        r = state.new_record("R One", "/in", "r-one")
        r["detection"] = {"theme": "pinequest", "confidence": 0.82, "scores": {}, "evidence": []}
        r["needs"] = ["Name is missing"]
        state.save(self.cfg, r)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv), cfg=self.cfg)
        return code, out.getvalue(), err.getvalue()

    def test_status_board(self) -> None:
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("r-one", out)
        self.assertIn("new", out)
        self.assertIn("pinequest (0.82)", out)
        self.assertIn("\n    Name is missing", out)

    def test_status_empty(self) -> None:
        cfg = Config(home=Path(self.tmp.name) / "empty")
        self.assertEqual(cli.main(["status"], cfg=cfg), 0)

    def test_unknown_reel_exit_2(self) -> None:
        for argv in (["show", "zzz"], ["approve", "zzz"], ["reject", "zzz", "c"], ["done", "zzz", "f"],
                     ["review-result", "zzz", "approved"]):
            self.assertEqual(self.run_cli(*argv)[0], 2, argv)

    def _proposed(self) -> None:
        r = state.load(self.cfg, "r-one")
        r.update(status="proposed")
        r["approval"]["state"] = "pending"
        r["proposal"]["path"] = "/x/proposal.md"
        state.save(self.cfg, r)

    def test_approve_reject_refused_unless_a_proposal_waits(self) -> None:
        for argv in (("approve", "r-one"), ("reject", "r-one", "no")):
            code, _, err = self.run_cli(*argv)  # status is "new"
            self.assertEqual(code, 1, argv)
            self.assertIn("nothing to decide", err)
            self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())
        r = state.load(self.cfg, "r-one")  # proposed, but the tick has not written proposal.md yet
        r["status"] = "proposed"
        state.save(self.cfg, r)
        self.assertEqual(self.run_cli("approve", "r-one")[0], 1)
        self.assertFalse((self.cfg.reel_dir("r-one") / "approval.json").exists())

    def test_tick_reports_a_running_step(self) -> None:
        import fcntl
        self.cfg.ensure_dirs()
        with open(self.cfg.tick_lock, "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            code, out, err = self.run_cli("tick")
        self.assertEqual(code, 1)
        self.assertIn("already running", out + err)

    def test_approve_reject_write_decision(self) -> None:
        self._proposed()
        self.assertEqual(self.run_cli("approve", "r-one", "good")[0], 0)
        self.assertEqual(state.load(self.cfg, "r-one")["approval"]["state"], "pending")  # tick applies it
        import json
        d = json.loads((self.cfg.reel_dir("r-one") / "approval.json").read_text())
        self.assertEqual((d["state"], d["comment"]), ("approved", "good"))
        self.run_cli("reject", "r-one", "no")
        d = json.loads((self.cfg.reel_dir("r-one") / "approval.json").read_text())
        self.assertEqual(d["state"], "rejected")

    def test_done_only_while_editing(self) -> None:
        f = Path(self.tmp.name) / "o.mp4"
        f.write_text("x")
        code, out, _ = self.run_cli("done", "r-one", str(f))  # status is "new": outputs would be lost
        self.assertEqual(code, 1)
        self.assertIn("not editing", out)
        self.assertEqual(state.load(self.cfg, "r-one")["edit"]["outputs"], [])

    def test_done_validates_files(self) -> None:
        r = state.load(self.cfg, "r-one")
        r["status"] = "editing"
        state.save(self.cfg, r)
        code, _, err = self.run_cli("done", "r-one", "/nope/x.mp4")
        self.assertEqual(code, 1)
        self.assertIn("x.mp4", err)
        f = Path(self.tmp.name) / "o.mp4"
        f.write_text("x")
        self.assertEqual(self.run_cli("done", "r-one", str(f))[0], 0)
        self.assertEqual(state.load(self.cfg, "r-one")["edit"]["outputs"], [str(f)])

    def test_review_result(self) -> None:
        r = state.load(self.cfg, "r-one")
        self.assertEqual(self.run_cli("review-result", "r-one", "approved")[0], 1)  # not in review yet
        r["status"] = "in_review"
        state.save(self.cfg, r)
        self.assertEqual(self.run_cli("review-result", "r-one", "changes", "cut earlier")[0], 0)
        r = state.load(self.cfg, "r-one")
        self.assertEqual((r["review"]["state"], r["review"]["comments"]), ("changes", ["cut earlier"]))
        self.assertEqual(self.run_cli("review-result", "r-one", "maybe")[0], 1)

    def test_show(self) -> None:
        code, out, _ = self.run_cli("show", "r-one")
        self.assertEqual(code, 0)
        self.assertIn('"id": "r-one"', out)

    def test_loop_runs_bounded(self) -> None:
        code, _, _ = self.run_cli("loop", "--every", "0", "--max-runs", "2")
        self.assertEqual(code, 0)

    def test_module_entrypoint_on_empty_home(self) -> None:
        env = {**os.environ, "FACTORY_HOME": str(Path(self.tmp.name) / "fresh")}
        p = subprocess.run([sys.executable, "-m", "factory", "status"], cwd=FACTORY_DIR, env=env,
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)


if __name__ == "__main__":
    unittest.main()
