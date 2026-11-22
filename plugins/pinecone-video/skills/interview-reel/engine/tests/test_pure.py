"""Unit tests for the pure helpers of the engine. No ffmpeg, no footage, no Remotion: only numpy.

Run from the engine folder:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from unittest import mock

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ENGINE)

import pinequest  # noqa: E402
import engineers  # noqa: E402
from reelpipe import media, stages  # noqa: E402


def piece(pid, answer, **kw):
    return {"id": pid, "answer": answer, "start": 0.0, "end": 5.0, **kw}


class AnswerTails(unittest.TestCase):
    JOB = {"cards": {"a2": {"text": "Q2"}, "a3": {"text": "Q3"}}}

    def test_tail_only_on_last_piece_before_a_card(self):
        pcs = [piece("p1", "a1"), piece("p2", "a1"), piece("p3", "a2"), piece("p4", "a3")]
        out = pinequest.answer_tails(self.JOB, pcs)
        self.assertNotIn("tail", out[0])   # next piece is the same answer
        self.assertEqual(out[1]["tail"], 1.0)  # next piece opens card a2
        self.assertEqual(out[2]["tail"], 1.0)  # next piece opens card a3
        self.assertNotIn("tail", out[3])   # last piece, nothing after it

    def test_no_tail_before_a_join(self):
        pcs = [piece("p1", "a1"), piece("p2", "a2", join=True)]
        out = pinequest.answer_tails(self.JOB, pcs)
        self.assertNotIn("tail", out[0])

    def test_no_tail_before_the_outro_or_an_answer_without_a_card(self):
        pcs = [piece("p1", "a1"), piece("p2", "outro")]
        self.assertNotIn("tail", pinequest.answer_tails(self.JOB, pcs)[0])

    def test_explicit_piece_tail_wins(self):
        pcs = [piece("p1", "a1", tail=0.4), piece("p2", "a2")]
        self.assertEqual(pinequest.answer_tails(self.JOB, pcs)[0]["tail"], 0.4)

    def test_explicit_zero_tail_is_kept(self):
        pcs = [piece("p1", "a1", tail=0), piece("p2", "a2")]
        self.assertEqual(pinequest.answer_tails(self.JOB, pcs)[0]["tail"], 0)

    def test_job_default_tail(self):
        job = {**self.JOB, "answer_tail": 0.6}
        pcs = [piece("p1", "a1"), piece("p2", "a2")]
        self.assertEqual(pinequest.answer_tails(job, pcs)[0]["tail"], 0.6)

    def test_answer_tail_zero_disables(self):
        job = {**self.JOB, "answer_tail": 0}
        pcs = [piece("p1", "a1"), piece("p2", "a2")]
        out = pinequest.answer_tails(job, pcs)
        self.assertEqual(out[0].get("tail", 0), 0)

    def test_input_is_not_mutated(self):
        pcs = [piece("p1", "a1"), piece("p2", "a2")]
        pinequest.answer_tails(self.JOB, pcs)
        self.assertNotIn("tail", pcs[0])


    def test_no_tail_on_the_hook_piece(self):
        job = {**self.JOB, "hook": {"piece": "h"}}
        pcs = [piece("h", "hook"), piece("p1", "a2")]
        self.assertNotIn("tail", pinequest.answer_tails(job, pcs)[0])
        pcs = [piece("h", "a1"), piece("p1", "a2")]  # hook id alone is enough
        self.assertNotIn("tail", pinequest.answer_tails(job, pcs)[0])


class PlanCaptions(unittest.TestCase):
    def test_caption_in_the_silent_tail_is_not_matched_to_the_piece(self):
        job = {"cards": {}, "captions": [[1.0, 1.5, "hello"], [5.5, 6.0, "next"]]}
        clips = [{"id": "p1", "answer": "a1", "src": "1.mp4", "start": 0.0, "end": 5.0, "seconds": 6.0, "tail": 1.0},
                 {"id": "p2", "answer": "a2", "src": "2.mp4", "start": 5.2, "end": 9.0, "seconds": 3.8}]
        with mock.patch.object(media, "duration", return_value=3.0):
            _, caps, _ = pinequest.plan(job, clips, "/nowhere")
        nxt = next(c for c in caps if c["text"] == "next")
        self.assertAlmostEqual(nxt["from"], 6.3, places=2)  # in p2 (starts at 6.0 on the reel), not in p1's tail


class JobDefaults(unittest.TestCase):
    def test_card_typing_default_off(self):
        self.assertIs(pinequest.card_typing({}), False)
        self.assertIs(pinequest.card_typing({"card_typing": True}), True)

    def test_card_sfx_default_off(self):
        self.assertIs(pinequest.card_sfx({}), False)
        self.assertIs(pinequest.card_sfx({"card_sfx": True}), True)

    def test_hook_motion_default_calm(self):
        self.assertEqual(pinequest.hook_motion({}), "calm")
        self.assertEqual(pinequest.hook_motion({"hook_motion": "punchy"}), "punchy")


class PathHelper(unittest.TestCase):
    def test_relative_is_joined_to_base(self):
        self.assertEqual(pinequest.P("/base/dir", "x/../y.mp4"), "/base/dir/y.mp4")

    def test_absolute_is_kept(self):
        self.assertEqual(pinequest.P("/base", "/abs/z.mp4"), "/abs/z.mp4")

    def test_home_is_expanded(self):
        self.assertEqual(pinequest.P("/base", "~/z.mp4"), os.path.expanduser("~/z.mp4"))


class Stages(unittest.TestCase):
    def test_frames_rounds_at_30fps(self):
        self.assertEqual(stages.frames(1.0), 30)
        self.assertEqual(stages.frames(0.5), 15)
        self.assertEqual(stages.frames(0.016), 0)

    def test_caption_time_parse(self):
        self.assertAlmostEqual(stages._t("1:02.50"), 62.5)
        self.assertAlmostEqual(stages._t("0:00.00"), 0.0)

    def _props(self):
        return {"items": [
            {"kind": "question", "seconds": 2.0},
            {"kind": "clip", "seconds": 4.0},
            {"kind": "clip", "seconds": 3.0},
        ]}

    def test_speech_windows_skip_cards(self):
        self.assertEqual(stages.speech_windows(self._props()), [(2.0, 6.0), (6.0, 9.0)])

    def test_outro_start_is_sum_before_last_item(self):
        self.assertEqual(stages.outro_start(self._props()), 6.0)

    def test_resolve_pieces_passes_explicit_times_through(self):
        st = {"pieces": [{"id": "p1", "answer": "a1", "start": 1.0, "end": 2.0}]}
        self.assertEqual(stages.resolve_pieces(st), st["pieces"])

    def test_resolve_pieces_word_times_keep_tail_join_level(self):
        st = {"source": "x.mp4", "pieces": [{"id": "p1", "answer": "a1", "word_start": 2.0, "word_end": 3.0, "lo": 1.0,
                                              "hi": 5.0, "tail": 0.5, "join": True, "level": [1.0, 4.0]}]}
        with mock.patch.object(media, "pcm", return_value=None), mock.patch.object(media, "quietest", side_effect=[1.9, 3.1]):
            out = stages.resolve_pieces(st)[0]
        self.assertEqual(out, {"id": "p1", "answer": "a1", "start": 1.9, "end": 3.1, "tail": 0.5, "join": True, "level": [1.0, 4.0]})

    def _cut(self, piece_, src_dur):
        calls = []
        st = {"key": "s", "source": "src.mp4"}
        with mock.patch.object(media, "run", side_effect=lambda a: calls.append(a)), \
                mock.patch.object(media, "lufs_file", return_value=-20.0), \
                mock.patch.object(media, "duration", return_value=src_dur), \
                mock.patch.object(os.path, "exists", return_value=False):
            return stages.cut(st, [piece_], "/pub")[0], calls

    def test_cut_cache_name_encodes_both_level_ends(self):
        a, _ = self._cut({"id": "p", "answer": "a", "start": 1.0, "end": 3.0, "level": [1.0, 4.0]}, 100)
        b, _ = self._cut({"id": "p", "answer": "a", "start": 1.0, "end": 3.0, "level": [1.0, 6.0]}, 100)
        self.assertNotEqual(a["src"], b["src"])

    def test_cut_tail_is_clamped_to_the_source(self):
        c, calls = self._cut({"id": "p", "answer": "a", "start": 1.0, "end": 3.0, "tail": 1.0}, 3.4)
        self.assertLessEqual(c["seconds"], 2.4 + 1e-6)
        self.assertGreater(c["seconds"], 2.0)
        c, _ = self._cut({"id": "p", "answer": "a", "start": 1.0, "end": 3.0, "tail": 1.0}, 3.0)
        self.assertEqual(c["seconds"], 2.0)
        c, _ = self._cut({"id": "p", "answer": "a", "start": 1.0, "end": 3.0, "tail": 1.0}, 50)
        self.assertEqual(c["seconds"], 3.0)

    def test_props_adds_one_card_per_answer_and_outro(self):
        batch = {"cards": {"a1": {"text": "Q", "seconds": 2.0, "sfx": False}}, "end_card": "/x/end.mp4",
                 "end_card_seconds": 3.0, "kicker": "K"}
        student = {"key": "s", "name": "Сурагч"}
        clips = [{"src": "c1.mp4", "answer": "a1", "seconds": 4.0}, {"src": "c2.mp4", "answer": "a1", "seconds": 2.0}]
        p = stages.props(batch, student, clips)
        kinds = [i["kind"] for i in p["items"]]
        self.assertEqual(kinds, ["question", "clip", "clip", "clip"])
        self.assertEqual(p["items"][-1]["src"], "end.mp4")
        self.assertEqual(p["nameTitle"]["words"], ["Сурагч"])


class Media(unittest.TestCase):
    def test_quietest_finds_the_silent_window(self):
        import numpy as np
        sr = 16000
        x = np.ones(sr, dtype=np.float32) * 0.5
        x[int(0.5 * sr):int(0.6 * sr)] = 0.0  # silence around 0.55 s
        t = media.quietest(x, sr, 0.2, 0.9)
        self.assertGreaterEqual(t, 0.5)
        self.assertLessEqual(t, 0.6)


class Engineers(unittest.TestCase):
    SEGS = [{"a": 10.0, "d": 5.0, "p": 0.0, "ov": 0.1}, {"a": 30.0, "d": 4.0, "p": 5.0, "ov": 0.1}]

    def test_tmap_inside_clip(self):
        self.assertEqual(engineers.tmap(self.SEGS, 12.0), 2.0)
        self.assertEqual(engineers.tmap(self.SEGS, 31.0), 6.0)

    def test_tmap_removed_pause_lands_on_next_clip(self):
        self.assertEqual(engineers.tmap(self.SEGS, 20.0), 5.0)

    def test_tmap_past_the_end_clamps(self):
        self.assertEqual(engineers.tmap(self.SEGS, 99.0), 9.0)

    def test_camera_is_deterministic_and_bounded(self):
        segs = [{"p": i * 6.0, "d": 6.0, "ov": 0.1} for i in range(8)]
        job = {"camera_amount": 1.0, "camera_seed": 3}
        a, b = engineers.camera(job, segs, 48.0), engineers.camera(job, segs, 48.0)
        self.assertEqual(a, b)
        self.assertEqual(a[0], {"t": 0.0, "s": 1.0, "x": 0.0})
        for k in a:
            self.assertGreaterEqual(k["s"], 1.0)
            self.assertLessEqual(abs(k["x"]), (k["s"] - 1) * 480 + 1e-6)

    def test_camera_still_when_amount_zero(self):
        segs = [{"p": i * 6.0, "d": 6.0, "ov": 0.1} for i in range(4)]
        keys = engineers.camera({}, segs, 24.0)
        self.assertEqual([k["s"] for k in keys], [1.0, 1.0])

    def test_cut_fx_one_per_cut_never_repeats(self):
        segs = [{"p": i * 5.0, "ov": 0.2} for i in range(30)]
        out = engineers.cut_fx({}, segs)
        self.assertLessEqual(len(out), 29)
        for x, y in zip(out, out[1:]):  # a plain cut in between resets the rule, so only adjacent cuts are compared
            if y["t"] - x["t"] < 5.5:
                self.assertNotEqual(x["kind"], y["kind"])
        for o in out:
            self.assertIn(o["kind"], ("blur", "lift", "shift"))
            self.assertIn(o["dir"], (1, -1))

    def test_leaks_off(self):
        self.assertEqual(engineers.leaks({"leaks": "off"}, lambda t: t, 50.0), [])

    def test_leaks_auto_intro_plus_listed_and_closer(self):
        job = {"leaks_at": [20.0, {"at": 10.0, "tone": "green"}], "closer": True}
        out = engineers.leaks(job, lambda t: t, 50.0)
        self.assertEqual([o["t"] for o in out], [0.0, 10.0, 20.0, 50.0])
        self.assertEqual([o["tone"] for o in out], ["pink", "green", "pink", "pink"])
        self.assertEqual([o["dir"] for o in out], [1, -1, 1, -1])

    def test_leaks_no_intro_leak_when_opening_none(self):
        out = engineers.leaks({"opening": "none"}, lambda t: t, 50.0)
        self.assertEqual(out, [])

    def test_frames_of_with_end_card(self):
        p0, e, out, total = engineers.frames_of({"presenterSeconds": 10, "outroSeconds": 2, "endCardSeconds": 3, "endCard": True,
                                                 "noIntro": True})
        self.assertEqual((p0, e, out), (0, 300, 360))
        self.assertEqual(total, 360 + 90 - 12)

    def test_frames_of_closer_uses_closer_frames(self):
        _, e, out, total = engineers.frames_of({"presenterSeconds": 10, "noIntro": True, "closer": True})
        self.assertEqual(out, e + 150)
        self.assertEqual(total, out)


if __name__ == "__main__":
    unittest.main()
