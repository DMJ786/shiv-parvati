"""Edit for episode 2 (native 9:16): beat-snapped story cut, bell hard cut into Shiva's eyes opening, camera moves,
grade + grain, ducked ambience under the score, end card, -14 LUFS master."""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from film import edit, reel
from film.sati import REUSE, SECTIONS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sati"
FPS, W, H, SR = 24, 1080, 1920, 48000
FIRST_CLIPS = ROOT / "clips"
MIN_SHOT, MAX_SHOT, PAIR_MAX = 1.3, 3.4, 1.9
CARD_MIN = 3.0
DISSOLVE_AFTER = {"r12a"}          # the only dissolve: grief -> rebirth (the rest are hard cuts, like the reference)

# Camera per shot: push = zoom gained over the shot, punch = impact zoom on the cut, start_zoom for re-used halves.
CAM = {
    "s1": {"push": 0.08, "punch": 0.10}, "s2": {"push": 0.06}, "s3": {"push": 0.06, "punch": 0.14, "shake": 6},
    "r10": {"push": 0.08, "punch": 0.10}, "s3b": {"push": 0.04, "punch": 0.12, "start_zoom": 1.35, "shake": 8},
    "s4": {"push": 0.08}, "r12a": {"push": 0.05}, "r01": {"push": 0.08}, "s5": {"push": 0.06, "punch": 0.10},
    "r04": {"push": 0.07, "punch": 0.08}, "r06": {"push": 0.06, "punch": 0.08}, "s6": {"push": 0.06},
    "r14": {"push": 0.06}, "r12": {"push": 0.04, "start_zoom": 1.3},
    "r13": {"push": 0.08, "punch": 0.22, "flash": True, "shake": 14}, "s7": {"push": -0.08},
}


def source(sid):
    """(clip path, is_vertical, subject x for 9:16 crop, use='head'|'tail')."""
    base = sid.rstrip("ab") if sid in ("s3b", "r12a") else sid
    use = "tail" if sid in ("s3b", "r12") else "head"
    if base.startswith("s"):
        return OUT / "clips" / f"{base}.mp4", True, 0.5, use
    stem, x = REUSE[base]
    return FIRST_CLIPS / f"{stem}.mp4", False, x, use


def analyse(music):
    import librosa
    y, sr = librosa.load(str(music), sr=22050, mono=True)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    total = sum(s[1] for s in SECTIONS)
    marks = np.cumsum([0] + [s[1] for s in SECTIONS]) * (len(y) / sr) / total
    hop = int(0.05 * sr)
    db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop)[0] + 1e-9)
    times = librosa.times_like(db, sr=sr, hop_length=hop)
    loud = np.median(db[(times >= marks[3]) & (times < marks[4])])
    win = (times >= marks[4]) & (times <= marks[5] + 2.0)
    quiet = times[win][np.argmin(db[win])]
    silent = db[win].min() < loud - 20
    hit = float(marks[5])
    if silent:
        after = (times > quiet) & (db > loud - 8)
        if after.any():
            hit = float(times[after][0])
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)
    near = [o for o in onsets if abs(o - hit) <= 0.5]
    if near:
        hit = float(min(near, key=lambda o: abs(o - hit)))
    return {"beats": [float(b) for b in beats], "marks": marks.tolist(), "bell": hit, "silent": bool(silent),
            "length": len(y) / sr}


def plan(info):
    """Dynamic programming over beats: every cut on a beat (the cut into r13 on the bell), shots 1.3-3.4 s."""
    order, section_of = [], {}
    for k, (_, _, _, shots) in enumerate(SECTIONS):
        for s in shots:
            if s != "end":
                order.append(s)
                section_of[s] = k
    marks, bell = info["marks"], info["bell"]
    card_ideal = min(info["length"] - CARD_MIN - 0.5, bell + 6.8)
    ideal = []
    for s in order:
        k = section_of[s]
        group = [x for x in order if section_of[x] == k]
        a, b = marks[k], marks[k + 1]
        if k == 4:
            a, b = bell - 3.6, bell
        if k == 5:
            a, b = bell, card_ideal
        ideal.append(a + (b - a) * group.index(s) / len(group))
    ideal.append(card_ideal)
    # Cut candidates: beats plus the half-beats between them (eighth notes), on the frame grid.
    bb = info["beats"]
    halves = [(x + y) / 2 for x, y in zip(bb, bb[1:])]
    beats = sorted({round(b * FPS) / FPS for b in bb + halves})
    bell_t = round(bell * FPS) / FPS

    def max_len(s):
        return PAIR_MAX if s in ("s3", "s3b", "r12a", "r12") else MAX_SHOT

    n = len(order)
    cands = [[0.0]] + [[bell_t] if order[k] == "r13" else beats for k in range(1, n)] + \
            [sorted({b for b in beats if b <= info["length"] - CARD_MIN} |
                    {round(x * FPS) / FPS for x in np.arange(bell + 3.0, info["length"] - CARD_MIN, 0.25)})]
    best = [{0.0: (0.0, None)}]
    for k in range(1, n + 1):
        cur = {}
        for t in cands[k]:
            for tp, (cost, _) in best[k - 1].items():
                if MIN_SHOT - 1e-6 <= t - tp <= max_len(order[k - 1]) + 1e-6:
                    c = cost + (t - ideal[k]) ** 2
                    if t not in cur or c < cur[t][0]:
                        cur[t] = (c, tp)
        if not cur:
            raise SystemExit(f"No beat-aligned plan fits at cut {k} ({order[k - 1]}).")
        best.append(cur)
    t = min(best[n], key=lambda x: best[n][x][0])
    cuts = [t]
    for k in range(n, 0, -1):
        t = best[k][t][1]
        cuts.append(t)
    cuts = cuts[::-1]
    return [{"id": order[k], "start": cuts[k], "end": cuts[k + 1]} for k in range(n)]


def grief_drop(music, span, dst):
    """Muffled 'underwater' drop over the grief section: low-pass + dip, eased in and out."""
    import librosa
    import soundfile as sf
    from scipy.signal import butter, sosfiltfilt
    y, _ = librosa.load(str(music), sr=SR, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    lp = sosfiltfilt(butter(4, 650, "lowpass", fs=SR, output="sos"), y, axis=1) * 10 ** (-5 / 20)
    t = np.arange(y.shape[1]) / SR
    a, b = span
    env = np.clip(np.minimum((t - a) / 0.35, (b - t) / 0.6), 0, 1)
    env = env * env * (3 - 2 * env)
    sf.write(dst, (y * (1 - env) + lp * env).T, SR, subtype="PCM_24")
    return dst


def read_frames(clip, vertical, x, a_frame, n):
    """Frames [a_frame, a_frame + n) of a clip as 1080x1920 BGR (16:9 clips are cropped around the subject)."""
    if vertical:
        vf = f"fps={FPS},scale={W}:{H}:flags=lanczos"
    else:
        cw = 608
        vf = (f"fps={FPS},scale=1920:1080,crop={cw}:1080:'max(0,min(iw-{cw},{x:.3f}*iw-{cw}/2))':0,"
              f"scale={W}:{H}:flags=lanczos,unsharp=5:5:0.6")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"{vf},trim=start_frame={a_frame}:"
                          f"end_frame={a_frame + n}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    frames = []
    while len(frames) < n:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        frames.append(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
    p.stdout.close()
    p.wait()
    while len(frames) < n:                     # hold the last frame if a clip runs a frame short
        frames.append(frames[-1])
    return frames


def render(music, out):
    build = OUT / "build"
    build.mkdir(parents=True, exist_ok=True)
    info = analyse(music)
    cuts = plan(info)
    (build / "timeline.json").write_text(json.dumps({"bell": info["bell"], "cuts": cuts}, indent=1))
    for c in cuts:
        print(f"  {c['id']:5s} {c['start']:6.2f} -> {c['end']:6.2f} ({c['end'] - c['start']:.2f}s)")
    total = round(info["length"] * FPS)
    K = [round(c["start"] * FPS) for c in cuts] + [round(cuts[-1]["end"] * FPS)]
    rng = np.random.default_rng(11)
    beats = info["beats"]
    fury, union = (info["marks"][1], info["marks"][2]), (info["bell"] + 0.3, cuts[-1]["end"])

    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-vf", f"{edit.GRADE},{edit.GRAIN},format=yuv420p",
                            "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-tune", "grain",
                            str(build / "video.mp4")], stdin=subprocess.PIPE)
    amb = np.zeros((int((total / FPS + 1) * SR), 2), np.float32)
    prev_tail = None
    for k, c in enumerate(cuts):
        sid, cam = c["id"], CAM.get(c["id"], {})
        clip, vertical, x, use = source(sid)
        n = K[k + 1] - K[k]
        dis_out = sid in DISSOLVE_AFTER
        extra = edit.POST if dis_out else 0
        avail = int(edit.duration(clip) * FPS) - 1
        a = max(0, avail - n - extra) if use == "tail" else (0 if sid in ("r13",) else min(4, max(0, avail - n - extra)))
        frames = read_frames(clip, vertical, x, a, n + extra)
        z0 = cam.get("start_zoom", 1.0 + max(0.0, -cam.get("push", 0)))
        for i, fr in enumerate(frames[:n]):
            f = i / max(1, n)
            t = (K[k] + i) / FPS
            z = z0 + cam.get("push", 0) * reel.ease(f)
            if cam.get("punch") and i < 6:
                z += cam["punch"] * (1 - reel.ease(i / 6))
            for lo, hi, amp in ((fury[0], fury[1], 0.03), (union[0], union[1], 0.03)):
                for bt in beats:
                    if lo <= bt < hi and 0 <= t - bt < 0.25:
                        z += amp * np.exp(-(t - bt) / 0.075)
            sh = 0.0
            if cam.get("shake"):
                sh = cam["shake"] * (np.exp(-i / 4) if sid == "r13" else 0.4)
            img = reel.warp(fr, z, 0.5, 0.45 if sid in ("s4", "s7", "r01") else 0.5, sh, rng, out=(W, H))
            if cam.get("flash") and i < 3:
                a_ = [0.9, 0.55, 0.2][i]
                img = cv2.addWeighted(img, 1 - a_, np.full_like(img, 255), a_, 0)
            if prev_tail is not None and i < len(prev_tail):      # dissolve from the previous shot
                w = (i + 1) / (len(prev_tail) + 1)
                img = cv2.addWeighted(prev_tail[i], 1 - w, img, w, 0)
            enc.stdin.write(img.tobytes())
        prev_tail = [reel.warp(fr, z0 + cam.get("push", 0), 0.5, 0.5, 0, None, out=(W, H)) for fr in frames[n:]] \
            if dis_out else None
        # ambience for this shot
        aud = reel.load_audio(clip, a / FPS, n / FPS)
        m = min(len(aud), int(n / FPS * SR))
        ramp = min(int(0.02 * SR), m // 2)
        aud = aud[:m].copy()
        aud[:ramp] *= np.linspace(0, 1, ramp)[:, None]
        aud[-ramp:] *= np.linspace(1, 0, ramp)[:, None]
        i0 = int(K[k] / FPS * SR)
        amb[i0:i0 + m] += aud

    # End card over the darkening last frame of s7.
    last = frames[n - 1]
    card_n = total - K[-1]
    tmpd = build / "card"
    tmpd.mkdir(exist_ok=True)
    cv2.imwrite(str(tmpd / "last.png"), last)
    edit.end_card_images(tmpd / "last.png", (W, H), tmpd)
    bg = cv2.imread(str(tmpd / "card_bg.png"))
    t1 = Image.open(tmpd / "card_t1.png")
    t2 = Image.open(tmpd / "card_t2.png")
    for i in range(card_n):
        f = i / card_n
        base = cv2.addWeighted(last, 1 - reel.ease(f / 0.25), bg, reel.ease(f / 0.25), 0)
        img = reel.composite(base, t1, alpha=reel.ease((f - 0.15) / 0.2))
        img = reel.composite(img, t2, alpha=reel.ease((f - 0.35) / 0.2))
        img = (img * (1 - reel.ease((f - 0.88) / 0.12))).astype(np.uint8)
        enc.stdin.write(img.tobytes())
    enc.stdin.close()
    enc.wait()

    # Music bus (dip, heartbeats, bell on the cut) + ducked ambience, then master.
    import soundfile as sf
    starts = {c["id"]: c["start"] for c in cuts}
    shaped = grief_drop(music, (starts["s4"], starts["r01"]), build / "score_shaped.wav")
    prep_info = {"sections": info["marks"][1:], "bell": info["bell"], "silent": info["silent"]}
    score = edit.prepare_score(shaped, prep_info, build / "score_prepared.wav")
    sf.write(build / "ambience.wav", amb[:int(total / FPS * SR)], SR, subtype="PCM_24")
    mix = build / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(score), "-i", str(build / "ambience.wav"),
                    "-filter_complex", "[0:a]asplit=2[mus][key];[1:a]volume=-9dB[amb];"
                    "[amb][key]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=450:makeup=1[duck];"
                    f"[mus][duck]amix=inputs=2:duration=first:normalize=0,atrim=0:{total / FPS:.4f}[m]",
                    "-map", "[m]", "-c:a", "pcm_s24le", str(mix)], check=True)
    premaster = build / "premaster.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(build / "video.mp4"), "-i", str(mix), "-map", "0:v",
                    "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s24le", "-shortest", str(premaster)], check=True)
    edit.BUILD = build
    edit.master_audio(premaster, out)
    return out
