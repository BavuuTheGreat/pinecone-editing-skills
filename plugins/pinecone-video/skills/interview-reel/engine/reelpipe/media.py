"""ffmpeg helpers: probing, PCM, loudness, quiet-point search."""
import json
import re
import subprocess

import numpy as np

SR = 48000


def run(args: list) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duration(path: str) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


def pcm(path: str, sr: int = SR, channels: int = 2, ss: float | None = None, t: float | None = None) -> np.ndarray:
    seek = (["-ss", str(ss)] if ss is not None else []) + (["-t", str(t)] if t is not None else [])
    raw = subprocess.check_output(["ffmpeg", "-v", "error", *seek, "-i", path, "-vn", "-ac", str(channels),
                                   "-ar", str(sr), "-f", "f32le", "-"])
    a = np.frombuffer(raw, np.float32)
    return a.reshape(-1, channels) if channels > 1 else a


def lufs_of(x: np.ndarray, sr: int = SR, channels: int = 2) -> float:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-f", "f32le", "-ar", str(sr), "-ac", str(channels), "-i", "-",
                        "-af", "ebur128", "-f", "null", "-"], input=x.tobytes(), capture_output=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr.decode())[-1])


def lufs_file(path: str, ss: float | None = None, t: float | None = None) -> float:
    seek = (["-ss", str(ss)] if ss is not None else []) + (["-t", str(t)] if t is not None else [])
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *seek, "-i", path, "-vn", "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)[-1])


def loudness_report(path: str) -> tuple[float, float]:
    """Integrated LUFS and true peak (dBTP) of a file."""
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", p)[-1]), float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p)[-1])


def quietest(mono: np.ndarray, sr: int, lo: float, hi: float, win: float = 0.04) -> float:
    """Time in [lo, hi) whose 40 ms window has the lowest RMS: cut points land in breaths, not in words."""
    h = int(win * sr / 2)
    best_t, best_r = lo, float("inf")
    for t in np.arange(lo, hi, 0.01):
        i = int(t * sr)
        s = mono[max(0, i - h):i + h]
        r = float(np.sqrt(np.mean(s * s))) if len(s) else float("inf")
        if r < best_r:
            best_t, best_r = float(t), r
    return round(best_t, 2)
