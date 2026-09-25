#!/usr/bin/env python3
"""
Episode 2 — "Sati to Parvati", a native 9:16 story reel.

  python make_sati.py keyframes     7 new vertical keyframes (Nano Banana Pro), face-scored -> sati/keyframes/
  python make_sati.py video         animate them (Kling v3 Pro, 4 s)                      -> sati/clips/
  python make_sati.py music         one ~45 s score (Eleven Music v2.5)                   -> sati/music/
  python make_sati.py edit          beat-cut story edit                                   -> shiv_parvati_sati_reel.mp4

Reuses the face refs, the Shiva hero image and several clips from the first film (make_video.py).
"""
import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_video as mv
from film.sati import NEW, STYLE, SATI_LOCK

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "sati"
KF, CLIPS, MUSIC = OUT / "keyframes", OUT / "clips", OUT / "music"
FACE_MIN = 0.45
FACE_TRIES = 2        # budget: at most one redo per shot


def refs_for(sid):
    paths, notes = [], []
    for r in NEW[sid][0]:
        first = len(paths) + 1
        if r == "parvati":
            paths += [mv.REFS / f"{n}.png" for n in mv.CROPS]
            notes.append(f"Images {first}-{len(paths)} are identity photos of the woman.")
        elif r == "shiva":
            paths.append(mv.HERO_DIR / "shiva.png")
            notes.append(f"Image {first} is the character reference for Shiva; keep him exactly on-model "
                         "(clean-shaven, tripundra and third-eye mark, crescent moon, cobra, trishul with damru).")
        elif r.startswith("kf:"):
            paths.append(KF / f"{r[3:]}.png")
            notes.append(f"Image {first} is the previous shot of this scene; match its setting, lighting and costume.")
    return paths, " ".join(notes)


def who(sid):
    refs = NEW[sid][0]
    return "parvati" if "parvati" in refs else ("shiva" if sid in ("s3",) else None)


def prompt_for(sid):
    paths, notes = refs_for(sid)
    lock = (SATI_LOCK if sid in ("s1", "s2") else mv.PARVATI_LOCK) + " " if "parvati" in NEW[sid][0] else ""
    return f"{notes} {lock}Create a new photoreal vertical 9:16 film frame: {NEW[sid][1]} {STYLE}".strip()


def still(dst, prompt, ref_paths, seed):
    args = {"prompt": prompt, "aspect_ratio": "9:16", "resolution": "2K", "output_format": "png",
            "safety_tolerance": "5", "seed": seed, "image_urls": [mv.upload(p) for p in ref_paths]}
    res = mv.fal().subscribe(mv.IMAGE_MODEL, arguments=args)
    return mv.download(res["images"][0]["url"], dst)


def make_keyframe(sid, redo=()):
    from film.face import score
    dst = KF / f"{sid}.png"
    if dst.exists() and sid not in redo:
        return None
    paths, _ = refs_for(sid)
    w = who(sid)
    cands = []
    for attempt in range(FACE_TRIES if w else 1):
        cand = KF / f"{sid}_try{attempt + 1}.png"
        still(cand, prompt_for(sid), paths, seed=7000 + 10 * int(sid[1]) + attempt)
        cands.append((cand, score(cand, w) if w else None))
        print(f"  [{sid}] try {attempt + 1}: face {cands[-1][1]}")
        if not w or (cands[-1][1] and cands[-1][1][0] >= FACE_MIN):
            break
    best = max(cands, key=lambda c: c[1][0] if c[1] else -1)
    best[0].replace(dst)
    for f in KF.glob(f"{sid}_try*.png"):
        f.unlink()
    return sid, best[1]


def make_keyframes(redo=()):
    KF.mkdir(parents=True, exist_ok=True)
    sf = KF / "scores.json"
    scores = json.loads(sf.read_text()) if sf.exists() else {}
    with cf.ThreadPoolExecutor(7) as ex:
        for r in ex.map(lambda s: make_keyframe(s, redo), NEW):
            if r:
                scores[r[0]] = r[1]
                sf.write_text(json.dumps(scores, indent=1, sort_keys=True))
    grid(scores)


def grid(scores):
    tw, th, pad = 360, 640, 12
    ids = [s for s in NEW if (KF / f"{s}.png").exists()]
    g = Image.new("RGB", (len(ids) * (tw + pad) + pad, th + 2 * pad), (16, 16, 16))
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    for i, sid in enumerate(ids):
        im = Image.open(KF / f"{sid}.png").convert("RGB").resize((tw, th), Image.LANCZOS)
        x = pad + i * (tw + pad)
        g.paste(im, (x, pad))
        s = scores.get(sid)
        label = sid + (f"  face {s[0]:.2f}" if s else "")
        d = ImageDraw.Draw(g)
        d.rectangle([x, pad, x + 14 * len(label) + 12, pad + 32], fill=(0, 0, 0))
        d.text((x + 6, pad + 4), label, fill=(255, 220, 140), font=font)
    g.save(KF / "grid.jpg", quality=88)
    print("grid ->", KF / "grid.jpg")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["keyframes", "grid"])
    ap.add_argument("--redo", default="")
    a = ap.parse_args()
    redo = tuple(x for x in a.redo.split(",") if x)
    if a.stage == "keyframes":
        make_keyframes(redo)
    else:
        sf = KF / "scores.json"
        grid(json.loads(sf.read_text()) if sf.exists() else {})


if __name__ == "__main__":
    main()
