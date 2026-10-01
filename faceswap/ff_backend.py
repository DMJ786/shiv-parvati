#!/usr/bin/env python3
"""
FaceFusion backend for the face-replacement pipeline (local, no Gemini edit model).

Reuses faceswap.py's shot analysis/classification (work/shots.json), then for every shot in which
the pink-shirt man's face is visible:
  1. asks the vision model which face (counted left -> right) is the pink-shirt man on the shot's
     middle frame, so FaceFusion's reference selector locks onto him and nobody else;
  2. runs FaceFusion headless on just that shot: inswapper_128 face swap (+ optional face enhancer),
     face_selector_mode=reference, so only faces similar to the chosen reference face are swapped;
  3. conforms the result to the exact source frame count.
Shots without his face are copied untouched; everything is concatenated back frame-accurately.

Needs network access to github.com (FaceFusion code + model releases) and huggingface.co (models).
Setup:  git clone https://github.com/facefusion/facefusion work/facefusion && pip install -r work/facefusion/requirements.txt
Usage:  python ff_backend.py --shots 0            # test one shot -> output/ff_shot00_compare.mp4
        python ff_backend.py                      # all shots -> output/movie_facefusion.mp4
"""
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path

import faceswap as fs

FF_DIR = Path(os.getenv("FACEFUSION_DIR", fs.WORK / "facefusion"))
SOURCE = os.getenv("FF_SOURCE", str(fs.ROOT / "refs" / "ref_front_hero.png"))
D_SHOT, D_FF = fs.WORK / "ff_shots", fs.WORK / "ff_out"

REF_PROMPT = """This is one frame from a film. Count the human FACES visible in it from LEFT to RIGHT
(by the horizontal centre of each face; partial or profile faces count, faces with no visible eyes/nose/mouth do not).
The TARGET is the adult man in the LIGHT PINK shirt.
Answer JSON only: {"num_faces": n, "target_index_from_left": i}   // 0-based; -1 if the target's face is not visible"""


def ref_for_shot(c, video, meta, s):
    """Pick a reference frame inside the shot and the target's left->right face index on it."""
    if "ff_ref" in s:
        return s["ff_ref"]
    fps = meta["fps"]
    n = s["end"] - s["start"]
    for rel in (n // 2, n // 4, 3 * n // 4, 1):
        j = fs.gemini_json(c, [fs.frame_jpeg(video, s["start"] + rel, fps)], REF_PROMPT)
        idx = int(j.get("target_index_from_left", -1))
        if idx >= 0:
            s["ff_ref"] = {"frame": rel, "position": idx, "num_faces": int(j.get("num_faces", 0))}
            return s["ff_ref"]
    s["ff_ref"] = None
    return None


def cut_shot(video, meta, s, out):
    if out.exists() and fs.ffprobe(out)["frames"] == s["end"] - s["start"]:
        return
    fs.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf",
            f"trim=start_frame={s['start']}:end_frame={s['end']},setpts=PTS-STARTPTS",
            "-an", "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", meta["fps_str"], str(out)])


def facefusion(src_clip, out, ref, enhance, threads):
    procs = ["face_swapper"] + (["face_enhancer"] if enhance else [])
    cmd = [sys.executable, "facefusion.py", "headless-run",
           "--source-paths", SOURCE,
           "--target-path", str(src_clip.resolve()),
           "--output-path", str(out.resolve()),
           "--processors", *procs,
           "--face-swapper-model", "inswapper_128",
           "--face-swapper-pixel-boost", "512x512",        # swap at higher internal res for 1080p close-ups
           "--face-selector-mode", "reference",
           "--face-selector-order", "left-right",
           "--reference-face-position", str(ref["position"]),
           "--reference-frame-number", str(ref["frame"]),
           "--reference-face-distance", "0.5",             # tighter = less chance of grabbing another man
           "--face-mask-types", "box", "occlusion",        # occlusion mask keeps hands/coin in front of the face
           "--face-mask-blur", "0.3",
           "--execution-providers", "cpu",
           "--execution-thread-count", str(threads),
           "--output-video-encoder", "libx264",
           "--output-video-quality", "95"]
    if enhance:
        cmd += ["--face-enhancer-model", "gfpgan_1.4", "--face-enhancer-blend", "35"]  # low blend keeps skin texture
    r = subprocess.run(cmd, cwd=FF_DIR, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(f"facefusion failed ({r.returncode}):\n{(r.stdout + r.stderr)[-2000:]}")


def conform(meta, n, raw, out):
    fs.conform(meta, {"id": raw.stem, "frames": n}, raw, out)


def compare(a, b, out):
    fs.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(a), "-i", str(b), "-filter_complex",
            "[0:v]scale=960:540,drawtext=text='ORIGINAL':x=20:y=60:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[a];"
            "[1:v]scale=960:540,drawtext=text='FACEFUSION':x=20:y=60:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6[b];"
            "[a][b]hstack", "-an", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(fs.WORK / "input.mp4"))
    ap.add_argument("--shots", default="", help="comma-separated shot ids to process (test mode); default all")
    ap.add_argument("--no-enhance", action="store_true")
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 4)
    a = ap.parse_args()
    if not (FF_DIR / "facefusion.py").exists():
        sys.exit(f"FaceFusion not found in {FF_DIR}; see setup in this file's docstring")
    video = Path(a.video)
    meta, shots = fs.load_json(fs.WORK / "meta.json"), fs.load_json(fs.WORK / "shots.json")
    if not shots or not all("target_face_visible" in s for s in shots):
        sys.exit("run `python faceswap.py --stages analyze,classify,plan` first")
    D_SHOT.mkdir(exist_ok=True); D_FF.mkdir(exist_ok=True); fs.OUT.mkdir(exist_ok=True)
    only = {int(x) for x in a.shots.split(",") if x != ""}
    c = fs.client()
    for s in shots:
        if only and s["id"] not in only:
            continue
        sid = f"s{s['id']:02d}"
        clip, final = D_SHOT / f"{sid}.mp4", D_FF / f"{sid}.mp4"
        cut_shot(video, meta, s, clip)
        if final.exists():
            continue
        ref = ref_for_shot(c, video, meta, s) if s["target_face_visible"] else None
        fs.save_json(fs.WORK / "shots.json", shots)
        if not ref:
            shutil.copy(clip, final)
            fs.log(f"{sid} [{s['t0']:.2f}-{s['t1']:.2f}] no target face -> untouched")
            continue
        fs.log(f"{sid} [{s['t0']:.2f}-{s['t1']:.2f}] facefusion: target face #{ref['position']} of {ref['num_faces']} on frame {ref['frame']}…")
        raw = D_FF / f"{sid}_raw.mp4"
        facefusion(clip, raw, ref, not a.no_enhance, a.threads)
        conform(meta, s["end"] - s["start"], raw, final)
        fs.log(f"{sid} done")
    if only:
        for i in sorted(only):
            sid = f"s{i:02d}"
            compare(D_SHOT / f"{sid}.mp4", D_FF / f"{sid}.mp4", fs.OUT / f"ff_shot{i:02d}_compare.mp4")
            fs.log(f"compare -> {fs.OUT / f'ff_shot{i:02d}_compare.mp4'}")
        return
    lst = fs.WORK / "ff_concat.txt"
    lst.write_text("".join(f"file '{D_FF / ('s%02d.mp4' % s['id'])}'\n" for s in shots))
    out = fs.OUT / "movie_facefusion.mp4"
    fs.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(video),
            "-map", "0:v:0", "-map", "1:a?", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p",
            "-r", meta["fps_str"], "-c:a", "copy", "-movflags", "+faststart", str(out)])
    m = fs.ffprobe(out)
    assert m["frames"] == meta["frames"], f"frame count {m['frames']} != source {meta['frames']}"
    compare(video, out, fs.OUT / "movie_facefusion_compare.mp4")
    fs.log(f"final -> {out} ({m['frames']} frames, {m['duration']:.3f}s)")


if __name__ == "__main__":
    main()
