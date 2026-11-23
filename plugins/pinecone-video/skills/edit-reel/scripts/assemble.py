"""General reel assembler for themes without their own engine.

  python3 -I assemble.py cut    edl.json      # clips -> 1080x1920/30 cut + end card, no music
  python3 -I assemble.py finish edl.json      # (captioned) cut + music bed -> -14.5 LUFS, <= -1 dBTP

edl.json:
{
  "name": "03_hackathon-recap",
  "work": "build/03",                      # scratch folder (relative to edl.json)
  "out": "~/Desktop/ai edited reels/03_hackathon-recap.mp4",
  "clips": [{"src": "raw/a.mp4", "start": 12.4, "end": 15.1, "crop_x": 0.5, "audio": true}],
  "end_card": "default" | null | "path.mp4",
  "music": "default" | null | "path.mp3",
  "speech_over_bed_db": 16.5,              # talk themes; ignored when "music_lead": true
  "music_lead": false,                     # true: no speech, music is the soundtrack (trend, teaser, recap)
  "captioned": "build/03/captioned.mp4"    # optional: brand-templates WordCaptions render of cut.mp4
}
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

SR, W, H, FPS = 48000, 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
TR_ASSETS = os.path.normpath(os.path.join(HERE, "..", "..", "interview-reel", "engine", "assets"))
DEFAULTS = {"end_card": os.path.join(TR_ASSETS, "end_card_9x16.mp4"),
            "music": os.path.join(TR_ASSETS, "music", "Funkorama.mp3")}


def ff(args: list) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def probe(path: str) -> dict:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
                                   "-of", "json", path])
    j = json.loads(out)
    return {"dur": float(j["format"]["duration"]), "audio": any(s["codec_type"] == "audio" for s in j["streams"])}


def pcm(path: str, t: float | None = None) -> np.ndarray:
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, *(["-t", str(t)] if t else []),
                                   "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32).reshape(-1, 2)


def lufs(x: np.ndarray) -> float:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                        "-af", "ebur128", "-f", "null", "-"], input=x.tobytes(), capture_output=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr.decode())[-1])


def report(path: str) -> tuple[float, float]:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p)[-1])


def fit(crop_x: float) -> str:
    """Cover 1080x1920; crop_x 0..1 slides the window across wide footage."""
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:(iw-{W})*{crop_x}:(ih-{H})/2,fps={FPS},setsar=1,format=yuv420p")


def norm_clip(src: str, out: str, start: float | None, end: float | None, crop_x: float, keep_audio: bool) -> float:
    info = probe(src)
    seek = (["-ss", f"{start:.3f}"] if start is not None else []) + (["-to", f"{end:.3f}"] if end is not None else [])
    dur = (end if end is not None else info["dur"]) - (start or 0.0)
    dur = int(dur * FPS + 0.05) / FPS
    if keep_audio and info["audio"]:
        a_in, amap = [], "0:a"
        af = ["-af", f"aresample={SR},afade=t=in:d=0.01,afade=t=out:st={max(dur - 0.01, 0):.3f}:d=0.01"]
    else:
        a_in, amap, af = ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", f"anullsrc=r={SR}:cl=stereo"], "1:a", []
    ff([*seek, "-i", src, *a_in, "-map", "0:v", "-map", amap, "-vf", fit(crop_x), *af, "-t", f"{dur:.3f}",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "256k", "-ac", "2", out])
    return dur


def path_of(edl: dict, base: str, key: str) -> str | None:
    v = edl.get(key, "default")
    if v is None:
        return None
    v = DEFAULTS[key] if v == "default" else v
    return os.path.normpath(os.path.join(base, os.path.expanduser(v)))


def cut(edl: dict, base: str) -> None:
    work = os.path.join(base, edl["work"])
    os.makedirs(work, exist_ok=True)
    parts, spans, t = [], [], 0.0
    for i, c in enumerate(edl["clips"]):
        p = os.path.join(work, f"c{i:02d}.mp4")
        d = norm_clip(os.path.join(base, os.path.expanduser(c["src"])), p, c.get("start"), c.get("end"),
                      c.get("crop_x", 0.5), c.get("audio", True))
        parts.append(p)
        spans.append([round(t, 3), round(t + d, 3)])
        t += d
    end = path_of(edl, base, "end_card")
    if end:
        p = os.path.join(work, "end.mp4")
        norm_clip(end, p, None, None, 0.5, keep_audio=False)
        parts.append(p)
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    ff(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", os.path.join(work, "cut.mp4")])
    with open(os.path.join(work, "spans.json"), "w") as f:
        json.dump({"clips": spans, "body_end": round(t, 3)}, f)
    cuts = max(len(spans) - 1, 0)
    print(json.dumps({"cut": os.path.join(work, "cut.mp4"), "body_s": round(t, 2), "clips": len(spans),
                      "cuts_per_min": round(cuts / t * 60, 1) if t else 0}))


def finish(edl: dict, base: str) -> None:
    work = os.path.join(base, edl["work"])
    src = os.path.join(base, edl["captioned"]) if edl.get("captioned") else os.path.join(work, "cut.mp4")
    out = os.path.normpath(os.path.join(base, os.path.expanduser(edl["out"])))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    music = path_of(edl, base, "music")
    dur = probe(src)["dur"]
    body_end = json.load(open(os.path.join(work, "spans.json")))["body_end"]
    ln = "loudnorm=I=-14.5:TP=-1:LRA=11"
    if music:
        if edl.get("music_lead"):
            g, chain = 0.0, f"[0:a]volume=-60dB[v];"
        else:
            body = pcm(src, body_end)
            g = lufs(body) - edl.get("speech_over_bed_db", 16.5) - lufs(pcm(music, body_end))
            chain = "[0:a]anull[v];"
        chain += (f"[1:a]volume={g:.2f}dB,afade=t=in:d=0.5,afade=t=out:st={dur - 2.5:.3f}:d=2.5[m];"
                  f"[v][m]amix=inputs=2:duration=first:normalize=0,")
        inputs = ["-i", src, "-stream_loop", "-1", "-i", music]
    else:
        chain, inputs = "[0:a]", ["-i", src]
    m = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *inputs, "-t", f"{dur:.3f}", "-filter_complex",
                        chain + ln + ":print_format=json[o]", "-map", "[o]", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
    ex = (f":measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
          f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    raw = os.path.join(work, "mix_raw.mp4")
    ff([*inputs, "-filter_complex", chain + ln + ex + f",aresample={SR}[o]", "-map", "0:v", "-map", "[o]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-t", f"{dur:.3f}", raw])
    lim, (lu, tp) = 0.82, report(raw)
    if tp <= -1.0:
        os.replace(raw, out)
    else:  # linear loudnorm can't always hold the ceiling: limit until it does
        for _ in range(8):
            ff(["-i", raw, "-map", "0:v", "-map", "0:a", "-c:v", "copy", "-af",
                f"volume=0.6dB,alimiter=limit={lim:.3f}:level=disabled:attack=1:release=50,aresample={SR}",
                "-c:a", "aac", "-b:a", "256k", out])
            lu, tp = report(out)
            if tp <= -1.0:
                break
            lim *= 0.94
        os.remove(raw)
    spec = {"name": edl.get("name"), "theme": edl.get("theme"), "out": out, "duration_s": round(dur, 2),
            "lufs": lu, "true_peak": tp, "clips": len(edl["clips"]), "music": music and os.path.basename(music)}
    with open(os.path.join(work, "edit_spec.json"), "w") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    print(json.dumps(spec, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("cut", "finish"):
        sys.exit(__doc__)
    path = os.path.abspath(sys.argv[2])
    edl = json.load(open(path, encoding="utf-8"))
    (cut if sys.argv[1] == "cut" else finish)(edl, os.path.dirname(path))
