"""Beat grid for cutting on the music.

  python3 beats.py track.wav > beats.json          measure a real track (needs librosa)
  python3 beats.py --bpm 120 --dur 20 > beats.json  exact grid for synthesized music

Output: {"bpm", "beats": [s...], "downbeats": [s...], "hits": [s...]}
- beats: every beat; cut or change something on these
- downbeats: every 4th beat (bar starts); put big moments here
- hits: strongest onsets (measured tracks only); put sound effects here
"""
import argparse
import json
import sys

ap = argparse.ArgumentParser()
ap.add_argument("track", nargs="?")
ap.add_argument("--bpm", type=float)
ap.add_argument("--dur", type=float)
ap.add_argument("--offset", type=float, default=0.0, help="first downbeat, seconds")
a = ap.parse_args()

if a.track is None:
    if not (a.bpm and a.dur):
        sys.exit("give a track, or --bpm and --dur")
    step = 60.0 / a.bpm
    n = int((a.dur - a.offset) / step) + 1
    beats = [round(a.offset + i * step, 3) for i in range(n)]
    out = {"bpm": a.bpm, "beats": beats, "downbeats": beats[::4], "hits": beats[::4]}
else:
    try:
        import librosa
        import numpy as np
    except ImportError:
        sys.exit("pip install librosa numpy soundfile  (or use --bpm/--dur)")
    y, sr = librosa.load(a.track, sr=None, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    beats = librosa.frames_to_time(frames, sr=sr)
    env = librosa.onset.onset_strength(y=y, sr=sr)
    peaks = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=3, post_avg=5, delta=0.5, wait=10)
    # Downbeat guess: the beat phase (0-3) whose beats carry the most onset energy.
    beat_energy = env[np.clip(frames, 0, len(env) - 1)]
    phase = int(np.argmax([beat_energy[p::4].sum() for p in range(4)])) if len(frames) >= 4 else 0
    out = {
        "bpm": round(float(np.atleast_1d(tempo)[0]), 2),
        "beats": [round(float(b), 3) for b in beats],
        "downbeats": [round(float(b), 3) for b in beats[phase::4]],
        "hits": [round(float(h), 3) for h in librosa.frames_to_time(peaks, sr=sr)],
    }
json.dump(out, sys.stdout, indent=1)
print()
