"""Tests for theme detection. Stand-in config, no footage, no network."""
import unittest
from pathlib import Path
from types import SimpleNamespace

from factory import detect

CFG = SimpleNamespace(home=Path("/nonexistent"), repo=Path("/nonexistent"))

PINEQUEST_TEXT = (
    "Сайн байна уу. PineQuest тэмцээнд оролцсон баг маань байр эзэлсэн. "
    "Ямар төсөл хийсэн бэ гэвэл вэб төсөл. Хэцүү зүйл нь цаг байсан. "
    "Хакатон дээр баг маань сайн ажилласан. Шүүгч нар сэтгэгдэл хэлсэн. "
    "Таван жилийн дараа компанийн захирал болно. Зөвлөгөө гэвэл бүү ай."
)
BOOTCAMP_TEXT = (
    "Намайг танилцуулъя. Яагаад Pinecone гэвэл bootcamp-д сурахаар болсон. "
    "Хамгийн сорилттой нь код байсан. Зөвлөгөө өгөх юм бол чадна гэж бод."
)


def reel(text="", name="", trust="high", files=None, note_theme="") -> dict:
    return {
        "name": name,
        "files": files if files is not None else [],
        "note": {"theme": note_theme},
        "transcript": {"text": text, "trust": trust},
    }


def vid(seconds=100.0, w=1080, h=1920, path="/x/clip.mp4") -> dict:
    return {"path": path, "kind": "video", "seconds": seconds, "width": w, "height": h}


class DetectTests(unittest.TestCase):
    def test_note_theme_wins_by_stem_and_label(self):
        r = detect.detect(reel(PINEQUEST_TEXT, note_theme="podcast-clip"), CFG)
        self.assertEqual(r["theme"], "podcast-clip")
        self.assertEqual(r["confidence"], 1.0)
        self.assertIn("note", " ".join(r["evidence"]).lower())
        r = detect.detect(reel("", note_theme="Podcast clip"), CFG)
        self.assertEqual(r["theme"], "podcast-clip")

    def test_unknown_note_theme_is_ignored(self):
        r = detect.detect(reel(PINEQUEST_TEXT, note_theme="nonsense"), CFG)
        self.assertEqual(r["theme"], "pinequest-testimonial")

    def test_pinequest_transcript(self):
        r = detect.detect(reel(PINEQUEST_TEXT, files=[vid()]), CFG)
        self.assertEqual(r["theme"], "pinequest-testimonial")
        self.assertGreater(r["confidence"], 0.3)
        self.assertAlmostEqual(sum(r["scores"].values()), 1.0, places=3)
        self.assertTrue(any("pinequest" in e.lower() for e in r["evidence"]))
        self.assertTrue(any(e.startswith("question:") for e in r["evidence"]))

    def test_bootcamp_transcript(self):
        r = detect.detect(reel(BOOTCAMP_TEXT, files=[vid(w=1920, h=1080)]), CFG)
        self.assertEqual(r["theme"], "testimonial")

    def test_low_trust_halves_keyword_weight(self):
        # Footage says "podcast" (horizontal, long); words say a little PineQuest.
        files = [vid(seconds=1800, w=1920, h=1080)]
        words = "pinequest хакатон " + "морил " * 59
        high = detect.detect(reel(words, files=files, trust="high"), CFG)
        low = detect.detect(reel(words, files=files, trust="low"), CFG)
        self.assertEqual(high["theme"], "pinequest-testimonial")
        self.assertEqual(low["theme"], "podcast-clip")
        self.assertLess(low["scores"]["pinequest-testimonial"], high["scores"]["pinequest-testimonial"])

    def test_empty_input_gives_no_signal(self):
        r = detect.detect(reel(), CFG)
        self.assertEqual(r["theme"], "")
        self.assertEqual(r["confidence"], 0.0)
        self.assertEqual(r["evidence"], ["no signal"])

    def test_folder_name_hint_counts_triple(self):
        plain = detect.detect(reel("pinequest", name="clip 1"), CFG)
        named = detect.detect(reel("pinequest", name="2026-11-20 PineQuest Anar"), CFG)
        self.assertEqual(named["theme"], "pinequest-testimonial")
        self.assertGreater(named["confidence"], plain["confidence"])
        self.assertTrue(any("name" in e for e in named["evidence"]))

    def test_short_terms_match_whole_words_only(self):
        # "баг" must not fire inside "багш"; "ai" not inside "mail"
        self.assertEqual(detect.count_hits("багш", "баг"), 0)
        self.assertEqual(detect.count_hits("mail", "ai"), 0)
        self.assertEqual(detect.count_hits("баг, баг.", "баг"), 2)
        self.assertEqual(detect.count_hits("төслийн төсөл", "төсөл"), 1)  # substring, 4+ letters
        self.assertEqual(detect.count_hits("төслийн", "төс"), 0)

    def test_screen_recording_helps_engineers(self):
        files = [vid(seconds=60), vid(seconds=30, w=1920, h=1080, path="/x/Screen Recording 1.mov")]
        r = detect.detect(reel("claude code ашиглаад систем бүтээсэн инженер", files=files), CFG)
        self.assertEqual(r["theme"], "engineers-matter-ai")
        self.assertTrue(any("screen recording" in e for e in r["evidence"]))

    def test_themes_path_override_and_loader(self):
        themes = detect.load_themes(CFG)
        self.assertIn("pinequest-testimonial", themes)
        self.assertNotIn("_template", themes)
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            p.write_text(json.dumps({"themes": {"x": {"label": "X", "keywords": [{"term": "зохиомол", "weight": 3}]}}}))
            cfg = SimpleNamespace(themes_path=p)
            r = detect.detect(reel("зохиомол үг"), cfg)
            self.assertEqual(r["theme"], "x")


if __name__ == "__main__":
    unittest.main()
