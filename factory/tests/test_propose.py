"""Tests for the first-proposal builder. No footage, no network."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from factory import propose

# Intro sentence first (skipped as a weak hook), then a quotable line with a theme keyword.
TEXT = (
    "Сайн байна уу би энд ирлээ мэндчилье. "
    "Ямар төсөл хийсэн бэ? "
    "Бид PineQuest дээр гурван өдөр хэрэглэгчийн төсөл хийсэн. "
    "Тийм. "
    "Хамгийн хэцүү зүйл бол цаг байсан гэж бодож байна даа энэ бүхний дараа маш их ядарсан ч гэсэн бид хийсэн."
)


def reel(text=TEXT, trust="high", name="2026-11-20 PineQuest Anar", note_name="Anar", files=None) -> dict:
    return {
        "id": "2026-11-20-pinequest-сурагч",
        "name": name,
        "files": files if files is not None else [
            {"path": "/x/a.mp4", "kind": "video", "seconds": 76.0, "width": 1080, "height": 1920}],
        "note": {"name": note_name, "theme": ""},
        "transcript": {"text": text, "trust": trust},
    }


class ProposeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = SimpleNamespace(repo=Path(self.tmp.name), home=Path(self.tmp.name))

    def test_target_is_theme_middle_for_long_footage(self):
        files = [{"path": "/x/a.mp4", "kind": "video", "seconds": 300.0, "width": 1080, "height": 1920}]
        block, _ = propose.build(reel(files=files), self.cfg)
        self.assertEqual(block["theme"], "pinequest-testimonial")
        self.assertEqual(block["target_seconds"], 56)  # middle of 46-66

    def test_target_capped_for_short_footage(self):
        files = [{"path": "/x/a.mp4", "kind": "video", "seconds": 40.0, "width": 1080, "height": 1920}]
        block, _ = propose.build(reel(files=files), self.cfg)
        self.assertEqual(block["target_seconds"], 24)  # 60 % of 40 s

    def test_hook_picks_keyword_sentence_not_intro_or_question(self):
        block, _ = propose.build(reel(), self.cfg)
        self.assertEqual(block["hook"], "Бид PineQuest дээр гурван өдөр хэрэглэгчийн төсөл хийсэн")

    def test_hook_empty_when_low_trust_or_no_text(self):
        for r in (reel(trust="low"), reel(text="")):
            block, _ = propose.build(r, self.cfg)
            self.assertEqual(block["hook"], "")
            self.assertTrue(any("hook" in q.lower() for q in block["open_questions"]))

    def test_open_questions(self):
        block, _ = propose.build(reel(note_name="", trust="low", text="мэдэхгүй"), self.cfg)
        qs = " | ".join(block["open_questions"])
        self.assertIn("Name is missing: add `name:` to note.txt, spelled exactly", qs)
        self.assertIn("Transcript is from whisper (weak on Mongolian): captions need a human check", qs)
        block, _ = propose.build(reel(name="clip", text="подкаст хакатон влог тренд", files=[]), self.cfg)  # weak evidence
        self.assertTrue(any(q.startswith("Theme is a guess (") and "add `theme:` to note.txt" in q
                            for q in block["open_questions"]))

    def test_clean_reel_has_no_name_question(self):
        block, _ = propose.build(reel(), self.cfg)
        self.assertFalse(any("Name is missing" in q for q in block["open_questions"]))

    def test_non_ready_theme_is_flagged(self):
        r = reel(); r["note"]["theme"] = "creator-collab"
        block, _ = propose.build(r, self.cfg)
        self.assertTrue(any("not ready" in q.lower() for q in block["open_questions"]))

    def test_inserts(self):
        files = [
            {"path": "/x/main.mp4", "kind": "video", "seconds": 90.0, "width": 1080, "height": 1920},
            {"path": "/x/Screen Recording 1.mov", "kind": "video", "seconds": 20.0, "width": 1920, "height": 1080},
            {"path": "/x/phone.mp4", "kind": "video", "seconds": 8.0, "width": 1080, "height": 1920},
            {"path": "/x/team.jpg", "kind": "image", "seconds": None, "width": 800, "height": 600},
            {"path": "/x/voice.m4a", "kind": "audio", "seconds": 5.0},
        ]
        block, _ = propose.build(reel(files=files), self.cfg)
        got = {i["file"]: i for i in block["inserts"]}
        self.assertEqual(set(got), {"Screen Recording 1.mov", "phone.mp4", "team.jpg"})
        self.assertEqual(got["Screen Recording 1.mov"]["use"], "framed")
        self.assertEqual(got["phone.mp4"]["use"], "phone")
        self.assertEqual(got["team.jpg"]["kind"], "image")

    def test_music_fallbacks(self):
        block, _ = propose.build(reel(), self.cfg)
        self.assertEqual(block["music"], "generated")  # no manifest
        manifest = self.cfg.repo / "assets" / "MANIFEST.json"
        manifest.parent.mkdir()
        manifest.write_text("{not json")
        self.assertEqual(propose.build(reel(), self.cfg)[0]["music"], "generated")
        manifest.write_text(json.dumps({"music": [
            {"id": "a", "themes": [], "tags": []},
            {"id": "b", "themes": [], "tags": ["default"]},
            {"id": "c", "themes": ["pinequest-testimonial"], "tags": []}]}))
        self.assertEqual(propose.build(reel(), self.cfg)[0]["music"], "c")
        manifest.write_text(json.dumps({"music": [{"id": "a", "themes": ["x"], "tags": []},
                                                  {"id": "b", "themes": [], "tags": ["default"]}]}))
        self.assertEqual(propose.build(reel(), self.cfg)[0]["music"], "b")

    def test_markdown(self):
        block, md = propose.build(reel(), self.cfg)
        self.assertTrue(md.startswith("# 2026-11-20 PineQuest Anar"))
        self.assertIn("python3 -m factory approve 2026-11-20-pinequest-сурагч", md)
        self.assertIn('python3 -m factory reject 2026-11-20-pinequest-сурагч "<reason>"', md)
        for part in ("Why this theme", "Open questions", "| Theme |", "| Hook |", "| Length |", "| Inserts |", "| Music |"):
            self.assertIn(part, md)
        self.assertNotIn("path", block)


if __name__ == "__main__":
    unittest.main()
