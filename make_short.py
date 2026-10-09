#!/usr/bin/env python3
"""
The 30 s native 9:16 Reel of "Shiv & Parvati" (plan: film/short30.py).

  python make_short.py keyframes   new 9:16 stills: storm prayer (70), seasons (71-74), Shiva's gaze (75), blessing (76)
  python make_short.py video       Kling clips for them -> clips/7N_t1.mp4
  python make_short.py music       the 30 s score (Eleven Music v2.5) + a damaru accent (ElevenLabs SFX)
  python make_short.py edit        both openings -> shiv_parvati_30s_storm.mp4 and shiv_parvati_30s_seasons.mp4

Reuses make_video.py (fal, Nano Banana Pro, Kling), make_devotion.py (best-of face scoring), film/edit.py
(face-tracked 9:16 crops, grade, master).
"""
import argparse
import concurrent.futures as cf
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import make_devotion as md
import make_video as mv
from film import short30 as sh
from film.shots import PARVATI_LOCK, SAGES, SHIVA, STYLE

KF, CLIPS, BUILD = mv.KF, mv.CLIPS, mv.ROOT / "build"
FPS, W, H = 24, 1080, 1920
VSTYLE = STYLE.replace("16:9 widescreen, ", "vertical 9:16, ")


# ---------------------------------------------------------------- keyframes
def refs_and_notes(refs):
    paths, notes = [], []
    for r in refs:
        first = len(paths) + 1
        if r == "parvati":
            paths += md.CROPS
            notes.append(f"Images {first}-{len(paths)} are identity photos of the young woman (Parvati): her face must "
                         "be exactly this person.")
        elif r in ("shiva", "sages"):
            paths.append(md.HEROES / f"{r}.png")
            notes.append(f"Image {first} is the character reference for {'Shiva' if r == 'shiva' else 'the rishis'}; "
                         "keep them exactly on-model.")
        elif r.startswith("kf:"):
            paths.append(KF / f"{r[3:]}.png")
            notes.append(f"Image {first} is an earlier shot of the same story: match its costumes, light and world.")
    return paths, " ".join(notes)


def keyframe(sid):
    refs, desc, _, _, _, who = sh.SHOTS[sid]
    if refs[0].startswith("base:"):
        base = KF / f"{refs[0][5:]}.png"
        paths, notes = refs_and_notes(refs[1:])
        paths = [base] + paths
        notes = notes.replace("Images 1-4", "Images 2-5")
        prompt = (f"Image 1 is a vertical film frame. {notes} Edit image 1: keep the camera, framing, composition, her "
                  f"exact position and pose (eyes closed, hands in namaste), her face, crimson sari and jewellery "
                  f"exactly the same, and change only the season and what it does to her: {desc} {VSTYLE}")
    else:
        paths, notes = refs_and_notes(refs)
        locks = (PARVATI_LOCK + " " if "parvati" in refs else "") + (SHIVA + ". " if "shiva" in refs else "") + \
                (SAGES + ". " if "sages" in refs else "")
        prompt = f"{notes} {locks}Create a new photoreal vertical 9:16 film frame: {desc} {VSTYLE}"
    md.best_of(sid, lambda p, i: mv.still(p, prompt, paths, seed=70000 + 100 * int(sid) + i, aspect="9:16"), who)


def make_keyframes():
    first = [s for s in sh.SHOTS if not sh.SHOTS[s][0][0].startswith("base:")]
    later = [s for s in sh.SHOTS if s not in first]
    for batch in (first, later):
        with cf.ThreadPoolExecutor(6) as ex:
            list(ex.map(keyframe, batch))
    ids = list(sh.SHOTS)
    sheet = Image.new("RGB", (len(ids) * 300, 533), (16, 16, 16))
    for i, sid in enumerate(ids):
        sheet.paste(Image.open(KF / f"{sid}.png").convert("RGB").resize((300, 533), Image.LANCZOS), (i * 300, 0))
    sheet.save(BUILD / "short30_keyframes.jpg", quality=88)
    print("sheet ->", BUILD / "short30_keyframes.jpg")


# ---------------------------------------------------------------- video
def clip(sid):
    dst = CLIPS / f"{sid}_t1.mp4"
    if dst.exists():
        return dst
    _, _, action, sound, secs, _ = sh.SHOTS[sid]
    start = CLIPS / f"{sid}_start.jpg"
    Image.open(KF / f"{sid}.png").convert("RGB").resize((W, H), Image.LANCZOS).save(start, quality=95)
    args = {"start_image_url": mv.upload(start), "duration": secs, "generate_audio": True, "negative_prompt": mv.VIDEO_NEG,
            "prompt": f"{action} {mv.VIDEO_LOOK} Audio: {sound}; ambience and sound effects only, no music, no speech."}
    if "@Element1" in action:
        args["elements"] = md.parvati_element()
    print(f"[{sid}] {secs}s", flush=True)
    mv.download(mv.fal().subscribe(mv.VIDEO_MODEL, arguments=args)["video"]["url"], dst)
    mv.clip_frames(dst, CLIPS / f"{sid}_t1_frames.jpg")
    return dst


def make_video():
    with cf.ThreadPoolExecutor(7) as ex:
        list(ex.map(clip, sh.SHOTS))


# ---------------------------------------------------------------- music
def make_music(versions):
    mv.MUSIC.mkdir(exist_ok=True)

    def one(v):
        dst = mv.MUSIC / f"short30_{v}.mp3"
        if not dst.exists():
            flavour = {"A": ["bansuri and strings led, warm"], "B": ["santoor and soft strings, luminous"]}[v]
            plan = {"chunks": [{"text": "", "duration_ms": int(sec * 1000), "positive_styles": sh.MUSIC_GLOBAL + st + flavour,
                                "negative_styles": sh.MUSIC_NEGATIVE} for _, sec, st in sh.MUSIC_SECTIONS]}
            res = mv.fal().subscribe(mv.MUSIC_MODEL, arguments={"composition_plan": plan, "output_format": "mp3_48000_192"})
            mv.download(res["audio"]["url"], dst)
        print("music ->", dst)
    jobs = list(versions)
    with cf.ThreadPoolExecutor(3) as ex:
        list(ex.map(one, jobs))
    sfx = mv.MUSIC / "sfx" / "damaru.mp3"
    if not sfx.exists():
        res = mv.fal().subscribe("fal-ai/elevenlabs/sound-effects/v2",
                                 arguments={"text": sh.DAMARU_PROMPT, "duration_seconds": 2.5, "prompt_influence": 0.6})
        mv.download(res["audio"]["url"], sfx)
    print("sfx ->", sfx)


def prepare_score(music, dst):
    """Score with a gentle pull-back before his eyes open and one damaru accent as his gaze settles."""
    import librosa
    import numpy as np
    import soundfile as sf
    sr = 48000
    y, _ = librosa.load(str(music), sr=sr, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    t = np.arange(y.shape[1]) / sr
    a, b, db = sh.DIP
    floor = 10 ** (db / 20)
    g = np.ones_like(t)
    down = (t >= a) & (t < a + 0.6)
    g[down] = 1 - (1 - floor) * (0.5 - 0.5 * np.cos(np.pi * (t[down] - a) / 0.6))
    g[(t >= a + 0.6) & (t < b)] = floor
    up = (t >= b) & (t < b + 0.4)
    g[up] = floor + (1 - floor) * (t[up] - b) / 0.4
    y = y * g
    loud = np.sqrt(np.mean(y[:, int(8 * sr):int(16 * sr)] ** 2))
    d, _ = librosa.load(str(mv.MUSIC / "sfx" / "damaru.mp3"), sr=sr, mono=True)
    on = librosa.onset.onset_detect(y=d, sr=sr, units="samples", backtrack=True)
    d = d[(on[0] if len(on) else 0):]
    d = d / (np.abs(d).max() + 1e-9) * loud * 3.0
    i = int(sh.DAMARU_AT * sr)
    m = min(len(d), y.shape[1] - i)
    y[:, i:i + m] += d[:m]
    peak = np.abs(y).max()
    if peak > 0.98:
        y *= 0.98 / peak
    sf.write(dst, y.T, sr, subtype="PCM_24")
    return dst


# ---------------------------------------------------------------- edit
def text_layer(dst):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fs = 96
    while max(d.textlength(l, font=ImageFont.truetype(str(mv.ROOT / "assets/fonts/Cinzel-700.ttf"), fs))
              for l in sh.TEXT) > W * 0.86:
        fs -= 2
    font = ImageFont.truetype(str(mv.ROOT / "assets/fonts/Cinzel-700.ttf"), fs)
    y = int(H * 0.70)
    for line in sh.TEXT:
        x = (W - d.textlength(line, font=font)) / 2
        d.text((x, y), line, font=font, fill=(255, 241, 210, 255))
        y += int(fs * 1.35)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.85)))
    glow = Image.new("RGBA", (W, H), (255, 180, 80, 0))
    glow.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.35)))
    out = Image.alpha_composite(Image.alpha_composite(shadow, glow), im)
    out.save(dst)
    return dst


def render(opening, music, out):
    from film import edit
    edit.REFRAME.update(sh.REFRAME)
    picks = mv.load_picks()
    ins, vf, af = [], [], []
    tl = list(sh.TIMELINE)
    for i, (sid, a, b) in enumerate(tl):
        d = b - a
        n = round(b * FPS) - round(a * FPS)
        if i == 0 and opening == "seasons":
            src, speed = sh.OPENING_SEASONS
            ins += ["-i", str(CLIPS / f"{src}_t1.mp4")]
            vf.append(f"[{i}:v]setpts=PTS/{speed},fps={FPS},trim=end_frame={n},setpts=PTS-STARTPTS,scale=1920:1080,"
                      f"crop=608:1080:{round(0.52 * 1920 - 304)}:0,scale={W}:{H}:flags=lanczos,format=yuv420p,setsar=1[v{i}]")
            af.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{n / FPS:.6f}[a{i}]")
            continue
        native = sid in sh.NATIVE
        path = CLIPS / (f"{sh.NATIVE[sid]}_t1.mp4" if native else f"{sid}_t{picks[sid]}.mp4")
        t0 = sh.IN_POINT.get(sid, 0.3)
        ins += ["-i", str(path)]
        v = f"[{i}:v]fps={FPS},trim=start_frame={round(t0 * FPS)}:end_frame={round(t0 * FPS) + n},setpts=PTS-STARTPTS,"
        if native:
            v += f"scale={W}:{H}:flags=lanczos"
        else:
            x0, x1 = edit.subject_x(path, t0, t0 + d, sid)
            xe = f"'max(0,min(iw-608,({x0:.3f}+({x1 - x0:.3f})*t/{d:.4f})*iw-304))'"
            v += f"scale=1920:1080,crop=608:1080:{xe}:0,scale={W}:{H}:flags=lanczos"
        vf.append(v + f",format=yuv420p,setsar=1[v{i}]")
        af.append(f"[{i}:a]atrim=start={t0:.6f}:end={t0 + n / FPS:.6f},asetpts=PTS-STARTPTS,aresample=48000,"
                  f"aformat=channel_layouts=stereo,apad=whole_dur={n / FPS:.6f},atrim=0:{n / FPS:.6f},"
                  f"afade=t=in:d=0.02,afade=t=out:st={n / FPS - 0.02:.6f}:d=0.02[a{i}]")
    k = len(tl)
    total = round(tl[-1][2] * FPS) / FPS
    vf.append("".join(f"[v{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[vc]")
    af.append("".join(f"[a{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1[amb0]")
    txt = text_layer(BUILD / "short30_text.png")
    ins += ["-loop", "1", "-framerate", str(FPS), "-t", f"{total:.3f}", "-i", str(txt)]
    vf.append(f"[{k}:v]format=rgba,fade=t=in:st={sh.TEXT_AT}:d=0.7:alpha=1[tx]")
    vf.append(f"[vc]{edit.GRADE},{edit.GRAIN}[vg];[vg][tx]overlay=0:0:format=auto,format=yuv420p[vout]")
    ins += ["-i", str(music)]
    af.append(f"[{k + 1}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.4f},"
              f"afade=t=out:st={total - 1.2:.3f}:d=1.2,asplit=2[mus][key]")
    af.append("[amb0]volume=-8dB[amb]")
    af.append("[amb][key]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=450:makeup=1[duck]")
    af.append("[mus][duck]amix=inputs=2:duration=first:normalize=0,highpass=f=35[mix]")
    pre = BUILD / f"{out.stem}_premaster.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(vf + af), "-map", "[vout]",
                    "-map", "[mix]", "-t", f"{total:.4f}", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
                    "-tune", "grain", "-c:a", "pcm_s24le", str(pre)], check=True)
    edit.master_audio(pre, out)
    return out


def make_edit(version):
    from film import edit
    score = prepare_score(mv.MUSIC / f"short30_{version}.mp3", BUILD / "score_short30.wav")
    for opening in ("storm", "seasons"):
        out = render(opening, score, mv.ROOT / f"shiv_parvati_30s_{opening}.mp4")
        lufs, tp = edit.loudness(out)
        # Phone-speaker proxy: the mix with everything under 200 Hz removed should lose little loudness.
        phone = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-af",
                                "highpass=f=200,highpass=f=200,ebur128", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        ph = float(phone[phone.rindex("Summary:"):].split("I:")[1].split("LUFS")[0])
        print(f"{out.name}: {edit.duration(out):.2f}s, {out.stat().st_size / 1e6:.1f} MB, {lufs:.1f} LUFS, "
              f"{tp:.1f} dBTP, above 200 Hz {ph:.1f} LUFS")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["keyframes", "video", "music", "edit"])
    ap.add_argument("--versions", default="A,B")
    ap.add_argument("--music", default="A")
    a = ap.parse_args()
    if a.stage == "keyframes":
        make_keyframes()
    elif a.stage == "video":
        make_video()
    elif a.stage == "music":
        make_music([v for v in a.versions.split(",") if v])
    else:
        make_edit(a.music)


if __name__ == "__main__":
    main()
