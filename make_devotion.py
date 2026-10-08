#!/usr/bin/env python3
"""
The devotion cut of "Shiv & Parvati": ~45 s, built for 9:16 (a 16:9 version comes out of the same cut).

  python make_devotion.py keyframes   the four season edits of keyframe 05, the rishis' look (25), the blessing (26)
  python make_devotion.py video       Kling: season transitions (joined into one shot, clips/30_t1.mp4), 25 and 26
  python make_devotion.py music       the ~46 s score cut to the story (Eleven Music v2.5) -> music/devotion_X.mp3
  python make_devotion.py edit        cut, grade, card, mix, master -> shiv_parvati_devotion_9x16.mp4 / _16x9.mp4

Shot list, cut and score plan: film/devotion.py. Reuses make_video.py (fal, Nano Banana Pro, Kling helpers),
film/face.py (ArcFace scoring), film/edit.py (render, master) and film/reel.py (camera moves on the 9:16 cut).
"""
import argparse
import concurrent.futures as cf
import json
import subprocess
import threading

from PIL import Image

import make_video as mv
from film import devotion as dv
from film import face
from film.shots import PARVATI_LOCK, SHIVA, SAGES, STYLE

KF, CLIPS, REFS, HEROES = mv.KF, mv.CLIPS, mv.REFS, mv.HERO_DIR
CROPS = [REFS / f"{n}.png" for n in mv.CROPS]
FACE_MIN, TRIES = 0.45, 3
LOCK = threading.Lock()


# ---------------------------------------------------------------- keyframes
def best_of(sid, make, who, tries=TRIES):
    """Generate up to `tries` candidates (make(path, attempt)), keep the best face score."""
    dst = KF / f"{sid}.png"
    if dst.exists():
        return
    cands = []
    for i in range(tries if who else 1):
        cand = KF / f"{sid}_try{i + 1}.png"
        make(cand, i)
        cands.append((cand, face.score(cand, who) if who else None))
        print(f"  [{sid}] try {i + 1}: face {cands[-1][1]}", flush=True)
        if not who or (cands[-1][1] and cands[-1][1][0] >= FACE_MIN):
            break
    best = max(cands, key=lambda c: c[1][0] if c[1] else -1)
    best[0].replace(dst)
    for f in KF.glob(f"{sid}_try*.png"):
        f.unlink()
    with LOCK:
        scores = mv.load_scores()
        scores[sid] = best[1]
        (KF / "scores.json").write_text(json.dumps(scores, indent=1, sort_keys=True))


def season(sid):
    _, change = dv.SEASONS[sid]
    prompt = dv.SEASON_EDIT.format(season=change)
    best_of(sid, lambda p, i: mv.still(p, prompt, [KF / f"{dv.SEASON_BASE}.png"] + CROPS, seed=31000 + 100 * int(sid) + i),
            "parvati")


def rishis_look():
    refs, desc = dv.SHOTS["25"][0], dv.SHOTS["25"][1]
    prompt = (f"Image 1 is the character reference for the three rishis; keep them exactly on-model. Image 2 is the "
              f"previous shot of this scene; match its light and setting. {SAGES}. Create a new photoreal 16:9 film "
              f"frame: {desc} {STYLE}")
    best_of("25", lambda p, i: mv.still(p, prompt, [HEROES / "sages.png", KF / "19.png"], seed=32500 + i), None)


def blessing():
    desc = dv.SHOTS["26"][1]
    prompt = (f"Images 1-4 are identity photos of the young woman (Parvati) and image 5 is her previous close-up: her "
              f"face must be exactly this person. Image 6 is the character reference for Shiva and image 7 his face "
              f"with eyes open; keep him exactly on-model. {PARVATI_LOCK} {SHIVA}. Create a new photoreal 16:9 film "
              f"frame: {desc} {STYLE}")
    refs = CROPS + [KF / "22.png", HEROES / "shiva.png", KF / "21.png"]
    best_of("26", lambda p, i: mv.still(p, prompt, refs, seed=32600 + i), "parvati", tries=4)


def make_keyframes():
    with cf.ThreadPoolExecutor(6) as ex:
        list(ex.map(lambda f: f(), [lambda s=s: season(s) for s in dv.SEASONS] + [rishis_look, blessing]))
    sheet = Image.new("RGB", (4 * 640, 2 * 360), (16, 16, 16))
    for i, sid in enumerate([dv.SEASON_BASE, *dv.SEASONS, "25", "26"]):
        im = Image.open(KF / f"{sid}.png").convert("RGB").resize((640, 360), Image.LANCZOS)
        sheet.paste(im, ((i % 4) * 640, (i // 4) * 360))
    sheet.save(mv.ROOT / "build" / "devotion_keyframes.jpg", quality=88)
    print("sheet ->", mv.ROOT / "build" / "devotion_keyframes.jpg")


# ---------------------------------------------------------------- video
def parvati_element():
    return [{"frontal_image_url": mv.upload(REFS / "p01.png"),
             "reference_image_urls": [mv.upload(REFS / f"{n}.png") for n in ("p03", "p04", "p06")]}]


def frame_jpg(sid, dst):
    Image.open(KF / f"{sid}.png").convert("RGB").resize((1920, 1080), Image.LANCZOS).save(dst, quality=95)
    return mv.upload(dst)


def transition(k):
    a, b, change = dv.TRANSITIONS[k]
    dst = CLIPS / f"season{k + 1}.mp4"
    if dst.exists():
        return dst
    args = {"start_image_url": frame_jpg(a, CLIPS / f"season{k + 1}_start.jpg"),
            "end_image_url": frame_jpg(b, CLIPS / f"season{k + 1}_end.jpg"),
            "prompt": dv.TRANSITION_PROMPT.format(change=change) + f" {mv.VIDEO_LOOK} Audio: {dv.TRANSITION_SOUND}; "
                      "ambience only, no music, no speech.",
            "duration": "3", "generate_audio": True, "negative_prompt": mv.VIDEO_NEG, "elements": parvati_element()}
    print(f"[season {k + 1}] {a} -> {b}", flush=True)
    mv.download(mv.fal().subscribe(mv.VIDEO_MODEL, arguments=args)["video"]["url"], dst)
    return dst


def shot_clip(sid, secs):
    dst = CLIPS / f"{sid}_t1.mp4"
    if dst.exists():
        return dst
    _, _, action, sound = dv.SHOTS[sid]
    args = {"start_image_url": frame_jpg(sid, CLIPS / f"{sid}_start.jpg"), "duration": secs, "generate_audio": True,
            "negative_prompt": mv.VIDEO_NEG,
            "prompt": f"{action} {mv.VIDEO_LOOK} Audio: {sound}; ambience and sound effects only, no music, no speech."}
    if "@Element1" in action:
        args["elements"] = parvati_element()
    print(f"[{sid}] {secs}s", flush=True)
    mv.download(mv.fal().subscribe(mv.VIDEO_MODEL, arguments=args)["video"]["url"], dst)
    return dst


def join_seasons():
    """The four transitions as one continuous shot: each next take starts on the frame the last one ends on, so the
    shared frame is dropped once and the whole is retimed to SEASONS_SECONDS."""
    dst = CLIPS / f"{dv.SEASONS_CLIP}_t1.mp4"
    parts = [CLIPS / f"season{k + 1}.mp4" for k in range(len(dv.TRANSITIONS))]
    total = sum(mv_duration(p) for p in parts) - (len(parts) - 1) / 24
    speed = total / dv.SEASONS_SECONDS
    ins, fc = [], []
    for i, p in enumerate(parts):
        ins += ["-i", str(p)]
        last = i == len(parts) - 1
        trim = "" if last else f",trim=end_frame={round(mv_duration(p) * 24) - 1}"
        fc.append(f"[{i}:v]fps=24{trim},setpts=PTS-STARTPTS[v{i}]")
        atrim = "" if last else f",atrim=end={mv_duration(p) - 1 / 24:.4f}"
        fc.append(f"[{i}:a]aresample=48000{atrim},asetpts=PTS-STARTPTS[a{i}]")
    n = len(parts)
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]setpts=PTS/{speed:.5f},fps=24[v]")
    fc.append(f"[ac]atempo={speed:.5f}[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "12", "-preset", "medium", "-c:a", "aac", "-b:a", "256k", str(dst)],
                   check=True)
    print(f"seasons -> {dst} ({mv_duration(dst):.2f}s, x{speed:.3f})")
    return dst


def mv_duration(p):
    from film import edit
    return edit.duration(p)


def make_video():
    CLIPS.mkdir(exist_ok=True)
    with cf.ThreadPoolExecutor(6) as ex:
        jobs = [ex.submit(transition, k) for k in range(len(dv.TRANSITIONS))]
        jobs += [ex.submit(shot_clip, "25", "4"), ex.submit(shot_clip, "26", "5")]
        clips = [j.result() for j in jobs]
    join_seasons()
    for c in clips + [CLIPS / f"{dv.SEASONS_CLIP}_t1.mp4"]:
        mv.clip_frames(c, CLIPS / f"{c.stem}_frames.jpg", n=6 if c.stem.startswith("30") else 5)
    for sid in ("26",):
        print(f"  {sid} face {mv.clip_face_score(CLIPS / f'{sid}_t1.mp4', 'parvati')}")


# ---------------------------------------------------------------- music
def make_music(versions):
    mv.MUSIC.mkdir(exist_ok=True)

    def one(v):
        dst = mv.MUSIC / f"devotion_{v}.mp3"
        if not dst.exists():
            flavour = {"A": ["warm strings and bansuri led"], "B": ["sitar and santoor colours, lush strings"]}[v]
            plan = {"chunks": [{"text": "", "duration_ms": int(sec * 1000),
                                "positive_styles": dv.MUSIC_GLOBAL + styles + flavour,
                                "negative_styles": dv.MUSIC_NEGATIVE} for _, sec, styles in dv.MUSIC_SECTIONS]}
            res = mv.fal().subscribe(mv.MUSIC_MODEL, arguments={"composition_plan": plan,
                                                                 "output_format": "mp3_48000_192"})
            mv.download(res["audio"]["url"], dst)
        print("music ->", dst)
    with cf.ThreadPoolExecutor(2) as ex:
        list(ex.map(one, versions))


def prepare_score(music, dst):
    """The score with a brief, gentle reduction (not silence) just before Shiva's eyes open, and one temple bell
    on the moment they open."""
    import librosa
    import numpy as np
    import soundfile as sf
    from film import edit
    sr = 48000
    y, _ = librosa.load(str(music), sr=sr, mono=False)
    y = np.atleast_2d(y)
    if y.shape[0] == 1:
        y = np.vstack([y, y])
    t = np.arange(y.shape[1]) / sr
    a, b, db = dv.DIP
    floor = 10 ** (db / 20)
    gain = np.ones_like(t)
    down = (t >= a) & (t < a + 0.6)
    gain[down] = 1 - (1 - floor) * (0.5 - 0.5 * np.cos(np.pi * (t[down] - a) / 0.6))
    gain[(t >= a + 0.6) & (t < b)] = floor
    up = (t >= b) & (t < b + 0.25)
    gain[up] = floor + (1 - floor) * (t[up] - b) / 0.25
    y = y * gain
    loud = np.sqrt(np.mean(y[:, int(14 * sr):int(27 * sr)] ** 2))
    bell, _ = librosa.load(str(edit.BELL_SFX), sr=sr, mono=True)
    on = librosa.onset.onset_detect(y=bell, sr=sr, units="samples", backtrack=True)
    bell = bell[(on[0] if len(on) else 0):]
    bell = bell / (np.sqrt(np.mean(bell[: sr // 2] ** 2)) + 1e-9) * loud * 1.3
    i = int(dv.BELL_AT * sr)
    m = min(len(bell), y.shape[1] - i)
    y[:, i:i + m] += bell[:m]
    peak = np.abs(y).max()
    if peak > 0.98:
        y *= 0.98 / peak
    sf.write(dst, y.T, sr, subtype="PCM_24")
    return dst


# ---------------------------------------------------------------- edit
def make_edit(version, formats=("9x16", "16x9")):
    import librosa
    from film import edit, reel
    music = mv.MUSIC / f"devotion_{version}.mp3"
    edit.REFRAME.update(dv.REFRAME)
    edit.IN_AT.update(dv.IN_AT)
    edit.FIT.update(dv.FIT)
    length = edit.duration(music)
    y, sr = librosa.load(str(music), sr=22050, mono=True)
    beats = [float(b) for b in librosa.beat.beat_track(y=y, sr=sr, units="time")[1]]
    info = {"bell": dv.BELL_AT, "length": length, "beats": beats}
    cuts = [{"id": s, "start": a, "end": b, "dissolve_out": d} for s, a, b, d in dv.TIMELINE]
    picks = {c["id"]: mv.load_picks().get(c["id"], 1) for c in cuts}
    picks.update({"25": 1, "26": 1, dv.SEASONS_CLIP: 1})
    timeline = edit.BUILD / "timeline_devotion.json"
    timeline.write_text(json.dumps({"music": music.name, "picks": picks, "bell": dv.BELL_AT, "cuts": cuts}, indent=1))
    score = prepare_score(music, edit.BUILD / "score_devotion.wav")
    card = {"lines": dv.CARD_LINES, "title": dv.CARD_TITLE}
    film16 = edit.BUILD / "devotion_16x9_premaster.mov"
    if "16x9" in formats or not film16.exists():
        film16 = edit.render(cuts, picks, score, info, False, edit.BUILD / "devotion_16x9.mp4", master=False, card=card)
    film9 = edit.render(cuts, picks, score, info, True, edit.BUILD / "devotion_9x16.mp4", master=False, card=card)
    outs = [reel.render_vertical(mv.ROOT / "shiv_parvati_devotion_9x16.mp4", src=film9, timeline=timeline,
                                 src16=film16, treatment=dv.TREATMENT, pulses=False)]
    if "16x9" in formats:
        out16 = mv.ROOT / "shiv_parvati_devotion_16x9.mp4"
        edit.master_audio(film16, out16)
        outs.append(out16)
    for out in outs:
        lufs, tp = edit.loudness(out)
        print(f"{out.name}: {edit.duration(out):.2f}s, {out.stat().st_size / 1e6:.1f} MB, {lufs:.1f} LUFS, {tp:.1f} dBTP")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["keyframes", "video", "music", "edit"])
    ap.add_argument("--versions", default="A,B")
    ap.add_argument("--music", default="A")
    ap.add_argument("--formats", default="9x16,16x9")
    a = ap.parse_args()
    if a.stage == "keyframes":
        make_keyframes()
    elif a.stage == "video":
        make_video()
    elif a.stage == "music":
        make_music([v for v in a.versions.split(",") if v])
    else:
        make_edit(a.music, tuple(a.formats.split(",")))


if __name__ == "__main__":
    main()
