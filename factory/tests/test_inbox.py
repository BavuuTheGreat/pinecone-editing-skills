import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from factory import inbox, state
from factory.config import Config


def fake_probe(path: str) -> dict:
    return {"seconds": 12.5, "width": 1080, "height": 1920}


class FakeRun:
    def __init__(self, returncode: int = 0, stdout: str = "") -> None:
        self.returncode, self.stdout = returncode, stdout


class InboxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = Config(home=Path(self.tmp.name))
        self.cfg.inbox.mkdir(parents=True)

    def make_folder(self, name: str, files: tuple[str, ...] = ("a.mp4",), age: float = 3600) -> Path:
        d = self.cfg.inbox / name
        d.mkdir()
        for f in files:
            (d / f).write_text("x")
        old = time.time() - age
        for p in [*d.iterdir(), d]:
            os.utime(p, (old, old))
        return d

    def test_kind_by_extension(self) -> None:
        self.assertEqual(inbox.kind_of("a.MP4"), "video")
        self.assertEqual(inbox.kind_of("a.m4a"), "audio")
        self.assertEqual(inbox.kind_of("a.png"), "image")
        self.assertEqual(inbox.kind_of("a.pdf"), "other")

    def test_parse_note(self) -> None:
        note = inbox.parse_note("name: Сурагч\nTeam: Alpha\nresult: 1st\nhandle: @x\ntheme: pinequest\nhello there\nfoo: bar\n")
        self.assertEqual(note["name"], "Сурагч")
        self.assertEqual(note["team"], "Alpha")
        self.assertEqual(note["theme"], "pinequest")
        self.assertEqual(note["extra"], "hello there\nfoo: bar")

    def test_settled(self) -> None:
        old = self.make_folder("old")
        new = self.make_folder("new", age=1)
        self.assertTrue(inbox.is_settled(old, 60))
        self.assertFalse(inbox.is_settled(new, 60))

    def test_scan_creates_records_once_and_skips_unsettled(self) -> None:
        self.make_folder("Reel One")
        self.make_folder("Copying", age=1)
        (self.cfg.inbox / "loose.mp4").write_text("x")
        made = inbox.scan(self.cfg)
        self.assertEqual([r["id"] for r in made], ["reel-one"])
        self.assertEqual(made[0]["status"], "new")
        self.assertEqual(inbox.scan(self.cfg), [])
        self.assertEqual(len(state.list_reels(self.cfg)), 1)

    def test_describe_probes_and_reads_note(self) -> None:
        d = self.make_folder("R", ("a.mp4", "b.wav", "note.txt"))
        (d / "note.txt").write_text("name: Bat\n")
        r = state.new_record("R", str(d), "r")
        inbox.describe(r, fake_probe)
        kinds = {Path(f["path"]).name: f["kind"] for f in r["files"]}
        self.assertEqual(kinds, {"a.mp4": "video", "b.wav": "audio"})
        vid = r["files"][0]
        self.assertTrue(os.path.isabs(vid["path"]))
        self.assertEqual((vid["seconds"], vid["width"], vid["height"]), (12.5, 1080, 1920))
        self.assertEqual(r["note"]["name"], "Bat")

    def test_ffprobe_missing_or_failing_gives_none(self) -> None:
        def boom(*a, **k):
            raise FileNotFoundError("ffprobe")
        none = {"seconds": None, "width": None, "height": None}
        self.assertEqual(inbox.ffprobe("x.mp4", runner=boom), none)
        self.assertEqual(inbox.ffprobe("x.mp4", runner=lambda *a, **k: FakeRun(1, "")), none)
        self.assertEqual(inbox.ffprobe("x.mp4", runner=lambda *a, **k: FakeRun(0, "not json")), none)

    def test_ffprobe_parses(self) -> None:
        out = json.dumps({"format": {"duration": "76.2"}, "streams": [{"codec_type": "audio"},
                          {"codec_type": "video", "width": 2160, "height": 3840}]})
        got = inbox.ffprobe("x.mp4", runner=lambda *a, **k: FakeRun(0, out))
        self.assertEqual(got, {"seconds": 76.2, "width": 2160, "height": 3840})


if __name__ == "__main__":
    unittest.main()
