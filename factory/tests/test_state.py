import json
import re
import tempfile
import unittest
from pathlib import Path

from factory import state
from factory.config import Config

SPEC_KEYS = ["id", "name", "inbox_path", "status", "created", "updated", "files", "note", "transcript",
             "detection", "proposal", "approval", "edit", "review", "needs", "history"]


class StateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name))

    def test_slug_keeps_cyrillic_and_collapses(self) -> None:
        self.assertEqual(state.slugify("2026-11-20 PineQuest Сурагч"), "2026-11-20-pinequest-сурагч")
        self.assertEqual(state.slugify("  A!!  b__c -- d "), "a-b-c-d")
        self.assertEqual(state.slugify("!!!"), "reel")

    def test_unique_id_suffix_on_collision(self) -> None:
        a = state.unique_id(self.cfg, "My Reel")
        state.save(self.cfg, state.new_record("My Reel", "/x", a))
        b = state.unique_id(self.cfg, "my reel")
        self.assertEqual((a, b), ("my-reel", "my-reel-2"))
        state.save(self.cfg, state.new_record("my reel", "/y", b))
        self.assertEqual(state.unique_id(self.cfg, "My  Reel"), "my-reel-3")

    def test_new_record_matches_spec(self) -> None:
        r = state.new_record("N", "/in/N", "n")
        self.assertEqual(list(r), SPEC_KEYS)
        self.assertEqual(r["status"], "new")
        self.assertEqual(r["approval"]["state"], "none")
        self.assertEqual(r["review"], {"state": "none", "comments": []})
        self.assertRegex(r["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        self.assertEqual(r["history"][0]["to"], "new")

    def test_save_load_atomic(self) -> None:
        r = state.new_record("Сурагч", "/in", "сурагч")
        state.save(self.cfg, r)
        self.assertEqual(state.load(self.cfg, "сурагч"), r)
        left = [p.name for p in (self.cfg.state / "сурагч").iterdir()]
        self.assertEqual(left, ["reel.json"])
        self.assertIn("Сурагч", (self.cfg.state / "сурагч" / "reel.json").read_text(encoding="utf-8"))

    def test_load_unknown(self) -> None:
        with self.assertRaises(state.UnknownReel):
            state.load(self.cfg, "nope")

    def test_list_reels_sorted_and_skips_corrupt(self) -> None:
        for n in ("b", "a"):
            state.save(self.cfg, state.new_record(n, "/", n))
        bad = self.cfg.state / "bad"
        bad.mkdir()
        (bad / "reel.json").write_text("{nope")
        self.assertEqual([r["id"] for r in state.list_reels(self.cfg)], ["a", "b"])

    def test_set_status_appends_history(self) -> None:
        r = state.new_record("n", "/", "n")
        state.set_status(r, "transcribing", "probed")
        self.assertEqual(r["status"], "transcribing")
        self.assertEqual(r["history"][-1]["from"], "new")
        self.assertEqual(r["history"][-1]["to"], "transcribing")
        self.assertEqual(r["history"][-1]["why"], "probed")
        self.assertEqual(len(r["history"]), 2)

    def test_needs(self) -> None:
        r = state.new_record("n", "/", "n")
        self.assertTrue(state.add_need(r, "Name is missing"))
        self.assertFalse(state.add_need(r, "Name is missing"))
        state.add_need(r, "Error at new: x")
        state.clear_needs(r, "Error at")
        self.assertEqual(r["needs"], ["Name is missing"])
        state.clear_needs(r)
        self.assertEqual(r["needs"], [])


if __name__ == "__main__":
    unittest.main()
