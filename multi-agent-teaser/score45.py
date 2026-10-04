#!/usr/bin/env python3
"""Trailer sound design for the 45 s narrated teaser: drones, heartbeat, ticking clock, braams,
staccato ostinato, impacts, riser, silences. C minor. Writes mix_raw.wav (48 kHz stereo).
Deterministic (fixed seed)."""
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
import wave

SR = 48000
DUR = 45.0
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

# ---- 0–5.6: drone, heartbeat, clock ----
t = tv(5.6)
drone = (np.sin(2 * np.pi * 65.4 * t) + .5 * np.sin(2 * np.pi * 98 * t) + .3 * np.sin(2 * np.pi * 130.8 * t * 1.002))
drone += flt(rng.standard_normal(len(t)), 'band', [80, 400]) * .4
drone *= np.minimum(1, t / .05) * (0.5 + 0.5 * t / 5.6)
place(reverb(drone * .25, 2.0, .3), 0, .9)
for b in np.arange(0, 5.6, .84):
    place(thump(), b, .9); place(thump(48), b + .2, .55)
tt, gap = 1.7, .56
while tt < 5.55:
    place(tick(), tt, .3 + .25 * (tt - 1.7) / 3.9, .3)
    gap = .56 if tt < 3.6 else max(.11, .56 - (tt - 3.6) * .25); tt += gap
place(whoosh(.45, True), 5.15, .5)
out[int(5.6 * SR): int(5.9 * SR)] = 0                          # hard silence

# ---- 5.9 UNTIL NOW ----
place(reverb(braam(3.2, 36, 1.2), 3.0, .4), 5.9, .9)
place(impact(1.0), 5.9, .9)

# ---- 7.4–12.8 code ----
for i in range(32):
    place(tick(), 7.8 + i * (3.0 / 32), .2, (i % 5 - 2) * .15)
for b in np.arange(7.4, 12.8, .5): place(thump(44), b, .35)
t = tv(1.6); whomp = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 2.5) + 35) / SR) * np.exp(-t * 2.4)
place(whomp, 11.85, .9)
for i, m in enumerate((84, 87, 91, 96)):
    tb = tv(2.0); place(reverb(np.sin(2 * np.pi * mtof(m) * tb) * np.exp(-tb * 2.5) * .25, 2.5, .5), 11.85 + i * .05, .5, (i - 1.5) * .3)

# ---- 12.8–21: the team, then parallel lanes: driving ostinato ----
place(impact(.8), 12.8, .8); place(reverb(braam(2.2, 43, .8), 2.0, .35), 12.8, .55)
SEQ = [36, 36, 39, 36, 43, 36, 39, 41]
for i, tt in enumerate(np.arange(13.3, 23.4, .125)):
    m = SEQ[i % 8] + (12 if (i // 16) % 2 and tt > 17.3 else 0)
    place(stac(m), tt, .4 if tt < 17.3 else .55, (-.4 if i % 2 else .4))
for tt in np.arange(13.3, 23.4, .5):
    place(tom(80), tt, .45 if tt < 17.3 else .7)
    if 17.3 <= tt < 21.0: place(tom(120), tt + .375, .4, .3)
for tt in np.arange(17.3, 21.0, .25): place(tick(), tt + .125, .16, -.3)
place(whoosh(.9), 16.9, .5)

# ---- 23.42–27.6 six hosted actions, on the spoken words ----
for i, tt in enumerate((23.42, 24.12, 24.77, 25.64, 26.29, 26.8)):
    place(impact(.7), tt, .65); place(reverb(clang(), 1.8, .45), tt, .35, (i % 2 - .5) * .6)

# ---- 27.6–31.4 the record ----
for tt in np.arange(27.6, 31.4, .25): place(stac(36, .09), tt, .28, .2)
for tt in np.arange(27.6, 31.4, 1.0): place(tom(70), tt, .45)

# ---- 31.4–34.6 riser into silence ----
d = 3.2; t = tv(d); ris = np.zeros(len(t))
for k in range(5):
    f = 110 * 2 ** (k + t / d * 1.0)
    ris += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * (k + t / d) / 5) ** 2
ris = ris * (t / d) ** 1.5 * .35 + whoosh(d, True) * .5
place(reverb(ris, 1.5, .3), 31.4, .8)
for tt in np.arange(31.4, 34.5, .25): place(thump(46), tt, .3 + .4 * (tt - 31.4) / 3.1)
out[int(34.6 * SR): int(35.0 * SR)] = 0

# ---- 35.0 title ----
place(reverb(braam(4.0, 36, 1.6), 3.5, .45), 35.0, 1.0)
place(impact(1.0), 35.0, 1.0)
t = tv(3.0); subdrop = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 1.8) + 30) / SR) * np.exp(-t * 1.2)
place(subdrop, 35.0, .7)

# ---- 38.6–45 credits pad + end hit ----
t = tv(6.4); pad = np.zeros(len(t))
for m in (48, 51, 55, 62):
    for det in (-6, 6): pad += saw(mtof(m), 6.4, det)
pad = flt(pad, 'low', 900) * np.minimum(1, t / 1.0) * np.minimum(1, (6.4 - t) / 1.2) * .06
place(reverb(pad, 2.5, .4), 38.6, .8)
place(impact(.8), 41.6, .7); place(reverb(braam(3.0, 36, .7), 3.0, .5), 41.6, .45)

# ---- narration: duck the music under the voice, then mix the voice on top ----
import soundfile as sf
vo, vsr = sf.read('vo_track.wav'); vo = vo[:N]
venv = np.abs(vo[:, 0]); k = int(.12 * SR)
venv = np.convolve(venv, np.ones(k) / k, 'same'); venv = np.minimum(1, venv / (venv.max() * .25))
att = np.convolve(venv, np.ones(int(.25 * SR)) / int(.25 * SR), 'same')
out *= (1 - .5 * np.clip(att, 0, 1))[:, None]          # about -6 dB under speech
# the two lines spoken over braams get an extra dip (about -10 dB) so the words cut through
for a0, a1 in ((6.0, 6.95), (35.65, 37.8)):
    g = np.ones(N); i0, i1 = int(a0 * SR), int(a1 * SR); r = int(.08 * SR)
    g[i0:i1] = .32; g[i0 - r:i0] = np.linspace(1, .32, r); g[i1:i1 + r] = np.linspace(.32, 1, r)
    out *= g[:, None]
out = out / np.abs(out).max() * .55
out[: len(vo)] += vo * .62

out[: int(.005 * SR)] *= np.linspace(0, 1, int(.005 * SR))[:, None]
out[-int(.15 * SR):] *= np.linspace(1, 0, int(.15 * SR))[:, None]
y = out / np.abs(out).max() * .89
with wave.open('mix_raw.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((y * 32767).astype('<i2').tobytes())
print('ok')
