#!/usr/bin/env python3
"""
Gemini Omni video face-replacement pipeline.

Replaces ONLY the target character (adult man in the light-pink shirt) with the identity
from a reference portrait, chunk by chunk (Gemini Omni edit input must be <= 10 s),
then rebuilds the full movie frame-accurately.

Stages (each is cached in work/, re-run anytime; finished steps are skipped):
  analyze   probe video, detect shot boundaries               -> work/shots.json
  classify  Gemini looks at each shot: is the target's face visible?
  plan      pack shots into <= MAX_CHUNK s chunks, cut only at shot boundaries
            (a single shot longer than MAX_CHUNK is split evenly)  -> work/plan.json
  cut       frame-accurate chunk extraction                    -> work/chunks/
  edit      Gemini Omni edit per relevant chunk (+ QC + retake) -> work/edited/
  conform   force every edited chunk back to the exact source frame count/size/fps
  assemble  concat all chunks -> output/<name>_faceswap.mp4 (+ side-by-side compare)

Auth: reads GEMINI_KEY from the environment (never printed or stored).
Usage: python faceswap.py [--video IN.mp4] [--ref refs/] [--stages all] [--workers 3]
"""
import argparse, base64, concurrent.futures as cf, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK, OUT = ROOT / "work", ROOT / "output"
MODEL = os.getenv("OMNI_MODEL", "gemini-omni-1.1-flash")          # video editing
VISION_MODEL = os.getenv("VISION_MODEL", "gemini-3.8-flash")     # shot classification + QC (text out)
MAX_CHUNK = 9.0           # seconds; Gemini Omni edit limit is 10 s
MIN_EDIT_CHUNK = 2.0      # very short edit chunks get padded with neighbouring shots
SCENE_THRESH = 0.08       # ffmpeg scene score threshold for a cut
MIN_SHOT = 0.5            # cuts closer than this are merged (flash frames, fast zooms)
MAX_TAKES = 3             # edit attempts per chunk when QC fails
QC_PASS = 7               # min QC score (0-10) on identity / others-unchanged / realism

if "GEMINI_API_KEY" not in os.environ and "GEMINI_KEY" in os.environ:
    os.environ["GEMINI_API_KEY"] = os.environ["GEMINI_KEY"]  # SDK reads this; never logged


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def run(cmd, text=True):
    return subprocess.run(cmd, check=True, capture_output=True, text=text)


def ffprobe(path):
    out = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate,nb_read_frames:format=duration", "-of", "json", str(path)]).stdout
    j = json.loads(out)
    s = j["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return {"width": s["width"], "height": s["height"], "fps": num / den, "fps_str": s["r_frame_rate"],
            "frames": int(s["nb_read_frames"]), "duration": float(j["format"]["duration"])}


def client():
    from google import genai
    return genai.Client()


def load_json(p, default=None):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


def save_json(p, obj):
    Path(p).write_text(json.dumps(obj, indent=2))


# ---------------------------------------------------------------- analyze
def analyze(video):
    meta = ffprobe(video)
    log(f"video {meta['width']}x{meta['height']} @ {meta['fps']:.3f} fps, {meta['frames']} frames, {meta['duration']:.3f}s")
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                          f"select='gt(scene,{SCENE_THRESH})',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    times = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", err)]
    fps = meta["fps"]
    frames = sorted({round(t * fps) for t in times})
    merged = []
    for f in frames:
        if f <= 0 or f >= meta["frames"]:
            continue
        if merged and (f - merged[-1]) < MIN_SHOT * fps:
            continue  # flash / zoom burst: keep the first cut of the burst only
        merged.append(f)
    bounds = [0] + merged + [meta["frames"]]
    # Drop a trailing micro-shot produced by bursts
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        if shots and (b - a) < MIN_SHOT * fps:
            shots[-1]["end"] = b
            continue
        shots.append({"start": a, "end": b})
    for i, s in enumerate(shots):
        s["id"] = i
        s["t0"], s["t1"] = round(s["start"] / fps, 3), round(s["end"] / fps, 3)
    save_json(WORK / "meta.json", meta)
    save_json(WORK / "shots.json", shots)
    log(f"{len(shots)} shots:", ", ".join(f"[{s['t0']:.2f}-{s['t1']:.2f}]" for s in shots))
    return meta, shots


# ---------------------------------------------------------------- classify
CLASSIFY_PROMPT = """These {n} frames come from ONE continuous shot of a film (start, middle, end).
The TARGET character is an adult man wearing a LIGHT PINK shirt (moustache, dark hair).
Other men in the film wear dark shirts and must never be edited.
Answer in JSON only:
{{"target_face_visible": true/false,   // is any part of the pink-shirt man's FACE visible in any frame (profile counts; hands/shirt only does not)
  "target_position": "short description of where the pink-shirt man is in frame and which way he faces",
  "others": "short description of any other people visible and where, or 'none'",
  "shot_type": "close-up / medium / wide / insert etc."}}"""


def frame_jpeg(video, frame_idx, fps, width=960):
    out = run(["ffmpeg", "-loglevel", "error", "-ss", f"{frame_idx / fps:.4f}", "-i", str(video), "-frames:v", "1",
               "-vf", f"scale={width}:-2", "-f", "image2", "-c:v", "mjpeg", "-q:v", "3", "pipe:1"],
              text=False).stdout
    return out


def parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    return json.loads(m.group(0)) if m else None


def gemini_json(c, parts, prompt, retries=4):
    inp = [{"type": "image", "data": base64.b64encode(p).decode(), "mime_type": "image/jpeg"} for p in parts]
    inp.append({"type": "text", "text": prompt})
    for k in range(retries):
        try:
            r = c.interactions.create(model=VISION_MODEL, input=inp)
            j = parse_json(r.output_text)
            if j is not None:
                return j
        except Exception as e:
            log(f"  gemini text call failed ({type(e).__name__}): {str(e)[:200]}")
        time.sleep(2 ** (k + 1))
    raise RuntimeError("gemini JSON call failed")


def classify(video, meta, shots):
    c = client()
    fps = meta["fps"]
    for s in shots:
        if "target_face_visible" in s:
            continue
        idx = sorted({s["start"] + 1, (s["start"] + s["end"]) // 2, s["end"] - 2})
        frames = [frame_jpeg(video, i, fps) for i in idx if s["start"] <= i < s["end"]]
        j = gemini_json(c, frames, CLASSIFY_PROMPT.format(n=len(frames)))
        s.update({k: j.get(k) for k in ("target_face_visible", "target_position", "others", "shot_type")})
        s["target_face_visible"] = bool(s["target_face_visible"])
        log(f"shot {s['id']:2d} [{s['t0']:6.2f}-{s['t1']:6.2f}] face={s['target_face_visible']!s:5} {s['shot_type']} | {s['target_position']}")
        save_json(WORK / "shots.json", shots)
    return shots


# ---------------------------------------------------------------- plan
def plan(meta, shots):
    fps = meta["fps"]
    maxf = int(MAX_CHUNK * fps)
    # 1) split overlong shots evenly so every piece <= MAX_CHUNK
    pieces = []
    for s in shots:
        n = s["end"] - s["start"]
        k = max(1, math.ceil(n / maxf))
        edges = [s["start"] + round(i * n / k) for i in range(k + 1)]
        for i, (a, b) in enumerate(zip(edges, edges[1:])):
            pieces.append({**s, "start": a, "end": b, "part": i, "parts": k})
    # 2) group runs of equal edit-status, packing greedily up to MAX_CHUNK
    chunks = []
    for p in pieces:
        edit = p["target_face_visible"]
        cur = chunks[-1] if chunks else None
        if cur and cur["edit"] == edit and (p["end"] - cur["start"]) <= maxf:
            cur["end"] = p["end"]; cur["shots"].append(p["id"]); cur["pieces"].append(p)
        else:
            chunks.append({"edit": edit, "start": p["start"], "end": p["end"], "shots": [p["id"]], "pieces": [p]})
    # 3) an edit chunk that is too short absorbs neighbouring pass-through material (still <= MAX_CHUNK)
    minf = int(MIN_EDIT_CHUNK * fps)
    i = 0
    while i < len(chunks):
        ch = chunks[i]
        if ch["edit"] and ch["end"] - ch["start"] < minf:
            for j in (i + 1, i - 1):
                if 0 <= j < len(chunks) and not chunks[j]["edit"]:
                    nb = chunks[j]
                    if max(ch["end"], nb["end"]) - min(ch["start"], nb["start"]) <= maxf:
                        ch["start"], ch["end"] = min(ch["start"], nb["start"]), max(ch["end"], nb["end"])
                        ch["shots"] = sorted(set(ch["shots"] + nb["shots"])); ch["pieces"] = sorted(ch["pieces"] + nb["pieces"], key=lambda x: x["start"])
                        chunks.pop(j)
                        if j < i:
                            i -= 1
                        break
        i += 1
    for i, ch in enumerate(chunks):
        ch["id"] = f"c{i:02d}"
        ch["t0"], ch["t1"] = round(ch["start"] / fps, 3), round(ch["end"] / fps, 3)
        ch["frames"] = ch["end"] - ch["start"]
        # continuation of a split shot -> previous chunk's last edited frame is a continuity reference
        first = ch["pieces"][0]
        ch["continues"] = chunks[i - 1]["id"] if (i and first.get("part", 0) > 0 and chunks[i - 1]["edit"]) else None
    save_json(WORK / "plan.json", chunks)
    for ch in chunks:
        log(f"{ch['id']} [{ch['t0']:6.2f}-{ch['t1']:6.2f}] {ch['frames']/fps:5.2f}s {'EDIT' if ch['edit'] else 'keep'} shots={ch['shots']}"
            + (f" (continues {ch['continues']})" if ch["continues"] else ""))
    return chunks


# ---------------------------------------------------------------- cut
def cut(video, meta, chunks):
    d = WORK / "chunks"; d.mkdir(exist_ok=True)
    for ch in chunks:
        out = d / f"{ch['id']}.mp4"
        if out.exists() and ffprobe(out)["frames"] == ch["frames"]:
            continue
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf",
             f"trim=start_frame={ch['start']}:end_frame={ch['end']},setpts=PTS-STARTPTS",
             "-an", "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p",
             "-r", meta["fps_str"], str(out)])
        got = ffprobe(out)["frames"]
        assert got == ch["frames"], f"{ch['id']}: cut {got} frames, expected {ch['frames']}"
    log(f"cut {len(chunks)} chunks -> {d}")


# ---------------------------------------------------------------- edit
EDIT_PROMPT = """FACE REPLACEMENT EDIT. Replace the identity of exactly ONE person in this video: the adult man wearing the LIGHT PINK SHIRT ({position}).
Give him the face of the person shown in the reference photos (front view, left profile, right profile).

Transfer from the reference: facial identity, face shape, eyes, eyebrows, nose, lips, cheeks, jawline, full beard and moustache, natural skin texture with pores, skin tone.
He must clearly be the reference person from every angle, including profile and three-quarter views.

Preserve EXACTLY from the original video: his body, pink shirt and all clothing, body proportions, pose, gestures, hands and the coin, camera framing, camera motion, head position and head motion, his acting performance, expression and its timing, eye direction and blinks, mouth and lip movement, and the scene's night-time lighting, colour grade, film grain, focus and depth of field. Keep his general hair silhouette; adjust hair only where needed to blend the new face naturally.
Every frame stays the same length and timing as the input; do not add, remove, slow down or speed up anything.

DO NOT CHANGE ANY OTHER PERSON. {others} Their faces, hair and bodies must remain pixel-identical to the input.
Do not change the background, props, the on-screen logo, or the black letterbox bars.

Photorealistic film footage. Not beautified, not younger, not airbrushed, not plastic, no AI look. Keep real skin texture, natural imperfections and the original grain.{continuity}"""

QC_PROMPT = """You are a strict VFX supervisor reviewing a face-replacement shot.
Image 1: reference identity photo. Then pairs of frames: ORIGINAL then EDITED, at the same moments.
Task was: replace ONLY the face of the man in the light-pink shirt with the reference identity; nobody else may change.
Score 0-10 and answer JSON only:
{"identity_match": n,          // does the pink-shirt man in EDITED frames look like the reference person (face, beard, eyes, nose)?
 "others_unchanged": n,        // are all OTHER people's faces identical to ORIGINAL? 10 = untouched; give 10 if no other person is visible
 "performance_preserved": n,   // same pose, head direction, expression, framing, lighting as ORIGINAL
 "realism": n,                 // photoreal, natural skin texture, no artifacts/warping/plastic look
 "problems": "short text"}"""


def upload(c, path):
    f = c.files.upload(file=str(path))
    while getattr(f.state, "name", "") == "PROCESSING":
        time.sleep(3); f = c.files.get(name=f.name)
    if getattr(f.state, "name", "") == "FAILED":
        raise RuntimeError(f"upload failed: {path}")
    return f


def edit_once(c, ch, chunk_file, refs, continuity_png):
    pos = "; ".join(sorted({p.get("target_position") or "" for p in ch["pieces"] if p["target_face_visible"]}))
    oth = "; ".join(sorted({p.get("others") or "" for p in ch["pieces"]} - {"", "none", "None"}))
    others = f"Other people in this clip ({oth}) must keep their own faces." if oth else "If any other person appears, leave them untouched."
    cont = ("\nThe last reference image is the final edited frame of the previous part of this same shot: match that exact look so the cut is seamless."
            if continuity_png else "")
    inp = [{"type": "video", "uri": chunk_file.uri, "mime_type": "video/mp4"}]
    for r in refs:
        inp.append({"type": "image", "uri": r.uri, "mime_type": r.mime_type or "image/png"})
    if continuity_png:
        inp.append({"type": "image", "uri": continuity_png.uri, "mime_type": "image/png"})
    inp.append({"type": "text", "text": EDIT_PROMPT.format(position=pos or "the main foreground man", others=others, continuity=cont)})
    r = c.interactions.create(model=MODEL, input=inp, response_modalities=["video"],
                              response_format={"type": "video", "resolution": "1080p"},
                              generation_config={"video_config": {"task": "edit"}})
    v = r.output_video
    if not v:
        raise RuntimeError(f"no video returned (status={r.status}, text={str(r.output_text)[:200]})")
    if v.data:
        return base64.b64decode(v.data) if isinstance(v.data, str) else v.data
    if v.uri:
        import urllib.request
        req = urllib.request.Request(v.uri, headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        return urllib.request.urlopen(req).read()
    raise RuntimeError("empty video payload")


def qc(c, meta, ch, src, edited, ref_bytes):
    fps = meta["fps"]
    n = ch["frames"]
    picks = []
    for p in ch["pieces"]:
        if p["target_face_visible"]:
            a, b = p["start"] - ch["start"], p["end"] - ch["start"]
            picks += [a + (b - a) // 4, a + 3 * (b - a) // 4]
    picks = sorted(set(min(max(x, 0), n - 1) for x in picks))[:6]
    imgs = [ref_bytes]
    for f in picks:
        imgs += [frame_jpeg(src, f, fps, 768), frame_jpeg(edited, f, fps, 768)]
    return gemini_json(c, imgs, QC_PROMPT)


def conform(meta, ch, raw, out):
    """Force edited clip to exactly the source chunk's frame count, size, fps; drop generated audio."""
    m = ffprobe(raw)
    n = ch["frames"]
    W, H = meta["width"], meta["height"]
    vf = [f"scale={W}:{H}:flags=lanczos", "setsar=1"]
    if abs(m["frames"] - n) <= 3:
        # same timing (codec padding): trim or clone last frame
        vf += [f"tpad=stop_mode=clone:stop=3", f"trim=end_frame={n}"]
    else:
        # different length: retime so the performance stays in sync with the source
        vf += [f"setpts=PTS*{n / m['frames']:.6f}", f"fps={meta['fps_str']}", f"tpad=stop_mode=clone:stop=3", f"trim=end_frame={n}"]
    vf.append("setpts=PTS-STARTPTS")
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-vf", ",".join(vf), "-an", "-r", meta["fps_str"],
         "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", str(out)])
    got = ffprobe(out)["frames"]
    assert got == n, f"{ch['id']}: conformed to {got} frames, expected {n}"
    return m


def last_frame_png(path, out):
    run(["ffmpeg", "-loglevel", "error", "-y", "-sseof", "-0.1", "-i", str(path), "-frames:v", "1", "-update", "1", str(out)])


def edit_chunk(meta, ch, ref_paths, ref_qc_bytes):
    c = client()
    d_raw, d_ok = WORK / "edited_raw", WORK / "edited"
    final = d_ok / f"{ch['id']}.mp4"
    report_p = WORK / "qc" / f"{ch['id']}.json"
    if report_p.exists() and (final.exists() or load_json(report_p).get("blocked")):
        return load_json(report_p)
    src = WORK / "chunks" / f"{ch['id']}.mp4"
    refs = [upload(c, p) for p in ref_paths]
    cont = None
    if ch["continues"]:
        prev = d_ok / f"{ch['continues']}.mp4"
        for _ in range(240):  # wait for the previous part of the same shot (it runs in another worker)
            if (WORK / "qc" / f"{ch['continues']}.json").exists():
                break
            time.sleep(5)
        if prev.exists() and not load_json(WORK / "qc" / f"{ch['continues']}.json", {}).get("blocked"):
            png = WORK / "edited_raw" / f"{ch['continues']}_last.png"
            last_frame_png(prev, png)
            cont = upload(c, png)
    chunk_file = upload(c, src)
    takes = []
    for t in range(1, MAX_TAKES + 1):
        raw = d_raw / f"{ch['id']}_take{t}.mp4"
        conf = d_raw / f"{ch['id']}_take{t}_conf.mp4"
        try:
            if not raw.exists():
                log(f"{ch['id']} take {t}: editing ({ch['frames'] / meta['fps']:.2f}s)…")
                t0 = time.time()
                raw.write_bytes(edit_once(c, ch, chunk_file, refs, cont))
                log(f"{ch['id']} take {t}: got video in {time.time() - t0:.0f}s")
            m = conform(meta, ch, raw, conf)
            score = qc(c, meta, ch, src, conf, ref_qc_bytes)
        except Exception as e:
            log(f"{ch['id']} take {t} failed: {type(e).__name__}: {str(e)[:300]}")
            if "content_blocked" in str(e):
                # Safety refusal: do not retry or work around it; keep the original footage for this chunk.
                rep = {"chunk": ch["id"], "blocked": True, "reason": str(e)[:300], "takes": takes}
                save_json(report_p, rep)
                log(f"{ch['id']}: BLOCKED by Gemini safety filter -> original footage kept")
                return rep
            time.sleep(10 * t)
            continue
        keys = ("identity_match", "others_unchanged", "performance_preserved", "realism")
        s = {k: float(score.get(k, 0)) for k in keys}
        total = sum(s.values()) + 2 * s["others_unchanged"]  # weigh the absolute rule higher
        takes.append({"take": t, "raw_frames": m["frames"], "raw_size": f"{m['width']}x{m['height']}", **s,
                      "problems": score.get("problems", ""), "total": total, "file": conf.name})
        log(f"{ch['id']} take {t}: QC {s} | {score.get('problems', '')[:160]}")
        if min(s.values()) >= QC_PASS:
            break
    if not takes:
        raise RuntimeError(f"{ch['id']}: all takes failed")
    best = max(takes, key=lambda x: x["total"])
    shutil.copy(d_raw / best["file"], final)
    rep = {"chunk": ch["id"], "chosen_take": best["take"], "takes": takes}
    save_json(report_p, rep)
    log(f"{ch['id']}: chose take {best['take']}")
    return rep


def edit_all(meta, chunks, ref_paths, workers):
    for d in ("edited_raw", "edited", "qc"):
        (WORK / d).mkdir(exist_ok=True)
    ref_qc = frame_from_image(ref_paths[0])
    todo = [ch for ch in chunks if ch["edit"]]
    # chunks continuing a split shot run after their predecessor (handled by waiting inside edit_chunk);
    # submit in order so predecessors start first
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(edit_chunk, meta, ch, ref_paths, ref_qc): ch["id"] for ch in todo}
        errors = []
        for f in cf.as_completed(futs):
            try:
                f.result()
            except Exception as e:
                errors.append(f"{futs[f]}: {e}")
        if errors:
            raise RuntimeError("edit failures:\n" + "\n".join(errors))


def frame_from_image(p):
    return run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-vf", "scale=512:-2", "-f", "image2", "-c:v", "mjpeg",
                "-q:v", "3", "pipe:1"], text=False).stdout


# ---------------------------------------------------------------- assemble
def assemble(video, meta, chunks, name):
    OUT.mkdir(exist_ok=True)
    lst = WORK / "concat.txt"
    lines = []
    for ch in chunks:
        blocked = load_json(WORK / "qc" / f"{ch['id']}.json", {}).get("blocked")
        p = (WORK / "edited" if ch["edit"] and not blocked else WORK / "chunks") / f"{ch['id']}.mp4"
        assert p.exists(), f"missing {p}"
        lines.append(f"file '{p}'")
    lst.write_text("\n".join(lines) + "\n")
    out = OUT / f"{name}_faceswap.mp4"
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(video),
         "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
         "-r", meta["fps_str"], "-c:a", "copy", "-movflags", "+faststart", str(out)])
    m = ffprobe(out)
    log(f"final: {out} {m['width']}x{m['height']} {m['frames']} frames {m['duration']:.3f}s (source {meta['frames']} frames)")
    assert m["frames"] == meta["frames"], "frame count mismatch with source"
    cmp_ = OUT / f"{name}_compare.mp4"
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-i", str(out), "-filter_complex",
         "[0:v]scale=960:540,drawtext=text='ORIGINAL':x=20:y=60:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[a];"
         "[1:v]scale=960:540,drawtext=text='FACE SWAP':x=20:y=60:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[b];"
         "[a][b]hstack", "-an", "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", str(cmp_)])
    log(f"compare: {cmp_}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(WORK / "input.mp4"))
    ap.add_argument("--refs", nargs="+", default=[str(ROOT / "refs" / n) for n in
                                                  ("ref_front_hero.png", "ref_left_profile.png", "ref_right_profile.png")])
    ap.add_argument("--stages", default="analyze,classify,plan,cut,edit,assemble")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--name", default="movie")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    st = set(a.stages.split(","))
    video = Path(a.video)
    if not (WORK / "shots.json").exists():
        analyze(video)
    meta, shots = load_json(WORK / "meta.json"), load_json(WORK / "shots.json")
    if "classify" in st:
        shots = classify(video, meta, shots)
    if "plan" in st or (not (WORK / "plan.json").exists() and all("target_face_visible" in s for s in shots)):
        plan(meta, shots)
    chunks = load_json(WORK / "plan.json")
    if "cut" in st:
        cut(video, meta, chunks)
    if "edit" in st:
        edit_all(meta, chunks, a.refs, a.workers)
    if "assemble" in st:
        assemble(video, meta, chunks, a.name)


if __name__ == "__main__":
    main()
