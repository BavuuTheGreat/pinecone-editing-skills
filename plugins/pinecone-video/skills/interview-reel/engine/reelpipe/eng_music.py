"""Sound for the "Engineers matter more with AI" series: an upbeat swing-jazz bed + a few soft tonal sounds.
Synthesized (numpy + ffmpeg), safe to publish, no sample libraries.

  python3 eng_music.py plan.json out_dir

plan.json: {"fps":30, "total_s", "presenter_start_f", "presenter_end_f", "signoff_f", "leaks":[frame...], "stacks":[[from_f,to_f]...],
            "music_style": {"bpm":108,"seed":3,"key":0}}
Writes out_dir/bed.wav (108 BPM swing: electric piano comping on a swung "Charleston" feel, a walking upright bass, a pad, dorian fills
every other bar, a tonal ride, a soft tonal kick on 1 and 3 and a woodblock tick on 2 and 4; ii-V-I-vi; no noise anywhere) and out_dir/sfx.wav (tonal only).
Review 2026-11-16: the old noise-based sounds (typing clicks, air swells, swishes, brush ticks) were "sandy" and repetitive and are gone;
the typing comes back (sixth round) as a soft tonal "thock" with no noise in it, only for the intro title and the sign-off line.
Intro timings come from src/eng/intro_timing.json, the same file the Remotion intro reads.
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
TIM = json.load(open(os.path.join(HERE, "..", "src", "eng", "intro_timing.json")))
plan = json.load(open(sys.argv[1]))
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
FPS = plan.get("fps", 30)
MS = plan.get("music_style") or {}
BPM = float(MS.get("bpm", 108))
BEAT = 60 / BPM
SHIFT = 2 ** (MS.get("key", 0) / 12)
rng = np.random.default_rng(MS.get("seed", 3))
IOFF = plan.get("intro_at_f", 0) / FPS  # when the Ghost Text title plays (0 = at the start; the 30 s cut plays it at the end)
CLOSER = bool(plan.get("closer"))
EXT = plan.get("external_bed")  # {"file": path, "start": seconds}: a supplied track replaces the synthesized bed (and the pitched sounds that would clash with it)
total = plan["total_s"]
N = int((total + 2) * SR)
t_p0 = plan["presenter_start_f"] / FPS


def tt(L): return np.arange(L) / SR
def f2s(f): return f / FPS
def hz(m): return 440.0 * 2 ** ((m - 69) / 12) * SHIFT


def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    s0 = max(0, -i); i = max(i, 0); e = min(len(buf), i + len(sig) - s0)
    buf[i:e] += g * sig[s0:s0 + e - i]


def env(L, a=0.002, d=0.2):
    x = tt(L); return np.minimum(x / a, 1) * np.exp(-x / d)


def wav(path, x, y=None):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x if y is None else np.clip(y, -1, 1)], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------- instruments (all tonal) ----------------
def epiano(f, L, g=1.0, bright=1.0):
    """Rhodes-like: sine body + a tine partial at 2x and a bell at ~7x that dies fast; slight chorus; long soft decay."""
    x = tt(L); y = np.zeros(L)
    for det in (-0.0025, 0.0025):
        ph = 2 * np.pi * f * (1 + det) * x
        y += np.sin(ph) + 0.35 * bright * np.sin(2 * ph) * np.exp(-x / 0.5) + 0.16 * bright * np.sin(7.0 * ph) * np.exp(-x / 0.06)
    return y * 0.5 * g * np.minimum(x / 0.006, 1) * np.exp(-x / 1.1)


def upright(f, L, g=1.0):
    x = tt(L)
    y = np.sin(2 * np.pi * f * x) + 0.5 * np.sin(4 * np.pi * f * x) * np.exp(-x / 0.25) + 0.22 * np.sin(6 * np.pi * f * x) * np.exp(-x / 0.12)
    return y * g * np.minimum(x / 0.008, 1) * np.exp(-x / 0.42)


def pad_note(f, L):
    x = tt(L); y = np.zeros(L)
    for det in (-0.005, 0.0, 0.005):
        y += np.sin(2 * np.pi * f * (1 + det) * x)
    a = np.minimum(x / 1.0, 1) * np.minimum((L / SR - x) / 1.0, 1)
    return y * a * 0.18


def ride(g=1.0):
    """A very quiet metallic 'ding': three inharmonic sines, no noise."""
    n_ = int(0.35 * SR); x = tt(n_)
    return sum(np.sin(2 * np.pi * f * x + p) * a for f, p, a in ((4180, 0.3, 1.0), (6330, 1.1, 0.7), (8870, 2.0, 0.5))) * env(n_, 0.004, 0.09) * g


def kick_soft(g=1.0):
    """A soft tonal kick: a sine that falls from ~140 to 45 Hz. No noise."""
    n_ = int(0.16 * SR); x = tt(n_)
    ph = 2 * np.pi * np.cumsum(45 + 95 * np.exp(-x * 24)) / SR
    return np.sin(ph) * env(n_, 0.002, 0.055) * 0.9 * g


def wood_tick(g=1.0):
    n_ = int(0.05 * SR); x = tt(n_)
    return (np.sin(2 * np.pi * 1150 * x) + 0.4 * np.sin(2 * np.pi * 2300 * x)) * env(n_, 0.003, 0.016) * g


# ---------------- bed: 108 BPM, swung, ii-V-I-vi ----------------
# rootless voicings (midi) and bass roots; one chord per bar
VOICE = [(53, 57, 60, 64), (59, 64, 65, 69), (52, 55, 59, 62), (55, 61, 65, 70)]   # Dm9, G13, Cmaj9, A7b13
ROOT = [38, 43, 36, 45]
THIRD = [41, 47, 40, 49]
FIFTH = [45, 50, 43, 52]
DORIAN = [62, 64, 65, 67, 69, 71, 72]
SW = 2 / 3  # swung 8th lands two thirds of the way through the beat
bar = 4 * BEAT
nb = int((total + 2) / bar) + 1
bed = np.zeros(N); bedR = np.zeros(N)
for k in range(nb):
    t0 = k * bar; ci = k % 4; nxt = (k + 1) % 4
    # pad
    L = int(bar * 1.05 * SR)
    for m in VOICE[ci]:
        place(bed, pad_note(hz(m), L), t0, 0.5)
    # bass: root, third, fifth, chromatic approach to the next root
    walk = [ROOT[ci], THIRD[ci], FIFTH[ci], ROOT[nxt] + (1 if ROOT[nxt] < ROOT[ci] else -1)]
    for b, m in enumerate(walk):
        place(bed, upright(hz(m), int(0.5 * SR), 0.8), t0 + b * BEAT)
    # comping: beat 1 (soft, long) and the "and of 2" and, every other bar, the "and of 4"
    hits = [(0.0, 0.85), (1 + SW, 1.0), (2 + SW, 0.75)] + ([(3 + SW, 0.7)] if k % 2 else [])
    for pos, g in hits:
        for j, m in enumerate(VOICE[ci]):
            place(bed, epiano(hz(m), int(1.8 * SR), 0.20 * g), t0 + pos * BEAT + j * 0.011)
            place(bedR, epiano(hz(m), int(1.8 * SR), 0.20 * g), t0 + pos * BEAT + j * 0.011 + 0.016)
    # ride: ding, ding-a, ding-a (swung), almost inaudible
    for pos in (0, 1, 1 + SW, 2, 3, 3 + SW):
        place(bed, ride(0.09 if pos in (0, 2) else 0.06), t0 + pos * BEAT)
    # kick on 1 and 3, woodblock tick on 2 and 4 (both tonal)
    for pos in (0, 2):
        place(bed, kick_soft(0.32), t0 + pos * BEAT)
    for pos in (1, 3):
        place(bed, wood_tick(0.12), t0 + pos * BEAT)
    # fill every other bar: three to five dorian notes, high and bright
    if k % 2 == 1 and rng.random() < 0.92:
        for j in range(int(rng.integers(3, 6))):
            m = int(rng.choice(DORIAN)) + 12
            pos = 1.5 + j * 0.5 + (SW - 0.5 if j % 2 else 0)
            place(bed, epiano(hz(m), int(1.4 * SR), 0.3, 0.9), t0 + pos * BEAT)
            place(bedR, epiano(hz(m), int(1.4 * SR), 0.3, 0.9), t0 + pos * BEAT + 0.02)
# envelope: starts under the reveal, breathes up while a card is open, resolves at the end
g = np.zeros(N)
a0 = max(0, min(N - 2, int((t_p0 - 0.2) * SR))); a1 = min(N - 1, int((t_p0 + 2.4) * SR))
g[a0:a1] = np.linspace(0, 1, a1 - a0) ** 1.5
g[a1:] = 1.0
for a, b in plan.get("stacks", []):
    i, j = int(a / FPS * SR), int(b / FPS * SR)
    r = int(0.8 * SR)
    g[i:j] *= 1.15
    g[max(0, i - r):i] *= np.linspace(1, 1.15, len(g[max(0, i - r):i]))
    g[j:j + r] *= np.linspace(1.15, 1, len(g[j:j + r]))
tail = int((total - 0.6) * SR)
g[tail:] *= np.linspace(1, 0, len(g[tail:]))
bed *= g; bedR *= g
wav(os.path.join(out, "bed_raw.wav"), bed, bedR)
# warmth + a small room: high cut, low cut, three short reflections
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(out, "bed_raw.wav"), "-af",
                "lowpass=f=6500,highpass=f=45,aecho=0.7:0.5:48|97|173:0.22|0.16|0.1,aecho=0.8:0.4:310:0.12,alimiter=limit=0.7:level=disabled",
                os.path.join(out, "bed.wav")], check=True)

if EXT:
    # while he speaks the track sits under him; when the speech ends (the Ghost Text closer) it rises 6 dB over 0.6 s
    swell = f"volume='1+1*clip((t-{plan['presenter_end_f'] / FPS - 0.3:.2f})/0.6,0,1)':eval=frame," if CLOSER else ""
    D = int(max(0.0, t_p0 - 0.2) * 1000)
    L = total - max(0.0, t_p0 - 0.2)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(EXT.get("start", 0)), "-t", f"{L:.2f}", "-i", EXT["file"], "-af",
                    f"aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-26:TP=-3:LRA=7,aresample=48000,afade=t=in:st=0:d={plan.get('bed_fade_in', 2.4)},afade=t=out:st={max(0.0, L - 3.0):.2f}:d=3.0,adelay={D}|{D},{swell}apad=whole_dur={total + 2:.2f}",
                    os.path.join(out, "bed.wav")], check=True)

# ---------------- sfx: tonal only, a handful of events ----------------
sfx = np.zeros(N + 2 * SR)


def chime(f, L=0.9, g=1.0):
    n_ = int(L * SR); x = tt(n_)
    return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x / 0.12)) * env(n_, 0.003, 0.3) * 0.22 * g


def tock():
    n_ = int(0.2 * SR); x = tt(n_)
    return np.sin(2 * np.pi * 196 * x) * env(n_, 0.001, 0.04) * 0.8 + np.sin(2 * np.pi * 588 * x) * env(n_, 0.0008, 0.015) * 0.35


def key_tone(g=1.0):
    """A soft typed key that fits the room: a short muted 'thock' made of two low sines (no noise, so nothing sandy), pitch varied a little."""
    f = 150 * (1 + 0.16 * (rng.random() - 0.5))
    n_ = int(0.07 * SR); x = tt(n_)
    return (np.sin(2 * np.pi * f * x) * env(n_, 0.0012, 0.018) * 0.9 + np.sin(2 * np.pi * f * 3.1 * x) * env(n_, 0.0008, 0.008) * 0.35) * g


def thum(f, L=0.9, g=1.0):
    n_ = int(L * SR); x = tt(n_)
    return np.sin(2 * np.pi * f * x) * env(n_, 0.012, 0.25) * 0.6 * g


for fr in TIM["line1Keys"] + TIM["line2Keys"]:                                             # the title being typed: soft keys, subtle
    place(sfx, key_tone(0.55 + 0.25 * rng.random()), f2s(fr) + IOFF)
if not EXT:
    place(sfx, chime(hz(88), 0.8, 0.55), f2s(TIM["shimmer"][0] + 2) + IOFF)                      # the ghost appears
place(sfx, tock(), f2s(TIM["tabPress"]) + IOFF, 0.8)                                            # Tab
for i, m in enumerate((69, 72, 74, 77) if not EXT else ()):                               # accepted: Dm9 arpeggio up
    place(sfx, chime(hz(m + 12), 1.2), f2s(TIM["acceptStart"]) + IOFF + 0.09 * i, 0.9)
if not EXT:
    place(sfx, thum(hz(38), 1.0), f2s(TIM["exitStart"]) + IOFF - 0.1, 0.9)                       # the first shot opens
for i, fr in enumerate(plan.get("leaks", []) if not EXT else []):                                            # light leak: an open fifth, a different pair each time
    pair = ((74, 81), (76, 83), (72, 79))[i % 3]
    for j, m in enumerate(pair):
        place(sfx, chime(hz(m), 1.1, 0.6), f2s(fr) - 0.12 + 0.07 * j)
if not EXT and not CLOSER:
    place(sfx, thum(hz(38), 1.3), f2s(plan["signoff_f"]), 0.5)                            # sign-off
for i in range(plan.get("next_len", 0)):                                                  # the sign-off line being typed
    place(sfx, key_tone(0.45 + 0.2 * rng.random()), f2s(plan["signoff_f"] + 38 + 1.6 * i))
sfx *= 0.32  # tonal sounds read much louder than the old noise ones: whole sfx bus down 10 dB
_lo = int(IOFF * SR) if CLOSER else 0
sfx[_lo: _lo + int(((0 if CLOSER else t_p0) + 4.6) * SR)] *= 0.7
sfx = sfx[:N]
wav(os.path.join(out, "sfx.wav"), sfx)
print("bed+sfx", round(total, 2), "s")
