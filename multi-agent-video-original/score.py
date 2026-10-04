#!/usr/bin/env python3
"""Original score + sound design for the 33.5 s cut. 120 BPM, C major, marimba-led.
Writes music.wav and sfx.wav (48 kHz stereo), deterministic (fixed seed)."""
import numpy as np
from scipy.signal import butter, sosfilt
import wave

SR = 48000
DUR = 33.5
N = int(SR * DUR)
rng = np.random.default_rng(21)

def tv(d): return np.arange(int(d * SR)) / SR
def flt(x, kind, f, o=2): return sosfilt(butter(o, f, kind, fs=SR, output='sos'), x)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def place(buf, sig, t, g=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0: return
    sig = sig[: len(buf) - i]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * g * l * 1.414
    buf[i:i + len(sig), 1] += sig * g * r * 1.414

def marimba(f, d=0.7):
    t = tv(d)
    idx = 2.2 * np.exp(-t * 35)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * 4.0 * f * t))
    y += 0.25 * np.sin(2 * np.pi * 10 * f * t) * np.exp(-t * 60)
    return y * np.exp(-t * 7) * np.minimum(1, t / 0.002)

def bell(f, d=1.6):
    t = tv(d)
    y = np.sin(2 * np.pi * f * t + 1.4 * np.exp(-t * 4) * np.sin(2 * np.pi * 3.5 * f * t))
    return y * np.exp(-t * 2.8) * np.minimum(1, t / 0.003)

def kick(g=1.0):
    t = tv(0.32); f = 48 + 90 * np.exp(-t * 30)
    return np.tanh(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 10) * 1.5) * g

def shaker():
    t = tv(0.07); return flt(rng.uniform(-1, 1, len(t)), 'high', 6000, 4) * np.exp(-t * 60) * np.minimum(1, t / 0.01)

def clap():
    t = tv(0.22); n = flt(rng.uniform(-1, 1, len(t)), 'band', [1000, 3500])
    env = np.exp(-t * 25)
    for k in (0.0, 0.012, 0.024): env = env + 0.5 * np.exp(-np.maximum(0, t - k) * 140) * (t >= k)
    return n * env * 0.5

def sub_pad(ms, d):
    t = tv(d); y = np.zeros(len(t))
    for m in ms:
        for det in (-0.06, 0.06):
            y += np.sin(2 * np.pi * mtof(m + det) * t) + 0.3 * np.sin(2 * np.pi * 2 * mtof(m + det) * t)
    env = np.minimum(1, t / 0.3) * np.minimum(1, (d - t) / 0.3)
    return y * env / (len(ms) * 2)

music = np.zeros((N, 2))
CH = [[60, 64, 67], [57, 60, 64], [53, 57, 60], [55, 59, 62]]   # C Am F G, one bar (2 s) each
BASS = [36, 33, 29, 31]
def ch(t): return int(t // 2) % 4

# slam hits on the three hook words
for t in (0.0, 0.5, 1.0):
    place(music, kick(1.0), t, 0.9); place(music, marimba(mtof(48), 1.0), t, 0.5)
place(music, clap(), 1.0, 0.6)

# pads under everything from 1.5 s, one bar each, ending on the C chord at 31 s
for bar in range(1, 16):
    t0 = bar * 2.0 - 0.5
    if t0 >= 31: break
    place(music, sub_pad(CH[ch(t0 + .5)], 2.3), t0, 0.22)
place(music, sub_pad([48, 60, 64, 67, 72], 2.5), 31.0, 0.3)

# marimba ostinato (16ths in pairs) from 1.5 s, sparser during the receipt scene
pat = [0, 2, 1, 2, 0, 2, 1, 3]
for i in range(int(1.5 / 0.25), int(31.0 / 0.25)):
    t = i * 0.25
    if 20.5 <= t < 24.0 and i % 2: continue
    c = CH[ch(t)]; notes = c + [c[0] + 12]
    m = notes[pat[i % 8]] + 12
    place(music, marimba(mtof(m), 0.5), t, 0.2 if i % 2 == 0 else 0.13, -0.3 if i % 2 else 0.3)

# bass on 8ths, kick on beats, clap on 2 and 4, shaker 16ths
for i in range(int(2.5 / 0.25), int(31.0 / 0.25)):
    t = i * 0.25
    b = mtof(BASS[ch(t)] + (12 if i % 4 == 2 else 0))
    tt = tv(0.2)
    s = np.tanh(2 * np.sin(2 * np.pi * b * tt)) * np.exp(-tt * 10) * np.minimum(1, tt / 0.004)
    if i % 2 == 0: place(music, flt(s, 'low', 500), t, 0.3)
    place(music, shaker(), t, 0.05 if i % 2 else 0.08, 0.4)
for b in range(int(2.5 / 0.5), int(31.0 / 0.5)):
    t = b * 0.5
    place(music, kick(), t, 0.75)
    if b % 2 == 1: place(music, clap(), t, 0.28, -0.1)
place(music, kick(), 31.0, 0.9)

# sidechain pump
duck = np.ones(N)
for b in range(int(2.5 / 0.5), int(31.0 / 0.5) + 1):
    i = int(b * 0.5 * SR); n = int(0.25 * SR); k = np.linspace(0, 1, n)
    duck[i:i + n] = np.minimum(duck[i:i + n], 0.6 + 0.4 * k ** 0.6)
music *= duck[:, None]
music[: int(0.005 * SR)] *= np.linspace(0, 1, int(0.005 * SR))[:, None]
music[-int(0.4 * SR):] *= np.linspace(1, 0, int(0.4 * SR))[:, None]

# ---------- sound design ----------
sfx = np.zeros((N, 2))
def whip(d=0.32):
    t = tv(d); n = rng.uniform(-1, 1, len(t)); out = np.zeros_like(n); blk = 480
    for s in range(0, len(t), blk):
        fc = 900 * (5.0 ** (s / len(t)))
        seg = n[max(0, s - 1920): s + blk]; y = flt(seg, 'band', [fc * .6, min(fc * 1.7, 16000)])
        out[s:s + blk] = y[-len(out[s:s + blk]):]
    return flt(out * np.sin(np.pi * t / d) ** 1.4, 'high', 250, 4)
def paper():
    t = tv(0.12); return flt(rng.uniform(-1, 1, len(t)), 'band', [1500, 6000]) * np.exp(-t * 35) * np.minimum(1, t / 0.004)
def thud():
    t = tv(0.25); f = 160 + 120 * np.exp(-t * 40)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18)
    slap = flt(rng.uniform(-1, 1, len(t)), 'band', [400, 2500]) * np.exp(-t * 70)
    return flt(body * .8 + slap * .6, 'high', 140, 2)
def click():
    t = tv(0.05); return flt(rng.uniform(-1, 1, len(t)), 'band', [1800, 5000]) * np.exp(-t * 160)

for t in (2.5, 5.5, 12.0, 15.5, 20.5, 24.0, 27.0, 30.0):
    place(sfx, whip(), t - 0.16, 0.5)
for i in range(8):                                    # sticky notes landing
    place(sfx, paper(), 2.75 + i * .27 + .27, 0.35, (i % 3 - 1) * .3)
place(sfx, click(), 6.55, 0.7); place(sfx, thud(), 6.6, 0.45)   # the switch
place(sfx, bell(mtof(84)), 6.7, 0.18)
for i, t in enumerate((9.05, 9.27, 9.49, 10.6)):     # subagents land
    place(sfx, marimba(mtof([79, 83, 86, 91][i]), .6), t, 0.3, [-.5, 0, .5, -.4][i])
place(sfx, bell(mtof(91), 1.2), 13.9, 0.14)           # parallel lanes done
for i in range(6):                                    # stamps
    place(sfx, thud(), 15.95 + i * .5 + .12, 0.6, (-.3 if i % 2 == 0 else .3))
for k in range(26):                                   # receipt printer feed steps
    place(sfx, click(), 20.75 + k * (2.25 / 26), 0.18, 0.1)
for i, m in enumerate((84, 88, 91, 96)):              # final answer
    place(sfx, bell(mtof(m)), 25.5 + i * .09, 0.13)
for i in range(4):                                    # end-card doodle pops
    place(sfx, marimba(mtof([84, 79, 83, 86][i]), .5), 30.9 + i * .12, 0.2)

def write(name, x, ref):
    y = np.clip(x / ref * 0.89, -1, 1)
    with wave.open(name, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype('<i2').tobytes())
pk = np.abs(music).max()
write('music.wav', music, pk); write('sfx.wav', sfx, pk)
print('ok', pk, np.abs(sfx).max() / pk)
