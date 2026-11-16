"""Original 122 BPM tech/future-house bed + transition SFX, synthesized (numpy + ffmpeg). Safe to publish.

  python3 music.py plan.json out_dir

Writes out_dir/bed.wav (music, stops at body_end with a tail) and out_dir/sfx.wav (whooshes, hits, glitch).
Cards (question items) get a filtered, drumless break; answers get the full groove with a hit on the downbeat.

Opt-in second song: the plan may carry "music_style" (job key of the same name), e.g. {"bpm": 128, "seed": 5, "key": 3}.
Without it the output is byte-identical to the original bed. With it: own tempo, transposition in semitones ("key"),
noise seed, and a different song (major I-V-vi-IV, broken-beat kick, 3+3+2 chord stabs, 8th arp, syncopated bass).
"""
import json, os, subprocess, sys, wave
import numpy as np

SR = 48000
plan = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
MS = plan.get("music_style") or {}
ALT = bool(MS)
BPM = float(MS.get("bpm", 122.0))
BEAT = 60 / BPM
rng = np.random.default_rng(MS.get("seed", 11))
SHIFT = 2 ** (MS.get("key", 0) / 12)
items, FPS = plan["base"]["items"], 30
segs, t = [], 0.0
for it in items:
    n = round(it["seconds"] * FPS) / FPS
    segs.append((it["kind"], t, t + n, it.get("src", "")))
    t += n
body_end = plan["body_end"]
dur = body_end + 2.0
N = int(dur * SR)
cards = [(a, b) for k, a, b, s in segs if k == "question"]
ins = [(x["from"], x["from"] + x["seconds"]) for x in plan["base"]["inserts"]]


def tt(L): return np.arange(L) / SR
def env(L, a=0.002, d=0.2): x = tt(L); return np.minimum(x / a, 1) * np.exp(-x / d)


def place(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i + len(sig) <= 0: return
    s0 = max(0, -i); i = max(i, 0); e = min(len(buf), i + len(sig) - s0)
    buf[i:e] += g * sig[s0:s0 + e - i]


def saw(f, L, harm=14, detune=0.0):
    x = tt(L); y = np.zeros(L)
    for k in range(1, harm + 1):
        if f * k > 9000: break
        y += np.sin(2 * np.pi * f * (1 + detune) * k * x) / k
    return y * 0.55


# ---------- drums ----------
def kick():
    L = int(0.42 * SR); x = tt(L); fr = 48 + 140 * np.exp(-x * 38)
    body = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(L, 0.001, 0.16)
    click = rng.standard_normal(L) * env(L, 0.0005, 0.004) * 0.25
    return np.tanh((body + click) * 1.6)


def clap():
    L = int(0.3 * SR); n = rng.standard_normal(L); e = np.zeros(L)
    for d in (0, 0.011, 0.022):
        e += np.roll(env(L, 0.0008, 0.012), int(d * SR))
    e += env(L, 0.001, 0.09) * 0.6
    return np.diff(n, prepend=0) * e * 0.55


def hat(open_=False):
    L = int((0.22 if open_ else 0.05) * SR); n = rng.standard_normal(L)
    hp = n - np.convolve(n, np.ones(6) / 6, "same")
    return hp * env(L, 0.0007, 0.09 if open_ else 0.014) * (0.35 if open_ else 0.3)


# progression i-VI-III-VII in A minor, one chord per bar
CH = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (261.63, 329.63, 392.0), (196.0, 246.94, 293.66)]
ROOT = [55.0, 43.65, 65.41, 49.0]
if ALT:  # I-V-vi-IV in A major (then transposed by "key")
    def _f(semi): return 220.0 * 2 ** (semi / 12)
    CH = [(_f(0), _f(4), _f(7)), (_f(7), _f(11), _f(14)), (_f(9), _f(12), _f(16)), (_f(5), _f(9), _f(12))]
    ROOT = [55.0, 82.41, 69.30, 73.42]
    CH = [tuple(x * SHIFT for x in c) for c in CH]
    ROOT = [x * SHIFT for x in ROOT]

drums, bass, pad, arp = (np.zeros(N) for _ in range(4))
K, C, H, HO = kick(), clap(), hat(), hat(True)
nbeats = int(dur / BEAT) + 1
kick_times = []
for b in range(nbeats):
    t0 = b * BEAT
    if ALT:  # broken beat: kick on 1, "a" of 2, "and" of 3; clap on 2 and 4; swung 16th hats, open hat on every off-8th
        if b % 4 == 0: place(drums, K, t0, 0.95); kick_times.append(t0)
        if b % 4 == 1:
            place(drums, K, t0 + BEAT * 0.75, 0.85); kick_times.append(t0 + BEAT * 0.75)
        if b % 4 == 2: place(drums, K, t0 + BEAT * 0.5, 0.9); kick_times.append(t0 + BEAT * 0.5)
        if b % 4 == 3 or b % 4 == 1: place(drums, C, t0, 0.7)
        for q in range(4):
            place(drums, H, t0 + BEAT * (q / 4 + (0.03 if q % 2 else 0)), 0.14 if q % 2 else 0.3)
        place(drums, HO, t0 + BEAT / 2, 0.3)
        continue
    place(drums, K, t0, 0.95); kick_times.append(t0)
    if b % 2 == 1: place(drums, C, t0, 0.7)
    place(drums, H, t0 + BEAT / 2, 0.45)
    place(drums, H, t0 + BEAT * 0.25, 0.12); place(drums, H, t0 + BEAT * 0.75, 0.15)
    if b % 4 == 3: place(drums, HO, t0 + BEAT / 2, 0.35)

bar = 4 * BEAT
for k in range(int(dur / bar) + 1):
    t0 = k * bar; ci = k % 4
    if ALT:
        # bass: syncopated 16ths, octave jump on the last hit
        for s in (0, 3, 6, 8, 11, 14):
            L = int(BEAT / 4 * SR * 2.4); f = ROOT[ci] * (2 if s == 14 else 1)
            place(bass, np.tanh(2.0 * saw(f, L, 8)) * env(L, 0.004, 0.13), t0 + s * BEAT / 4, 0.6)
        # chord stabs 3+3+2 (8th steps 0, 3, 6)
        for s in (0, 3, 6):
            L = int(BEAT * 0.7 * SR); y = np.zeros(L)
            for f in CH[ci]:
                y += saw(f, L, 10, -0.004) + saw(f, L, 10, 0.004)
            a = np.minimum(tt(L) / 0.006, 1) * np.exp(-tt(L) / 0.22)
            place(pad, y * a, t0 + s * BEAT / 2, 0.14)
        # arp: up-down 8ths over chord tones, two octaves up
        ar = [CH[ci][0], CH[ci][1], CH[ci][2], CH[ci][1] * 2, CH[ci][2], CH[ci][1], CH[ci][0] * 2, CH[ci][1]]
        for s in range(8):
            L = int(BEAT / 2 * SR * 1.5)
            place(arp, saw(ar[s] * 2, L, 6) * env(L, 0.002, 0.12), t0 + s * BEAT / 2, 0.15)
        continue
    # bass: offbeat 8ths, pluck-ish
    for s in range(8):
        if s % 2 == 0: continue
        L = int(BEAT / 2 * SR); f = ROOT[ci] * (2 if s in (3, 7) else 1)
        y = np.tanh(2.2 * saw(f, L, 8)) * env(L, 0.004, 0.16)
        place(bass, y, t0 + s * BEAT / 2, 0.55)
    # pad: detuned saws, whole bar
    L = int(bar * SR); y = np.zeros(L)
    for f in CH[ci]:
        y += saw(f, L, 10, -0.004) + saw(f, L, 10, 0.004)
    a = np.minimum(tt(L) / 0.04, 1) * np.minimum((bar - tt(L)) / 0.05, 1)
    place(pad, y * a, t0, 0.11)
    # arp: 16ths over chord tones +1 octave
    notes = [CH[ci][0] * 2, CH[ci][1] * 2, CH[ci][2] * 2, CH[ci][1] * 2]
    for s in range(16):
        L = int(BEAT / 4 * SR * 1.6); f = notes[s % 4] * (2 if s % 8 == 6 else 1)
        place(arp, saw(f, L, 6) * env(L, 0.002, 0.07), t0 + s * BEAT / 4, 0.16)

# ---------- arrangement: breaks on cards, full on answers ----------
def gain_env(level_in_card):
    g = np.ones(N)
    for a, b in cards:
        i, j = int(a * SR), int(b * SR)
        g[i:j] = level_in_card
        r = int(0.08 * SR)
        g[max(0, i - r):i] = np.linspace(1, level_in_card, len(g[max(0, i - r):i]))
    return g

drums *= gain_env(0.0)
bass *= gain_env(0.25)
# end: everything fades over the last 0.6 s of the body, 1.4 s tail of pad only
fade = np.ones(N); i = int((body_end - 0.35) * SR); fade[i:] = np.exp(-np.arange(N - i) / (0.25 * SR))
drums *= fade; bass *= fade; arp *= fade
pf = np.ones(N); pf[i:] = np.exp(-np.arange(N - i) / (0.9 * SR)); pad *= pf


def wav(path, x, stereo=None):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x if stereo is None else stereo], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

wav(f"{out}/drums.wav", drums * 0.8)
wav(f"{out}/bass.wav", bass * 0.8)
wav(f"{out}/pad.wav", pad * 0.8, np.roll(pad, int(0.011 * SR)) * 0.8)
wav(f"{out}/arp.wav", arp * 0.8, np.roll(arp, int(0.017 * SR)) * 0.8)
key = np.zeros(N)
for t0 in kick_times: place(key, np.ones(int(0.12 * SR)) * 0.9, t0)
key *= gain_env(0.0)
wav(f"{out}/key.wav", key)

# lowpass during cards on pad/arp, sidechain pump from kick, mix
lp = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in cards)
fc = (f"[2:a]lowpass=f=700:enable='{lp}',highpass=f=150[p];[3:a]lowpass=f=1100:enable='{lp}',highpass=f=300,aecho=0.8:0.5:{BEAT*750:.0f}:0.25[r];"
      f"[r]volume=8dB[r2];[p][r2]amix=inputs=2:normalize=0[syn];"
      f"[syn][4:a]sidechaincompress=threshold=0.1:ratio=4:attack=5:release=160[pump];"
      f"[0:a]volume=-5dB[dr];[1:a]volume=1dB[bs];[dr][bs][pump]amix=inputs=3:normalize=0,volume=-7dB,alimiter=limit=0.6:level=disabled:attack=2:release=80[o]")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{out}/drums.wav", "-i", f"{out}/bass.wav", "-i", f"{out}/pad.wav",
                "-i", f"{out}/arp.wav", "-i", f"{out}/key.wav", "-filter_complex", fc, "-map", "[o]", f"{out}/bed.wav"], check=True)

# ---------- SFX ----------
sfx = np.zeros(N + SR * 8)


def whoosh(L=0.45, up=True):
    n = int(L * SR); x = tt(n); noise = rng.standard_normal(n)
    sm = np.convolve(noise, np.ones(18) / 18, "same"); y = noise - sm * (0.2 if up else 0.8)
    e = np.sin(np.pi * np.clip(x / L, 0, 1)) ** 2
    return y * e * 0.22


def hit():
    n = int(0.9 * SR); x = tt(n); fr = 38 + 70 * np.exp(-x * 9)
    sub = np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(n, 0.002, 0.35)
    crack = rng.standard_normal(n) * env(n, 0.001, 0.05) * 0.35
    return np.tanh((sub + crack) * 1.3) * 0.6


def glitch():
    n = int(0.5 * SR); y = np.zeros(n)
    for k in range(7):
        s = int(rng.uniform(0, 0.42) * SR); L = int(rng.uniform(0.02, 0.06) * SR)
        f = rng.choice([220, 440, 880, 1760, 3520])
        y[s:s + L] += np.sign(np.sin(2 * np.pi * f * tt(L))) * 0.18
    return y + rng.standard_normal(n) * env(n, 0.001, 0.08) * 0.15


# Transition sounds (v2, after review "too obnoxious and repetitive"): one soft sound per card, a different
# variant each time, nothing on inserts, no hits on every answer. The music break itself carries the transition.
def swell(L=0.55):  # reverse-cymbal-like airy rise into the answer
    n = int(L * SR); x = tt(n); noise = rng.standard_normal(n)
    hp = noise - np.convolve(noise, np.ones(4) / 4, "same")
    return hp * (x / L) ** 2.2 * np.exp(-np.maximum(0, x - L * 0.92) * 80) * 0.10


def swish(L=0.22):  # short soft air swish
    n = int(L * SR); x = tt(n); noise = rng.standard_normal(n)
    bp = np.convolve(noise, np.ones(10) / 10, "same") - np.convolve(noise, np.ones(40) / 40, "same")
    return bp * np.sin(np.pi * x / L) ** 3 * 0.35


def pluck(f, L=0.5):  # muted tuned pluck, in key (A minor)
    n = int(L * SR); y = np.zeros(n)
    for k, g in ((1, 1), (2, 0.35), (3, 0.12)):
        y += g * np.sin(2 * np.pi * f * k * tt(n))
    return y * env(n, 0.003, 0.09) * 0.12


def thump():  # soft low pulse, no crack
    n = int(0.45 * SR); x = tt(n); fr = 60 + 40 * np.exp(-x * 14)
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * env(n, 0.004, 0.12) * 0.22


variants = [
    lambda a, b: place(sfx, swell(0.6), b - 0.6),
    lambda a, b: (place(sfx, pluck(440.0 * SHIFT), a), place(sfx, pluck(659.25 * SHIFT), a + BEAT / 2, 0.8)),
    lambda a, b: place(sfx, swish(0.24), a - 0.08),
    lambda a, b: place(sfx, thump(), b, 0.9),
]
if plan.get("hook_motion", "calm") == "punchy":  # calm hook (default) has no pulse and no swish
    place(sfx, thump(), 0.0, 1.0)                    # cold open: one soft pulse
    place(sfx, swish(0.26), segs[1][1] - 0.1, 0.8)   # cold open -> story
if plan.get("card_sfx", False):  # default off since review 2026-11-16 ("sound effect болиулах")
    for k, (a, b) in enumerate(cards):
        variants[k % len(variants)](a, b)
place(sfx, glitch() * 0.45, body_end - 0.05, 0.7)
sfx = sfx[:N + 7 * SR]
wav(f"{out}/sfx.wav", sfx)
print("bed", dur, "cards", cards)
