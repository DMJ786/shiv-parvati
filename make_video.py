#!/usr/bin/env python3
"""
Shiv & Parvati — ~55 s cinematic AI film, built in stages on fal.ai.

  python make_video.py crops        face refs from parvati_sheet.png -> refs/
  python make_video.py heroes       Shiva + sages reference images -> heroes/
  python make_video.py keyframes    one 16:9 still per shot (Nano Banana Pro), face-scored -> keyframes/
  python make_video.py grid         contact sheet of all keyframes -> keyframes/grid.jpg
  python make_video.py video --shots 01 --takes 1   animate keyframes (Kling v3 Pro) -> clips/NN_tK.mp4
  python make_video.py music        2-3 versions of the ~60 s score (Eleven Music) -> music/
  python make_video.py edit --music A   beat-cut, grade, end card, mix, master -> shiv_parvati_16x9.mp4 / _9x16.mp4

Every stage is resumable: finished files are skipped. Delete a file (or pass --redo 03,07) to regenerate it.
Setup: pip install -r requirements.txt, ffmpeg on PATH, export FAL_KEY=...
"""
import argparse
import concurrent.futures as cf
import json
import os
import sys
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from film.shots import (HEROES, MUSIC_GLOBAL, MUSIC_NEGATIVE, MUSIC_SECTIONS, MUSIC_VERSIONS, PARVATI_LOCK,
                         SHOTS, STYLE)

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "parvati_sheet.png"
REFS, HERO_DIR, KF = ROOT / "refs", ROOT / "heroes", ROOT / "keyframes"
CLIPS, MUSIC = ROOT / "clips", ROOT / "music"

IMAGE_MODEL = os.getenv("IMAGE_MODEL", "fal-ai/nano-banana-pro/edit")
IMAGE_T2I = os.getenv("IMAGE_T2I", "fal-ai/nano-banana-pro")
# Mean ArcFace cosine vs the refs. The refs score 0.53-0.76 against each other, other people score ~0.0,
# and profile / eyes-closed frames of the right person land around 0.45-0.55.
FACE_MIN = 0.45
FACE_TRIES = 4
FACE_SHIVA = ("11", "12", "13")   # Shiva shots where his face is readable

VIDEO_MODEL = os.getenv("VIDEO_MODEL", "fal-ai/kling-video/v3/pro/image-to-video")
CLIP_SECONDS = os.getenv("CLIP_SECONDS", "4")
VIDEO_LOOK = ("Cinematic, photoreal, smooth natural motion, epic Indian mythological film. Keep every character's face, "
              "costume and the lighting exactly as in the start frame.")
MUSIC_MODEL = os.getenv("MUSIC_MODEL", "elevenlabs/music/v2.5")
VIDEO_NEG = "blur, distortion, morphing face, extra limbs, flicker, text, subtitles, watermark, low quality"

# Crops of parvati_sheet.png (1122x1402), clear of the sheet's captions and calligraphy.
CROPS = {
    "p01": (148, 200, 483, 640),    # 01 hero portrait, frontal
    "p03": (843, 262, 1033, 452),   # 03 tapasya, eyes closed
    "p04": (20, 852, 280, 1112),    # 04 side profile
    "p06": (615, 852, 870, 1107),   # 06 flowing hair, three-quarter
}


def fal():
    import fal_client
    if not os.getenv("FAL_KEY"):
        sys.exit("Set FAL_KEY first.")
    return fal_client


_uploaded = {}
def upload(path):
    path = str(path)
    if path not in _uploaded:
        _uploaded[path] = fal().upload_file(path)
    return _uploaded[path]


def download(url, dst):
    tmp = Path(str(dst) + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dst)
    return dst


# ---------------------------------------------------------------- crops
def make_crops():
    REFS.mkdir(exist_ok=True)
    sheet = Image.open(SHEET).convert("RGB")
    for name, box in CROPS.items():
        dst = REFS / f"{name}.png"
        if dst.exists():
            continue
        im = sheet.crop(box)
        scale = 1024 / max(im.size)
        im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS).save(dst)
        print("crop ->", dst)


# ---------------------------------------------------------------- stills
def still(dst, prompt, ref_paths, seed=None):
    args = {"prompt": prompt, "aspect_ratio": "16:9", "resolution": "2K", "output_format": "png",
            "safety_tolerance": "5"}
    if seed is not None:
        args["seed"] = seed
    if ref_paths:
        args["image_urls"] = [upload(p) for p in ref_paths]
    res = fal().subscribe(IMAGE_MODEL if ref_paths else IMAGE_T2I, arguments=args)
    return download(res["images"][0]["url"], dst)


def make_heroes(redo=()):
    HERO_DIR.mkdir(exist_ok=True)
    def one(name):
        dst = HERO_DIR / f"{name}.png"
        if dst.exists() and name not in redo:
            return
        still(dst, HEROES[name]["prompt"] + STYLE, [])
        print("hero ->", dst)
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(one, HEROES))


def shot_refs(sid):
    """Reference image paths for a shot and a sentence telling the model what each one is."""
    paths, notes = [], []
    for r in SHOTS[sid][0]:
        first = len(paths) + 1
        if r == "parvati":
            paths += [REFS / f"{n}.png" for n in CROPS]
            notes.append(f"Images {first}-{len(paths)} are identity photos of the woman (Parvati).")
        elif r in HEROES:
            paths.append(HERO_DIR / f"{r}.png")
            who = "Shiva" if r == "shiva" else "the three rishis"
            notes.append(f"Image {first} is the character reference for {who}; keep them exactly on-model.")
        elif r.startswith("kf:"):
            paths.append(KF / f"{r[3:]}.png")
            notes.append(f"Image {first} is the previous shot of this scene; match its lighting, colour and setting.")
    return paths, " ".join(notes)


def keyframe_prompt(sid):
    refs, desc = SHOTS[sid][0], SHOTS[sid][1]
    _, notes = shot_refs(sid)
    lock = PARVATI_LOCK + " " if "parvati" in refs else ""
    return f"{notes} {lock}Create a new photoreal 16:9 film frame: {desc} {STYLE}".strip()


def load_scores():
    f = KF / "scores.json"
    return json.loads(f.read_text()) if f.exists() else {}


def identity(sid):
    """Whose face to score in a shot (None where no face is readable: landscapes, macro, silhouettes)."""
    refs = SHOTS[sid][0]
    if "parvati" in refs:
        return "parvati"
    if "shiva" in refs and sid in FACE_SHIVA:
        return "shiva"
    return None


def make_keyframe(sid, redo=()):
    from film.face import score
    dst = KF / f"{sid}.png"
    if dst.exists() and sid not in redo:
        return
    paths, _ = shot_refs(sid)
    prompt = keyframe_prompt(sid)
    who = identity(sid)
    cands = []
    for attempt in range(FACE_TRIES if who else 1):
        cand = KF / f"{sid}_try{attempt + 1}.png"
        still(cand, prompt, paths, seed=1000 * int(sid) + attempt)
        cands.append((cand, score(cand, who) if who else None))
        print(f"  [{sid}] try {attempt + 1}: face {cands[-1][1]}")
        if not who or (cands[-1][1] and cands[-1][1][0] >= FACE_MIN):
            break
    key = lambda c: c[1][0] if c[1] else -1
    best = max(cands, key=key)
    best[0].replace(dst)
    for f in KF.glob(f"{sid}_try*.png"):
        f.unlink()
    return sid, best[1]


def make_keyframes(redo=()):
    KF.mkdir(exist_ok=True)
    scores = load_scores()
    first = [s for s in SHOTS if not any(r.startswith("kf:") for r in SHOTS[s][0])]
    later = [s for s in SHOTS if s not in first]
    for batch in (first, later):
        with cf.ThreadPoolExecutor(6) as ex:
            for r in ex.map(lambda s: make_keyframe(s, redo), batch):
                if r:
                    scores[r[0]] = r[1]
                    (KF / "scores.json").write_text(json.dumps(scores, indent=1, sort_keys=True))
    make_grid()


def make_grid():
    scores = load_scores()
    tw, th, pad, cols = 640, 360, 12, 3
    ids = [s for s in SHOTS if (KF / f"{s}.png").exists()]
    rows = -(-len(ids) // cols)
    grid = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (16, 16, 16))
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22) if _has_font() else ImageFont.load_default()
    for i, sid in enumerate(ids):
        im = Image.open(KF / f"{sid}.png").convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)
        grid.paste(im, (x, y))
        s = scores.get(sid)
        label = sid + (f"  face {s[0]:.2f}" if s else "")
        d = ImageDraw.Draw(grid)
        d.rectangle([x, y, x + 12 + 13 * len(label), y + 32], fill=(0, 0, 0))
        d.text((x + 6, y + 4), label, fill=(255, 220, 140), font=font)
    grid.save(KF / "grid.jpg", quality=88)
    print("grid ->", KF / "grid.jpg")


def _has_font():
    try:
        ImageFont.truetype("DejaVuSans-Bold.ttf", 10)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- video
def video_prompt(sid):
    _, _, action, sound = SHOTS[sid]
    who = "@Element1 " if "parvati" in SHOTS[sid][0] else ""
    return f"{who}{action} {VIDEO_LOOK} Audio: {sound}; ambience and sound effects only — no music, no speech."


def make_clip(sid, take):
    dst = CLIPS / f"{sid}_t{take}.mp4"
    if dst.exists():
        return dst
    start = CLIPS / f"{sid}_start.jpg"
    if not start.exists():
        Image.open(KF / f"{sid}.png").convert("RGB").resize((1920, 1080), Image.LANCZOS).save(start, quality=95)
    args = {"start_image_url": upload(start), "prompt": video_prompt(sid), "duration": CLIP_SECONDS,
            "generate_audio": True, "negative_prompt": VIDEO_NEG}
    if "parvati" in SHOTS[sid][0]:
        # Kling element = identity lock: frontal portrait plus up to three other angles.
        args["elements"] = [{"frontal_image_url": upload(REFS / "p01.png"),
                             "reference_image_urls": [upload(REFS / f"{n}.png") for n in ("p03", "p04", "p06")]}]
    print(f"[{sid} take {take}] {VIDEO_MODEL} {CLIP_SECONDS}s")
    res = fal().subscribe(VIDEO_MODEL, arguments=args)
    download(res["video"]["url"], dst)
    print("  ->", dst)
    return dst


def clip_frames(clip, dst, n=5):
    """Contact strip of n frames spread across a clip."""
    import subprocess
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(clip)], capture_output=True, text=True, check=True).stdout)
    tiles = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        png = dst.with_suffix(f".{i}.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(clip), "-frames:v", "1",
                        "-vf", "scale=640:-2", str(png)], check=True)
        tiles.append((Image.open(png).convert("RGB"), t))
        png.unlink()
    w, h = tiles[0][0].size
    strip = Image.new("RGB", (n * (w + 8) + 8, h + 16), (16, 16, 16))
    d = ImageDraw.Draw(strip)
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20) if _has_font() else ImageFont.load_default()
    for i, (im, t) in enumerate(tiles):
        strip.paste(im, (8 + i * (w + 8), 8))
        d.text((16 + i * (w + 8), 14), f"{clip.stem}  {t:.1f}s", fill=(255, 220, 140), font=font)
    strip.save(dst, quality=88)
    return dst


def clip_face_score(clip, who, n=8):
    """Face similarity over n frames of a clip: (mean, worst frame), or None if no face was found."""
    import subprocess
    from film.face import score
    vals = []
    for i in range(n):
        png = CLIPS / f"{clip.stem}.score{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(i + 0.5) * 3.9 / n:.2f}", "-i", str(clip),
                        "-frames:v", "1", str(png)], check=True)
        s = score(png, who)
        png.unlink()
        if s:
            vals.append(s[0])
    return (sum(vals) / len(vals), min(vals)) if vals else None


def make_video(shots, takes):
    CLIPS.mkdir(exist_ok=True)
    jobs = [(s, t) for s in shots for t in range(1, (takes.get(s, 1) if isinstance(takes, dict) else takes) + 1)]
    with cf.ThreadPoolExecutor(6) as ex:
        clips = list(ex.map(lambda j: make_clip(*j), jobs))
    f = CLIPS / "scores.json"
    scores = json.loads(f.read_text()) if f.exists() else {}
    for c in clips:
        print("frames ->", clip_frames(c, CLIPS / f"{c.stem}_frames.jpg"))
        who = identity(c.stem[:2])
        if who and c.stem not in scores:
            scores[c.stem] = clip_face_score(c, who)
            print(f"  {c.stem} face {scores[c.stem]}")
            f.write_text(json.dumps(scores, indent=1, sort_keys=True))


# ---------------------------------------------------------------- music
def music_plan(version):
    return {"chunks": [{"text": "", "duration_ms": sec * 1000,
                        "positive_styles": MUSIC_GLOBAL + styles + MUSIC_VERSIONS[version],
                        "negative_styles": MUSIC_NEGATIVE}
                       for _, sec, styles in MUSIC_SECTIONS]}


def make_music(versions):
    import subprocess
    MUSIC.mkdir(exist_ok=True)
    def one(v):
        dst = MUSIC / f"score_{v}.mp3"
        if not dst.exists():
            args = {"composition_plan": music_plan(v), "output_format": "mp3_48000_192"}
            res = fal().subscribe(MUSIC_MODEL, arguments=args)
            download(res["audio"]["url"], dst)
        return dst
    with cf.ThreadPoolExecutor(3) as ex:
        outs = list(ex.map(one, versions))
    # 20 s preview per version: the build into the choir, the silent bell beat and the climax.
    marks = [0]
    for _, sec, _ in MUSIC_SECTIONS:
        marks.append(marks[-1] + sec)
    for o in outs:
        prev = o.with_name(o.stem + "_preview.mp3")
        a, b = marks[2] - 6, marks[4] + 8
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(o),
                        "-af", "afade=t=in:d=0.5,afade=t=out:st=" + str(b - a - 1.5) + ":d=1.5", str(prev)], check=True)
        print("music ->", o, "| preview", prev)


# ---------------------------------------------------------------- edit
def load_picks():
    """Chosen take per shot: picks.json if present, otherwise the take with the best face score (or take 1)."""
    f = ROOT / "picks.json"
    picks = json.loads(f.read_text()) if f.exists() else {}
    sf = CLIPS / "scores.json"
    scores = json.loads(sf.read_text()) if sf.exists() else {}
    for sid in SHOTS:
        if sid not in picks:
            takes = sorted(CLIPS.glob(f"{sid}_t*.mp4"))
            if not takes:
                sys.exit(f"No clip for shot {sid}; run the video stage first.")
            picks[sid] = max(takes, key=lambda p: (scores.get(p.stem) or [0])[0]).stem.split("_t")[1]
    return {k: int(v) for k, v in picks.items()}


def make_edit(version, formats=("16x9", "9x16")):
    from film import edit
    music = MUSIC / f"score_{version}.mp3"
    picks = load_picks()
    info = edit.analyse(music)
    clip_len = {sid: edit.duration(CLIPS / f"{sid}_t{picks[sid]}.mp4") for sid in SHOTS}
    cuts = edit.plan_cuts(info, clip_len)
    edit.BUILD.mkdir(exist_ok=True)
    (edit.BUILD / "timeline.json").write_text(json.dumps({"music": music.name, "picks": picks, "tempo": info["tempo"],
                                                          "bell": info["bell"], "cuts": cuts}, indent=1))
    print(f"tempo {info['tempo']:.1f} bpm, bell at {info['bell']:.2f}s, card at {cuts[-1]['end']:.2f}s")
    for c in cuts:
        print(f"  {c['id']}  {c['start']:6.2f} -> {c['end']:6.2f}  ({c['end'] - c['start']:.2f}s)"
              f"{'  dissolve' if c['dissolve_out'] else ''}")
    for fmt in formats:
        out = ROOT / f"shiv_parvati_{fmt}.mp4"
        edit.render(cuts, picks, music, info, fmt == "9x16", out)
        lufs, tp = edit.loudness(out)
        print(f"{out.name}: {edit.duration(out):.2f}s, {out.stat().st_size / 1e6:.1f} MB, {lufs:.1f} LUFS, {tp:.1f} dBTP")


# ---------------------------------------------------------------- cli
def main():
    global CLIP_SECONDS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["crops", "heroes", "keyframes", "grid", "video", "music", "edit"])
    ap.add_argument("--shots", default=",".join(SHOTS), help="comma-separated shot ids")
    ap.add_argument("--takes", type=int, default=1)
    ap.add_argument("--versions", default="A,B,C", help="music versions to make")
    ap.add_argument("--music", default="A", help="music version to cut to")
    ap.add_argument("--formats", default="16x9,9x16")
    ap.add_argument("--seconds", default=CLIP_SECONDS, help="clip length for new clips (Kling: 3-15)")
    ap.add_argument("--redo", default="", help="comma-separated ids to regenerate, e.g. 03,07 or shiva")
    a = ap.parse_args()
    redo = tuple(x for x in a.redo.split(",") if x)
    if a.stage == "crops":
        make_crops()
    elif a.stage == "heroes":
        make_crops()
        make_heroes(redo)
    elif a.stage == "keyframes":
        make_crops()
        make_heroes()
        make_keyframes(redo)
    elif a.stage == "grid":
        make_grid()
    elif a.stage == "video":
        CLIP_SECONDS = a.seconds
        make_video([x for x in a.shots.split(",") if x], a.takes)
    elif a.stage == "music":
        make_music([x for x in a.versions.split(",") if x])
    elif a.stage == "edit":
        make_edit(a.music, tuple(a.formats.split(",")))


if __name__ == "__main__":
    main()
