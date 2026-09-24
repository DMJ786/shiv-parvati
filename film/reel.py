"""Instagram "rotate your phone" reel: vertical hook -> rotate prompt -> the 16:9 film turned 90 degrees
to fill 1080x1920, re-edited with push-ins, impact zooms on hard cuts, beat pulses, punch-in close-ups
and a flash + shake on the bell. Frames are warped in numpy/OpenCV (sub-pixel, no zoompan jitter)."""
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from film import edit

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
FPS = 24
FW, FH = 1920, 1080                   # film frame (before rotation)
RW, RH = 1080, 1920                   # reel frame
SR = 48000
BOLD = ROOT / "assets" / "fonts" / "Montserrat-800.ttf"
SEMI = ROOT / "assets" / "fonts" / "Montserrat-600.ttf"

HOOK_START, HOOK_LEN = None, 2.6      # hook = the bell + Shiva's eyes opening (start filled from the timeline)
ROTATE_LEN = 2.4
HOOK_LINES = ["After spending hours", "I made this with AI"]
ROTATE_LINES = ["ROTATE YOUR PHONE", "for the full cinematic experience"]

# Per-shot camera treatment. push: zoom gained over the shot; punch: impact zoom on a hard cut into the shot;
# jump: (zoom, point) punch-in jump cut on the beat nearest mid-shot, point = "eyes" or (x, y).
TREATMENT = {
    "01": {"push": 0.10},
    "02": {"push": 0.06, "punch": 0.10},
    "03": {"push": 0.08, "punch": 0.10},
    "04": {"push": 0.07},
    "05": {"push": 0.04, "punch": 0.08},
    "06": {"push": 0.07},
    "07": {"push": 0.08, "punch": 0.10, "jump": (1.35, "eyes")},
    "08": {"push": 0.06},
    "09": {"push": 0.07, "punch": 0.10},
    "10": {"push": 0.10, "jump": (1.45, (0.62, 0.42))},
    "11": {"push": 0.08, "punch": 0.12, "shake": 5},
    "12": {"push": 0.05, "punch": 0.08, "jump": (1.4, "eyes")},
    "13": {"push": 0.08, "punch": 0.20, "flash": True, "shake": 14},
    "14": {"push": 0.06, "jump": (1.45, "eyes")},
    "15": {"push": -0.08},            # slow pull-back reveal
}
FALLBACK_CENTRE = {"01": (0.5, 0.5), "09": (0.52, 0.45), "10": (0.61, 0.45), "11": (0.5, 0.45), "15": (0.5, 0.5)}


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- analysis
def frame_at(src, t, w=FW, h=FH):
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 3)


def subject_points(src, cuts):
    """Normalised (x, y) of the subject and of the eyes for every shot, from face landmarks where possible."""
    from film.face import _app
    pts = {}
    for c in cuts:
        sid = c["id"]
        im = frame_at(src, (c["start"] + c["end"]) / 2)
        faces = [f for f in _app().get(im) if f.det_score > 0.5]
        if faces and sid not in FALLBACK_CENTRE:
            faces.sort(key=lambda f: -(f.bbox[2] - f.bbox[0]))
            use = faces if sid == "08" else faces[:1]
            box = np.array([f.bbox for f in use])
            centre = ((box[:, 0].min() + box[:, 2].max()) / 2 / FW, (box[:, 1].min() + box[:, 3].max()) / 2 / FH)
            eyes = faces[0].kps[:2].mean(0) / [FW, FH]
            pts[sid] = {"centre": centre, "eyes": (float(eyes[0]), float(eyes[1]))}
        else:
            c0 = FALLBACK_CENTRE.get(sid, (0.5, 0.5))
            pts[sid] = {"centre": c0, "eyes": c0}
    return pts


# ---------------------------------------------------------------- camera curve
def camera(cuts, beats, bell, pts):
    """Per-frame (zoom, cx, cy, flash, shake_px) for the whole film, keyed to the cut plan."""
    n = round(cuts[-1]["end"] * FPS) + 400
    z = np.ones(n)
    cx, cy = np.full(n, 0.5), np.full(n, 0.5)
    flash, shake = np.zeros(n), np.zeros(n)
    prev_end_z = 1.0
    for k, c in enumerate(cuts):
        sid, tr = c["id"], TREATMENT.get(c["id"], {})
        a, b = round(c["start"] * FPS), round(c["end"] * FPS)
        dis_in = k > 0 and cuts[k - 1]["dissolve_out"]
        z0 = max(prev_end_z, 1.0 + max(0.0, -tr.get("push", 0))) if dis_in else 1.0 + max(0.0, -tr.get("push", 0))
        z1 = z0 + tr.get("push", 0)
        centre = pts[sid]["centre"]
        jump_at, jump = None, tr.get("jump")
        if jump:
            mid = (c["start"] + c["end"]) / 2
            cands = [bt for bt in beats if c["start"] + 1.0 < bt < c["end"] - 0.6]
            jump_at = round((min(cands, key=lambda bt: abs(bt - mid)) if cands else mid) * FPS)
        for i in range(a, b):
            f = (i - a) / max(1, b - a)
            zz, (x, y) = z0 + (z1 - z0) * ease(f), centre
            if jump_at is not None and i >= jump_at:
                point = pts[sid]["eyes"] if jump[1] == "eyes" else jump[1]
                zz = jump[0] + (tr.get("push", 0) * 0.5) * (i - jump_at) / max(1, b - jump_at)
                x, y = point
            if not dis_in or i >= a + edit.POST:
                p = tr.get("punch", 0) if not dis_in else 0
                if p and i - a < 6:
                    zz += p * (1 - ease((i - a) / 6))
            z[i], cx[i], cy[i] = zz, x, y
        prev_end_z = z1
        if tr.get("flash"):
            flash[a:a + 3] = [0.9, 0.55, 0.2]
        if tr.get("shake"):
            amp = tr["shake"]
            for j in range(12 if sid == "13" else b - a):
                shake[a + j] = max(shake[a + j], amp * (np.exp(-j / 4) if sid == "13" else 0.35))
        # Smooth the centre across dissolves so the blended frames do not jump.
        if dis_in:
            lo, hi = a - edit.PRE, a + edit.POST
            for i in range(lo, hi):
                w = ease((i - lo) / (hi - lo))
                for arr in (z, cx, cy):
                    arr[i] = arr[lo - 1] * (1 - w) + arr[hi] * w
    # Beat pulses: every beat in the climax, every other beat under the choir.
    sec = [c["start"] for c in cuts]
    for j, bt in enumerate(beats):
        if bell + 0.3 <= bt < cuts[-1]["end"] - 0.3:
            amp = 0.035
        elif cuts[7]["start"] <= bt < cuts[11]["start"] and j % 2 == 0:
            amp = 0.022
        else:
            continue
        i0 = round(bt * FPS)
        for d in range(6):
            if i0 + d < n:
                z[i0 + d] += amp * np.exp(-d / 1.8)
    card = round(cuts[-1]["end"] * FPS)
    z[card:] = 1.0
    cx[card:], cy[card:] = 0.5, 0.5
    return z, cx, cy, flash, shake


def warp(frame, zoom, cx, cy, shake_px=0.0, rng=None, out=(FW, FH)):
    h, w = frame.shape[:2]
    zoom = max(zoom, 1.0 + (2.5 * shake_px / min(w, h) if shake_px else 0))
    vw, vh = w / zoom, h / zoom
    x0 = min(max(cx * w - vw / 2, 0), w - vw)
    y0 = min(max(cy * h - vh / 2, 0), h - vh)
    if shake_px and rng is not None:
        x0 = min(max(x0 + rng.uniform(-shake_px, shake_px), 0), w - vw)
        y0 = min(max(y0 + rng.uniform(-shake_px, shake_px), 0), h - vh)
    sx, sy = out[0] / vw, out[1] / vh
    m = np.float32([[sx, 0, -x0 * sx], [0, sy, -y0 * sy]])
    return cv2.warpAffine(frame, m, out, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------- graphics
def text_layer(lines, fonts, top, size=(RW, RH), gap=1.25, stroke=6):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = top
    for line, font in zip(lines, fonts):
        tw = d.textlength(line, font=font)
        d.text(((size[0] - tw) / 2, y), line, font=font, fill=(255, 255, 255, 255),
               stroke_width=stroke, stroke_fill=(0, 0, 0, 210))
        y += int(font.size * gap)
    shadow = layer.filter(ImageFilter.GaussianBlur(10))
    shadow.putalpha(shadow.getchannel("A").point(lambda v: int(v * 0.6)))
    base = Image.new("RGBA", size, (0, 0, 0, 0))
    base.alpha_composite(shadow, (0, 8))
    base.alpha_composite(layer)
    return base


def composite(bgr, layer, alpha=1.0, scale=1.0):
    im = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    if scale != 1.0:
        w, h = layer.size
        sl = layer.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        tmp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        tmp.alpha_composite(sl, ((w - sl.width) // 2, (h - sl.height) // 2))
        layer = tmp
    if alpha < 1.0:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    im.alpha_composite(layer)
    return cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR)


def phone_frames(n, bg):
    """Phone outline turning from portrait to landscape (counter-clockwise), with the prompt text."""
    title = ImageFont.truetype(str(BOLD), 70)
    sub = ImageFont.truetype(str(SEMI), 40)
    text = text_layer(ROTATE_LINES, [title, sub], 1330, gap=1.5, stroke=0)
    pw, ph, r = 300, 560, 46
    icon = Image.new("RGBA", (ph + 80, ph + 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    ox, oy = (icon.width - pw) // 2, (icon.height - ph) // 2
    d.rounded_rectangle([ox, oy, ox + pw, oy + ph], radius=r, outline=(255, 255, 255, 255), width=12)
    d.rounded_rectangle([ox + pw / 2 - 45, oy + 22, ox + pw / 2 + 45, oy + 42], radius=10, fill=(255, 255, 255, 255))
    frames = []
    for i in range(n):
        t = i / n
        ang = 90 * ease((t - 0.2) / 0.45)                    # counter-clockwise quarter turn
        appear = ease(t / 0.12)
        ic = icon.rotate(ang, resample=Image.BICUBIC, expand=False)
        ic = ic.resize((int(ic.width * (0.85 + 0.15 * appear)),) * 2, Image.LANCZOS)
        ic.putalpha(ic.getchannel("A").point(lambda v, a=appear: int(v * a)))
        im = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB)).convert("RGBA")
        im.alpha_composite(ic, ((RW - ic.width) // 2, 860 - ic.height // 2))
        ta = ease((t - 0.1) / 0.15)
        tl = text.copy()
        tl.putalpha(tl.getchannel("A").point(lambda v, a=ta: int(v * a)))
        im.alpha_composite(tl)
        fade = 1 - ease((t - 0.93) / 0.07)
        frames.append((cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2BGR) * fade).astype(np.uint8))
    return frames


# ---------------------------------------------------------------- audio
def load_audio(src, t0=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", str(src)]
    if dur:
        cmd += ["-t", f"{dur:.4f}"]
    cmd += ["-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


def whoosh(dur, peak_at):
    """Filtered-noise whoosh swelling to a peak, then a soft sub drop."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(3).standard_normal(n)
    env = np.exp(-((t - peak_at) / 0.28) ** 2)
    # sweep a one-pole low-pass cut-off up and down with the envelope
    out = np.zeros(n)
    y = 0.0
    for i in range(n):
        a = 0.02 + 0.5 * env[i]
        y += a * (noise[i] - y)
        out[i] = y
    out = out / (np.abs(out).max() + 1e-9) * env * 0.35
    boom_t = t - (peak_at + 0.3)
    boom = np.where(boom_t > 0, np.sin(2 * np.pi * 45 * boom_t) * np.exp(-boom_t * 6), 0) * 0.45
    s = out + boom
    return np.stack([s, s], 1).astype(np.float32)


# ---------------------------------------------------------------- render
def render(out):
    tl = json.loads((BUILD / "timeline.json").read_text())
    cuts, bell = tl["cuts"], tl["bell"]
    src = BUILD / "shiv_parvati_16x9_premaster.mov"
    info = edit.analyse(ROOT / "music" / tl["music"])
    beats = info["beats"]
    film_frames = round(edit.duration(src) * FPS)
    pts = subject_points(src, cuts)
    z, cx, cy, flash, shake = camera(cuts, beats, bell, pts)
    rng = np.random.default_rng(7)

    video = BUILD / "reel_video.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{RW}x{RH}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
                            "-tune", "grain", "-pix_fmt", "yuv420p", str(video)], stdin=subprocess.PIPE)

    def reader(t0, frames):
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", str(src), "-frames:v", str(frames),
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
        for _ in range(frames):
            buf = p.stdout.read(FW * FH * 3)
            if len(buf) < FW * FH * 3:
                break
            yield np.frombuffer(buf, np.uint8).reshape(FH, FW, 3)
        p.stdout.close()
        p.wait()

    # 1) Hook: Shiva's eyes open on the bell, vertical crop around his face, captions popping in.
    hook_n = round(HOOK_LEN * FPS)
    hook_t0 = cuts[12]["start"]
    size = 80
    while True:
        big = ImageFont.truetype(str(BOLD), size)
        if max(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(l, font=big) for l in HOOK_LINES) <= RW - 120:
            break
        size -= 2
    caption = text_layer(HOOK_LINES, [big, big], 330)
    fx, fy = pts["13"]["centre"]
    for i, fr in enumerate(reader(hook_t0, hook_n)):
        zz = 1.0 + 0.10 * ease(i / hook_n) + (0.12 * (1 - ease(i / 6)) if i < 6 else 0)
        vw = FH * RW / RH                                 # 9:16 window inside the 16:9 frame
        crop_w = vw / zz
        x0 = min(max(fx * FW - crop_w / 2, 0), FW - crop_w)
        crop_h = FH / zz
        y0 = min(max(fy * FH - crop_h / 2, 0), FH - crop_h)
        sx, sy = RW / crop_w, RH / crop_h
        m = np.float32([[sx, 0, -x0 * sx], [0, sy, -y0 * sy]])
        frame = cv2.warpAffine(fr, m, (RW, RH), flags=cv2.INTER_CUBIC)
        frame = cv2.addWeighted(frame, 1.25, cv2.GaussianBlur(frame, (0, 0), 2.0), -0.25, 0)   # restore crispness
        # Caption readable from the very first frame (it doubles as the thumbnail), with a quick settle.
        pop = ease((i + 1) / 4)
        frame = composite(frame, caption, alpha=min(1.0, 0.75 + pop), scale=0.94 + 0.06 * pop)
        enc.stdin.write(frame.tobytes())

    # 2) Rotate prompt over a dark, blurred first frame of the film.
    first = frame_at(src, 0.5)
    bg = cv2.rotate(first, cv2.ROTATE_90_CLOCKWISE)
    bg = (cv2.GaussianBlur(bg, (0, 0), 25) * 0.28).astype(np.uint8)
    rot_frames = phone_frames(round(ROTATE_LEN * FPS), bg)
    for frame in rot_frames:
        enc.stdin.write(frame.tobytes())

    # 3) The film, re-cut with camera moves, turned 90 degrees clockwise to fill the vertical frame.
    for i, fr in enumerate(reader(0.0, film_frames)):
        frame = warp(fr, z[i], cx[i], cy[i], shake[i], rng)
        if flash[i] > 0:
            frame = cv2.addWeighted(frame, 1 - flash[i], np.full_like(frame, 255), flash[i], 0)
        enc.stdin.write(cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE).tobytes())
    enc.stdin.close()
    enc.wait()

    # Audio: bell + climax under the hook, whoosh through the rotate prompt, then the film's own mix.
    hook_a = load_audio(src, hook_t0, HOOK_LEN)
    fade = np.ones(len(hook_a))
    fade[-int(0.35 * SR):] = np.linspace(1, 0.15, int(0.35 * SR))
    hook_a *= fade[:, None]
    rot_a = whoosh(ROTATE_LEN, peak_at=0.2 * ROTATE_LEN + 0.45 * ROTATE_LEN / 2)
    film_a = load_audio(src)
    mix = np.concatenate([hook_a, rot_a, film_a])
    wav = BUILD / "reel_mix.wav"
    import soundfile as sf
    sf.write(wav, mix, SR, subtype="PCM_24")
    premaster = BUILD / "reel_premaster.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "pcm_s24le", "-shortest", str(premaster)], check=True)
    edit.master_audio(premaster, out)
    return out
