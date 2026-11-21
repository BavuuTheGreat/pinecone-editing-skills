import tempfile
import unittest
from pathlib import Path

from factory import edit, state
from factory.config import Config


class FakeRun:
    returncode = 0
    stdout = ""


class EditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name) / "home", repo=Path(self.tmp.name) / "repo")
        self.clip = Path(self.tmp.name) / "clip.mp4"
        self.clip.write_text("x")
        r = state.new_record("2026 PineQuest Bat", "/in", "pq-bat")
        r["files"] = [{"path": str(self.clip), "kind": "video", "seconds": 76.2, "width": 1080, "height": 1920}]
        r["note"]["name"] = "Bat"
        r["detection"] = {"theme": "pinequest", "confidence": 0.8, "scores": {}, "evidence": []}
        r["proposal"] = {"path": "", "theme": "pinequest", "hook": "Bat built it", "target_seconds": 45,
                         "inserts": ["title card"], "music": "funk", "open_questions": []}
        r["transcript"] = {"path": "/t/transcript.txt", "source": "whisper", "trust": "low", "text": "hi"}
        r["status"] = "approved"
        self.reel = r
        state.save(self.cfg, r)

    def test_request_is_complete(self) -> None:
        path = edit.write_request(self.cfg, self.reel)
        text = Path(path).read_text(encoding="utf-8")
        self.assertEqual(path, str(self.cfg.reel_dir("pq-bat") / "EDIT_REQUEST.md"))
        self.assertEqual(self.reel["edit"]["request_path"], path)
        for needle in ["2026 PineQuest Bat", str(self.clip), "76.2", "Bat", "pinequest",
                       str(self.cfg.repo / "plugins/pinecone-video/skills/edit-reel/references/themes/pinequest.md"),
                       "Bat built it", "/t/transcript.txt", "low",
                       "never clip speech", "finished sentence", "no interviewer voice",
                       "names only as given in the note", "unsure caption words",
                       "python3 -m factory done pq-bat", str(self.cfg.reel_dir("pq-bat") / "outputs")]:
            self.assertIn(needle.lower(), text.lower())
        self.assertNotIn("Review comments", text)

    def test_changes_put_comments_on_top(self) -> None:
        self.reel["status"] = "changes"
        self.reel["review"] = {"state": "changes", "comments": ["cut the second answer earlier"]}
        text = Path(edit.write_request(self.cfg, self.reel)).read_text(encoding="utf-8")
        self.assertLess(text.index("cut the second answer earlier"), text.index("PineQuest Bat"))
        self.assertIn("Review comments", text)

    def test_mark_done_validates_and_saves(self) -> None:
        with self.assertRaises(FileNotFoundError):
            edit.mark_done(self.cfg, self.reel, [str(self.clip) + ".missing"])
        with self.assertRaises(ValueError):
            edit.mark_done(self.cfg, self.reel, [])
        edit.mark_done(self.cfg, self.reel, [str(self.clip)])
        saved = state.load(self.cfg, "pq-bat")
        self.assertEqual(saved["edit"]["outputs"], [str(self.clip)])
        self.assertTrue(saved["edit"]["finished"])

    def test_handoff_does_nothing(self) -> None:
        ed = edit.get_editor(self.cfg)
        self.assertEqual(ed.name, "handoff")
        ed.run(self.reel, self.cfg)
        self.assertEqual(self.reel["edit"]["outputs"], [])

    def test_claude_editor_builds_command(self) -> None:
        calls = []
        cfg = Config(home=self.cfg.home, repo=self.cfg.repo, editor="claude")
        edit.write_request(cfg, self.reel)
        ed = edit.get_editor(cfg, runner=lambda cmd, **kw: calls.append((cmd, kw)) or FakeRun())
        ed.run(self.reel, cfg)
        cmd = calls[0][0]
        self.assertEqual(cmd[:2], ["claude", "-p"])
        self.assertIn(self.reel["edit"]["request_path"], cmd[2])


if __name__ == "__main__":
    unittest.main()
