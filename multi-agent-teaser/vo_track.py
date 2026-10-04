"""Place narration lines on the 45 s timeline, write vo_track.wav (48 kHz stereo) and vo.js (caption chunks)."""
import json, re, numpy as np, soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt
V = '../vo/'
SR, DUR = 48000, 45.0
PLACE = {"L1": 0.4, "L2": 6.05, "L3": 7.6, "L4": 12.9, "L5": 17.45, "L6": 21.1, "L7": 27.75, "L8": 31.5, "L9": 35.7, "L10": 38.9, "L11": 41.75}
meta = json.load(open(V + 'vo_dur.json'))
track = np.zeros(int(SR * DUR)); out = []
for lid, t0 in PLACE.items():
    s, sr = sf.read(V + f'{lid}.wav')
    s = resample_poly(s, SR, sr)
    s = sosfilt(butter(2, 90, 'high', fs=SR, output='sos'), s)
    i = int(t0 * SR); track[i:i + len(s)] += s[: len(track) - i]
    d = len(s) / SR; text = meta[lid]["text"]
    # caption chunks: split at sentence / ellipsis boundaries, time by character share
    parts = [p.strip() for p in re.split(r'(?<=[.?!])\s+|(?<=\.\.\.)\s*', text) if p.strip()]
    if lid == "L6": parts = [parts[0], " ".join(parts[1:])]
    tot = sum(len(p) for p in parts); a = t0; chunks = []
    for p in parts:
        b = a + d * len(p) / tot; chunks.append({"a": round(a, 2), "b": round(b, 2), "text": p.replace('...', '…')}); a = b
    if lid == "L6":   # measured: the action words start 2.3 s into the line
        chunks[0]["b"] = round(t0 + 2.25, 2); chunks[1]["a"] = round(t0 + 2.25, 2)
    if lid == "L1":   # measured phrase onsets 0, 2.0, 3.2 s
        chunks[0]["b"] = chunks[1]["a"] = round(t0 + 1.95, 2); chunks[1]["b"] = chunks[2]["a"] = round(t0 + 3.15, 2)
    if lid == "L3":
        chunks[0]["b"] = chunks[1]["a"] = round(t0 + 3.95, 2)
    out.append({"id": lid, "start": t0, "end": round(t0 + d, 2), "chunks": chunks})
    assert t0 + d < DUR, lid
peak = np.abs(track).max(); track = track / peak * .9
sf.write('vo_track.wav', np.stack([track, track], 1), SR)
open('vo.js', 'w').write('window.VO = ' + json.dumps(out) + ';\n')
json.dump(out, open('vo_placed.json', 'w'), indent=1)
for o in out: print(o['id'], o['start'], o['end'], [c['text'] for c in o['chunks']])
