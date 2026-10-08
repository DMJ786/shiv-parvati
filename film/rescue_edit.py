"""Edit for episode 3, "The Rescue": beat-locked cut with two sync points (bell on the cut into the golden light,
the climax on the catch), slow motion on the reach and the catch, camera moves, grade + grain, closing title,
ambience under the score with the cry and the impact lifted, -14 LUFS master; 16:9 film and vertical Reel together."""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from film import edit, reel
from film.rescue import MUSIC_SECTIONS, SHOTS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rescue"
CLIPS, BUILD = OUT / "clips", OUT / "build"
FPS, SR = 24, 48000
W, H, VW, VH = 1920, 1080, 1080, 1920
MIN_SHOT = 1.5
XFADE = 8                                   # frames of dissolve, only where time passes
DISSOLVE_INTO = {"14", "18", "16"}
BELL_INTO, CLIMAX_INTO = "17", "08"         # cut into 17 on the bell; the climax lands on the catch
SLOW = {"07": 0.6, "08": 0.6}               # slow motion factors (frame-blended); 16 is slowed only if it must be
# Usable part of a clip, from its first frame (Kling went wrong after this point): seconds.
CLIP_MAX = {"06": 1.55, "10": 2.3, "17": 2.1}
MIN_OVERRIDE = {"06": 1.25}
AMB_GAIN = {"06": 6.0, "03": 3.0, "08": 3.0, "04": 2.0}   # dB lift on the native sound: the cry, crack, impact, fall
TITLE_LINES = ["When you call with all your heart, He answers."]
FONT = ROOT / "assets" / "fonts" / "Cinzel-700.ttf"
FONT_LIGHT = ROOT / "assets" / "fonts" / "Cinzel-400.ttf"

# Camera per shot: push = zoom gained over the shot, punch = impact zoom on the cut, shake = px of camera shake.
CAM = {
    "01": {"push": 0.06}, "02": {"push": 0.05, "punch": 0.06}, "03": {"punch": 0.12, "shake": 6, "push": 0.04},
    "04": {"punch": 0.15, "shake": 10, "push": 0.08}, "05": {"push": 0.06, "shake": 3}, "06": {"push": 0.10},
    "17": {"push": 0.06}, "07": {"push": 0.05}, "08": {"punch": 0.10, "shake": 8, "push": 0.03},
    "09": {"push": 0.06}, "10": {"push": 0.04}, "11": {"push": 0.04}, "12": {"push": 0.05}, "13": {"push": 0.05},
    "14": {"push": 0.06}, "15": {"push": 0.06}, "18": {"push": 0.05}, "16": {"push": -0.06},
}
# 9:16 framing: subject x (0-1 of the 16:9 frame) at the start and end of each shot; faces are tracked otherwise.
VERT = {"01": (0.27, 0.32), "03": (0.45, 0.45), "07": (0.5, 0.5), "08": (0.55, 0.55), "10": (0.36, 0.6),
        "11": (0.36, 0.58), "12": (0.4, 0.58), "14": (0.38, 0.42), "16": (0.58, 0.6), "17": (0.5, 0.5),
        "18": (0.3, 0.72)}


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- music
def analyse(music):
    import librosa
    y, sr = librosa.load(str(music), sr=22050, mono=True)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    total = sum(s[1] for s in MUSIC_SECTIONS)
    marks = np.cumsum([0] + [s[1] for s in MUSIC_SECTIONS]) * (len(y) / sr) / total
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)

    def snap(t, win=0.45):
        near = [o for o in onsets if abs(o - t) <= win]
        return float(min(near, key=lambda o: abs(o - t))) if near else float(t)
    return {"beats": [float(b) for b in beats], "marks": marks.tolist(), "length": len(y) / sr,
            "bell": snap(marks[2]), "climax": snap(marks[3])}


# ---------------------------------------------------------------- clips
def clip_for(sid):
    """The clip to cut from: slowed (frame-blended) for the slow-motion shots."""
    src = CLIPS / f"{sid}.mp4"
    if not src.exists() and (CLIPS / f"{sid}_still.mp4").exists():
        return CLIPS / f"{sid}_still.mp4"          # stand-in made from the keyframe (no fal credit for the clip)
    if sid not in SLOW:
        return src
    dst = BUILD / f"slow_{sid}.mp4"
    if not dst.exists():
        f = SLOW[sid]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
                        f"[0:v]setpts=PTS/{f},framerate=fps={FPS}:interp_start=0:interp_end=255:scene=100[v];"
                        f"[0:a]atempo={f}[a]", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(dst)], check=True)
    return dst


def plan(info):
    """Dynamic programming over beats and half-beats: shots >= 1.5 s and within their clip, the cut into 17 on the
    bell and the cut into 08 on the climax, staying close to the storyboard's proportions."""
    order = list(SHOTS)
    n = len(order)
    L = info["length"]
    secs = [SHOTS[s][1] for s in order]
    scale = (L - 0.3) / sum(secs)
    ideal = list(np.cumsum([0] + secs) * scale)
    bb = info["beats"]
    beats = sorted({round(b * FPS) / FPS for b in bb + [(x + y) / 2 for x, y in zip(bb, bb[1:])]})
    fixed = {order.index(BELL_INTO): round(info["bell"] * FPS) / FPS,
             order.index(CLIMAX_INTO): round(info["climax"] * FPS) / FPS}
    avail = {s: min(CLIP_MAX.get(s, 99.0), edit.duration(clip_for(s)) - (XFADE + 2) / FPS) for s in order}
    avail["16"] = 99.0                                       # the last shot may be slowed to fill the tail
    end = round(L * FPS) / FPS
    # Off-beat fallback every quarter second (penalised) where the music has no detectable beat (the quiet intro).
    grid = sorted({round(x * FPS) / FPS for x in np.arange(0.125, L, 0.125)} - set(beats))
    on_beat = set(beats)
    cands = [[0.0]] + [[fixed[k]] if k in fixed else beats + grid for k in range(1, n)] + [[end]]
    best = [{0.0: (0.0, None)}]
    for k in range(1, n + 1):
        cur = {}
        for t in cands[k]:
            for tp, (cost, _) in best[k - 1].items():
                if MIN_OVERRIDE.get(order[k - 1], MIN_SHOT) - 1e-6 <= t - tp <= avail[order[k - 1]] + 1e-6:
                    c = cost + (t - ideal[k]) ** 2 + (0 if t in on_beat or k in fixed or k == n else 0.6)
                    if t not in cur or c < cur[t][0]:
                        cur[t] = (c, tp)
        if not cur:
            raise SystemExit(f"No beat-aligned plan fits at cut {k} ({order[k - 1]}).")
        best.append(cur)
    t = end
    cuts = [t]
    for k in range(n, 0, -1):
        t = best[k][t][1]
        cuts.append(t)
    cuts = cuts[::-1]
    return [{"id": order[k], "start": cuts[k], "end": cuts[k + 1]} for k in range(n)]


def read_frames(clip, a, n, speed=1.0):
    vf = f"fps={FPS},scale={W}:{H}:flags=lanczos"
    if speed != 1.0:
        vf = f"setpts=PTS/{speed},framerate=fps={FPS}:interp_start=0:interp_end=255:scene=100,scale={W}:{H}"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"{vf},trim=start_frame={a}:end_frame={a + n}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    frames = []
    while len(frames) < n:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        frames.append(np.frombuffer(buf, np.uint8).reshape(H, W, 3))
    p.stdout.close()
    p.wait()
    while len(frames) < n:
        frames.append(frames[-1])
    return frames


def subject_x(sid):
    if sid in VERT:
        return VERT[sid]
    from film.face import _detect
    im = cv2.imread(str(OUT / "keyframes" / f"{sid}.png"))
    found, pad = _detect(im)
    if not found:
        return 0.5, 0.5
    b = found[0].bbox - pad
    x = float((b[0] + b[2]) / 2 / im.shape[1])
    return x, x


# ---------------------------------------------------------------- title
def title_layer(size):
    """Closing title at the top of the frame, over a soft dark gradient, clear of the walking figure."""
    w, h = size
    vertical = h > w
    fs = int(w * (0.06 if vertical else 0.028))
    small = ImageFont.truetype(str(FONT_LIGHT), fs)
    big = ImageFont.truetype(str(FONT), int(fs * (1.05 if vertical else 1.2)))
    gold, glow = (246, 220, 160, 255), (255, 170, 60)
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lines = (["When you call", "with all your heart,", "He answers."] if vertical else TITLE_LINES)
    y = h * (0.10 if vertical else 0.05)
    for line in lines:
        d.text(((w - d.textlength(line, font=small)) / 2, y), line, font=small, fill=gold)
        y += int(fs * 1.5)
    y += int(fs * 0.45)
    line = "HAR HAR MAHADEV"
    track = int(fs * 0.15)
    x = (w - (d.textlength(line, font=big) + track * (len(line) - 1))) / 2
    for ch in line:
        d.text((x, y), ch, font=big, fill=gold)
        x += d.textlength(ch, font=big) + track
    bottom = y + big.size * 1.6
    g = im.filter(ImageFilter.GaussianBlur(fs * 0.4))
    tint = Image.new("RGBA", size, glow + (0,))
    tint.putalpha(g.getchannel("A").point(lambda a: int(a * 0.55)))
    shade = Image.new("L", size, 0)
    sd = ImageDraw.Draw(shade)
    for yy in range(int(bottom + h * 0.08)):
        sd.line([(0, yy), (w, yy)], fill=int(170 * min(1.0, (bottom + h * 0.08 - yy) / (h * 0.12))))
    dark = Image.new("RGBA", size, (6, 6, 10, 255))
    dark.putalpha(shade)
    return Image.alpha_composite(Image.alpha_composite(dark, tint), im)


# ---------------------------------------------------------------- render
def render(music, out16, out9):
    BUILD.mkdir(parents=True, exist_ok=True)
    info = analyse(music)
    cuts = plan(info)
    (BUILD / "timeline.json").write_text(json.dumps({"bell": info["bell"], "climax": info["climax"], "cuts": cuts},
                                                    indent=1))
    for c in cuts:
        print(f"  {c['id']}  {c['start']:6.2f} -> {c['end']:6.2f} ({c['end'] - c['start']:.2f}s)")
    K = [round(c["start"] * FPS) for c in cuts] + [round(cuts[-1]["end"] * FPS)]
    total = K[-1]
    beats = info["beats"]
    tension = (0.0, info["bell"])
    rng = np.random.default_rng(5)
    t16, t9 = title_layer((W, H)), title_layer((VW, VH))
    title_from = total - round(3.6 * FPS)

    def encoder(path, size):
        return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
                                 f"{size[0]}x{size[1]}", "-r", str(FPS), "-i", "-", "-vf",
                                 f"{edit.GRADE},{edit.GRAIN},format=yuv420p", "-c:v", "libx264", "-crf", "14",
                                 "-preset", "medium", "-tune", "grain", str(path)], stdin=subprocess.PIPE)
    e16, e9 = encoder(BUILD / "video_16x9.mp4", (W, H)), encoder(BUILD / "video_9x16.mp4", (VW, VH))
    amb = np.zeros((int((total / FPS + 1) * SR), 2), np.float32)
    tail16 = tail9 = None
    for k, c in enumerate(cuts):
        sid, cam = c["id"], CAM.get(c["id"], {})
        clip = clip_for(sid)
        n = K[k + 1] - K[k]
        clen = int(edit.duration(clip) * FPS) - 1
        speed = 1.0
        if sid == "16" and n + 2 > clen:
            speed = max(0.6, (clen - 2) / (n + 2))
        avail = int(clen / speed) if speed != 1.0 else clen
        extra = XFADE if k + 1 < len(cuts) and cuts[k + 1]["id"] in DISSOLVE_INTO else 0
        a = 0 if sid in (CLIMAX_INTO, "07") or sid in CLIP_MAX else \
            max(0, min(int((avail - n - extra) * 0.3), avail - n - extra))
        frames = read_frames(clip, a, n + extra, speed)
        z0 = 1.0 + max(0.0, -cam.get("push", 0))
        vx0, vx1 = subject_x(sid)
        f16, f9 = [], []
        for i, fr in enumerate(frames):
            f = min(1.0, i / max(1, n))
            t = (K[k] + i) / FPS
            z = z0 + cam.get("push", 0) * ease(f)
            if cam.get("punch") and i < 6:
                z += cam["punch"] * (1 - ease(i / 6))
            if tension[0] <= t < tension[1]:
                for j, bt in enumerate(beats):
                    if j % 2 == 0 and 0 <= t - bt < 0.25:
                        z += 0.025 * np.exp(-(t - bt) / 0.075)
            sh = cam.get("shake", 0) * (np.exp(-i / 5) if sid in ("03", "04", "08") else 0.3)
            img = reel.warp(fr, z, 0.5, 0.5, sh, rng, out=(W, H))
            if sid == CLIMAX_INTO and i < 10:
                img = reel.bloom(img, 0.35 * np.exp(-i / 3))
            vx = vx0 + (vx1 - vx0) * ease(f)
            cw = round(H * VW / VH)
            x0 = int(min(max(vx * W - cw / 2, 0), W - cw))
            v = cv2.resize(img[:, x0:x0 + cw], (VW, VH), interpolation=cv2.INTER_CUBIC)
            f16.append(img)
            f9.append(v)
        for i in range(n):
            a16, a9 = f16[i], f9[i]
            if tail16 is not None and i < len(tail16):
                w_ = (i + 1) / (len(tail16) + 1)
                a16 = cv2.addWeighted(tail16[i], 1 - w_, a16, w_, 0)
                a9 = cv2.addWeighted(tail9[i], 1 - w_, a9, w_, 0)
            gi = K[k] + i
            if gi >= title_from:
                al = ease((gi - title_from) / (1.2 * FPS))
                a16 = reel.composite(a16, t16, alpha=al)
                a9 = reel.composite(a9, t9, alpha=al)
            fade = 1 - ease((gi - (total - 18)) / 18)
            if fade < 1:
                a16 = (a16 * fade).astype(np.uint8)
                a9 = (a9 * fade).astype(np.uint8)
            e16.stdin.write(a16.tobytes())
            e9.stdin.write(a9.tobytes())
        tail16, tail9 = (f16[n:], f9[n:]) if extra else (None, None)
        # native ambience of the used part of the clip, lifted for the cry / crack / impact
        aud = reel.load_audio(clip, a / FPS * speed, n / FPS)
        if len(aud) == 0:
            aud = np.zeros((int(n / FPS * SR), 2), np.float32)
        if speed != 1.0:
            idx = np.clip((np.arange(int(n / FPS * SR)) * speed).astype(int), 0, len(aud) - 1)
            aud = aud[idx]
        m = min(len(aud), int(n / FPS * SR))
        aud = aud[:m] * 10 ** (AMB_GAIN.get(sid, 0) / 20)
        r = min(int(0.02 * SR), m // 2)
        aud[:r] *= np.linspace(0, 1, r)[:, None]
        aud[-r:] *= np.linspace(1, 0, r)[:, None]
        i0 = int(K[k] / FPS * SR)
        amb[i0:i0 + m] += aud
    e16.stdin.close()
    e9.stdin.close()
    e16.wait()
    e9.wait()

    # Music bus: the score + one temple bell on the cut into the golden light + a sub boom on the catch.
    import librosa
    import soundfile as sf
    y, _ = librosa.load(str(music), sr=SR, mono=False)
    y = np.atleast_2d(y)
    y = np.vstack([y, y]) if y.shape[0] == 1 else y
    y = y[:, :int(total / FPS * SR)]
    # Shape the score: a filtered hush from the bell to the catch (the climax then slams back in on the grip),
    # and a gentler level under the gratitude and the keepsake.
    from scipy.signal import butter, sosfiltfilt
    tt = np.arange(y.shape[1]) / SR
    starts = {c["id"]: c["start"] for c in cuts}
    hush = np.clip(np.minimum((tt - starts[BELL_INTO]) / 0.25, (starts[CLIMAX_INTO] - tt) / 0.06), 0, 1)
    soft = np.clip(np.minimum((tt - starts["13"]) / 0.8, (starts["18"] - tt) / 0.8), 0, 1)
    lp = sosfiltfilt(butter(4, 900, "lowpass", fs=SR, output="sos"), y, axis=1)
    y = (y * (1 - hush) + lp * 10 ** (-12 / 20) * hush) * (1 - soft * (1 - 10 ** (-5 / 20)))
    loud = np.sqrt(np.mean(y ** 2)) + 1e-9
    bell, _ = librosa.load(str(edit.BELL_SFX), sr=SR, mono=True)
    on = librosa.onset.onset_detect(y=bell, sr=SR, units="samples", backtrack=True)
    bell = bell[(on[0] if len(on) else 0):]
    bell = bell / (np.sqrt(np.mean(bell[: SR // 2] ** 2)) + 1e-9) * loud * 1.6
    i = int(K[[c["id"] for c in cuts].index(BELL_INTO)] / FPS * SR)
    m = min(len(bell), y.shape[1] - i)
    y[:, i:i + m] += bell[:m]
    tb = np.arange(int(0.6 * SR)) / SR
    boom = np.sin(2 * np.pi * np.cumsum(40 + 50 * np.exp(-tb * 18)) / SR) * np.exp(-tb * 7) * loud * 3.0
    i = int(K[[c["id"] for c in cuts].index(CLIMAX_INTO)] / FPS * SR)
    y[:, i:i + len(boom)] += boom[: y.shape[1] - i]
    y *= min(1.0, 0.98 / (np.abs(y).max() + 1e-9))
    sf.write(BUILD / "score_prepared.wav", y.T, SR, subtype="PCM_24")
    sf.write(BUILD / "ambience.wav", amb[:y.shape[1]], SR, subtype="PCM_24")
    mix = BUILD / "mix.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(BUILD / "score_prepared.wav"), "-i",
                    str(BUILD / "ambience.wav"), "-filter_complex",
                    "[0:a]asplit=2[mus][key];[1:a]volume=-8dB[amb];"
                    "[amb][key]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=400:makeup=1[duck];"
                    f"[mus][duck]amix=inputs=2:duration=first:normalize=0,atrim=0:{total / FPS:.4f}[m]",
                    "-map", "[m]", "-c:a", "pcm_s24le", str(mix)], check=True)
    edit.BUILD = BUILD
    for video, out in ((BUILD / "video_16x9.mp4", out16), (BUILD / "video_9x16.mp4", out9)):
        pm = BUILD / (out.stem + "_premaster.mov")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(mix), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "pcm_s24le", "-shortest", str(pm)], check=True)
        edit.master_audio(pm, out)
    return out16, out9
