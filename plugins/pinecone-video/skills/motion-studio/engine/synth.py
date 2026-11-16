"""Original soundtrack + UI sound effects, generated in code (numpy only).

  python3 synth.py --bpm 120 --dur 6 --cues cues.json --out out/audio.wav

cues.json: [{"t": 1.5, "sfx": "pop"}, {"t": 3.0, "sfx": "whoosh"}, ...]
sfx: click | pop | thump | whoosh | rise. Times should come from beats.json.
The bed is kick on every beat, offbeat hat, and a bass line on the bar root.
Everything is synthesized here, so it is safe to publish.
"""
import argparse
import json
import wave

import numpy as np

SR = 48000
ap = argparse.ArgumentParser()
ap.add_argument("--bpm", type=float, default=120)
ap.add_argument("--dur", type=float, required=True)
ap.add_argument("--cues", default=None)
ap.add_argument("--key", type=float, default=55.0, help="bass root Hz (A1=55)")
ap.add_argument("--out", default="out/audio.wav")
a = ap.parse_args()

n = int(a.dur * SR)
mix = np.zeros(n)
rng = np.random.default_rng(7)  # seeded: identical audio every run


def env(length, attack=0.002, decay=0.15):
    t = np.arange(length) / SR
    return np.minimum(t / attack, 1.0) * np.exp(-t / decay)


def place(sig, t, gain=1.0):
    i = int(t * SR)
    if i >= n:
        return
    end = min(n, i + len(sig))
    mix[i:end] += gain * sig[: end - i]


def kick():
    L = int(0.35 * SR); t = np.arange(L) / SR
    freq = 45 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * env(L, decay=0.12)


def hat():
    L = int(0.06 * SR)
    noise = rng.standard_normal(L)
    return np.diff(noise, prepend=0) * env(L, 0.001, 0.015) * 0.5


def bass(freq, length):
    L = int(length * SR); t = np.arange(L) / SR
    tone = np.sign(np.sin(2 * np.pi * freq * t)) * 0.3 + np.sin(2 * np.pi * freq * t)
    return np.tanh(tone) * env(L, 0.005, length * 0.6) * 0.5


SFX = {
    "click": lambda: np.sin(2 * np.pi * 2200 * np.arange(int(0.03 * SR)) / SR) * env(int(0.03 * SR), 0.0005, 0.006),
    "pop": lambda: np.sin(2 * np.pi * np.cumsum(np.linspace(900, 300, int(0.08 * SR))) / SR) * env(int(0.08 * SR), 0.001, 0.03),
    "thump": lambda: kick() * 1.3,
    "whoosh": lambda: np.convolve(rng.standard_normal(int(0.45 * SR)), np.ones(40) / 40, "same") * np.hanning(int(0.45 * SR)) * 1.5,
    "rise": lambda: np.convolve(rng.standard_normal(int(1.0 * SR)), np.ones(20) / 20, "same") * np.linspace(0, 1, int(1.0 * SR)) ** 2,
}

beat = 60.0 / a.bpm
roots = [1.0, 1.0, 4 / 3, 3 / 2]  # i - i - iv - v, one per bar
for i in range(int(a.dur / beat) + 1):
    t = i * beat
    place(kick(), t, 0.9)
    place(hat(), t + beat / 2, 0.35)
    place(bass(a.key * roots[(i // 4) % 4], beat * 0.9), t, 0.45)

for cue in json.load(open(a.cues)) if a.cues else []:
    place(SFX[cue["sfx"]](), cue["t"], cue.get("gain", 0.8))

mix /= max(1e-9, np.abs(mix).max()) / 0.9  # peak-normalize; finish.sh sets loudness
pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
stereo = np.repeat(pcm[:, None], 2, axis=1)
with wave.open(a.out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(stereo.tobytes())
print(f"wrote {a.out} ({a.dur}s @ {a.bpm} BPM)")
