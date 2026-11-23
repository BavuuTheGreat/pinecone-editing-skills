"""PineQuest reel (participant / judge impression) from one job file.

    python3 -I pinequest.py batches/pinequest/<job>.json            # plan + edited + clean
    python3 -I pinequest.py batches/pinequest/<job>.json --plan     # cut + timeline only (check before rendering)
    python3 -I pinequest.py batches/pinequest/<job>.json --edited   # captions + music only
    python3 -I pinequest.py <job>.json --align                      # snap caption times to the audio (needs setup.py --align)
    python3 -I pinequest.py <job>.json --check-captions             # caption start vs speech onset, flags > 0.15 s

Look: references/themes/pinequest-testimonial.md (edit-reel skill). Calm cold-open hook with headline (job hook_motion:
"punchy" restores impact zoom/ramp/pop), grid cards shown whole and silent (job card_typing / card_sfx: true bring back
typing + sounds), framed project inserts, whip/glitch transitions, punch-ins, original 122 BPM bed, PineQuest S5 end card.
All paths in the job file are relative to the job file. Outputs: <out_dir>/<file_stem>-edited.mp4 and <file_stem>.mp4.
"""
import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reelpipe import media, stages  # noqa: E402

ENGINE = stages.ENGINE
FPS, CPS = 30, 22
HOOK_TOP = 230  # chevron logo spans y 86-136; the headline starts well below it (review 2026-11-16 "logotoigoo naalddag"); old jobs with top 150 are lifted to this
JOIN_PUNCH = (1.09, 26)  # scale, y shift (px) of the alternate framing on a jump cut (piece "join": true)
MIN_FACE_TAIL = 1.5  # s of speaker that must remain after an insert, else the insert runs to the end of the answer
CAPSTYLE = {"size": 47, "gap": 13, "baseline": 1292, "cx": 540, "thin": False}


def P(base, p):
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def prep(job, base, pub):
    for f in os.listdir(os.path.join(ENGINE, "assets")):
        if f.endswith((".wav", ".svg", ".woff2")):
            shutil.copy(os.path.join(ENGINE, "assets", f), pub)
    for g in job.get("grabs", []):  # stills / clips pulled from team or event videos
        dst = os.path.join(pub, g["out"])
        if os.path.exists(dst):
            continue
        vf = ["-vf", f"crop={g['crop']}"] if g.get("crop") else []
        if g.get("seconds"):
            media.run(["-ss", str(g["t"]), "-t", str(g["seconds"]), "-i", P(base, g["from"]), "-an", *vf, "-r", "30",
                       "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", dst])
        else:
            media.run(["-ss", str(g["t"]), "-i", P(base, g["from"]), "-frames:v", "1", *vf, dst])
    for f in job.get("files", []):  # ready images (team photo crops etc.)
        shutil.copy(P(base, f), pub)
    end = P(base, job.get("end_card", os.path.join(ENGINE, "assets", "pinequest", "pq_s5_end_card.mp4")))
    dst = os.path.join(pub, "pq_end.mp4")
    if not os.path.exists(dst):
        media.run(["-i", end, "-vf", "scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p", "-c:v", "libx264", "-crf", "16",
                   "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", dst])


def key_samples():
    """Single keystrokes cut from the recorded typing loops (assets/type_*.wav)."""
    import numpy as np
    keys = []
    for f in ("type_1.wav", "type_2.wav", "type_3.wav", "type_4.wav"):
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", os.path.join(ENGINE, "assets", f), "-ac", "1", "-ar", "48000",
                                       "-f", "f32le", "-"])
        a = np.frombuffer(raw, np.float32)
        e = np.array([np.abs(a[i:i + 240]).max() for i in range(0, len(a) - 240, 240)])
        last = -1.0
        for i in range(1, len(e)):
            t = i * 0.005
            if e[i] > 0.08 and e[i] > 3 * e[i - 1] and t - last > 0.07:
                s0 = max(0, int((t - 0.004) * 48000))
                k = a[s0:s0 + int(0.06 * 48000)].copy()
                k *= np.minimum(1, np.linspace(6, 0, len(k)))  # short fade-out
                keys.append(k)
                last = t
    return keys


def type_track(text, out, keys, seed):
    """One keystroke per typed character, on the frames PQCard types them (3 frames lead-in, CPS chars/s)."""
    import numpy as np, wave
    rng = np.random.default_rng(seed)
    n = int((len(text) / CPS + 1.2) * 48000)
    y = np.zeros(n)
    for i, ch in enumerate(text):
        t = (3 + i * FPS / CPS) / FPS
        k = keys[rng.integers(len(keys))]
        g = 0.55 if ch == " " else rng.uniform(0.8, 1.0)
        j = int(t * 48000)
        y[j:j + len(k)] += g * k[: max(0, min(len(k), n - j))]
    y = np.clip(y * 2.2, -1, 1)
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


def card_typing(job):
    """New PineQuest default (review 2026-11-16): the question appears whole, no typing."""
    return bool(job.get("card_typing", False))


def card_sfx(job):
    """New default: no key sounds and no per-card transition sound."""
    return bool(job.get("card_sfx", False))


def hook_motion(job):
    """"calm" (default): no impact zoom, fixed framing, headline fades in, hard cut into answer 1. "punchy": the old look."""
    return job.get("hook_motion", "calm")


def answer_tails(job, pieces):
    """Review 2026-11-21 ("yriag ni duusgaad ydaj 1 second bolood daraagiin asuult garch ireh"): when he finishes an answer,
    stay on him about 1 s before the next question card. The last piece before each card gets `tail` seconds of picture
    with the sound faded out (room tone only, so the interviewer's next question is never heard). A piece's own "tail" wins;
    job "answer_tail" sets the default (0 turns it off). Check the source: he must not start talking inside the tail."""
    dflt, cards = float(job.get("answer_tail", 1.0)), job.get("cards", {})
    out = [dict(p) for p in pieces]
    hook_id = (job.get("hook") or {}).get("piece")
    for k, p in enumerate(out):
        if p["answer"] == "hook" or p["id"] == hook_id:  # the hook is a teaser, not an answer: no tail
            continue
        nxt = out[k + 1] if k + 1 < len(out) else None
        if "tail" not in p and nxt and not nxt.get("join") and nxt["answer"] != p["answer"] and cards.get(nxt["answer"]):
            p["tail"] = dflt
    return out


def plan(job, clips, pub):
    items, starts, t = [], {}, 0.0
    cards = job.get("cards", {})
    zoom = dict(job.get("zoom", {}))
    typing, calm = card_typing(job), hook_motion(job) != "punchy"
    hook_id = (job.get("hook") or {}).get("piece")
    if calm and hook_id:  # one fixed gentle framing for the hook: the job's first hook key, held from frame 0, no ramp
        if zoom.get(hook_id):  # no zoom key on the hook piece = no zoom at all
            k0 = zoom[hook_id][0]
            zoom[hook_id] = [{"t": 0, "scale": k0.get("scale", 1), "y": k0.get("y", 0), "still": True}]
    keys = key_samples() if typing and card_sfx(job) else None
    run = 0
    for c in clips:
        q = cards.get(c["answer"])
        if q and not any(i.get("answer_card") == c["answer"] for i in items):
            # typing: the question types on at CPS chars/s; otherwise it appears whole and holds long enough to read
            secs = round(len(q) / CPS + 0.95, 2) if typing else round(min(2.8, max(1.6, 1.0 + len(q) / 35)), 2)
            item = {"kind": "question", "text": q, "seconds": secs, "answer_card": c["answer"]}
            if keys:
                item["sfx"] = f"typing_{c['answer']}.wav"
                type_track(q, os.path.join(pub, item["sfx"]), keys, seed=len(items))
            items.append(item)
            t += round(secs * FPS) / FPS
        # join: this piece continues the previous one after a removed pause (jump cut, no whip). Every other
        # joined piece sits slightly punched in, so the jump reads as a camera move, not a glitch.
        run = run + 1 if c.get("join") else 0
        z = zoom.get(c["id"]) or ([{"t": 0, "scale": JOIN_PUNCH[0], "y": JOIN_PUNCH[1], "still": True}] if run % 2 == 1 else None)
        items.append({"kind": "clip", "src": c["src"], "answer": c["answer"], "seconds": c["seconds"],
                      **({"join": True} if c.get("join") else {}),
                      **({"zoom": z} if z else {}), **({"hook": True} if c["id"] == hook_id else {})})
        starts[c["id"]] = (t, c["start"])
        t += round(c["seconds"] * FPS) / FPS
    end_s = round(media.duration(os.path.join(pub, "pq_end.mp4")) - 0.05, 2)
    items.append({"kind": "clip", "src": "pq_end.mp4", "answer": "outro", "seconds": end_s, "bare": True})
    body_end = t
    by_id = {c["id"]: c for c in clips}

    def reel(pid, s):
        r0, s0 = starts[pid]
        return r0 + (s - s0)

    caps = []
    for row in job["captions"]:
        a, b, text = row[:3]
        text = re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"\s*\[[^\]]*\]", "", text)).strip()  # [words] = spoken, used by --align for timing, not shown
        if not re.search(r"\w", text):  # the whole line was [hidden]: nothing to show
            continue
        pid = row[3] if len(row) > 3 else next(c["id"] for c in clips
                                               if c["id"] != hook_id and c["start"] - 0.06 <= a < c["end"])
        end_clip = starts[pid][0] + by_id[pid]["seconds"]
        nxt = clips[[c["id"] for c in clips].index(pid) + 1:][:1]
        hold = 0.0 if (nxt and nxt[0].get("join")) else 0.12  # a line never hangs over a jump cut
        caps.append({"from": round(reel(pid, a), 3), "to": round(min(reel(pid, b) + hold, end_clip), 3), "text": text})
    # keep captions off transitions: start after the in-edge, end before the out-edge (6 frames each side)
    edge = 6 / FPS
    for c in caps:
        for k, cl in enumerate(clips):
            r0 = starts[cl["id"]][0]
            r1 = r0 + cl["seconds"]
            if r0 - 0.05 <= c["from"] < r1:
                e_in = 0 if (r0 == 0 or cl.get("join")) else edge  # no transition on a jump cut: nothing to keep clear of
                e_out = 0 if (k + 1 < len(clips) and clips[k + 1].get("join")) else edge
                c["from"] = round(max(c["from"], r0 + e_in), 3)
                c["to"] = round(min(c["to"], r1 - e_out), 3)
    caps = [c for c in caps if c["to"] - c["from"] > 0.2]
    caps.sort(key=lambda c: c["from"])
    for i in range(len(caps) - 1):
        caps[i]["to"] = min(caps[i]["to"], caps[i + 1]["from"])
    ins = []
    for x in job.get("inserts", []):
        f, u = reel(*x["at"]), reel(*x["until"])
        cid = x["until"][0]
        # end of the answer this insert sits in (the last joined piece after the `until` clip)
        k = [c["id"] for c in clips].index(cid)
        while k + 1 < len(clips) and clips[k + 1].get("join"):
            k += 1
        ans_end = starts[clips[k]["id"]][0] + clips[k]["seconds"]
        # Never show a short flash of the speaker between an insert and the next card (review 2026-11-19): if less than
        # MIN_FACE_TAIL s of the answer is left, the insert stays to the answer's last frame and dims out with it.
        dim_out = ans_end - u < MIN_FACE_TAIL
        if dim_out:
            u = ans_end
        else:  # otherwise inserts end before the clip's out-edge so they never sit sharp over a transition
            u = min(u, starts[cid][0] + by_id[cid]["seconds"] - 8 / FPS)
        f = max(f, starts[x["at"][0]][0] + 6 / FPS)
        d = {k: x[k] for k in ("src", "media", "layout", "videoStart") if k in x}
        ins.append({**d, "from": round(f, 3), "seconds": round(u - f, 3), "pan": len(ins) % 4, **({"dimOut": True} if dim_out else {})})
    # back-to-back inserts cross-fade: the earlier one stays under the next one's 10-frame fade-in instead of cutting
    for a_, b_ in zip(ins, ins[1:]):
        if 0 <= b_["from"] - (a_["from"] + a_["seconds"]) < 0.4:
            a_["seconds"] = round(b_["from"] + 12 / FPS - a_["from"], 3)
            a_["cutOut"] = True
    base = {"cardTyping": typing, "hookMotion": hook_motion(job), "shrinkSeconds": 1.1, "holdSeconds": 0, "builtInOutro": False, "titles": [], "items": items, "inserts": ins}
    if hook_id:
        base["hook"] = {"from": 0, "seconds": round(round(job["hook"].get("seconds", by_id[hook_id]["seconds"]) * FPS) / FPS, 3),
                        "lines": job["hook"]["lines"], "top": max(job["hook"].get("top", HOOK_TOP), HOOK_TOP), "motion": hook_motion(job)}
    return base, caps, body_end


ALIGN_PY = os.path.join(ENGINE, ".venv-align", "bin", "python")


def align(jp, force=False):
    """Forced-align the job's caption lines to the audio (reelpipe/align_captions.py, runs in the optional venv)."""
    win = os.name == "nt"
    py = os.path.join(ENGINE, ".venv-align", "Scripts" if win else "bin", "python.exe" if win else "python")
    setup = r"py scripts\setup.py --align" if win else "python3 scripts/setup.py --align"
    ok = os.path.exists(py) and subprocess.run([py, "-c", "import torch, torchaudio; from torchaudio.pipelines import MMS_FA"],
                                               capture_output=True).returncode == 0
    if not ok:
        sys.exit(f"aligner not installed or broken: run  {setup}  (one-time, ~0.5 GB venv + ~1.2 GB model; needs python 3.10-3.12)")
    base, job = os.path.dirname(jp), json.load(open(jp, encoding="utf8"))
    # resolve pieces given as word_start/word_end exactly as the cut will (snapped to silence), hand the bounds to the aligner
    st = {"key": job.get("key", "PQ"), "source": P(base, job["source"]), "pieces": job["pieces"]}
    res = [{"id": p["id"], "start": p["start"], "end": p["end"]} for p in stages.resolve_pieces(st)]
    fd, pf = tempfile.mkstemp(suffix=".pieces.json")
    with os.fdopen(fd, "w") as fh:
        json.dump(res, fh)
    try:
        subprocess.run([py, os.path.join(ENGINE, "reelpipe", "align_captions.py"), jp, "--pieces", pf, *(["--force"] if force else [])], check=True)
    finally:
        os.remove(pf)


def speech_onsets(src, a, b):
    """Energy-based onsets (seconds, source time) in [a, b]: 10 ms RMS in dB (3-frame smooth); an onset is the frame where the level
    first climbs 8 dB above its minimum over the previous 80 ms while within 30 dB of the loud level (word or syllable start),
    at least 80 ms apart. Dense on purpose: a caption that starts mid-phrase still has an onset of its own to be measured against."""
    import numpy as np
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src, "-ac", "1", "-ar", "16000",
                                   "-f", "f32le", "-"])
    x = np.frombuffer(raw, np.float32)
    n = len(x) // 160
    db = 20 * np.log10(np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-6)
    db = np.convolve(db, np.ones(3) / 3, "same")
    floor = np.percentile(db, 95) - 30
    out, last = [], -99
    for i in range(8, n):
        if db[i] > floor and db[i] - db[i - 8:i].min() >= 8 and db[i - 1] - db[i - 8:i - 1].min() < 8 and i - last >= 8:
            out.append(a + i * 0.01)
            last = i
    return out


def check_captions(job, base, clips, items, caps, limit=0.15):
    """Per rendered caption: start vs nearest speech onset in the source audio. |offset| > limit is flagged
    (positive = caption late). A caption that begins mid-phrase has no onset of its own: expect big offsets there."""
    src = P(base, job["source"])
    starts, t = {}, 0.0
    for it in items:
        if it["kind"] == "clip":
            starts[it["src"]] = t
        t += round(it["seconds"] * FPS) / FPS
    print(f"{'#':>3} {'reel':>6} {'source':>7}  {'text':34s} {'offset':>7}  flag")
    bad = 0
    onsets = {}
    for i, c in enumerate(caps):
        cl = next((x for x in clips if x["src"] in starts and starts[x["src"]] - 0.05 <= c["from"] < starts[x["src"]] + x["seconds"]), None)
        if cl is None:
            print(f"{i:3d} {c['from']:6.2f}  {c['text'][:34]:34s} outside every clip, skipped")
            continue
        s = cl["start"] + (c["from"] - starts[cl["src"]])
        if cl["id"] not in onsets:
            onsets[cl["id"]] = speech_onsets(src, cl["start"], cl["start"] + cl["seconds"])
        near = min(onsets[cl["id"]], key=lambda o: abs(o - s), default=None)
        off = None if near is None else s - near
        flag = "" if off is not None and abs(off) <= limit else ("LATE" if off and off > 0 else "EARLY" if off else "no onset")
        bad += bool(flag)
        print(f"{i:3d} {c['from']:6.2f} {s:7.2f}  {c['text'][:34]:34s} {'' if off is None else f'{off:+7.2f}'}  {flag}")
    print(f"{len(caps)} captions, {bad} with |offset| > {limit}s")


def song_bed(song, base, body_end, out, o):
    """Bed from a supplied song. music_opts: start (s into the song), card_db (level on cards, default -7),
    fade_in, fade_out. Cards get a low-pass + dip (the same 'music breaks for the question' idea as the generated bed)."""
    t, cards = 0.0, []
    for it in base["items"]:
        n = round(it["seconds"] * FPS) / FPS
        if it["kind"] == "question":
            cards.append((t, t + n))
        t += n
    start, fi, fo = o.get("start", 0.0), o.get("fade_in", 0.25), o.get("fade_out", 1.6)
    dip = 10 ** (o.get("card_db", -7.0) / 20)
    en = "+".join(f"between(t,{a - 0.05:.3f},{b - 0.08:.3f})" for a, b in cards) or "0"
    end = body_end + 0.5
    af = (f"aresample=48000,afade=t=in:d={fi},lowpass=f=900:enable='{en}',volume='if({en},{dip:.3f},1)':eval=frame,"
          f"afade=t=out:st={end - fo:.3f}:d={fo}")
    media.run(["-ss", str(start), "-t", f"{end:.3f}", "-i", song, "-af", af, "-ac", "2", out])
    return out


def finish(src, body_end, out, bed=None, sfx=None, over_bed=14.0, speech_from=0.0, intro_boost_db=0.0, end_card=True, static_master=False):
    """Speech level per section (end card sting 0.5 dB under the body), bed + SFX under the body,
    then two-pass loudnorm to -14.5 LUFS / -1.5 dBTP (loudnorm's own true-peak limiter; it falls back to
    dynamic mode by itself when linear gain can't hold the ceiling). The old alimiter loop overshot to +5 dBTP."""
    dur = media.duration(src)
    sp = media.lufs_file(src, speech_from, body_end - speech_from)  # speech_from: skip a speechless intro (series themes)
    endl = media.lufs_file(src, body_end + 0.1, dur - body_end - 0.2) if end_card else sp
    gb, ge = -14.5 - sp, (-15.0 - endl if end_card else -14.5 - sp)
    vol = f"volume='if(lt(t,{body_end:.3f}),{10 ** (gb / 20):.4f},{10 ** (ge / 20):.4f})':eval=frame"
    if bed:
        g = -14.5 - over_bed - media.lufs_file(bed, speech_from, body_end - speech_from)
        boost = f",volume='if(lt(t,{speech_from:.3f}),{10 ** (intro_boost_db / 20):.3f},1)':eval=frame" if intro_boost_db else ""
        pre = (f"[0:a]{vol}[s];[1:a]volume={g:.2f}dB,apad[m];[2:a]volume={g - 1:.2f}dB{boost},apad[x];"
               f"[s][m][x]amix=inputs=3:duration=first:normalize=0,")
        inp = ["-i", src, "-i", bed, "-i", sfx]
    else:
        pre, inp = f"[0:a]{vol},", ["-i", src]
    ln = "loudnorm=I=-14.5:TP=-1.5:LRA=11"
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *inp, "-t", f"{dur:.3f}", "-filter_complex",
                        pre + ln + ":print_format=json[o]", "-map", "[o]", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ex = (f":measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    if static_master:  # one constant gain + a peak limiter: loudnorm's dynamic fallback lifts quiet intros (series theme: intro was -12 LUFS)
        master = f"volume={-14.5 - float(j['input_i']):.2f}dB,alimiter=limit=0.84:level=disabled:attack=5:release=60,aresample=48000"
    else:
        master = ln + ex + ",aresample=48000"
    media.run([*inp, "-filter_complex", pre + master + "[o]", "-map", "0:v", "-map", "[o]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-t", f"{dur:.3f}", out])
    lu, tp = media.loudness_report(out)
    if tp > -1.0:  # rare: AAC overshoot after linear gain; one more pass in dynamic mode
        tmp = out + ".tmp.mp4"
        os.replace(out, tmp)
        media.run(["-i", tmp, "-af", "loudnorm=I=-14.5:TP=-2:LRA=11,aresample=48000", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", out])
        os.remove(tmp)
        lu, tp = media.loudness_report(out)
    if tp > -1.0 or abs(lu + 14.5) > 0.6:
        raise RuntimeError(f"loudness out of spec: {lu} LUFS / {tp} dBTP -> {out}")
    return lu, tp


def render(props, out, pub, conc):
    pf = out + ".props.json"
    json.dump(props, open(pf, "w"), ensure_ascii=False, indent=1)
    try:
        stages.render(pf, out, pub, conc, comp="PineQuestReel")
    except RuntimeError as e:  # stall / crash loop: one retry at concurrency 1
        print(f"  render retry at concurrency 1 ({e})", flush=True)
        stages.render(pf, out, pub, 1, comp="PineQuestReel")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--edited", action="store_true")
    g.add_argument("--clean", action="store_true")
    g.add_argument("--align", action="store_true", help="forced-align caption timings to the audio (rewrites the job; backup job.before-align.json)")
    ap.add_argument("--force", action="store_true", help="with --align: also apply lines the aligner moved more than 1 s")
    g.add_argument("--check-captions", action="store_true", help="print caption start vs nearest speech onset, flag |offset| > 0.15 s")
    a = ap.parse_args()
    jp = os.path.abspath(a.job)
    if a.align:
        return align(jp, a.force)
    base, job = os.path.dirname(jp), json.load(open(jp, encoding="utf8"))
    name = os.path.splitext(os.path.basename(jp))[0]
    if name == "job":  # <job folder>/job.json: use the folder name so jobs never share a build dir
        name = os.path.basename(base)
    build = os.path.join(ENGINE, "build", "pinequest", name)
    pub = os.path.join(build, "public")
    os.makedirs(pub, exist_ok=True)
    prep(job, base, pub)
    st = {"key": job.get("key", "PQ"), "source": P(base, job["source"]), "pieces": job["pieces"]}
    clips = stages.cut(st, answer_tails(job, stages.resolve_pieces(st)), pub)
    b, caps, body_end = plan(job, clips, pub)
    pl = os.path.join(build, "plan.json")
    json.dump({"base": b, "caps": caps, "body_end": body_end, "card_sfx": card_sfx(job), "hook_motion": hook_motion(job), **({"music_style": job["music_style"]} if job.get("music_style") else {})}, open(pl, "w"), ensure_ascii=False, indent=1)
    t = 0.0
    for it in b["items"]:
        print(f"  {t:6.2f}  {it['kind']:8s} {it.get('text', it.get('src'))}")
        t += round(it["seconds"] * FPS) / FPS
    print(f"body {body_end:.2f}s, total {t:.2f}s", flush=True)
    if a.check_captions:
        return check_captions(job, base, clips, b["items"], caps)
    if a.plan:
        return
    out_dir = P(base, job.get("out_dir", "~/Desktop/ai edited reels"))
    os.makedirs(out_dir, exist_ok=True)
    stem, conc = job["file_stem"], job.get("concurrency", 3)
    if not a.clean:
        render({**b, "captions": caps, "captionStyle": {**CAPSTYLE, **job.get("caption_style", {})}}, os.path.join(build, "cap_render.mp4"), pub, conc)
        mdir = os.path.join(build, "music")
        if job.get("music", "generate") == "generate":
            subprocess.run([sys.executable, "-I", os.path.join(ENGINE, "reelpipe", "pq_music.py"), pl, mdir], check=True)
            bed = os.path.join(mdir, "bed.wav")
        else:  # a real song: trimmed to the body, dipped and filtered under the question cards, faded out into the end card
            subprocess.run([sys.executable, "-I", os.path.join(ENGINE, "reelpipe", "pq_music.py"), pl, mdir], check=True)  # SFX only
            bed = song_bed(P(base, job["music"]), b, body_end, os.path.join(mdir, "song_bed.wav"), job.get("music_opts", {}))
        out = os.path.join(out_dir, stem + "-edited.mp4")
        lu, tp = finish(os.path.join(build, "cap_render.mp4"), body_end, out, bed, os.path.join(mdir, "sfx.wav"),
                        job.get("speech_over_bed_db", 14.0))
        print(f"edited -> {out}  {lu} LUFS / {tp} dBTP", flush=True)
    if not a.edited:
        render(b, os.path.join(build, "clean_render.mp4"), pub, conc)
        out = os.path.join(out_dir, stem + ".mp4")
        lu, tp = finish(os.path.join(build, "clean_render.mp4"), body_end, out)
        print(f"clean  -> {out}  {lu} LUFS / {tp} dBTP", flush=True)


if __name__ == "__main__":
    main()
