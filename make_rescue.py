#!/usr/bin/env python3
"""
Episode 3 — "The Rescue": 16 shots, 42 s, from the approved character sheet and storyboards in rescue/references/.

  python make_rescue.py keyframes     16 photoreal 16:9 stills matching the storyboard, face-scored -> rescue/keyframes/
  python make_rescue.py grid          contact sheet of the keyframes

Reuses the helpers of make_video.py (fal upload/download, Nano Banana Pro) and film/face.py (ArcFace scoring).
"""
import argparse
import concurrent.futures as cf
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_video as mv
from film import face
from film.rescue import CLIMBER, SCORE, SHIVA, SHOTS, STYLE

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rescue"
REFS, BOARD, KF = OUT / "refs", OUT / "storyboard", OUT / "keyframes"
FACE_MIN = 0.45
FACE_TRIES = 2
FACE_TRIES_REDO = 3     # a shot sent back for its face gets one more try

# Identities for scoring: the Climber is the same person as Parvati (0.90 on the front crop), so Parvati's
# closed-eye and profile crops widen her reference set.
face.IDENTITIES["climber"] = [REFS / "climber_front.png", REFS / "climber_34.png",
                              mv.REFS / "p03.png", mv.REFS / "p04.png"]
face.IDENTITIES["shiva_beard"] = [REFS / "shiva_front.png", REFS / "shiva_34.png"]


def refs_for(sid):
    who = SHOTS[sid][0]
    paths = [BOARD / f"{sid}.png"]
    notes = ["Image 1 is the storyboard frame for this shot: match its composition, camera angle, framing, poses and "
             "action, but render it as a new photoreal high-resolution film frame (do not copy its softness or text)."]
    if "c" in who:
        first = len(paths) + 1
        paths += [REFS / "climber_front.png", REFS / "climber_34.png", REFS / "climber_full.png"]
        notes.append(f"Images {first}-{first + 1} are identity photos of the young woman; image {first + 2} shows her "
                     "full costume.")
    if "s" in who:
        first = len(paths) + 1
        paths += [REFS / "shiva_front.png", REFS / "shiva_34.png", REFS / "shiva_full.png"]
        notes.append(f"Images {first}-{first + 1} are close-ups of Shiva; image {first + 2} shows his full costume "
                     "and trishul.")
    return paths, " ".join(notes)


def prompt_for(sid):
    who, _, desc, _, _ = SHOTS[sid]
    _, notes = refs_for(sid)
    locks = (CLIMBER + " " if "c" in who else "") + (SHIVA + " " if "s" in who else "")
    return f"{notes} {locks}Create the photoreal film frame: {desc} {STYLE}"


def make_keyframe(sid, redo=()):
    dst = KF / f"{sid}.png"
    if dst.exists() and sid not in redo:
        return None
    paths, _ = refs_for(sid)
    who = SCORE.get(sid)
    cands = []
    # Pass mark = what the approved storyboard panel itself scores (expressive, angled shots score lower), capped.
    need = min(FACE_MIN, face.score(BOARD / f"{sid}.png", who)[0] - 0.03) if who else None
    tries = (FACE_TRIES_REDO if sid in redo else FACE_TRIES) if who else 1
    for attempt in range(tries):
        cand = KF / f"{sid}_try{attempt + 1}.png"
        mv.still(cand, prompt_for(sid), paths, seed=9000 + 10 * int(sid) + attempt + (5 if sid in redo else 0))
        cands.append((cand, face.score(cand, who) if who else None))
        print(f"  [{sid}] try {attempt + 1}: face {cands[-1][1]}")
        if not who or (cands[-1][1] and cands[-1][1][0] >= need):
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
    with cf.ThreadPoolExecutor(6) as ex:
        for r in ex.map(lambda s: make_keyframe(s, redo), SHOTS):
            if r:
                scores[r[0]] = r[1]
                sf.write_text(json.dumps(scores, indent=1, sort_keys=True))
    grid(scores)


def grid(scores):
    tw, th, pad, cols = 480, 270, 10, 4
    ids = [s for s in SHOTS if (KF / f"{s}.png").exists()]
    rows = -(-len(ids) // cols)
    g = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad) + pad), (16, 16, 16))
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    for i, sid in enumerate(ids):
        im = Image.open(KF / f"{sid}.png").convert("RGB").resize((tw, th), Image.LANCZOS)
        x, y = pad + (i % cols) * (tw + pad), pad + (i // cols) * (th + pad)
        g.paste(im, (x, y))
        s = scores.get(sid)
        label = f"{sid}  {SHOTS[sid][1]}s" + (f"  face {s[0]:.2f}" if s else "")
        d = ImageDraw.Draw(g)
        d.rectangle([x, y, x + 12 * len(label) + 12, y + 28], fill=(0, 0, 0))
        d.text((x + 6, y + 3), label, fill=(255, 220, 140), font=font)
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
