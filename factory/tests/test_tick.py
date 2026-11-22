import json
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest import mock

import factory
from factory import approval, edit, state, tick
from factory.config import Config


def fake_probe(path: str) -> dict:
    return {"seconds": 30.0, "width": 1080, "height": 1920}


def make_detect(boom_for: str = "") -> types.ModuleType:
    m = types.ModuleType("factory.detect")

    def detect(reel: dict, cfg) -> dict:
        if boom_for and boom_for in reel["id"]:
            raise RuntimeError("boom")
        return {"theme": "pinequest", "confidence": 0.9, "scores": {"pinequest": 0.9}, "evidence": ["'x' x4"]}
    m.detect = detect
    return m


def make_propose() -> types.ModuleType:
    m = types.ModuleType("factory.propose")
    m.build = lambda reel, cfg: ({"theme": "pinequest", "hook": "h", "target_seconds": 40, "inserts": [],
                                  "music": "m", "open_questions": ["Name is missing"]}, "# Proposal\n")
    return m


class TickGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home", repo=Path(self.tmp.name) / "repo", transcriber="manual")
        self.cfg.ensure_dirs()
        for name, mod in (("detect", make_detect()), ("propose", make_propose())):
            for p in (mock.patch.dict(sys.modules, {f"factory.{name}": mod}), mock.patch.object(factory, name, mod, create=True)):
                p.start()
                self.addCleanup(p.stop)

    def test_early_approval_cannot_pre_empt_the_proposal(self) -> None:
        r = state.new_record("R", "/in", "r")
        r["status"] = "detecting"
        state.save(self.cfg, r)
        approval._decide(self.cfg, r, "approved", "too early", None)  # file written while detecting
        for _ in range(4):
            tick.tick(self.cfg)
        got = state.load(self.cfg, "r")
        self.assertEqual(got["status"], "proposed")
        self.assertEqual(got["approval"]["state"], "pending")
        self.assertFalse((self.cfg.reel_dir("r") / "approval.json").exists())

    def test_proposal_write_removes_an_old_decision(self) -> None:
        r = state.new_record("R", "/in", "r")
        r["status"] = "proposed"
        state.save(self.cfg, r)
        approval._decide(self.cfg, r, "approved", "", None)
        tick.tick(self.cfg)
        self.assertFalse((self.cfg.reel_dir("r") / "approval.json").exists())
        self.assertTrue(state.load(self.cfg, "r")["proposal"]["path"])

    def test_tick_refuses_while_another_tick_runs(self) -> None:
        import fcntl
        with open(self.cfg.tick_lock, "w") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(tick.TickBusy):
                tick.tick(self.cfg)
        tick.tick(self.cfg)  # released: runs fine

    def test_lock_is_released_after_a_crash_inside_tick(self) -> None:
        with mock.patch.object(tick.inbox, "scan", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                tick.tick(self.cfg)
        tick.tick(self.cfg)

    def test_reel_is_reloaded_from_disk_before_its_step(self) -> None:
        r = state.new_record("R", "/nonexistent", "r")
        state.save(self.cfg, r)
        stale = state.load(self.cfg, "r")  # a snapshot that says "new"
        r["status"] = "done"
        state.save(self.cfg, r)
        with mock.patch.object(state, "list_reels", return_value=[stale]):
            tick.tick(self.cfg)
        got = state.load(self.cfg, "r")
        self.assertEqual((got["status"], got["needs"]), ("done", []))


class TickTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home", repo=Path(self.tmp.name) / "repo", transcriber="manual")
        self.cfg.inbox.mkdir(parents=True)
        self.detect, self.propose = make_detect(), make_propose()
        self.enter_patch(self.detect, self.propose)

    def enter_patch(self, detect: types.ModuleType, propose: types.ModuleType) -> None:
        for name, mod in (("detect", detect), ("propose", propose)):
            p = mock.patch.dict(sys.modules, {f"factory.{name}": mod})
            p.start()
            self.addCleanup(p.stop)
            q = mock.patch.object(factory, name, mod, create=True)
            q.start()
            self.addCleanup(q.stop)

    def folder(self, name: str, age: float = 3600) -> Path:
        d = self.cfg.inbox / name
        d.mkdir()
        (d / "a.mp4").write_text("x")
        (d / "note.txt").write_text("name: Bat\n")
        t = time.time() - age
        for p in (d / "a.mp4", d / "note.txt", d):
            os.utime(p, (t, t))
        return d

    def reel(self, rid: str) -> dict:
        return state.load(self.cfg, rid)

    def tk(self) -> list[str]:
        return tick.tick(self.cfg, probe=fake_probe)

    def test_full_walk_new_to_done(self) -> None:
        self.folder("Test Reel")
        rid = "test-reel"
        seen = []

        def step() -> str:
            self.tk()
            s = self.reel(rid)["status"]
            if not seen or seen[-1] != s:
                seen.append(s)
            return s

        self.assertEqual(step(), "transcribing")
        self.assertEqual(self.reel(rid)["files"][0]["seconds"], 30.0)
        self.assertEqual(self.reel(rid)["note"]["name"], "Bat")
        step()  # no transcript yet: stays, visible need
        self.assertIn("No transcript", self.reel(rid)["needs"][0])
        (self.cfg.reel_dir(rid) / "transcript.txt").write_text("sain baina uu")
        self.assertEqual(step(), "detecting")
        self.assertEqual(self.reel(rid)["transcript"]["source"], "manual")
        self.assertEqual(self.reel(rid)["needs"], [])
        self.assertEqual(step(), "proposed")
        self.assertEqual(self.reel(rid)["detection"]["theme"], "pinequest")
        step()  # builds the proposal, stays proposed
        r = self.reel(rid)
        self.assertEqual(r["approval"]["state"], "pending")
        self.assertTrue(Path(r["proposal"]["path"]).read_text().startswith("# Proposal"))
        self.assertIn("Name is missing", r["needs"])
        step()
        self.assertEqual(self.reel(rid)["status"], "proposed")  # waits
        approval.approve(self.cfg, r, "ok", by="boss")
        self.assertEqual(step(), "approved")
        self.assertEqual(self.reel(rid)["approval"]["state"], "approved")
        self.assertEqual(self.reel(rid)["needs"], [])
        self.assertEqual(step(), "editing")
        self.assertTrue(Path(self.reel(rid)["edit"]["request_path"]).is_file())
        step()
        self.assertEqual(self.reel(rid)["status"], "editing")  # handoff waits
        out = Path(self.tmp.name) / "out.mp4"
        out.write_text("x")
        edit.mark_done(self.cfg, self.reel(rid), [str(out)])
        self.assertEqual(step(), "in_review")
        self.assertEqual(self.reel(rid)["review"]["state"], "waiting")
        step()
        self.assertEqual(self.reel(rid)["status"], "in_review")
        r = self.reel(rid)
        r["review"].update(state="changes", comments=["shorter"])
        state.save(self.cfg, r)
        self.assertEqual(step(), "changes")
        self.assertEqual(step(), "editing")
        self.assertIn("shorter", Path(self.reel(rid)["edit"]["request_path"]).read_text())
        self.assertEqual(self.reel(rid)["edit"]["outputs"], [])
        edit.mark_done(self.cfg, self.reel(rid), [str(out)])
        step()
        r = self.reel(rid)
        r["review"]["state"] = "approved"
        state.save(self.cfg, r)
        self.assertEqual(step(), "done")
        before = (self.cfg.reel_dir(rid) / "reel.json").read_bytes()
        self.tk()
        self.assertEqual((self.cfg.reel_dir(rid) / "reel.json").read_bytes(), before)
        self.assertEqual(seen, ["transcribing", "detecting", "proposed", "approved", "editing", "in_review",
                                "changes", "editing", "in_review", "done"])

    def test_idempotent_while_waiting(self) -> None:
        self.folder("Wait")
        (self.cfg.reel_dir("wait")).mkdir(parents=True)
        (self.cfg.reel_dir("wait") / "transcript.txt").write_text("hi")
        for _ in range(5):
            self.tk()
        self.assertEqual(self.reel("wait")["status"], "proposed")
        snap = (self.cfg.reel_dir("wait") / "reel.json").read_bytes()
        hist = len(self.reel("wait")["history"])
        self.tk()
        self.tk()
        self.assertEqual((self.cfg.reel_dir("wait") / "reel.json").read_bytes(), snap)
        self.assertEqual(len(self.reel("wait")["history"]), hist)

    def test_unsettled_folder_is_skipped(self) -> None:
        d = self.folder("Copying", age=1)
        self.tk()
        self.assertEqual(state.list_reels(self.cfg), [])
        old = time.time() - 3600
        for p in (d / "a.mp4", d / "note.txt", d):
            os.utime(p, (old, old))
        self.tk()
        self.assertEqual(self.reel("copying")["status"], "transcribing")

    def test_no_video_adds_need_and_stays(self) -> None:
        d = self.folder("Empty")
        (d / "a.mp4").unlink()
        old = time.time() - 3600
        os.utime(d, (old, old))
        self.tk()
        r = self.reel("empty")
        self.assertEqual(r["status"], "new")
        self.assertTrue(any("video" in n.lower() for n in r["needs"]))

    def test_one_broken_reel_does_not_stop_others(self) -> None:
        self.folder("Good One")
        self.folder("Bad One")
        for n in ("good-one", "bad-one"):
            (self.cfg.reel_dir(n)).mkdir(parents=True)
            (self.cfg.reel_dir(n) / "transcript.txt").write_text("hi")
        self.enter_patch(make_detect(boom_for="bad"), self.propose)
        for _ in range(4):
            self.tk()
        self.assertEqual(self.reel("good-one")["status"], "proposed")
        bad = self.reel("bad-one")
        self.assertEqual(bad["status"], "detecting")
        self.assertEqual(bad["needs"], ["Error at detecting: boom"])

    def test_missing_module_becomes_need(self) -> None:
        self.folder("Solo")
        (self.cfg.reel_dir("solo")).mkdir(parents=True)
        (self.cfg.reel_dir("solo") / "transcript.txt").write_text("hi")
        with mock.patch.dict(sys.modules, {"factory.detect": None}), mock.patch.object(factory, "detect", None, create=True):
            for _ in range(3):
                self.tk()
        self.assertTrue(self.reel("solo")["needs"][0].startswith("Error at detecting:"))

    def test_lock_stale_and_held(self) -> None:
        with tick.render_lock(self.cfg) as got:
            self.assertTrue(got)
            with tick.render_lock(self.cfg) as again:
                self.assertFalse(again)
        self.assertFalse(self.cfg.lock.exists())
        self.cfg.home.mkdir(parents=True, exist_ok=True)
        self.cfg.lock.write_text("1")
        old = time.time() - 3 * 3600
        os.utime(self.cfg.lock, (old, old))
        with tick.render_lock(self.cfg) as got:
            self.assertTrue(got)


if __name__ == "__main__":
    unittest.main()
