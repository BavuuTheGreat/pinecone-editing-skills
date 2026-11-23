"""Pipeline stages for one student: EDL -> cut -> props -> render -> finish -> captions -> mix -> check.

Every stage reads the batch manifest (see batches/*.json) and writes into build/<batch>/.
Rules come from the Editing rulebook (docs/tdd/content-factory-editing-tdd.md)."""
import json
import math
import os
import shutil
import subprocess
import time

import numpy as np

from . import media

FPS = 30
PIECE_LUFS = -14.3      # every piece gained to one level before assembly
SPEECH_LUFS = -14.5     # final speech level
CAPTION_HOLD = 0.58     # caption stays this long after its words end (matches the caption tool)
VF = ("[0:v]scale=1080:1920:flags=lanczos,fps=30,setsar=1,eq=contrast=1.04:saturation=1.05,"
      "unsharp=5:5:0.35,format=yuv420p[vo]")
ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def frames(sec: float) -> int:
    return round(sec * FPS)


# ---------- EDL ----------

def resolve_pieces(student: dict) -> list[dict]:
    """Pieces with explicit start/end pass through. Pieces given as word times
    (word_start, word_end, lo, hi) are snapped to the quietest 40 ms nearby."""
    pieces, mono = [], None
    for p in student["pieces"]:
        if "start" in p:
            pieces.append(p)
            continue
        if mono is None:
            mono = media.pcm(student["source"], sr=16000, channels=1)
        s = media.quietest(mono, 16000, max(p["lo"], p["word_start"] - 0.45), p["word_start"] - 0.03)
        e = media.quietest(mono, 16000, p["word_end"] + 0.05, min(p["hi"], p["word_end"] + 0.5))
        rest = {k: v for k, v in p.items() if k not in ("word_start", "word_end", "lo", "hi")}  # keep tail / join / level
        pieces.append({**rest, "start": s, "end": e})
    return pieces


# ---------- cut ----------

def cut(student: dict, pieces: list[dict], public: str) -> list[dict]:
    """Cut each piece to 1080x1920/30 with the house grade, gained to PIECE_LUFS, 120 ms fade-out."""
    clips = []
    for p in pieces:
        a = p["start"]
        d = math.floor((p["end"] - a) * FPS + 0.05) / FPS  # tolerance: ms-rounded EDL times must not lose a frame
        tail = float(p.get("tail", 0))
        if tail > 0:  # never ask for picture past the end of the source file
            tail = min(tail, max(0.0, media.duration(student["source"]) - p["end"]))
        tail = math.floor(tail * FPS + 0.05) / FPS  # tail: picture keeps running after the speech, sound faded out
        dst = os.path.join(public, f"{student['key']}_{p['id']}_{round(a * 1000)}_{round(p['end'] * 1000)}{'_L%d-%d' % (round(p['level'][0] * 1000), round(p['level'][1] * 1000)) if p.get('level') else ''}{'_T%d' % round(tail * 1000) if tail else ''}.mp4")  # times in name: an edited piece never reuses a stale cut
        if not os.path.exists(dst):
            la, lb = p.get("level") or (a, a + d)  # level: measure the gain over the whole answer, so pieces of one
            g = round(PIECE_LUFS - media.lufs_file(student["source"], la, lb - la), 2)  # answer (pauses removed) keep their natural dynamics
            af = (f"[0:a]aresample=48000,volume={g}dB,alimiter=limit=0.84:level=disabled,"
                  f"afade=t=in:d=0.025,afade=t=out:st={round(d - 0.12, 4)}:d=0.12[ao]")
            media.run(["-ss", str(a), "-t", str(d + tail), "-i", student["source"], "-filter_complex", VF + ";" + af,
                       "-map", "[vo]", "-map", "[ao]", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-g", "15",
                       "-c:a", "aac", "-b:a", "256k", "-t", str(d + tail), dst])
        clips.append({**p, "src": os.path.basename(dst), "seconds": round(d + tail, 4)})
    return clips


# ---------- props ----------

def props(batch: dict, student: dict, clips: list[dict]) -> dict:
    items = []
    for c in clips:
        card = batch["cards"].get(c["answer"])
        if card and not any(i.get("answer_card") == c["answer"] for i in items):
            items.append({"kind": "question", "text": card["text"], "seconds": card["seconds"],
                          "sfx": card["sfx"], "answer_card": c["answer"]})
        items.append({"kind": "clip", "src": c["src"], "answer": c["answer"], "student": student["key"], "seconds": c["seconds"]})
    items.append({"kind": "clip", "src": os.path.basename(batch["end_card"]), "answer": "outro",
                  "student": student["key"], "seconds": batch["end_card_seconds"], "bare": True})
    title = {"kicker": batch["kicker"], "words": [student["name"]], "wordSeconds": 2.7, "top": 1240, "from": 0.45, "seconds": 3.0}
    if student.get("title_scale"):
        title["scale"] = student["title_scale"]
    return {"shrinkSeconds": 1.1, "holdSeconds": 0, "builtInOutro": False, "titles": [], "items": items, "nameTitle": title}


def speech_windows(p: dict) -> list[tuple[float, float]]:
    t, out = 0, []
    for it in p["items"]:
        n = frames(it["seconds"])
        if it["kind"] == "clip":
            out.append((t / FPS, (t + n) / FPS))
        t += n
    return out


def outro_start(p: dict) -> float:
    return sum(frames(i["seconds"]) for i in p["items"][:-1]) / FPS


# ---------- captions ----------

def _t(s: str) -> float:
    m, r = s.split(":")
    return int(m) * 60 + float(r)


def caption_props(base: dict, caption_file: str, style: dict, dy: dict | None) -> dict:
    """Caption lines `m:ss.cc|m:ss.cc|text` (from the caption tool, human-corrected) -> on-screen captions.
    Each line holds CAPTION_HOLD after its words, never past the next line or the end of its clip."""
    lines = [l.rstrip("\n").split("|") for l in open(caption_file, encoding="utf8") if l.strip()]
    wins = speech_windows(base)[:-1]  # clips only, not the end card
    caps = []
    for i, (a, b, text) in enumerate(lines):
        a, b = _t(a), _t(b)
        nxt = _t(lines[i + 1][0]) if i + 1 < len(lines) else 1e9
        c = {"from": a, "to": min(b + CAPTION_HOLD, max(nxt, b)), "text": text}
        for ws, we in wins:
            if ws - 0.05 <= a < we:
                c["to"] = min(c["to"], we)
        c["to"] = min(c["to"], outro_start(base))
        if dy and a < dy["until"]:
            c["dy"] = dy["dy"]
        caps.append(c)
    return {**base, "captions": caps, "captionStyle": style}


# ---------- render ----------

def _kill_group(proc) -> None:
    """Kill the render and every headless browser it started (plain kill left orphans holding RAM)."""
    import signal
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.kill()


def render(props_file: str, out: str, public: str, concurrency: int, comp: str = "StudentReel") -> None:
    """Remotion render. Stops early if the browser crash-loops (seen at concurrency 6 on a 16 GB Mac)."""
    log = out + ".log"
    exe = os.path.join(ENGINE, "node_modules", ".bin", "remotion.cmd" if os.name == "nt" else "remotion")
    cmd = [exe, "render", "src/index.tsx", comp, out,
           f"--props={props_file}", f"--public-dir={public}", "--codec=h264", "--crf=16", f"--concurrency={concurrency}"]
    stall = {"mark": None, "since": time.time()}
    with open(log, "w") as fh:
        proc = subprocess.Popen(cmd, cwd=ENGINE, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)  # own group: kill browsers too
        while proc.poll() is None:
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                text = open(log, errors="ignore").read()
                if text.count("browser crashed") > 50:
                    _kill_group(proc)
                    raise RuntimeError(f"render crash-loop, lower concurrency: {log}")
                last = text.rfind("Rendered ")
                mark = text[last:last + 30] if last >= 0 else ""
                if mark == stall.get("mark"):
                    if time.time() - stall["since"] > 120:  # no progress for 2 min (browser tab died)
                        _kill_group(proc)
                        raise RuntimeError(f"render stalled at {mark.strip()}, lower concurrency: {log}")
                else:
                    stall.update(mark=mark, since=time.time())
    if proc.returncode:
        raise RuntimeError(f"render failed: {log}")


# ---------- audio ----------

def finish(src: str, p: dict, out: str) -> None:
    """Gain speech to SPEECH_LUFS, limit true peak to <= -1 dBTP."""
    a = media.pcm(src)
    sp = np.concatenate([a[int(s * media.SR):int(e * media.SR)] for s, e in speech_windows(p)])
    g = SPEECH_LUFS - media.lufs_of(sp)
    lim = 0.85
    for _ in range(5):
        media.run(["-i", src, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af",
                   f"volume={g}dB,alimiter=limit={lim}:level=disabled:attack=2:release=60,aresample=48000",
                   "-c:a", "aac", "-b:a", "256k", out])
        if media.loudness_report(out)[1] <= -1.0:
            return
        lim *= 0.95


def mix(src: str, p: dict, music: str, out: str, speech_over_bed_db: float) -> dict:
    """Constant music bed (no ducking, as in the reference reels), 0.5 s in / 2.5 s out,
    two-pass loudnorm to -14.5 LUFS / -1 dBTP, then a safety limiter if the peak still overshoots."""
    dur = media.duration(src)
    a = media.pcm(src)
    sp = np.concatenate([a[int(s * media.SR):int(e * media.SR)] for s, e in speech_windows(p)])
    m = media.pcm(music, t=dur)
    ms = np.concatenate([m[int(s * media.SR):int(e * media.SR)] for s, e in speech_windows(p) if s * media.SR < len(m)])
    g = media.lufs_of(sp) - speech_over_bed_db - media.lufs_of(ms)
    chain = (f"[1:a]volume={g}dB,afade=t=in:d=0.5,afade=t=out:st={dur - 2.5}:d=2.5[m];"
             f"[0:a][m]amix=inputs=2:duration=first:normalize=0,")
    ln = "loudnorm=I=-14.5:TP=-1:LRA=11"
    measure = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-t", str(dur), "-i", music, "-filter_complex",
                              chain + ln + ":print_format=json[o]", "-map", "[o]", "-f", "null", "-"],
                             capture_output=True, text=True).stderr
    j = json.loads(measure[measure.rindex("{"):measure.rindex("}") + 1])
    ex = (f":measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    media.run(["-i", src, "-i", music, "-filter_complex", chain + ln + ex + ",aresample=48000[o]", "-map", "0:v", "-map", "[o]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-t", str(dur), out])
    lufs, tp = media.loudness_report(out)
    if tp > -1.0:  # linear loudnorm can't always hold the ceiling: limit from the unlimited mix until it does
        raw, tmp, lim = out + ".raw.mp4", out + ".lim.mp4", 0.82
        os.replace(out, raw)
        for _ in range(6):
            media.run(["-i", raw, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af",
                       f"volume=0.6dB,alimiter=limit={lim:.3f}:level=disabled:attack=1:release=50,aresample=48000",
                       "-c:a", "aac", "-b:a", "256k", tmp])
            lufs, tp = media.loudness_report(tmp)
            if tp <= -1.0:
                break
            lim *= 0.94
        os.replace(tmp, out)
        os.remove(raw)
    return {"lufs": lufs, "true_peak": tp}


# ---------- edit spec (for the Analytics feedback loop) ----------

def edit_spec(batch: dict, student: dict, p: dict, out: str, loud: dict | None) -> dict:
    clips = [i for i in p["items"] if i["kind"] == "clip" and i.get("answer") != "outro"]
    return {
        "video_id": student.get("video_id"), "student": student["name"], "format": batch.get("format", "testimonial"),
        "duration_s": round(media.duration(out), 2), "answers": sorted({c["answer"] for c in clips}),
        "cards": sum(1 for i in p["items"] if i["kind"] == "question"),
        "avg_piece_s": round(sum(c["seconds"] for c in clips) / max(1, len(clips)), 2),
        "music": os.path.basename(batch["music"]) if loud else None, "speech_over_bed_db": batch["speech_over_bed_db"] if loud else None,
        "caption_style": "v1" if "captions" in p else None, "end_card": os.path.basename(batch["end_card"]),
        "loudness": loud, "rulebook": batch.get("rulebook", "v1"),
    }


def stage_public(batch: dict, public: str) -> None:
    os.makedirs(public, exist_ok=True)
    assets = os.path.join(ENGINE, "assets")
    for f in os.listdir(assets):
        if os.path.isfile(os.path.join(assets, f)) and not os.path.exists(os.path.join(public, f)):
            shutil.copy2(os.path.join(assets, f), public)
