"""Sound design + score for 'THE SIP' (all synthesized, plus the original café ambience)."""
import numpy as np, subprocess, wave

SR = 48000
TOTAL = 40.0
N = int(TOTAL * SR)
rng = np.random.default_rng(12)
T = dict(A=0.0, B=2.5, C=5.0, D1=6.5, D2=10.5, D3=13.5, D4=17.0, D5=21.0, R1=25.0, R2=27.5, R3=33.5, END=37.2)


def buf(): return np.zeros((N, 2), np.float32)
def tt(d): return np.arange(int(d * SR)) / SR
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)
def add(b, x, t0, g=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N: return
    if x.ndim == 1: x = np.stack([x * (1 - pan) ** 0.5, x * (1 + pan) ** 0.5], 1) / 1.0
    x = x[:N - i]
    b[i:i + len(x)] += x * g
def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x, axis=0); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * (m[:, None] if x.ndim > 1 else m), len(x), axis=0)
def env_pts(n, pts):
    t = np.arange(n) / SR
    return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])


# ------------------------------------------------------------------ instruments
def piano(m, dur=4.0, vel=1.0):
    f0 = midi(m); t = tt(dur); s = np.zeros_like(t)
    for n in range(1, 10):
        fn = f0 * n * np.sqrt(1 + 0.0004 * n * n)
        if fn > 16000: break
        s += np.sin(2 * np.pi * fn * t + rng.uniform(0, 6)) * (1 / n ** 1.25) * np.exp(-t * (0.9 + 0.55 * n) * (f0 / 260) ** 0.3)
    s *= np.minimum(1, t / 0.004)
    ham = fft_filter(rng.normal(0, 1, len(t)), hi=3000) * np.exp(-t * 90) * 0.15
    return (s + ham) * vel * 0.25

def strings(m, dur, att=0.8, rel=1.0, bright=1.0):
    f0 = midi(m); t = tt(dur); s = np.zeros_like(t)
    for d in (-0.08, -0.03, 0.0, 0.04, 0.09):
        f = f0 * 2 ** (d / 12)
        vib = 1 + 0.003 * np.sin(2 * np.pi * (5.1 + d) * t + rng.uniform(0, 6))
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        for n in range(1, 11):
            if f * n > 9000: break
            s += np.sin(n * ph) * (1 / n) * np.exp(-n / (4.0 * bright))
    e = np.minimum(1, t / att) * np.minimum(1, (dur - t) / rel).clip(0, 1)
    return s * e * 0.05

def sub_boom(dur=3.0, f1=62, f2=28, g=1.0):
    t = tt(dur)
    f = f2 + (f1 - f2) * np.exp(-t * 2.2)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3)
    s = np.tanh(s * 2.2) * 0.6
    click = fft_filter(rng.normal(0, 1, len(t)), hi=1800) * np.exp(-t * 40) * 0.5
    brass = sum(np.sin(2 * np.pi * midi(m) * t * (1 + 0.002 * k)) for k, m in enumerate([33, 40, 45, 52])) * np.exp(-t * 1.6) * 0.12
    return (s + click + np.tanh(brass * 2) * 0.5) * g

def rev_swell(dur=1.4, g=1.0):
    t = tt(dur); x = rng.normal(0, 1, len(t))
    x = fft_filter(x, lo=3000)
    return x * (t / dur) ** 3 * 0.35 * g

def whoosh(dur=1.2, g=1.0, up=True):
    t = tt(dur); x = fft_filter(rng.normal(0, 1, len(t)), lo=200, hi=4000)
    e = np.sin(np.pi * (t / dur)) ** 2
    return x * e * 0.3 * g

def ice_clink(g=1.0):
    t = tt(1.6); s = np.zeros_like(t)
    for f, d, a in [(2380, 3.5, 1.0), (3655, 5, 0.7), (5120, 7, 0.5), (6980, 9, 0.35), (1610, 4, 0.3)]:
        s += a * np.sin(2 * np.pi * f * t) * np.exp(-t * d)
    s *= np.minimum(1, t / 0.0015)
    s2 = np.zeros_like(s); k = int(0.085 * SR)
    s2[k:] = s[:-k] * 0.45
    tick = fft_filter(rng.normal(0, 1, len(t)), lo=4000) * np.exp(-t * 400) * 0.6
    return (s + s2 + tick) * 0.22 * g

def heartbeat(g=1.0):
    t = tt(0.6); s = np.zeros_like(t)
    for off, a in ((0, 1.0), (0.17, 0.7)):
        tt_ = np.clip(t - off, 0, None)
        s += np.where(t >= off, np.sin(2 * np.pi * 52 * tt_) * np.exp(-tt_ * 22) * a, 0)
    return np.tanh(s * 1.5) * 0.5 * g

def applause(dur, density=220):
    n = int(dur * SR); x = np.zeros(n)
    k = int(density * dur)
    for p in rng.integers(0, n - 800, k):
        L = rng.integers(200, 700)
        x[p:p + L] += rng.normal(0, 1, L) * np.exp(-np.arange(L) / (L / 4)) * rng.uniform(0.3, 1)
    x = fft_filter(x, lo=700, hi=5000)
    return x / (np.abs(x).max() + 1e-9) * 0.35

def coins(dur, n=40):
    out = np.zeros(int(dur * SR))
    for _ in range(n):
        p = rng.uniform(0, dur - 0.3); f = rng.uniform(2800, 6000)
        t = tt(0.3); s = (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.47 * t)) * np.exp(-t * rng.uniform(15, 30))
        i = int(p * SR); out[i:i + len(s)] += s * rng.uniform(0.2, 0.6)
    return out * 0.12

def shutter():
    t = tt(0.12); s = np.zeros_like(t)
    for off in (0, 0.06):
        i = int(off * SR); L = 150
        s[i:i + L] += rng.normal(0, 1, L) * np.exp(-np.arange(L) / 30)
    return fft_filter(s, lo=1500) * 0.5

def wind(dur, g=1.0):
    n = int(dur * SR); x = fft_filter(rng.normal(0, 1, n), lo=120, hi=900)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.35 * np.arange(n) / SR + 1.3)
    return x * lfo * 0.25 * g

def crickets(dur):
    t = tt(dur); s = np.sin(2 * np.pi * 4600 * t) * (np.sin(2 * np.pi * 28 * t) > 0.3) * ((t * 1.3) % 1 < 0.35)
    return s * 0.02

def riser(dur):
    t = tt(dur); s = np.zeros_like(t)
    for k in range(6):  # shepard-ish rising partials
        f = 110 * 2 ** (k * 0.5 + 1.2 * t / dur)
        s += np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-((np.log2(f / 440)) ** 2) * 0.5)
    noise = fft_filter(rng.normal(0, 1, len(t)), lo=1500) * (t / dur) ** 2 * 0.3
    return (s * 0.08 + noise * 0.4) * (t / dur) ** 1.5


def reverb(x, secs=2.8, wet=0.35, pre=0.02):
    n = int(secs * SR)
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-np.linspace(0, 6.5, n))[:, None]
    ir[:int(pre * SR)] = 0
    ir = fft_filter(ir, hi=7000)
    L = len(x) + n; F = 1 << (L - 1).bit_length()
    y = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], F) * np.fft.rfft(ir[:, c], F), F)[:len(x)] for c in range(2)], 1)
    y *= np.sqrt((x ** 2).mean() / ((y ** 2).mean() + 1e-12))
    return x * (1 - wet) + y * wet


# ------------------------------------------------------------------ café ambience
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', 'source/cafe_original.mp4', '-ac', '2', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
orig = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
amb = buf()
a1 = orig[:int(6.5 * SR)]
e1 = env_pts(len(a1), [(0, 0), (0.4, 1), (4.8, 1), (6.2, 0.15), (6.5, 0)])[:, None]
# drifting away: progressively muffled (crossfade to a low-passed copy)
lp = fft_filter(a1, hi=500)
mix = env_pts(len(a1), [(0, 0), (4.6, 0), (6.2, 1), (6.5, 1)])[:, None]
add(amb, (a1 * (1 - mix) + lp * mix) * e1, 0, 0.9)
a2 = orig[int(13.7 * SR):]
n2 = min(len(a2), N - int(T['R1'] * SR))
a2 = a2[:n2]
add(amb, a2 * env_pts(len(a2), [(0, 0), (0.25, 0), (1.2, 0.75), (len(a2) / SR - 1.2, 0.6), (len(a2) / SR, 0)])[:, None], T['R1'])
# loop a little more ambience to reach the smile hold
a3 = orig[int(2 * SR):int(10 * SR)]
add(amb, a3 * env_pts(len(a3), [(0, 0), (1, 0.5), (len(a3) / SR - 2, 0.5), (len(a3) / SR, 0)])[:, None], T['R1'] + n2 / SR - 1.0)

# ------------------------------------------------------------------ score
mus = buf()
# opening piano motif (A minor, hopeful)
for t0, notes, v in [(0.9, [57, 64], 0.7), (2.1, [72], 0.6), (3.1, [71], 0.55), (4.1, [67, 64], 0.6), (5.1, [69, 76], 0.5)]:
    for m in notes: add(mus, piano(m, 5, v), t0, 1.0, pan=(m - 66) / 40)
add(mus, strings(45, 6.8, att=3, rel=0.8, bright=0.6), 0.2, 0.7)
# into the dream
add(mus, ice_clink(), 5.75, 1.3)
add(mus, rev_swell(1.2), 5.3, 1.0)
# dream chords, one per scene (low strings + high strings)
chords = {'D1': [45, 52, 57, 60, 64], 'D2': [41, 48, 53, 57, 64], 'D3': [36, 43, 48, 55, 64], 'D4': [43, 50, 55, 59, 62], 'D5': [41, 48, 53, 57, 60, 65]}
order = ['D1', 'D2', 'D3', 'D4', 'D5']
for k, key in enumerate(order):
    t0 = T[key]; t1 = T[order[k + 1]] if k + 1 < len(order) else T['R1']
    d = t1 - t0 + 0.6
    for j, m in enumerate(chords[key]):
        add(mus, strings(m, d, att=0.25, rel=0.4, bright=0.8 + 0.3 * j / 5), t0, 1.0 + 0.3 * k / 4, pan=(j - 2) * 0.2)
    add(mus, sub_boom(3.0, g=1.0), t0, 1.0)
    if k > 0: add(mus, rev_swell(1.0), t0 - 1.0, 0.9)
    # heartbeat pulse, speeding up across the dream
    bpm = 84 + k * 10
    tb = t0 + 0.6
    while tb < t1 - 0.2:
        add(mus, heartbeat(), tb, 0.8 + 0.1 * k)
        tb += 60 / bpm
# scene foley
add(mus, wind(4.0, 1.0), T['D1'], 0.8)
add(mus, whoosh(1.6), T['D1'] + 0.4, 1.2)
add(mus, coins(3.0, 55), T['D2'], 1.0, pan=0.1)
ap = applause(3.8); add(mus, ap * env_pts(len(ap), [(0, 0), (0.6, 1), (3.0, 1), (3.8, 0)]), T['D3'], 0.9)
for fr in (9, 23, 31, 47, 58, 66, 77):
    add(mus, shutter(), T['D3'] + fr / 24, 0.7, pan=float(rng.uniform(-0.6, 0.6)))
add(mus, crickets(4.0), T['D4'], 1.0, pan=-0.3)
for t0, m in [(T['D4'] + 0.5, 76), (T['D4'] + 1.3, 74), (T['D4'] + 2.1, 72), (T['D4'] + 2.9, 71)]:
    add(mus, piano(m, 4, 0.5), t0, 1.0, pan=0.2)
add(mus, wind(4.0, 1.0), T['D5'], 0.7)
add(mus, riser(3.9), T['D5'] + 0.1, 1.4)
# SNAP back: silence, ice clink, café
add(mus, ice_clink(1.2), T['R1'] + 0.08, 1.5)
# return piano theme (C major, warm) under the smile
theme = [(0.6, [60, 64, 67], 0.5), (1.8, [72], 0.55), (2.9, [71], 0.5), (3.7, [67], 0.5), (4.6, [69, 64], 0.55),
         (6.2, [65, 69, 72], 0.5), (7.6, [76], 0.55), (8.6, [74], 0.5), (9.8, [72, 67, 64], 0.55)]
for t0, notes, v in theme:
    for m in notes: add(mus, piano(m, 6, v), T['R1'] + t0, 1.0, pan=(m - 66) / 40)
add(mus, strings(48, 12.5, att=4, rel=3, bright=0.7), T['R2'] - 0.5, 0.8)
add(mus, strings(55, 12.0, att=4, rel=3, bright=0.7), T['R2'], 0.6)
add(mus, strings(64, 11.0, att=5, rel=3, bright=0.9), T['R2'] + 1.0, 0.5)
# end card
add(mus, sub_boom(3.5, 48, 26, 0.7), T['END'] + 0.05, 1.0)
for m in (48, 55, 64, 67, 72):
    add(mus, piano(m, 5, 0.55), T['END'] + 0.3, 1.0, pan=(m - 60) / 40)
add(mus, ice_clink(0.8), T['END'] + 1.9, 0.8)

mus = reverb(mus, 2.6, 0.32)
# hard duck at the snap back to reality (silence before the clink)
mus *= env_pts(N, [(0, 1), (T['R1'] - 0.05, 1), (T['R1'], 0.0), (T['R1'] + 0.05, 1), (TOTAL - 0.8, 1), (TOTAL, 0)])[:, None]
mix = amb + mus
mix = np.tanh(mix * 1.4) / 1.4
mix = mix / np.abs(mix).max() * 0.93
pcm = (mix * 32767).astype('<i2')
w = wave.open('trailer.wav', 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close()
print('ok')
