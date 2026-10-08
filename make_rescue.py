#!/usr/bin/env python3
"""
Episode 3 — "The Rescue": 16 shots, 42 s, from the approved character sheet and storyboards in rescue/references/.

  python make_rescue.py keyframes     18 photoreal 16:9 stills (storyboard-matched or re-directed), face-scored
  python make_rescue.py grid          contact sheet of the keyframes
  python make_rescue.py video         animate the keyframes (Kling v3 Pro)            -> rescue/clips/
  python make_rescue.py music         the ~48 s score (Eleven Music v2.5)               -> rescue/music/
  python make_rescue.py edit          cut, grade, title, mix, master -> shiv_rescue_16x9.mp4 + shiv_rescue_9x16.mp4

Reuses the helpers of make_video.py (fal upload/download, Nano Banana Pro) and film/face.py (ArcFace scoring).
"""
import argparse
import concurrent.futures as cf
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_video as mv
from film import face
from film.rescue import (CLIMBER, ELEMENTS, FROM_BOARD, MUSIC_GLOBAL, MUSIC_NEGATIVE, MUSIC_SECTIONS, SCORE, SHIVA,
                         SHOTS, STYLE, STYLE_EMPTY)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rescue"
REFS, BOARD, KF = OUT / "refs", OUT / "storyboard", OUT / "keyframes"
CLIPS, MUSIC = OUT / "clips", OUT / "music"
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
    paths, notes = [], []
    if sid in FROM_BOARD:
        paths.append(BOARD / f"{sid}.png")
        notes.append("Image 1 is the storyboard frame for this shot: match its composition, camera angle, framing, "
                     "poses and action, but render it as a new photoreal high-resolution film frame (do not copy its "
                     "softness or text).")
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
    style = STYLE if who else STYLE_EMPTY
    return f"{notes} {locks}Create the photoreal film frame: {desc} {style}".strip()


def make_keyframe(sid, redo=()):
    dst = KF / f"{sid}.png"
    if dst.exists() and sid not in redo:
        return None
    paths, _ = refs_for(sid)
    who = SCORE.get(sid)
    cands = []
    # Pass mark = what the approved storyboard panel itself scores (expressive, angled shots score lower), capped.
    board = face.score(BOARD / f"{sid}.png", who) if who and sid in FROM_BOARD else None
    need = (min(FACE_MIN, board[0] - 0.03) if board else FACE_MIN) if who else None
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
    tw, th, pad, cols = 480, 270, 10, 6
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


def make_clip(sid):
    dst = CLIPS / f"{sid}.mp4"
    if dst.exists():
        return dst
    start = CLIPS / f"{sid}_start.jpg"
    Image.open(KF / f"{sid}.png").convert("RGB").resize((1920, 1080), Image.LANCZOS).save(start, quality=95)
    _, secs, _, action, sound = SHOTS[sid]
    els, tags = [], []
    for who in ELEMENTS.get(sid, ""):
        names = (["climber_front", "climber_34", "climber_full"] if who == "c" else
                 ["shiva_front", "shiva_34", "shiva_full"])
        els.append({"frontal_image_url": mv.upload(REFS / f"{names[0]}.png"),
                    "reference_image_urls": [mv.upload(REFS / f"{n}.png") for n in names[1:]]})
        tags.append(f"@Element{len(els)} is {'the young woman climber' if who == 'c' else 'Shiva'}.")
    args = {"start_image_url": mv.upload(start), "duration": "5" if secs > 3.5 else "4", "generate_audio": True,
            "negative_prompt": mv.VIDEO_NEG,
            "prompt": f"{' '.join(tags)} {action} {mv.VIDEO_LOOK} Audio: {sound}; ambience and sound effects only — "
                      "no music, no speech.".strip()}
    if els:
        args["elements"] = els
    res = mv.fal().subscribe(mv.VIDEO_MODEL, arguments=args)
    mv.download(res["video"]["url"], dst)
    print("clip ->", dst)
    return dst


def make_video(shots=None):
    CLIPS.mkdir(parents=True, exist_ok=True)
    shots = shots or list(SHOTS)
    with cf.ThreadPoolExecutor(6) as ex:
        clips = list(ex.map(make_clip, shots))
    sf = CLIPS / "scores.json"
    scores = json.loads(sf.read_text()) if sf.exists() else {}
    mv.CLIPS = CLIPS
    for c in clips:
        mv.clip_frames(c, CLIPS / f"{c.stem}_frames.jpg")
        who = SCORE.get(c.stem)
        if who and c.stem not in scores:
            scores[c.stem] = mv.clip_face_score(c, who)
            print(f"  {c.stem} face {scores[c.stem]}")
            sf.write_text(json.dumps(scores, indent=1, sort_keys=True))


def make_music(name="score"):
    MUSIC.mkdir(parents=True, exist_ok=True)
    dst = MUSIC / f"{name}.mp3"
    if not dst.exists():
        plan = {"chunks": [{"text": "", "duration_ms": int(sec * 1000), "positive_styles": MUSIC_GLOBAL + styles,
                            "negative_styles": MUSIC_NEGATIVE} for _, sec, styles in MUSIC_SECTIONS]}
        res = mv.fal().subscribe(mv.MUSIC_MODEL, arguments={"composition_plan": plan, "output_format": "mp3_48000_192"})
        mv.download(res["audio"]["url"], dst)
    print("music ->", dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["keyframes", "grid", "video", "music", "edit"])
    ap.add_argument("--shots", default="")
    ap.add_argument("--name", default="score")
    ap.add_argument("--redo", default="")
    a = ap.parse_args()
    redo = tuple(x for x in a.redo.split(",") if x)
    if a.stage == "keyframes":
        make_keyframes(redo)
    elif a.stage == "video":
        make_video([x for x in a.shots.split(",") if x] or None)
    elif a.stage == "music":
        make_music(a.name)
    elif a.stage == "edit":
        from film import edit, rescue_edit
        outs = rescue_edit.render(MUSIC / f"{a.name}.mp3", ROOT / "shiv_rescue_16x9.mp4", ROOT / "shiv_rescue_9x16.mp4")
        for out in outs:
            lufs, tp = edit.loudness(out)
            print(f"{out.name}: {edit.duration(out):.2f}s, {out.stat().st_size / 1e6:.1f} MB, {lufs:.1f} LUFS, {tp:.1f} dBTP")
    else:
        sf = KF / "scores.json"
        grid(json.loads(sf.read_text()) if sf.exists() else {})


if __name__ == "__main__":
    main()
