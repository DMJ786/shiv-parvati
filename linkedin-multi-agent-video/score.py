#!/usr/bin/env python3
"""Procedural 120 BPM score + sound design cut to the film's timeline (36 s).
Writes music.wav (music only) and sfx.wav (effects only), 48 kHz stereo.
Deterministic: fixed RNG seed."""
import numpy as np
from scipy.signal import butter, sosfilt
import wave

SR = 48000
DUR = 34.5
# old (36 s storyboard) -> new (34.5 s cut) time map, same as the page's WARP
WO = [(0, 0), (3.3, 3.3), (5.4, 4.9), (30.3, 29.8), (32.1, 30.8), (36, 34.5)]
def W(t):
    for (o0, n0), (o1, n1) in zip(WO, WO[1:]):
        if t <= o1: return n0 + (t - o0) / (o1 - o0) * (n1 - n0)
    return 34.5
N = int(SR * DUR)
BEAT = 0.5          # 120 BPM
rng = np.random.default_rng(7)

def tvec(d): return np.arange(int(d * SR)) / SR
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf): return
    sig = sig[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l * 1.414
    buf[i:i + len(sig), 1] += sig * gain * r * 1.414

def pluck(freq, d=0.6, bright=0.5):
    """Karplus-Strong pluck."""
    n = int(SR * d); p = max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, p); buf = lp(buf, 2000 + 6000 * bright, 1)
    out = np.zeros(n); idx = 0
    for i in range(n):
        out[i] = buf[idx]
        nxt = (idx + 1) % p
        buf[idx] = 0.996 * 0.5 * (buf[idx] + buf[nxt])
        idx = nxt
    env = np.minimum(1, tvec(d) / 0.003)
    return out * env

def saw(freq, d):
    t = tvec(d); ph = (t * freq) % 1.0
    return 2 * ph - 1

def kick():
    t = tvec(0.35)
    f = 45 + 85 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 9)
    click = hp(rng.uniform(-1, 1, len(t)), 2000) * np.exp(-t * 300) * 0.15
    return np.tanh((s + click) * 1.6)

def hat(open_=False):
    d = 0.18 if open_ else 0.045
    t = tvec(d)
    return hp(rng.uniform(-1, 1, len(t)), 7000, 4) * np.exp(-t * (18 if open_ else 90))

def clap():
    t = tvec(0.25)
    n = bp(rng.uniform(-1, 1, len(t)), 900, 3200)
    env = np.exp(-t * 22)
    for k in (0.0, 0.011, 0.022):  # flam
        env += 0.5 * np.exp(-np.maximum(0, t - k) * 120) * (t >= k)
    return n * env * 0.6

# ---------- harmony: Am | F | C | G  (one chord per bar = 2 s) ----------
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]
def chord_at(t): return int(t // 2.0) % 4

music = np.zeros((N, 2))

# pad (detuned saws, low-passed), every bar; filter opens with the film
for bar in range(16):
    t0 = bar * 2.0
    c = CHORDS[bar % 4]
    d = 2.3
    sig = np.zeros(int(d * SR))
    for m in c + [c[0] + 12]:
        for det in (-0.09, 0.0, 0.08):
            sig += saw(mtof(m + det), d)
    cut = 700 if t0 < 5.5 else (1400 if t0 < 21.5 else (900 if t0 < 25.0 else 1800))
    sig = lp(sig, cut, 2) / 12
    tt = tvec(d)
    env = np.minimum(1, tt / 0.25) * np.minimum(1, (d - tt) / 0.3)
    place(music, sig * env, t0, 0.55, 0)

# final ring-out chord (A minor add9) from 32.5 s
d = 3.5; sig = np.zeros(int(d * SR))
for m in (57, 60, 64, 71, 69 + 12):
    for det in (-0.07, 0.07):
        sig += saw(mtof(m + det), d)
tt = tvec(d)
place(music, lp(sig, 1500) / 12 * np.minimum(1, tt / 0.02) * np.exp(-tt * 0.9), 31.0, 0.75)

# arp: 8th-note plucks through the chord, enters at 0 (hook), sparser in the build
pat = [0, 1, 2, 3, 2, 1, 2, 3]
for i in range(int(31.0 / 0.25)):
    t = i * 0.25
    if 23.5 <= t < 25.0 and i % 2: continue
    c = CHORDS[chord_at(t)]
    notes = c + [c[0] + 12]
    m = notes[pat[i % 8]] + 12
    place(music, pluck(mtof(m), 0.5, 0.35), t, 0.16 if t < 3 else 0.2, -0.35 if i % 2 else 0.35)

# bass: 8th-note pulse from 6.0 s, off in the 0.5 s dead stop before 25.5
for i in range(int(5.5 / 0.25), int(31.0 / 0.25)):
    t = i * 0.25
    if 24.5 <= t < 25.0: continue
    f = mtof(ROOTS[chord_at(t)] - 12 + (12 if i % 2 else 0))
    tt = tvec(0.22)
    s = np.tanh(2.2 * np.sin(2 * np.pi * f * tt)) * np.exp(-tt * 9) * np.minimum(1, tt / 0.004)
    place(music, lp(s, 600), t, 0.32)

# drums
place(music, kick(), 0.0, 0.6)    # downbeat on frame 0
for b in range(int(31.0 / BEAT)):
    t = b * BEAT
    if 24.5 <= t < 25.0: continue
    if t >= 3.0 and (t < 21.5 or t >= 25.0 or b % 2 == 0):
        if t >= 5.5 or b % 2 == 0:
            place(music, kick(), t, 0.85)
    if t >= 9.0:
        place(music, hat(), t + 0.25, 0.12, 0.3)
        if b % 2 == 1 and not (21.5 <= t < 25.0):
            place(music, clap(), t, 0.32, -0.1)
    if t >= 5.5 and b % 4 == 3:
        place(music, hat(True), t + 0.25, 0.06, -0.3)
place(music, kick(), 31.0, 1.0)   # button on the end card

# sidechain pump on everything but kicks: duck 0.25 s after each kick
duck = np.ones(N)
for b in range(int(31.0 / BEAT)):
    t = b * BEAT
    if t >= 5.5 and not (24.5 <= t < 25.0):
        i = int(t * SR); n = int(0.28 * SR)
        k = np.linspace(0, 1, n)
        duck[i:i + n] = np.minimum(duck[i:i + n], 0.55 + 0.45 * k ** 0.6)
music *= duck[:, None]
# 5 ms fade-in, 300 ms tail fade
music[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
music[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))[:, None]

# ---------- sound design ----------
sfx = np.zeros((N, 2))

def whoosh(d=0.45, f0=600, f1=3200):
    t = tvec(d)
    noise = rng.uniform(-1, 1, len(t))
    # sweep a band-pass by blocks
    out = np.zeros_like(noise); blk = 512
    for s in range(0, len(t), blk):
        k = s / len(t); fc = f0 * (f1 / f0) ** k
        seg = noise[max(0, s - 2048): s + blk]
        y = bp(seg, fc * 0.6, min(fc * 1.6, 15000))
        out[s:s + blk] = y[-len(out[s:s + blk]):]
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.6
    return hp(out * env, 220, 4)

def ping(m, d=0.5): return hp(pluck(mtof(m), d, 0.7), 300)

for t, g in [(2.5, .55), (5.5, .45), (8.95, .5), (16.95, .3), (21.7, .4), (25.25, .4), (27.25, .45), (32.15, .55)]:
    place(sfx, whoosh(), W(t), g, 0)
for k in range(6):                       # sequential task ticks
    place(sfx, ping(84, .25), W(3.3 + 0.36 * (k + 1)), 0.16, 0.2)
place(sfx, ping(88, .8), W(7.88), 0.3)
for i, m in enumerate((76, 79, 83, 88)):   # hook tree spawning
    place(sfx, ping(m, .4), 0.25 + 0.1 * i, 0.16, (i - 1.5) / 3)
for i, m in enumerate((88, 91, 95)):        # final answer arrives
    place(sfx, ping(m, .9), W(27.6) + 0.12 * i, 0.2)     # flag highlighted
for t, m in [(9.45, 81), (10.05, 76), (10.18, 79), (10.31, 83), (11.2, 88)]:   # node pops
    place(sfx, ping(m, .5), W(t), 0.26, (m - 80) / 10)
for t in (15.0, 15.9, 16.3, 16.5):       # done
    place(sfx, ping(88, .4), W(t), 0.2)
for i in range(6):                       # hosted action switches
    place(sfx, ping(76 + [0, 2, 4, 7, 9, 12][i], .35), W(17.25 + 0.78 * i), 0.18)
for i in range(4):                       # log rows
    place(sfx, ping(81 + 2 * i, .3), W(22.1 + 0.32 * i), 0.16)
for i in range(3):
    place(sfx, ping(79, .3), W(29.15 + 0.22 * i), 0.14)
place(sfx, ping(93, .9), W(33.6), 0.24)     # CTA pill

def write(name, x):
    x = x / max(1e-9, np.abs(x).max()) * 0.89
    with wave.open(name, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
# keep relative level: normalise both by the music peak
peak = np.abs(music).max()
write('music.wav', music)
with wave.open('sfx.wav', 'wb') as w:
    y = sfx / peak * 0.89
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())
print('ok', peak, np.abs(sfx).max())
