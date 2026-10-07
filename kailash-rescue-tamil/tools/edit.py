#!/usr/bin/env python3
"""Assemble the rescue short. Usage: edit.py VARIANT(A|B) CAPTIONS(0|1) OUT.mp4
Hard cuts on movement (no flashes/dissolves), 1080x1920 @ 24 fps, Veo native sound + Tamil whisper + score from the catch."""
import json, subprocess, sys
variant, caps, out = sys.argv[1], sys.argv[2] == "1", sys.argv[3]
T = json.load(open("edit/trims.json"))          # {"A":[in,out], ...}
opening = [("B_rej1", *T["B"]), ("A", T["B"][1], T["A"][1])] if variant == "B" else [("A", *T["A"])]
SHOTS = opening + [("C", *T["C"]), ("D", *T["D"]), ("E", *T["E"]), ("G", *T["G"]), ("H", *T["H"])]
inputs, fc, starts, t = [], [], [], 0.0
for i, (c, a, b) in enumerate(SHOTS):
    inputs += ["-i", f"clips/{c}.mp4"]
    base = f"[{i}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps=24,scale=1080:1920,setsar=1"
    if c == "H":   # start in the same cold storm light as the previous shot and warm up gradually (no lighting jump at the cut)
        fc.append(f"{base},split[h1_{i}][h2_{i}]")
        fc.append(f"[h1_{i}]colortemperature=temperature=10500,eq=saturation=0.78:brightness=-0.05:contrast=1.03[hc_{i}]")
        fc.append(f"[hc_{i}][h2_{i}]blend=all_expr='A*(1-min(T/3.5\\,1))+B*min(T/3.5\\,1)',format=yuv420p[v{i}]")
    else:
        fc.append(f"{base},format=yuv420p[v{i}]")
    fc.append(f"[{i}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.02,afade=t=out:st={b-a-0.03:.3f}:d=0.03[a{i}]")
    starts.append(t); t += b - a
total = t
n = len(SHOTS)
fc.append("".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,eq=contrast=1.04:saturation=1.03[vc]")
fc.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,volume=0.9[amb]")
vlast, idx = "vc", n
if caps:
    o0, o1 = T["open_txt"], T["end_txt"]
    inputs += ["-loop", "1", "-t", f"{total:.3f}", "-i", "edit/ov_open.png", "-loop", "1", "-t", f"{total:.3f}", "-i", "edit/ov_end.png"]
    fc.append(f"[{idx}:v]format=rgba,fade=t=in:st={o0[0]}:d=0.25:alpha=1,fade=t=out:st={o0[1]-0.25}:d=0.25:alpha=1[o0]")
    fc.append(f"[{idx+1}:v]format=rgba,fade=t=in:st={total+o1}:d=0.5:alpha=1[o1]")
    fc.append(f"[{vlast}][o0]overlay=0:0:shortest=1[vx];[vx][o1]overlay=0:0:shortest=1[vout]"); vlast = "vout"; idx += 2
else:
    fc.append(f"[{vlast}]null[vout]")
catch = starts[n - 4]                             # start of the catch shot
w = T["whisper_at"]; wi, mi = idx, idx + 1
inputs += ["-i", "audio/siva_whisper.wav", "-i", "audio/score_0.mp3"]
fc.append(f"[{wi}:a]aresample=48000,highpass=f=120,volume=1.6,adelay={int(w*1000)}|{int(w*1000)}[wh]")
m0 = T["music_in"]
fc.append(f"[{mi}:a]atrim={m0}:{m0 + total - catch + 0.5},asetpts=PTS-STARTPTS,afade=t=in:d=1.2,volume=0.55,adelay={int(catch*1000)}|{int(catch*1000)}[mus]")
fc.append(f"[amb][wh][mus]amix=inputs=3:normalize=0,atrim=0:{total:.3f},afade=t=out:st={total-0.35:.3f}:d=0.35,"
          f"alimiter=limit=0.7:level=disabled,loudnorm=I=-14:TP=-2:LRA=11,alimiter=limit=0.79:level=disabled[aout]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "256k",
       "-movflags", "+faststart", "-t", f"{total:.3f}", out]
subprocess.run(cmd, check=True)
print(json.dumps({"out": out, "total": round(total, 3), "starts": [round(s, 2) for s in starts]}))
