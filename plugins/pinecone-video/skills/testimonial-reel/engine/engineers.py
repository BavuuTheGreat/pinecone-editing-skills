"""Episode of the series "Engineers matter more with AI" (theme: edit-reel/references/themes/engineers-matter-ai.md).

    python3 -I engineers.py <job>.json            # cut + render + music + master -> <out_dir>/<file_stem>.mp4
    python3 -I engineers.py <job>.json --plan     # cut + timeline only (look at plan.json before rendering)
    python3 -I engineers.py <job>.json --intro    # only the series intro with its sound -> <file_stem>_intro.mp4
    python3 -I engineers.py <job>.json --remix    # redo music + master on the last render (sound changes only)
    python3 -I engineers.py <job>.json --align    # snap caption times to the audio (needs `setup.py --align`)

One presenter take is trimmed of long pauses and joined with 4-frame dissolves (cuts hide inside the pauses), the
Remotion look ("Ghost Text": serif intro, ghost->solid captions, screen inserts the presenter slides aside for) is rendered
on top, a calm original bed + sound design are mixed under it, then two-pass loudnorm to -14.5 LUFS / -1.5 dBTP.
All paths in the job file are relative to the job file. Job format: batches/engineers/_example.json.
"""
import argparse
import hashlib
import math
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
from reelpipe import media, stages  # noqa: E402
import pinequest  # noqa: E402  (finish(), align(), P())

ENGINE = stages.ENGINE
FPS = 30
OV = 4  # frames of the plain dissolve
# Smooth, clean transitions between takes, rotated so no two in a row repeat (name -> frames). Each lives inside a pause.
# (zoomin and fadeblack were tried on episode 1 and dropped: the zoom crops the face, the dip to black is jarring)
PALETTE = {"fade": 5, "smoothleft": 6, "smoothup": 6, "smoothright": 6, "smoothdown": 6}
WEIGHTS = {"fade": 4, "smoothleft": 1, "smoothup": 1, "smoothright": 1, "smoothdown": 1}
# Soft move laid over a cut by the renderer (a bell curve centred on the cut): focus-breathe, small lift, small side drift.
FX = ["blur", "lift", "shift", None, None]
TIM = json.load(open(os.path.join(ENGINE, "src", "eng", "intro_timing.json")))
GRADE = "scale=1080:1920:flags=lanczos,fps=30,setsar=1,eq=contrast=1.04:saturation=1.05,unsharp=5:5:0.35,format=yuv420p"
P = pinequest.P


def prep(job, base, pub):
    """Fonts/logo from assets, optional brand end card. (Screen grabs are built after the presenter: they are stretched to fit.)"""
    for f in os.listdir(os.path.join(ENGINE, "assets")):
        if f.endswith((".svg", ".woff2", ".png")):
            shutil.copy(os.path.join(ENGINE, "assets", f), pub)
    ec = job.get("end_card")
    if ec == "default":
        ec = os.path.join(ENGINE, "assets", "end_card_9x16.mp4")
    if ec and os.path.exists(P(base, ec)):
        dst = os.path.join(pub, "end_card.mp4")
        if not os.path.exists(dst):
            media.run(["-i", P(base, ec), "-vf", "scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p", "-c:v", "libx264", "-crf", "16",
                       "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2", dst])
        return dst
    return None


def speech_segments(source, s0, s1, min_pause=0.8, keep=0.3, lead=0.35, tail=0.7):
    """Spans of the source to keep: from just before the first word to just after the last, with every pause longer than
    `min_pause` shortened to 2 x `keep`. Cut points sit in room tone, so a dissolve there is invisible."""
    x = media.pcm(source, sr=16000, channels=1, ss=s0, t=s1 - s0)
    n = len(x) // 320
    db = 20 * np.log10(np.sqrt((x[:n * 320].reshape(n, 320) ** 2).mean(1)) + 1e-7)
    db = np.convolve(db, np.ones(3) / 3, "same")
    sp = db > np.percentile(db, 10) + 4.5  # room tone +4.5 dB
    idx = np.where(sp)[0]
    first, last = idx[0] * 0.02, (idx[-1] + 1) * 0.02
    a0, b_end = max(0.0, first - lead), min(n * 0.02, last + tail)
    pauses, st = [], None
    for i, v in enumerate(sp):
        if not v and st is None:
            st = i
        if v and st is not None:
            if (i - st) * 0.02 >= min_pause and a0 < st * 0.02 and i * 0.02 < b_end:
                pauses.append((st * 0.02, i * 0.02))
            st = None
    segs, cur = [], a0
    for ps, pe in pauses:
        segs.append((cur, ps + keep))
        cur = pe - keep
    segs.append((cur, b_end))
    return [(round(s0 + a, 3), round(s0 + b, 3)) for a, b in segs]


def build_presenter(job, base, pub):
    """presenter.mp4 = the kept spans joined with OV-frame dissolves (video xfade, audio acrossfade), graded, level -14.3 LUFS."""
    src = P(base, job["source"])
    sp = job.get("speech", {})
    s0, s1 = sp.get("start", 0.0), sp.get("end", media.duration(src))
    if job.get("clips"):
        # CLIP MODE (the 30 s cut): the presenter take is cut to the listed clips (source seconds), each edge snapped to the quietest
        # 40 ms next to it (a breath, never inside a word), joined with hard cuts and 12 ms audio fades: smooth, no clicks.
        mono = media.pcm(src, sr=16000, channels=1)
        spans = []
        for c in job["clips"]:
            a, b = c["from"], c["to"]
            if c.get("snap", True):
                a = media.quietest(mono, 16000, max(0.0, a - 0.10), a + 0.03)
                b = media.quietest(mono, 16000, b - 0.03, b + 0.10)
            spans.append((round(a, 3), round(b, 3)))
        print("  clip edges (20 ms energy next to each edge; quiet = below -41 dB, speech clipped if the INSIDE of the edge is loud):")
        for (a, b), c in zip(spans, job["clips"]):
            def e(t0, t1):
                seg = mono[int(t0 * 16000):int(t1 * 16000)]
                return 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-7) if len(seg) else -99
            head_out, head_in, tail_in, tail_out = e(a - 0.04, a), e(a, a + 0.04), e(b - 0.04, b), e(b, b + 0.06)
            flag = ("START clips a word? " if head_in > -41 and head_out > -41 else "") + ("END clips a word? " if tail_in > -41 and tail_out > -41 else "")
            print(f"    {a:7.2f}-{b:7.2f}  start before {head_out:5.0f} / after {head_in:5.0f} dB   end before {tail_in:5.0f} / after {tail_out:5.0f} dB   {flag or 'ok'}")
    else:
        spans = speech_segments(src, s0, s1, sp.get("min_pause", 0.8), sp.get("keep", 0.3), sp.get("lead", 0.35), sp.get("tail", 0.7))
    segs = []
    for a, b in spans:
        # clips round UP to a whole frame: rounding down used to shave up to 33 ms off the end of a word ("cut too short")
        d = (math.ceil((b - a) * FPS - 0.02) / FPS) if job.get("clips") else int((b - a) * FPS + 0.05) / FPS
        segs.append({"a": a, "d": d})
    rng = np.random.default_rng(job.get("transition_seed", 5))
    kinds = job.get("transitions") or "cut"  # "cut" = hard cuts like the testimonial reels (default, review 2026-11-16); "auto" = rotating soft transitions
    prev = None
    for k, s in enumerate(segs):
        if k == 0:
            continue
        if kinds == "cut":
            s["tr"] = "cut"
        elif kinds == "auto":
            names = [n for n in PALETTE if n != prev]
            w = np.array([WEIGHTS[n] for n in names], float)
            s["tr"] = str(rng.choice(names, p=w / w.sum()))
        else:
            s["tr"] = kinds[(k - 1) % len(kinds)]
        prev = s["tr"]
        s["ov"] = 0.0 if s["tr"] == "cut" else round(PALETTE.get(s["tr"], OV) / FPS, 4)
    pk = 0.0
    for k, s in enumerate(segs):
        s["p"] = round(pk, 4)  # presenter time at which this span's first frame appears
        pk += s["d"] - (segs[k + 1]["ov"] if k + 1 < len(segs) else 0)
    total = round(pk, 4)
    key = json.dumps([[s["a"], s["d"], s.get("tr")] for s in segs]) + src + str(os.path.getmtime(src))
    dst = os.path.join(pub, "presenter.mp4")
    meta = dst + ".key"
    if os.path.exists(dst) and os.path.exists(meta) and open(meta).read() == key:
        return dst, segs, total
    g = round(-14.3 - media.lufs_file(src, s0, s1 - s0), 2)
    cmd, fc = [], []
    for i, s in enumerate(segs):
        cmd += ["-ss", f"{s['a']:.3f}", "-t", f"{s['d']:.4f}", "-i", src]
        fc.append(f"[{i}:v]{GRADE}[v{i}]")
        fc.append(f"[{i}:a]aresample=48000,volume={g}dB,alimiter=limit=0.84:level=disabled[a{i}]")
    cv, ca, acc = "v0", "a0", segs[0]["d"]
    if kinds == "cut":  # hard cuts, each inside a pause; 12 ms audio fades keep the join click-free
        for i, sg in enumerate(segs):
            fc[2 * i + 1] += f";[a{i}]afade=t=in:d=0.012,afade=t=out:st={sg['d'] - 0.012:.4f}:d=0.012[b{i}]"
        fc.append("".join(f"[v{i}][b{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[cv][ca]")
        cv, ca, acc = "cv", "ca", sum(sg["d"] for sg in segs)
    for k in range(1, len(segs) if kinds != "cut" else 1):
        ov = segs[k]["ov"]
        fc.append(f"[{cv}][v{k}]xfade=transition={segs[k]['tr']}:duration={ov:.4f}:offset={acc - ov:.4f}[x{k}]")
        fc.append(f"[{ca}][a{k}]acrossfade=d={ov:.4f}:c1=tri:c2=tri[y{k}]")
        cv, ca, acc = f"x{k}", f"y{k}", acc + segs[k]["d"] - ov
    fc.append(f"[{ca}]afade=t=in:d=0.02,afade=t=out:st={acc - 0.2:.3f}:d=0.2[ao]")
    print(f"  presenter: {len(segs)} takes, {total:.1f}s from {s1 - s0:.1f}s of speech; transitions: {' '.join(x.get('tr', '') for x in segs[1:])}", flush=True)
    media.run([*cmd, "-filter_complex", ";".join(fc), "-map", f"[{cv}]", "-map", "[ao]", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
               "-g", "15", "-c:a", "aac", "-b:a", "256k", dst])
    open(meta, "w").write(key)
    return dst, segs, total


def tmap(segs, ts):
    """Source time -> presenter time (a time inside a removed pause lands on the next kept frame)."""
    for s in segs:  # the clip that holds this source time (clips need not be in source order)
        if s["a"] - 0.02 <= ts <= s["a"] + s["d"] + 0.02:
            return round(s["p"] + min(s["d"], max(0.0, ts - s["a"])), 3)
    for s in segs:
        if ts <= s["a"] + s["d"]:
            return round(s["p"] + max(0.0, ts - s["a"]), 3)
    return round(segs[-1]["p"] + segs[-1]["d"], 3)


def camera(job, segs, total):
    """Subtle camera: a continuous scale/pan path over the talk. Most takes hold still; about 4 in 10 carry a slow move
    (push-in, pull-out or a gentle drift) that lasts the whole take. Never two moves of one kind in a row. Keyframes:
    {t, s, x} in presenter time; the renderer eases between them."""
    rng = np.random.default_rng(job.get("camera_seed", 11))
    cur, x, last = 1.0, 0.0, None
    keys = [{"t": 0.0, "s": 1.0, "x": 0.0}]
    for k, sg in enumerate(segs):
        t0, t1 = sg["p"], sg["p"] + sg["d"] - (segs[k + 1]["ov"] if k + 1 < len(segs) else 0)
        if k == 0 or t1 - t0 < 2.6 or rng.random() > job.get("camera_amount", 0.0):
            continue
        opts = ["push", "drift"] if cur < 1.02 else ["pull", "drift"]
        opts = [o for o in opts if o != last] or opts
        mv = str(rng.choice(opts))
        ns, nx = cur, x
        if mv == "push":
            ns = round(cur + 0.045, 3)
        elif mv == "pull":
            ns = 1.0
        else:
            ns = max(cur, 1.03)
            nx = round(float(rng.choice([-14, 14])) if abs(x) < 1 else -x, 1)
        nx = round(max(-(ns - 1) * 480, min((ns - 1) * 480, nx)), 1)  # a pan never shows the frame edge
        keys += [{"t": round(t0 + 0.2, 3), "s": cur, "x": x}, {"t": round(t1 - 0.1, 3), "s": ns, "x": nx}]
        cur, x, last = ns, nx, mv
    keys.append({"t": round(total, 3), "s": cur, "x": x})
    return keys


def cut_fx(job, segs):
    """About 3 in 5 cuts get a soft renderer move (never the same one twice in a row); the others stay a plain dissolve."""
    rng = np.random.default_rng(job.get("fx_seed", 9))
    out, prev = [], None
    for sg in segs[1:]:
        opts = [f for f in FX if f != prev] if prev else FX
        kind = opts[int(rng.integers(len(opts)))]
        if kind:
            out.append({"t": round(sg["p"] + sg["ov"] / 2, 3), "kind": kind, "dir": 1 if rng.random() < 0.5 else -1})
        prev = kind
    return out


def leaks(job, m, total):
    """Light leaks (the colourful smooth transition of the bootcamp testimonial reels) only where a transition is NECESSARY
    (review 2026-11-16/17): (1) the intro handing over to the first shot (pink, automatic unless the talk opens on frame 0),
    (2) every entry of job["leaks_at"]: a source time in seconds, or {"at": seconds, "tone": "pink" | "green"}, (3) the hand-over to
    the Ghost Text closer when job["closer"] (30 s cut). Direction alternates. `"leaks": "off"` = none."""
    if job.get("leaks", "auto") == "off":
        return []
    items = [] if job.get("opening") == "none" else [{"at": 0.0, "tone": "pink", "p": 0.0}]
    for x in job.get("leaks_at", []):
        d = x if isinstance(x, dict) else {"at": x}
        items.append({"at": d["at"], "tone": d.get("tone", "pink"), "p": m(d["at"])})
    if job.get("closer"):
        items.append({"at": None, "tone": "pink", "p": total})
    items.sort(key=lambda d: d["p"])
    return [{"t": round(d["p"], 3), "dir": 1 if i % 2 == 0 else -1, "tone": d["tone"]} for i, d in enumerate(items)]


def speech_end_trim(source, s0, s1, caps_src):
    """Trim each caption's end to the last frame of real speech inside it (+0.15 s): the aligner lets the last word run on into
    the pause after it, and the caption then hung on screen over silence."""
    x = media.pcm(source, sr=16000, channels=1, ss=s0, t=s1 - s0)
    n = len(x) // 320
    db = 20 * np.log10(np.sqrt((x[:n * 320].reshape(n, 320) ** 2).mean(1)) + 1e-7)
    db = np.convolve(db, np.ones(3) / 3, "same")
    act = db > np.percentile(db, 10) + 4.5
    out = []
    for a, b in caps_src:
        i0, i1 = max(0, int((a - s0) / 0.02)), min(n, int((b - s0) / 0.02))
        idx = np.where(act[i0:i1])[0]
        out.append(round(min(b, s0 + (i0 + idx[-1] + 1) * 0.02 + 0.15), 3) if len(idx) else b)
    return out


def build_screen(job, base, pub, st, x):
    """One screen grab for a single-video stack, cropped and slowed/sped to PLAY for the whole time it is on screen (a screen
    recording often idles: only its `seconds` of real motion are used, stretched to the stack length, 0.6x-1.6x)."""
    g = job["screens"][x["screen"]]
    want = st["to"] - st["from"] - 0.5  # the window needs ~0.5 s to open before the footage matters
    f = min(1.6, max(0.6, want / g["seconds"]))
    play = round(g["seconds"] * f, 2)
    dst = os.path.join(pub, f"screen_{x['screen']}_{g.get('t', 0)}_{g['seconds']}_{play}.mp4")  # name carries t/seconds/length so an edited job never reuses a stale grab
    if not os.path.exists(dst):
        media.run(["-ss", str(g.get("t", 0)), "-t", str(g["seconds"]), "-i", P(base, g["src"]), "-an",
                   "-vf", f"crop={g['crop']},setpts={f:.4f}*PTS,fps=30,scale={g.get('width', 1440)}:-2:flags=lanczos,format=yuv420p",
                   "-c:v", "libx264", "-crf", "16", "-preset", "medium", dst])
    return {**st, "src": os.path.basename(dst), "to": round(min(st["to"], st["from"] + 0.5 + play), 3)}


def build_scenes(job, base, pub, L, m):
    """A screen recording cut into SCENES that follow what is being said: each scene = a stretch of the recording (`t`, `seconds`)
    shown while the presenter says the words in `at` (source seconds), retimed 0.5x-2.2x to fit (frozen on its last frame if it
    is still too short). One file per scene, each padded with 0.8 s of its last frame so the renderer can hold it while the curtain
    (curtain-slider motion) wipes it away. Returns [(file name, presenter-time from, presenter-time to)]."""
    out = []
    for s in L["scenes"]:
        g = job["screens"][s.get("screen", L["screen"])]  # a scene may use another crop of the recording (e.g. a close-up of a side panel)
        a, b = m(s["at"][0]), m(s["at"][1])
        dur = b - a
        f = min(2.2, max(0.5, dur / s["seconds"]))
        pad = max(0.0, dur - s["seconds"] * f) + 0.8
        key = json.dumps([g["crop"], g.get("width"), s["t"], s["seconds"], round(dur, 3)])
        dst = os.path.join(pub, f"scene_{s.get('screen', L['screen'])}_{hashlib.md5(key.encode()).hexdigest()[:8]}.mp4")
        if not os.path.exists(dst):
            media.run(["-ss", str(s["t"]), "-t", str(s["seconds"]), "-i", P(base, g["src"]), "-an",
                       "-vf", f"crop={g['crop']},setpts={f:.4f}*PTS,fps=30,scale={g.get('width', 2016)}:-2:flags=lanczos,format=yuv420p,"
                              f"tpad=stop_mode=clone:stop_duration={pad:.3f},trim=duration={dur + 0.8:.3f},setpts=PTS-STARTPTS",
                       "-c:v", "libx264", "-crf", "16", "-preset", "medium", dst])
        out.append((os.path.basename(dst), a, b))
    return out


def plan(job, base, pub, segs, total, end_card):
    m = lambda t: tmap(segs, t)  # noqa: E731
    caps = []
    rows = job.get("captions", [])
    sp = job.get("speech", {})
    ends = speech_end_trim(P(base, job["source"]), sp.get("start", 0.0), sp.get("end", media.duration(P(base, job["source"]))), [(r[0], r[1]) for r in rows]) if rows else []
    for row, b_trim in zip(rows, ends):
        a, b, text = row[:3]
        b = b_trim
        text = re.sub(r"\s+([,.!?;:])", r"\1", re.sub(r"\s*\[[^\]]*\]", "", text)).strip()  # [hidden words] only help --align
        if not re.search(r"\w", text):
            continue
        if not any(sg["a"] - 0.05 <= (a + b) / 2 <= sg["a"] + sg["d"] + 0.05 for sg in segs):  # a caption outside every kept clip has nothing to sit on
            continue
        caps.append({"from": m(a), "to": min(total - 0.05, m(b) + 0.1), "text": text})
    caps.sort(key=lambda c: c["from"])
    for i in range(len(caps) - 1):
        caps[i]["to"] = min(caps[i]["to"], caps[i + 1]["from"])
    caps = [c for c in caps if c["to"] - c["from"] > 0.2]
    default_enter = {"tall": "slide", "wide": "rise"}
    stacks = []
    for x in job.get("stacks", []):
        enter = x.get("enter", default_enter[x["kind"]])
        if "layers" in x:
            layers = []
            for L in x["layers"]:
                lab = {"label": L["label"]} if L.get("label") else {}
                if L["type"] == "map":
                    f0, f1 = m(L["at"][0]), m(L["at"][1])
                    layers.append({"type": "map", "from": f0, "to": f1, "cues": {k: (round(m(v) - f0, 3) if k in ("arrive", "last50", "solved") else v) for k, v in L["cues"].items()}, **lab})  # start/legDur are plain durations

                else:
                    for src, f0, f1 in build_scenes(job, base, pub, L, m):
                        layers.append({"type": "video", "src": src, "from": f0, "to": f1, **lab})
            stacks.append({"from": layers[0]["from"], "to": layers[-1]["to"], "kind": x["kind"], "enter": enter, "layers": layers})
        else:
            st = {"from": m(x["at"][0]), "to": m(x["at"][1]), "kind": x["kind"], "enter": enter, **({"label": x["label"]} if x.get("label") else {})}
            stacks.append(build_screen(job, base, pub, st, x))
    chapters = [] if not job.get("show_chapters", False) else [{"from": m(c["at"][0]), "to": min(total - 0.5, m(c["at"][1])), "num": c["num"], "label": c["label"], } for c in job.get("chapters", [])]
    props = {"presenter": "presenter.mp4", "presenterSeconds": total, "cam": camera(job, segs, total), "leaks": leaks(job, m, total), "captionY": job.get("caption_y", 1620), "fx": cut_fx(job, segs) if job.get("fx_amount", 0) else [], "stacks": stacks, "captions": caps,
             "chapters": chapters, "captionFont": "GIP-Regular.woff2" if os.path.exists(os.path.join(pub, "GIP-Regular.woff2")) else None, "mark": "pinecone_mark.svg" if os.path.exists(os.path.join(ENGINE, "assets", "pinecone_mark.svg")) else None,
             "meta": bool(job.get("intro_meta", False)), "chapterStyle": job.get("chapter_style", "pill"), "look": job.get("look", "split"), "noIntro": job.get("opening") == "none", "closer": bool(job.get("closer")), "moveFrames": job.get("stack_move_frames", 20), "curtainFrames": job.get("curtain_frames", 21), "captionStyle": job.get("caption_style", "plate"), "captionFace": job.get("caption_face", "source"), "outroSeconds": job.get("outro_seconds", 3.2), "nextLabel": job.get("next_label", "EP 02 · soon")}
    if job.get("name_tag"):
        props["nameTag"] = job["name_tag"]
    if job.get("closer_ep"):
        props["closerEp"] = job["closer_ep"]
    if job.get("brand_moments"):
        props["brands"] = [{"name": b["name"], "label": b.get("label"), "word": b.get("word", "" if b["name"] == "text" else b["name"]), "color": b["color"], "logo": (f"{b['name']}_mark.png" if os.path.exists(os.path.join(pub, f"{b['name']}_mark.png")) else None), "from": m(b["at"][0]), "to": m(b["at"][1]), **({"plain": True} if b.get("plain") else {})} for b in job["brand_moments"]]
    if job.get("closer"):
        # the closer is as long as it takes for the whole video to land on its target length (30 s max)
        props["closerFrames"] = max(132, min(210, round(job.get("target_seconds", 30.0) * FPS) - round(total * FPS)))
        if job.get("name_tag") and job.get("closer_signature", True):
            props["signature"] = f"{job['name_tag']['name']}, {job['name_tag']['role']}"
    props = {k: v for k, v in props.items() if v is not None}
    if end_card:
        props["endCard"] = "end_card.mp4"
        props["endCardSeconds"] = round(media.duration(end_card) - 0.05, 2)
    return props


def frames_of(props):
    p0 = 0 if props.get("noIntro") else TIM["presenterStart"]
    pf = round(props["presenterSeconds"] * FPS)
    e = p0 + pf
    out = e + (props.get("closerFrames", 150) if props.get("closer") else round(props["outroSeconds"] * FPS))  # 150 = CLOSER_F in EngEpisode.tsx
    total = out + (round(props["endCardSeconds"] * FPS) - 12 if props.get("endCard") else 0)
    return p0, e, out, total


def render(props, comp, out, pub, conc):
    pf = out + ".props.json"
    json.dump(props, open(pf, "w"), ensure_ascii=False, indent=1)
    try:
        stages.render(pf, out, pub, conc, comp=comp)
    except RuntimeError as e:
        print(f"  render retry at concurrency 1 ({e})", flush=True)
        stages.render(pf, out, pub, 1, comp=comp)


def music(plan_file, mdir, style):
    subprocess.run([sys.executable, "-I", os.path.join(ENGINE, "reelpipe", "eng_music.py"), plan_file, mdir], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--plan", action="store_true")
    g.add_argument("--intro", action="store_true")
    g.add_argument("--align", action="store_true")
    g.add_argument("--remix", action="store_true", help="redo music + master on the last render (no re-render): for sound changes")
    ap.add_argument("--force", action="store_true", help="with --align: also apply lines the aligner moved more than 1 s")
    a = ap.parse_args()
    jp = os.path.abspath(a.job)
    if a.align:
        return pinequest.align(jp, a.force)
    base, job = os.path.dirname(jp), json.load(open(jp, encoding="utf8"))
    name = os.path.basename(base) if os.path.splitext(os.path.basename(jp))[0] == "job" else os.path.splitext(os.path.basename(jp))[0]
    build = os.path.join(ENGINE, "build", "engineers", name)
    pub = os.path.join(build, "public")
    os.makedirs(pub, exist_ok=True)
    out_dir = P(base, job.get("out_dir", "~/Desktop/ai edited reels"))
    os.makedirs(out_dir, exist_ok=True)
    stem, conc = job["file_stem"], job.get("concurrency", 2)
    end_card = prep(job, base, pub)
    mark = "pinecone_mark.svg" if os.path.exists(os.path.join(pub, "pinecone_mark.svg")) else None
    if a.intro:  # standalone intro: ink slate, own sound
        n = TIM["standaloneFrames"]
        mp = os.path.join(build, "intro_music.json")
        json.dump({"fps": FPS, "total_s": n / FPS, "presenter_start_f": n, "presenter_end_f": n, "signoff_f": n, "next_len": 0, "stacks": [],
                   **({"music_style": job["music_style"]} if job.get("music_style") else {})}, open(mp, "w"))
        music(mp, os.path.join(build, "intro_music"), job.get("music_style"))
        vid = os.path.join(build, "intro_render.mp4")
        render({**({"mark": mark} if mark else {}), "meta": bool(job.get("intro_meta", False))}, "EngIntro", vid, pub, conc)
        out = os.path.join(out_dir, stem + "_intro.mp4")
        sfx = os.path.join(build, "intro_music", "sfx.wav")
        media.run(["-i", vid, "-i", sfx, "-filter_complex", "[1:a]volume=0.8,loudnorm=I=-22:TP=-2:LRA=7,aresample=48000[o]", "-map", "0:v", "-map", "[o]",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-t", f"{n / FPS:.3f}", out])
        print(f"intro -> {out}", flush=True)
        return
    pres, segs, total = build_presenter(job, base, pub)
    props = plan(job, base, pub, segs, total, end_card)
    p0, e, out_f, tot = frames_of(props)
    pl = os.path.join(build, "plan.json")
    json.dump({"props": props, "segs": segs, "frames": {"presenter_start": p0, "presenter_end": e, "outro_end": out_f, "total": tot}}, open(pl, "w"), ensure_ascii=False, indent=1)
    print(f"  intro 0-{p0 / FPS:.2f}s  presenter {p0 / FPS:.2f}-{e / FPS:.2f}s  {'closer' if props.get('closer') else 'sign-off'} to {out_f / FPS:.2f}s  total {tot / FPS:.2f}s", flush=True)
    for s in props["stacks"]:
        print(f"  stack {s['kind']:4s} {s['enter']:5s} {s['from']:6.2f}-{s['to']:6.2f}  " + (s.get("src") or " + ".join(f"{l['type']}[{l['from']:.1f}-{l['to']:.1f}]" for l in s["layers"])))
    if a.plan:
        return
    vid = os.path.join(build, "render.mp4")
    if not (a.remix and os.path.exists(vid)):
        render(props, "EngEpisode", vid, pub, conc)
    mp = os.path.join(build, "music_plan.json")
    json.dump({"fps": FPS, "total_s": tot / FPS, "presenter_start_f": p0, "presenter_end_f": e, "signoff_f": e - 14, "next_len": 0 if props.get("closer") else len(props["nextLabel"]), "closer": bool(props.get("closer")), "intro_at_f": e if props.get("closer") else 0, "bed_fade_in": 1.0 if props.get("noIntro") else 2.4, "leaks": [p0 + round(l["t"] * FPS) for l in props.get("leaks", [])],
               "stacks": [[p0 + round(s["from"] * FPS), p0 + round(s["to"] * FPS)] for s in props["stacks"]],
               **({"music_style": job["music_style"]} if job.get("music_style") else {}),
               **({"external_bed": {"file": P(base, job["music_file"]), "start": job.get("music_start", 0)}} if job.get("music_file") else {})}, open(mp, "w"))
    mdir = os.path.join(build, "music")
    music(mp, mdir, job.get("music_style"))
    out = os.path.join(out_dir, stem + ".mp4")
    body_end = (out_f if not end_card else out_f - 12) / FPS
    lu, tp = pinequest.finish(vid, body_end, out, os.path.join(mdir, "bed.wav"), os.path.join(mdir, "sfx.wav"), job.get("speech_over_bed_db", 16.0),
                              speech_from=p0 / FPS, intro_boost_db=0.0 if props.get("noIntro") else job.get("intro_sfx_boost_db", 9.0), end_card=bool(end_card), static_master=True)
    print(f"episode -> {out}  {lu} LUFS / {tp} dBTP", flush=True)


if __name__ == "__main__":
    main()
