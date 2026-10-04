#!/usr/bin/env python3
"""Trailer sound design for the 34 s teaser: drones, heartbeat, ticking clock, braams,
staccato ostinato, impacts, riser, silences. C minor. Writes mix_raw.wav (48 kHz stereo).
Deterministic (fixed seed)."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
import wave

SR = 48000
DUR = 34.0
N = int(SR * DUR)
rng = np.random.default_rng(5)

def tv(d): return np.arange(int(d * SR)) / SR
def flt(x, kind, f, o=2): return sosfilt(butter(o, f, kind, fs=SR, output='sos'), x)
def mtof(m): return 440 * 2 ** ((m - 69) / 12)
out = np.zeros((N, 2))
def place(sig, t, g=1.0, pan=0.0, buf=None):
    buf = out if buf is None else buf
    i = int(t * SR)
    if i >= len(buf): return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * g

# stereo reverb from a decaying noise impulse response
def reverb(x, decay=2.2, wet=.35):
    n = int(decay * SR); t = tv(decay)
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-t * 6.9 / decay)[:, None]
    ir = flt(ir.T, 'low', 6000).T * .02
    if x.ndim == 1: x = np.stack([x, x], 1)
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[: len(x)] for c in range(2)], 1)
    return x * (1 - wet) + y * wet * 3

def saw(f, d, det=0):
    t = tv(d); ph = (t * f * 2 ** (det / 1200)) % 1; return 2 * ph - 1

def braam(d=3.0, root=36, big=1.0):
    t = tv(d); y = np.zeros(len(t))
    for m in (root - 12, root, root + 7, root + 12, root + 15):
        for det in (-14, 0, 13):
            y += saw(mtof(m), d, det) * (1.3 if m < root + 1 else .7)
    # filter opens then closes, like a brass swell
    out_ = np.zeros_like(y); blk = 1024
    for s in range(0, len(y), blk):
        tt = s / SR; fc = 180 + 1700 * np.exp(-((tt - .12) ** 2) / .08) * big + 300 * np.exp(-tt * 1.2)
        seg = y[max(0, s - 4096): s + blk]; z = flt(seg, 'low', min(fc, 8000), 2); out_[s:s + blk] = z[-len(out_[s:s + blk]):]
    env = np.minimum(1, t / .04) * np.exp(-t * (1.0 / big))
    sub = np.sin(2 * np.pi * np.cumsum(mtof(root - 12) * (1 + .5 * np.exp(-t * 6))) / SR) * np.exp(-t * .9)
    return np.tanh((out_ / 8) * env * 2.2) * .8 + sub * .7 * env

def impact(g=1.0):
    t = tv(1.2); f = 40 + 110 * np.exp(-t * 18)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.5)
    crack = flt(rng.standard_normal(len(t)), 'band', [300, 5000]) * np.exp(-t * 22) * .5
    return np.tanh((boom + crack) * 1.4) * g

def clang():
    t = tv(1.4); y = np.zeros(len(t))
    for r, a in ((1, 1), (2.76, .6), (5.4, .4), (8.93, .25)):
        y += a * np.sin(2 * np.pi * 330 * r * t) * np.exp(-t * (3 + r))
    return y * .35

def tick():
    t = tv(.04); return flt(rng.standard_normal(len(t)), 'band', [2500, 7000]) * np.exp(-t * 200)

def thump(f=52):
    t = tv(.35); return np.sin(2 * np.pi * np.cumsum(f * (1 + np.exp(-t * 30))) / SR) * np.exp(-t * 12)

def tom(f=90):
    t = tv(.5); body = np.sin(2 * np.pi * np.cumsum(f * (1 + .6 * np.exp(-t * 25))) / SR) * np.exp(-t * 7)
    return np.tanh(1.5 * (body + flt(rng.standard_normal(len(t)), 'band', [150, 1200]) * np.exp(-t * 30) * .4))

def stac(m, d=.12):
    y = sum(saw(mtof(m), d, det) for det in (-8, 8)); t = tv(d)
    return flt(y, 'low', 2200) * np.exp(-t * 18) * np.minimum(1, t / .004) * .5

def whoosh(d=.6, rev=False):
    t = tv(d); n = rng.standard_normal(len(t)); o = np.zeros_like(n); blk = 480
    for s in range(0, len(t), blk):
        k = s / len(t); fc = 400 * (12 ** k)
        seg = n[max(0, s - 1920): s + blk]; z = flt(seg, 'band', [fc * .6, min(fc * 1.6, 18000)]); o[s:s + blk] = z[-len(o[s:s + blk]):]
    e = (t / d) ** 2.5 if rev else np.sin(np.pi * t / d) ** 1.5
    return flt(o * e, 'high', 120)

# ---- 0–5: drone, heartbeat, clock ----
t = tv(5.0)
drone = (np.sin(2 * np.pi * 65.4 * t) + .5 * np.sin(2 * np.pi * 98 * t) + .3 * np.sin(2 * np.pi * 130.8 * t * 1.002))
drone += flt(rng.standard_normal(len(t)), 'band', [80, 400]) * .4
drone *= np.minimum(1, t / .05) * (0.5 + 0.5 * t / 5)
place(reverb(drone * .25, 2.0, .3), 0, .9)
for b in np.arange(0, 5.0, .75):
    place(thump(), b, .9); place(thump(48), b + .18, .55)
tt, gap = 1.5, .5
while tt < 4.98:
    place(tick(), tt, .35 + .25 * (tt - 1.5) / 3.5, .3)
    gap = .5 if tt < 3.4 else max(.11, .5 - (tt - 3.4) * .26); tt += gap
place(whoosh(.45, True), 4.55, .5)
out[int(5.0 * SR): int(5.3 * SR)] = 0                         # hard silence

# ---- 5.3 UNTIL NOW ----
place(reverb(braam(3.2, 36, 1.2), 3.0, .4), 5.3, .9)
place(impact(1.0), 5.3, .9)

# ---- 6.6–8.6 code ----
for i in range(32):
    place(tick(), 6.7 + i * (.95 / 32), .22, (i % 5 - 2) * .15)
t = tv(1.6); whomp = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 2.5) + 35) / SR) * np.exp(-t * 2.4)
place(whomp, 7.85, .9)
for i, m in enumerate((84, 87, 91, 96)):
    tb = tv(2.0); place(reverb(np.sin(2 * np.pi * mtof(m) * tb) * np.exp(-tb * 2.5) * .25, 2.5, .5), 7.85 + i * .05, .5, (i - 1.5) * .3)
for b in np.arange(6.6, 8.6, .5): place(thump(44), b, .4)

# ---- 8.6–14.5 the team: hit, then driving ostinato ----
place(impact(.8), 8.6, .8); place(reverb(braam(2.2, 43, .8), 2.0, .35), 8.6, .55)
SEQ = [36, 36, 39, 36, 43, 36, 39, 41]   # C minor staccato
for i, tt in enumerate(np.arange(9.1, 18.0, .125)):
    m = SEQ[i % 8] + (12 if (i // 16) % 2 and tt > 11.5 else 0)
    place(stac(m), tt, .45 if tt < 11.5 else .6, (-.4 if i % 2 else .4))
for tt in np.arange(9.1, 18.0, .5):
    place(tom(80), tt, .5 if tt < 11.5 else .75)
    if tt >= 11.5: place(tom(120), tt + .375, .45, .3)
for tt in np.arange(11.5, 14.5, .25): place(tick(), tt + .125, .18, -.3)
place(whoosh(.9), 11.1, .5)

# ---- 14.6–17.96 six hosted actions: a hit each ----
for i in range(6):
    tt = 14.6 + i * .56
    place(impact(.7), tt, .7); place(reverb(clang(), 1.8, .45), tt, .4, (i % 2 - .5) * .6)

# ---- 18–20.5 the record: pulse thins ----
for tt in np.arange(18.0, 20.5, .25): place(stac(36, .09), tt, .3, .2)
for tt in np.arange(18.0, 20.5, 1.0): place(tom(70), tt, .5)

# ---- 20.5–23 riser into silence ----
d = 2.5; t = tv(d); ris = np.zeros(len(t))
for k in range(5):
    f = 110 * 2 ** (k + t / d * 1.0)
    ris += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * (k + t / d) / 5) ** 2
ris = ris * (t / d) ** 1.5 * .35 + whoosh(d, True) * .5
place(reverb(ris, 1.5, .3), 20.5, .8)
for tt in np.arange(20.5, 22.9, .25): place(thump(46), tt, .3 + .4 * (tt - 20.5) / 2.4)
out[int(23.0 * SR): int(23.4 * SR)] = 0                        # breath before the title

# ---- 23.4 title ----
place(reverb(braam(4.0, 36, 1.6), 3.5, .45), 23.4, 1.0)
place(impact(1.0), 23.4, 1.0)
t = tv(3.0); subdrop = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 1.8) + 30) / SR) * np.exp(-t * 1.2)
place(subdrop, 23.4, .7)

# ---- 27.5–34 credits pad + end hit ----
t = tv(6.5); pad = np.zeros(len(t))
for m in (48, 51, 55, 62):
    for det in (-6, 6): pad += saw(mtof(m), 6.5, det)
pad = flt(pad, 'low', 900) * np.minimum(1, t / 1.0) * np.minimum(1, (6.5 - t) / 1.5) * .06
place(reverb(pad, 2.5, .4), 27.5, .8)
place(impact(.8), 30.5, .7); place(reverb(braam(3.0, 36, .7), 3.0, .5), 30.5, .45)

out[: int(.005 * SR)] *= np.linspace(0, 1, int(.005 * SR))[:, None]
out[-int(.6 * SR):] *= np.linspace(1, 0, int(.6 * SR))[:, None]
y = out / np.abs(out).max() * .89
with wave.open('mix_raw.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((y * 32767).astype('<i2').tobytes())
print('ok')
