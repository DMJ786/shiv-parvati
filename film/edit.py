"""Step 4: beat-synced cut, grade, end card, ducked mix, -14 LUFS master, 16:9 and 9:16 exports."""
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from film.shots import MUSIC_SECTIONS, SHOTS

ROOT = Path(__file__).resolve().parent.parent
CLIPS, MUSIC, BUILD = ROOT / "clips", ROOT / "music", ROOT / "build"
FONT = ROOT / "assets" / "fonts" / "Cinzel-700.ttf"
FONT_LIGHT = ROOT / "assets" / "fonts" / "Cinzel-400.ttf"
FPS = 24
DISSOLVE_FRAMES = 7                 # 0.29 s at 24 fps: 3 frames before the cut, 4 after
PRE, POST = 3, 4
DISSOLVE = DISSOLVE_FRAMES / 24
MIN_SHOT, MAX_SHOT = 2.0, 4.0
CARD_MIN = 5.0

# Scenes: a 0.3 s dissolve only where the scene changes, hard cuts inside a scene.
SCENES = {"01": "A", "02": "A", "03": "A", "04": "B", "05": "B", "06": "C", "07": "C", "08": "D", "09": "D",
          "10": "E", "11": "E", "12": "E", "13": "E", "14": "F", "15": "F", "card": "G"}
# Which music section each shot lives in (index into MUSIC_SECTIONS); 13 starts on the bell.
SECTION_OF = {"01": 0, "02": 0, "03": 0, "04": 1, "05": 1, "06": 1, "07": 1,
              "08": 2, "09": 2, "10": 2, "11": 2, "12": 3, "13": 4, "14": 4, "15": 4}
BELL_SHOT = "13"
# 9:16 reframing for shots without a readable face: subject x (0-1) at the start and end of the shot.
REFRAME = {"01": (0.45, 0.55), "09": (0.52, 0.52), "10": (0.6, 0.62), "11": (0.5, 0.5), "15": (0.26, 0.74)}


def run(cmd):
    subprocess.run([str(c) for c in cmd], check=True)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


def fr(t):
    """Snap a time to the 24 fps frame grid."""
    return round(t * FPS) / FPS


# ---------------------------------------------------------------- beats
def analyse(music):
    """Beats, section marks and the hit: the moment the climax lands after the near-silent section, where the
    bell strikes and the edit hard-cuts into shot 13."""
    import librosa
    y, sr = librosa.load(str(music), sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    total = sum(s for _, s, _ in MUSIC_SECTIONS)
    marks = np.cumsum([0] + [s for _, s, _ in MUSIC_SECTIONS]) * (len(y) / sr) / total
    hop = int(0.05 * sr)
    rms = librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-9)
    times = librosa.times_like(rms, sr=sr, hop_length=hop)
    loud = np.median(db[(times >= marks[2]) & (times < marks[3])])       # choir section level
    win = (times >= marks[3]) & (times <= marks[4] + 2.0)
    quiet = times[win][np.argmin(db[win])]
    silent = db[win].min() < loud - 20
    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time", backtrack=True)
    if silent:
        # The track really goes quiet: the hit is the first return to near choir level after the quietest point.
        after = (times > quiet) & (db > loud - 8)
        hit = float(times[after][0]) if after.any() else float(marks[4])
    else:
        hit = float(marks[4])
    near = [o for o in onsets if abs(o - hit) <= 0.5]
    if near:
        hit = float(min(near, key=lambda o: abs(o - hit)))
    return {"tempo": float(np.atleast_1d(tempo)[0]), "beats": [float(b) for b in beats], "sections": marks.tolist(),
            "bell": hit, "silent": bool(silent), "length": len(y) / sr}


# ---------------------------------------------------------------- the "eyes open" moment
BELL_SFX = MUSIC / "sfx" / "bell_1.mp3"


def heartbeat(sr, t0, n=2, gap=1.55):
    """Synthesised 'lub-dub' heartbeats: pitched-down sub thumps with a soft transient."""
    out = []
    for k in range(n):
        for off, amp in ((0.0, 1.0), (0.26, 0.7)):
            t = np.arange(int(0.45 * sr)) / sr
            f = 38 + 55 * np.exp(-t * 22)
            body = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 9)
            click = np.random.default_rng(k).standard_normal(len(t)) * np.exp(-t * 90) * 0.08
            out.append((t0 + k * gap + off, amp * (body + click)))
    return out


def prepare_score(music, info, dst):
    """Music bus: the score dipped to near-silence before the hit (if the track does not already do it),
    two heartbeats in the silence and one temple bell exactly on the hit."""
    import librosa
    import soundfile as sf
    sr = 48000
    y, _ = librosa.load(str(music), sr=sr, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    n = y.shape[1]
    t = np.arange(n) / sr
    hit, s3 = info["bell"], info["sections"][3]
    gain = np.ones(n)
    if not info["silent"]:
        floor = 10 ** (-34 / 20)
        fade_end = min(s3 + 0.9, hit - 0.3)
        seg = (t >= s3) & (t < fade_end)
        gain[seg] = np.cos(np.linspace(0, np.pi / 2, seg.sum())) * (1 - floor) + floor
        gain[(t >= fade_end) & (t < hit)] = floor
    y = y * gain
    loud = np.sqrt(np.mean(y[:, int(info["sections"][2] * sr):int(info["sections"][3] * sr)] ** 2))
    for start, sig in heartbeat(sr, hit - 3.1):
        i = int(start * sr)
        y[:, i:i + len(sig)] += sig * loud * 2.2
    bell, _ = librosa.load(str(BELL_SFX), sr=sr, mono=True)
    on = librosa.onset.onset_detect(y=bell, sr=sr, units="samples", backtrack=True)
    bell = bell[(on[0] if len(on) else 0):]
    bell = bell / (np.sqrt(np.mean(bell[: sr // 2] ** 2)) + 1e-9) * loud * 1.1
    i = int(hit * sr)
    m = min(len(bell), n - i)
    y[:, i:i + m] += bell[:m]
    peak = np.abs(y).max()
    if peak > 0.98:
        y *= 0.98 / peak
    sf.write(dst, y.T, sr, subtype="PCM_24")
    return dst


# ---------------------------------------------------------------- cut plan
def plan_cuts(info, clip_len):
    """Choose cut times on beats with dynamic programming.

    Cut k is the start of shot k (k = 0..14) and cut 15 is the start of the end card. Cut 0 = 0, the cut into
    shot 13 is the bell, every other cut is on a detected beat. Each shot lasts 2-4 s (less if its clip is shorter
    after dissolve handles), the end card gets at least 5 s, and the cuts stay as close as possible to an even
    spread of each shot group over its music section.
    """
    ids = list(SHOTS)
    n = len(ids)
    sec = info["sections"]
    bell = info["bell"]
    card_start_ideal = min(info["length"] - CARD_MIN - 1.0, bell + 3 * 3.6)
    ideal = []
    for k, sid in enumerate(ids):
        s = SECTION_OF[sid]
        group = [x for x in ids if SECTION_OF[x] == s]
        a, b = sec[s], sec[s + 1]
        if s == 3:
            a, b = bell - 3.5, bell
        if s == 4:
            a, b = bell, card_start_ideal
        ideal.append(a + (b - a) * group.index(sid) / len(group))
    ideal.append(card_start_ideal)

    def dissolve_after(k):   # between shot k and k+1 (or the card)
        nxt = ids[k + 1] if k + 1 < n else "card"
        return SCENES[ids[k]] != SCENES[nxt]

    def max_len(k):
        handles = (DISSOLVE / 2 if k > 0 and dissolve_after(k - 1) else 0) + (DISSOLVE / 2 if dissolve_after(k) else 0)
        return min(MAX_SHOT, clip_len[ids[k]] - handles - 1 / FPS)

    beats = [fr(b) for b in info["beats"]]
    bell = fr(bell)
    cands = [[0.0]] + [[bell] if ids[k] == BELL_SHOT else beats for k in range(1, n)] + \
            [[b for b in beats if b <= info["length"] - CARD_MIN]]
    # best[k][t] = (cost, previous cut) for cut k landing at t
    best = [{0.0: (0.0, None)}]
    for k in range(1, n + 1):
        cur = {}
        for t in cands[k]:
            for tp, (cost, _) in best[k - 1].items():
                d = t - tp
                if MIN_SHOT - 1e-6 <= d <= max_len(k - 1) + 1e-6:
                    c = cost + (t - ideal[k]) ** 2
                    if t not in cur or c < cur[t][0]:
                        cur[t] = (c, tp)
        if not cur:
            raise SystemExit(f"No beat-aligned cut plan fits at cut {k} ({ids[k - 1]}); check the track's beats.")
        best.append(cur)
    t = min(best[n], key=lambda x: best[n][x][0])
    cuts = [t]
    for k in range(n, 0, -1):
        t = best[k][t][1]
        cuts.append(t)
    cuts = cuts[::-1]
    return [{"id": ids[k], "start": cuts[k], "end": cuts[k + 1], "dissolve_out": dissolve_after(k)} for k in range(n)]


# ---------------------------------------------------------------- end card
def end_card_images(bg_frame, size, dst_dir):
    """Background (last frame, blurred and darkened) and two transparent text layers."""
    w, h = size
    bg = Image.open(bg_frame).convert("RGB")
    scale = max(w / bg.width, h / bg.height)
    bg = bg.resize((round(bg.width * scale), round(bg.height * scale)), Image.LANCZOS)
    bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
    bg = bg.filter(ImageFilter.GaussianBlur(w / 90))
    bg = Image.blend(bg, Image.new("RGB", (w, h), (8, 6, 10)), 0.62)
    bg.save(dst_dir / "card_bg.png")
    gold, glow = (243, 214, 150), (255, 170, 60)
    vertical = h > w
    lines = (["Same Soul.", "A Different Form.", "Always Divine."] if vertical
             else ["Same Soul. A Different Form.", "Always Divine."])
    fs = int(w * (0.062 if vertical else 0.034))
    font = ImageFont.truetype(str(FONT_LIGHT), fs)
    big = ImageFont.truetype(str(FONT), int(fs * (0.95 if vertical else 1.25)))

    def layer(texts, fnt, y0, gap, name, tracking=0):
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        y = y0
        for t in texts:
            tw = d.textlength(t, font=fnt) + tracking * (len(t) - 1)
            x = (w - tw) / 2
            for ch in t:
                d.text((x, y), ch, font=fnt, fill=gold + (255,))
                x += d.textlength(ch, font=fnt) + tracking
            y += gap
        g = im.filter(ImageFilter.GaussianBlur(fs * 0.35))
        tint = Image.new("RGBA", (w, h), glow + (0,))
        tint.putalpha(g.getchannel("A").point(lambda a: int(a * 0.55)))
        out = Image.alpha_composite(tint, im)
        out.save(dst_dir / name)

    gap = int(fs * 1.55)
    top = h * (0.36 if vertical else 0.36)
    layer(lines, font, top, gap, "card_t1.png")
    rule_y = top + gap * len(lines) + fs * 0.35
    layer(["HAR HAR MAHADEV"], big, rule_y + fs * 0.5, 0, "card_t2.png", tracking=int(fs * (0.12 if vertical else 0.18)))
    # Thin gold divider between the tagline and HAR HAR MAHADEV, drawn onto the second layer.
    t2 = Image.open(dst_dir / "card_t2.png")
    d = ImageDraw.Draw(t2)
    half = w * (0.12 if vertical else 0.07)
    d.line([(w / 2 - half, rule_y), (w / 2 + half, rule_y)], fill=gold + (200,), width=max(2, w // 900))
    t2.save(dst_dir / "card_t2.png")


def render_card(bg_frame, size, seconds, dst):
    tmp = dst.parent / (dst.stem + "_imgs")
    tmp.mkdir(exist_ok=True)
    end_card_images(bg_frame, size, tmp)
    w, h = size
    fc = (f"[0:v]scale={int(w * 1.06)}:-2,zoompan=z='min(1.06,1+0.0006*on)':d=1:s={w}x{h}:fps={FPS},"
          f"format=yuv420p[bg];"
          f"[1:v]format=rgba,fade=t=in:st=0.5:d=1.4:alpha=1[t1];"
          f"[2:v]format=rgba,fade=t=in:st=2.0:d=1.4:alpha=1[t2];"
          f"[bg][t1]overlay=0:0:format=auto[b1];[b1][t2]overlay=0:0:format=auto,"
          f"fade=t=out:st={seconds - 1.0:.2f}:d=1.0,format=yuv420p,setsar=1[v]")
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-framerate", FPS, "-t", f"{seconds:.3f}", "-i", tmp / "card_bg.png",
         "-loop", "1", "-framerate", FPS, "-t", f"{seconds:.3f}", "-i", tmp / "card_t1.png",
         "-loop", "1", "-framerate", FPS, "-t", f"{seconds:.3f}", "-i", tmp / "card_t2.png",
         "-filter_complex", fc, "-map", "[v]", "-r", FPS, "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", dst])
    return dst


# ---------------------------------------------------------------- 9:16 reframing
def subject_x(clip, t0, t1, sid):
    """Normalised subject x at the start and end of the used part of a clip (face-tracked where possible)."""
    if sid in REFRAME:
        return REFRAME[sid]
    import cv2
    from film.face import _detect
    xs = []
    for t in (t0 + 0.1, t1 - 0.1):
        png = BUILD / "reframe.png"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", clip, "-frames:v", "1", png])
        im = cv2.imread(str(png))
        found, pad = _detect(im)
        if found:
            centres = [((f.bbox[0] + f.bbox[2]) / 2 - pad) / im.shape[1] for f in found]
            xs.append(float(np.mean(centres)) if sid == "08" else centres[0])   # 08: frame the whole group
    if not xs:
        return 0.5, 0.5
    return xs[0], xs[-1]


# ---------------------------------------------------------------- render
GRADE = ("colorbalance=rs=-0.07:gs=-0.01:bs=0.08:rm=0.02:gm=0.0:bm=-0.03:rh=0.07:gh=0.02:bh=-0.07,"
         "eq=contrast=1.06:saturation=1.07:gamma=0.98,vignette=angle=PI/5")
GRAIN = "noise=c0s=6:c0f=t+u"


def render(cuts, picks, music, info, vertical, out):
    BUILD.mkdir(exist_ok=True)
    W, H = (1080, 1920) if vertical else (1920, 1080)
    # Everything below is in whole frames so every cut lands exactly on its planned (beat) frame.
    K = [round(c["start"] * FPS) for c in cuts] + [round(cuts[-1]["end"] * FPS)]
    total = round(info["length"] * FPS)
    card_frames = total - K[-1] + PRE
    last = CLIPS / f"{cuts[-1]['id']}_t{picks[cuts[-1]['id']]}.mp4"
    bg = BUILD / "card_src.png"
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.3", "-i", last, "-frames:v", "1", bg])
    card = render_card(bg, (W, H), card_frames / FPS, BUILD / f"card_{'v' if vertical else 'h'}.mp4")

    inputs, vf, af = [], [], []
    segs = []   # (clip, first frame, frame count, dissolve in, id)
    for k, c in enumerate(cuts):
        clip = CLIPS / f"{c['id']}_t{picks[c['id']]}.mp4"
        dis_in = k > 0 and cuts[k - 1]["dissolve_out"]
        n = K[k + 1] - K[k] + (PRE if dis_in else 0) + (POST if c["dissolve_out"] else 0)
        avail = int(duration(clip) * FPS) - 1
        # Shot 13 starts on its first frame (eyes already open on the bell); others sit a little into the clip.
        a = 0 if c["id"] == "13" else max(0, min(int((avail - n) * 0.35), avail - n))
        segs.append((clip, a, n, dis_in, c["id"]))
    segs.append((card, 0, card_frames, True, "card"))

    for i, (clip, a, n, dis_in, sid) in enumerate(segs):
        inputs += ["-i", clip]
        v = f"[{i}:v]fps={FPS},trim=start_frame={a}:end_frame={a + n},setpts=PTS-STARTPTS,"
        if sid == "card":
            v += "format=yuv420p,setsar=1,settb=AVTB"
        elif vertical:
            x0, x1 = subject_x(clip, a / FPS, (a + n) / FPS, sid)
            cw = round(1080 * 9 / 16 / 2) * 2   # 608 px of the 1920x1080 frame
            xexpr = f"'max(0,min(iw-{cw},({x0:.3f}+({x1 - x0:.3f})*t/{n / FPS:.4f})*iw-{cw}/2))'"
            v += f"scale=1920:1080,crop={cw}:1080:{xexpr}:0,scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1,settb=AVTB"
        else:
            v += f"scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1,settb=AVTB"
        vf.append(v + f"[v{i}]")
        a0, a1, d = a / FPS, (a + n) / FPS, n / FPS
        if sid == "card":
            af.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.6f}[a{i}]")
        else:
            af.append(f"[{i}:a]atrim=start={a0:.6f}:end={a1:.6f},asetpts=PTS-STARTPTS,aresample=48000,"
                      f"aformat=channel_layouts=stereo,apad=whole_dur={d:.6f},atrim=0:{d:.6f},"
                      f"afade=t=in:d=0.02,afade=t=out:st={d - 0.02:.6f}:d=0.02[a{i}]")

    # Chain: xfade/acrossfade at dissolves, concat at hard cuts.
    v, a_, t = "[v0]", "[a0]", segs[0][2]
    for i in range(1, len(segs)):
        n = segs[i][2]
        if segs[i][3]:
            vf.append(f"{v}[v{i}]xfade=transition=fade:duration={DISSOLVE:.6f}:offset={(t - DISSOLVE_FRAMES) / FPS:.6f},"
                      f"settb=AVTB[vc{i}]")
            af.append(f"{a_}[a{i}]acrossfade=d={DISSOLVE:.6f}:c1=tri:c2=tri[ac{i}]")
            t += n - DISSOLVE_FRAMES
        else:
            vf.append(f"{v}[v{i}]concat=n=2:v=1:a=0,settb=AVTB[vc{i}]")
            af.append(f"{a_}[a{i}]concat=n=2:v=0:a=1[ac{i}]")
            t += n
        v, a_ = f"[vc{i}]", f"[ac{i}]"
    t /= FPS
    vf.append(f"{v}{GRADE},{GRAIN},format=yuv420p[vout]")

    # Mix: music on top; Seedance/Kling ambience underneath, -9 dB and side-chain ducked by the music.
    m = len(segs)
    inputs += ["-i", music]
    af.append(f"[{m}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{t:.4f},asplit=2[mus][key]")
    af.append(f"{a_}volume=-9dB[amb]")
    af.append("[amb][key]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=450:makeup=1[duck]")
    af.append("[mus][duck]amix=inputs=2:duration=first:normalize=0[mix]")
    fc = ";".join(vf + af)
    premaster = BUILD / (out.stem + "_premaster.mov")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[vout]", "-map", "[mix]",
         "-t", f"{t:.4f}", "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-tune", "grain",
         "-c:a", "pcm_s24le", premaster])
    master_audio(premaster, out)
    return out


def master_audio(src, out, target=-14.0, ceiling=-1.0):
    """Video: 2-pass H.264 sized to stay under ~46 MB (fits in git). Audio: gain to the target integrated
    loudness, then a 4x-oversampled limiter so the true peak stays under the ceiling; re-measured and corrected."""
    dur = duration(src)
    vbit = int((46 * 8 * 1024 * 1024 / dur - 256000) * 0.97)
    common = ["-c:v", "libx264", "-preset", "slow", "-tune", "grain", "-profile:v", "high", "-pix_fmt", "yuv420p",
              "-b:v", str(vbit), "-maxrate", str(int(vbit * 1.5)), "-bufsize", str(vbit * 2)]
    log = BUILD / (out.stem + "_2pass")
    video = BUILD / (out.stem + "_video.mp4")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, *common, "-pass", "1", "-passlogfile", log, "-an", "-f", "mp4",
         "/dev/null"])
    run(["ffmpeg", "-v", "error", "-y", "-i", src, *common, "-pass", "2", "-passlogfile", log, "-an", video])
    wav = BUILD / (out.stem + "_mix.wav")
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-c:a", "pcm_s24le", wav])
    gain = target - loudness(wav)[0]
    limit = 10 ** ((ceiling - 0.6) / 20)       # headroom for AAC encoding overshoot
    aac = BUILD / (out.stem + "_audio.m4a")
    for _ in range(6):
        af = (f"volume={gain:.2f}dB,aresample=192000,alimiter=limit={limit:.4f}:attack=2:release=80:level=false,"
              f"aresample=48000")
        run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", af, "-c:a", "aac", "-b:a", "256k", "-ar", "48000", aac])
        i, tp = loudness(aac)
        if abs(i - target) <= 0.2 and tp <= ceiling:
            break
        gain += target - i
        if tp > ceiling:
            limit *= 10 ** ((ceiling - tp - 0.1) / 20)
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", aac, "-map", "0:v", "-map", "1:a", "-c", "copy",
         "-movflags", "+faststart", out])


def loudness(path):
    """(integrated LUFS, true peak dBTP) measured with ffmpeg's EBU R128 meter."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rindex("Summary:"):]
    i = float(summary.split("I:")[1].split("LUFS")[0])
    tp = float(summary.split("Peak:")[1].split("dBFS")[0])
    return i, tp
