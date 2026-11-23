"""Tests for the daily review. A fixed clock and a fake git runner, no real repo."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from factory import review

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 20, 18, 0, tzinfo=TZ)
SECTIONS = ["## Failing", "## Working", "## Needs you", "## Added and updated", "## Tomorrow"]


def rec(rid, status, history, **extra) -> dict:
    r = {"id": rid, "name": rid.upper(), "status": status, "history": history,
         "needs": [], "approval": {"state": "none"}, "review": {"state": "none", "comments": []},
         "proposal": {"open_questions": []}, "updated": history[-1]["at"]}
    r.update(extra)
    return r


def h(at, frm, to):
    return {"at": at, "from": frm, "to": to, "why": ""}


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cfg = SimpleNamespace(home=root, state_dir=root / "state", repo=root / "repo")

    def put(self, r: dict) -> None:
        d = self.cfg.state_dir / r["id"]
        d.mkdir(parents=True)
        (d / "reel.json").write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")

    def run_review(self, git="", date=None):
        return review.build(self.cfg, date, now=NOW, git_runner=lambda cmd: git)

    def test_empty_has_every_section_in_order(self):
        md = self.run_review()
        self.assertTrue(md.startswith("# Editing factory: daily review, 2026-11-20"))
        positions = [md.index(s) for s in SECTIONS]
        self.assertEqual(positions, sorted(positions))
        self.assertGreaterEqual(md.count("Nothing today."), 5)
        self.assertIn("0 reels", md)

    def test_summary_counts(self):
        self.put(rec("a", "proposed", [h("2026-11-20T09:00:00+08:00", "detecting", "proposed")],
                     approval={"state": "pending"}))
        self.put(rec("b", "editing", [h("2026-11-20T10:00:00+08:00", "approved", "editing")]))
        self.put(rec("c", "done", [h("2026-11-20T11:00:00+08:00", "in_review", "done")]))
        md = self.run_review()
        self.assertIn("3 reels: 1 waiting for approval, 1 editing, 1 done", md)

    def test_stuck_and_needs_are_failing(self):
        self.put(rec("old", "proposed", [h("2026-11-19T10:00:00+08:00", "detecting", "proposed")],
                     approval={"state": "pending"}))
        self.put(rec("fresh", "editing", [h("2026-11-20T09:00:00+08:00", "approved", "editing")]))
        self.put(rec("sick", "new", [h("2026-11-20T09:00:00+08:00", "", "new")],
                     needs=["Name is missing: add `name:` to note.txt"]))
        self.put(rec("fin", "done", [h("2026-11-01T09:00:00+08:00", "x", "done")]))
        failing = self.run_review().split("## Failing")[1].split("## Working")[0]
        self.assertIn("OLD", failing)
        self.assertIn("32 hours", failing)
        self.assertIn("Name is missing", failing)
        self.assertNotIn("FRESH", failing)
        self.assertNotIn("FIN", failing)

    def test_working_lists_changes_on_the_date_only(self):
        self.put(rec("a", "editing", [h("2026-11-19T09:00:00+08:00", "", "new"),
                                      h("2026-11-20T09:00:00+08:00", "approved", "editing")]))
        self.put(rec("b", "done", [h("2026-11-20T12:00:00+08:00", "in_review", "done")]))
        working = self.run_review().split("## Working")[1].split("## Needs you")[0]
        self.assertIn("A: approved -> editing", working)
        self.assertNotIn("-> new", working)
        self.assertIn("B: finished", working)

    def test_needs_you(self):
        self.put(rec("a", "proposed", [h("2026-11-20T09:00:00+08:00", "detecting", "proposed")],
                     approval={"state": "pending"}, proposal={"open_questions": ["Theme is a guess (30%)"]}))
        self.put(rec("b", "changes", [h("2026-11-20T09:00:00+08:00", "in_review", "changes")],
                     review={"state": "changes", "comments": ["Fix the caption on line 2"]}))
        needs = self.run_review().split("## Needs you")[1].split("## Added")[0]
        self.assertIn("python3 -m factory approve a", needs)
        self.assertIn("Theme is a guess (30%)", needs)
        self.assertIn("Fix the caption on line 2", needs)

    def test_git_grouping(self):
        git = "\n".join([
            "abc1234\tAdd theme card",
            "plugins/pinecone-video/skills/edit-reel/references/themes/x.md",
            "",
            "def5678\tTune engine",
            "plugins/pinecone-video/skills/interview-reel/engine/a.py",
            "factory/factory/detect.py",
            "",
            "0a0a0a0\tTouch skill and asset",
            "plugins/pinecone-video/skills/edit-reel/SKILL.md",
            "assets/MANIFEST.json",
            "README.md",
        ])
        added = self.run_review(git=git).split("## Added and updated")[1].split("## Tomorrow")[0]
        themes, engine = added.index("Themes"), added.index("Engine")
        self.assertLess(themes, engine)
        self.assertIn("abc1234 Add theme card", added.split("Engine")[0])
        engine_block = added.split("Engine")[1].split("Skills")[0]
        self.assertIn("def5678", engine_block)
        self.assertNotIn("0a0a0a0", engine_block)  # engine path checked before the generic skills path
        for group in ("Skills", "Factory", "Assets", "Other"):
            self.assertIn(group, added)

    def test_git_runner_gets_since_midnight(self):
        seen = []
        review.build(self.cfg, "2026-11-19", now=NOW, git_runner=lambda c: seen.append(c) or "")
        cmd = " ".join(seen[0])
        self.assertIn("--since=2026-11-19 00:00", cmd)
        self.assertIn(str(self.cfg.repo), cmd)

    def test_git_failure_is_a_sentence_not_an_exception(self):
        def boom(cmd):
            raise OSError("no git")
        md = review.build(self.cfg, None, now=NOW, git_runner=boom)
        self.assertIn("Could not read git log.", md)

    def test_tomorrow_per_open_reel(self):
        self.put(rec("a", "approved", [h("2026-11-20T09:00:00+08:00", "proposed", "approved")]))
        self.put(rec("b", "done", [h("2026-11-20T09:00:00+08:00", "in_review", "done")]))
        tomorrow = self.run_review().split("## Tomorrow")[1]
        self.assertIn("A: will write EDIT_REQUEST.md", tomorrow)
        self.assertNotIn("B:", tomorrow)

    def test_broken_record_is_skipped(self):
        d = self.cfg.state_dir / "bad"
        d.mkdir(parents=True)
        (d / "reel.json").write_text("{nope")
        self.assertIn("0 reels", self.run_review())


if __name__ == "__main__":
    unittest.main()
