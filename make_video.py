#!/usr/bin/env python3
"""
Shiv & Parvati — ~1 min AI film via fal.ai Seedance 2.5.
Parvati's face is locked by using crops of parvati_sheet.png as the FIRST FRAME of every Parvati shot.

Setup:  pip install fal-client pillow   |   ffmpeg on PATH   |   export FAL_KEY=...
Run:    python make_video.py            (re-run anytime; finished clips are skipped)
Options (env): TAKES=3  ASPECT=9:16|16:9  I2V_MODEL=...  T2V_MODEL=...
Music:  drop music.mp3 in this folder before running for the final mix (else native Seedance audio only).
Picks:  after TAKES>1, create picks.json like {"02": 3, "11": 2} to choose takes, then re-run.
"""
import json, os, shutil, subprocess, sys, urllib.request
from pathlib import Path
from PIL import Image
import fal_client

ROOT = Path(__file__).resolve().parent
SHEET = ROOT / "parvati_sheet.png"
REFS, CLIPS, NORM = ROOT / "refs", ROOT / "clips", ROOT / "norm"
for d in (REFS, CLIPS, NORM):
    d.mkdir(exist_ok=True)

I2V = os.getenv("I2V_MODEL", "bytedance/seedance-2.5/image-to-video")
T2V = os.getenv("T2V_MODEL", "bytedance/seedance-2.5/text-to-video")
ASPECT = os.getenv("ASPECT", "9:16")
W, H = (720, 1280) if ASPECT == "9:16" else (1280, 720)
TAKES = int(os.getenv("TAKES", "1"))
XF = 0.4  # crossfade seconds between shots

# Crops of parvati_sheet.png (1122x1402) that avoid the sheet's captions/calligraphy
CROPS = {
    "hero":     (140, 250, 480, 660),   # panel 01 close-up face
    "tapasya":  (827, 258, 1117, 650),  # panel 03 meditation, namaste
}

FACE_LOCK = (" Keep the woman exactly identical to the first frame: same face shape, eyes, nose, lips, skin tone, "
             "bindi, maang tikka, jhumka earrings, curly dark hair with jasmine, maroon silk sari with gold border. "
             "Do not alter or beautify her face.")
LOOK = " Photoreal cinematic film, Himalayan snow peaks, natural light, shallow depth of field. No text, captions or watermark."
SAGES = ("Three elderly Hindu rishis with long white beards, matted grey hair, saffron and ochre cloth, rudraksha beads, "
         "in the snowy Himalayas.")
SHIVA = ("Lord Shiva with blue-grey ash-smeared skin, long matted jata with a crescent moon, three white tripundra lines "
         "on his forehead, a cobra around his neck, rudraksha beads, trishul with damru beside him, on a misty Himalayan summit.")

# id, mode, ref, action prompt, sound prompt
SHOTS = [
    ("01", "i2v", "tapasya", "Wide dawn feel. She sits in deep meditation, hands in namaste, eyes closed, perfectly still. Slow camera push-in, mist drifting past.",
     "mountain wind, one distant temple bell, no speech, no music"),
    ("02", "i2v", "hero", "Close-up. She slowly closes her eyes, face becoming calm and devoted. Wind lifts loose curls. Warm golden rim light.",
     "soft wind, gentle breath, no speech, no music"),
    ("03", "i2v", "tapasya", "Locked-off camera. She stays completely still while the seasons change around her: snowfall, then spring blossoms, then falling autumn leaves.",
     "wind turning into birdsong then rustling leaves, no music"),
    ("04", "i2v", "hero", "She lifts her gaze toward the peaks, expression turning resolute and strong. Clouds part and sunlight falls on her face. Slow low-angle move.",
     "wind swell, distant bell, no speech"),
    ("05", "i2v", "tapasya", "Slow push-in toward her joined hands and bangles, lips moving in silent prayer, a small diya flame flickering beside her.",
     "crackling diya flame, soft bangle chime, quiet breath, no speech"),
    ("06", "t2v", None, SAGES + " They peer from behind a snowy boulder at a woman meditating on a distant ledge, whispering in awe. Handheld medium shot.",
     "wind, hushed murmurs with no clear words, no music"),
    ("07", "t2v", None, SAGES + " They climb ancient stone steps toward a misty summit with walking sticks. Tracking shot from behind.",
     "footsteps on stone, walking sticks tapping, wind"),
    ("08", "t2v", None, SAGES + " They bow with folded hands before a meditating figure hidden in fog, speaking reverently. Medium shot.",
     "low reverent murmurs with no clear words, distant conch shell"),
    ("09", "t2v", None, SHIVA + " Extreme close-up, eyes closed in deep meditation, snow settling, completely still.",
     "near silence, very low drone"),
    ("10", "t2v", None, SHIVA + " His eyes slowly open and a faint gentle smile forms. Warm golden light floods the frame.",
     "single deep temple bell strike, then silence"),
    ("11", "i2v", "hero", "She smiles softly as a single tear rolls down her cheek. Warm golden light fills the frame. Slow push-in.",
     "soft wind, lingering bell resonance, no speech"),
]


def run(cmd):
    print("  $", " ".join(map(str, cmd))[:160])
    subprocess.run(list(map(str, cmd)), check=True)


def probe(path, entry):
    out = subprocess.run(["ffprobe", "-v", "error", *entry, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def make_refs():
    sheet = Image.open(SHEET).convert("RGB")
    for name, box in CROPS.items():
        dst = REFS / f"{name}.png"
        if dst.exists():
            continue
        im = sheet.crop(box)
        scale = 1280 / max(im.size)  # upscale small crops so the model gets detail
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        im.save(dst)
        print(f"ref -> {dst} {im.size}")


_uploaded = {}
def ref_url(name):
    if name not in _uploaded:
        _uploaded[name] = fal_client.upload_file(str(REFS / f"{name}.png"))
    return _uploaded[name]


def generate(sid, mode, ref, action, sound, take):
    dst = CLIPS / f"{sid}_t{take}.mp4"
    if dst.exists():
        return dst
    prompt = action + (FACE_LOCK if mode == "i2v" else "") + LOOK + " Sound: " + sound + "."
    args = {"prompt": prompt, "aspect_ratio": ASPECT, "duration": "5", "resolution": "720p", "generate_audio": True}
    if mode == "i2v":
        args["image_url"] = ref_url(ref)
    model = I2V if mode == "i2v" else T2V
    print(f"\n[{sid} take {take}] {model}")
    for attempt, a in enumerate([args, {k: v for k, v in args.items() if k not in ("duration", "resolution")}]):
        try:
            res = fal_client.subscribe(model, arguments=a, with_logs=False)
            urllib.request.urlretrieve(res["video"]["url"], dst)
            print(f"  saved {dst}")
            return dst
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
    sys.exit(f"Shot {sid} failed twice — check the model's input schema on fal.ai and adjust args.")


def normalize(src, dst):
    if dst.exists():
        return dst
    has_audio = bool(probe(src, ["-select_streams", "a", "-show_entries", "stream=index"]).get("streams"))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=24,format=yuv420p,setsar=1"
    cmd = ["ffmpeg", "-y", "-i", src]
    if not has_audio:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
    cmd += ["-vf", vf, "-map", "0:v", "-map", "0:a" if has_audio else "1:a",
            "-af", "aresample=48000", "-ac", "2", "-shortest",
            "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-c:a", "aac", "-b:a", "192k", dst]
    run(cmd)
    return dst


def end_card(last_clip):
    """5 s title card built on the final frame of the last shot, softly blurred and darkened."""
    dst = NORM / "99_endcard.mp4"
    if dst.exists():
        return dst
    still = NORM / "last_frame.png"
    run(["ffmpeg", "-y", "-sseof", "-0.2", "-i", last_clip, "-frames:v", "1", still])
    font = subprocess.run(["fc-match", "-f", "%{file}", "serif"], capture_output=True, text=True).stdout.strip()
    fs = 40 if ASPECT == "9:16" else 48
    def txt(t, y, size, delay):
        return (f"drawtext=fontfile='{font}':text='{t}':fontcolor=0xF3E3B8:fontsize={size}:"
                f"x=(w-text_w)/2:y={y}:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"alpha='if(lt(t,{delay}),0,min(1,(t-{delay})/1.2))'")
    vf = (f"scale={W}:{H},gblur=sigma=6,eq=brightness=-0.12:saturation=0.85,"
          f"zoompan=z='1+0.0008*on':d=1:s={W}x{H}:fps=24,"
          + txt("Same Soul. A Different Form.", "h*0.40", fs, 0.5) + ","
          + txt("Always Divine.", "h*0.40+" + str(fs + 22), fs, 1.3) + ","
          + txt("HAR HAR MAHADEV  |  SHIV & PARVATI", "h*0.40+" + str(2 * fs + 70), fs // 2, 2.2)
          + ",fade=t=out:st=4.2:d=0.8,format=yuv420p,setsar=1")
    run(["ffmpeg", "-y", "-loop", "1", "-t", "5", "-i", still,
         "-f", "lavfi", "-t", "5", "-i", "anullsrc=r=48000:cl=stereo",
         "-vf", vf, "-r", "24", "-c:v", "libx264", "-crf", "17", "-c:a", "aac", "-b:a", "192k", "-shortest", dst])
    return dst


def stitch(parts, out):
    durs = [float(probe(p, ["-show_entries", "format=duration"])["format"]["duration"]) for p in parts]
    cmd = ["ffmpeg", "-y"]
    for p in parts:
        cmd += ["-i", p]
    f, offset, v, a = [], 0.0, "[0:v]", "[0:a]"
    for i in range(1, len(parts)):
        offset += durs[i - 1] - XF
        f.append(f"{v}[{i}:v]xfade=transition=fade:duration={XF}:offset={offset:.3f}[v{i}]")
        f.append(f"{a}[{i}:a]acrossfade=d={XF}[a{i}]")
        v, a = f"[v{i}]", f"[a{i}]"
    f.append(f"{v}format=yuv420p[vout]")
    cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", a,
            "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-c:a", "aac", "-b:a", "192k", out]
    run(cmd)
    return sum(durs) - XF * (len(parts) - 1)


def final_mix(stitched, total, out):
    music = ROOT / "music.mp3"
    if not music.exists():
        run(["ffmpeg", "-y", "-i", stitched, "-c:v", "copy",
             "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", out])
        return
    fc = (f"[0:a]volume=0.5[amb];"
          f"[1:a]atrim=0:{total:.2f},volume=0.9,afade=t=in:d=2,afade=t=out:st={total - 3:.2f}:d=3[mus];"
          f"[amb][mus]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    run(["ffmpeg", "-y", "-i", stitched, "-i", music, "-filter_complex", fc,
         "-map", "0:v", "-map", "[out]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", out])


def main():
    if not os.getenv("FAL_KEY"):
        sys.exit("Set FAL_KEY first.")
    for tool in ("ffmpeg", "ffprobe", "fc-match"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH.")
    make_refs()
    picks = json.loads((ROOT / "picks.json").read_text()) if (ROOT / "picks.json").exists() else {}
    parts = []
    for sid, mode, ref, action, sound in SHOTS:
        for t in range(1, TAKES + 1):
            generate(sid, mode, ref, action, sound, t)
        chosen = CLIPS / f"{sid}_t{picks.get(sid, 1)}.mp4"
        parts.append(normalize(chosen, NORM / f"{sid}.mp4"))
    parts.append(end_card(parts[-1]))
    total = stitch(parts, ROOT / "stitched.mp4")
    final_mix(ROOT / "stitched.mp4", total, ROOT / "shiv_parvati_final.mp4")
    print(f"\nDone -> {ROOT / 'shiv_parvati_final.mp4'}  ({total:.1f}s)")


if __name__ == "__main__":
    main()
