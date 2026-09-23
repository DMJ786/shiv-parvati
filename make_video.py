#!/usr/bin/env python3
"""
Shiv & Parvati — ~55 s cinematic AI film, built in stages on fal.ai.

  python make_video.py crops        face refs from parvati_sheet.png -> refs/
  python make_video.py heroes       Shiva + sages reference images -> heroes/
  python make_video.py keyframes    one 16:9 still per shot (Nano Banana Pro), face-scored -> keyframes/
  python make_video.py grid         contact sheet of all keyframes -> keyframes/grid.jpg

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

from film.shots import HEROES, PARVATI_LOCK, SHOTS, STYLE

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "parvati_sheet.png"
REFS, HERO_DIR, KF = ROOT / "refs", ROOT / "heroes", ROOT / "keyframes"

IMAGE_MODEL = os.getenv("IMAGE_MODEL", "fal-ai/nano-banana-pro/edit")
IMAGE_T2I = os.getenv("IMAGE_T2I", "fal-ai/nano-banana-pro")
# Mean ArcFace cosine vs the refs. The refs score 0.53-0.76 against each other, other people score ~0.0,
# and profile / eyes-closed frames of the right person land around 0.45-0.55.
FACE_MIN = 0.45
FACE_TRIES = 4
FACE_SHIVA = ("11", "12", "13")   # Shiva shots where his face is readable

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


# ---------------------------------------------------------------- cli
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["crops", "heroes", "keyframes", "grid"])
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


if __name__ == "__main__":
    main()
