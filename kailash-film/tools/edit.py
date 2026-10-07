#!/usr/bin/env python3
"""Assemble the film: trims + xfades + grade + title (video), and music cut to picture + Veo native SFX (audio)."""
import subprocess, json
FPS = 24
# (clip, src_in, src_out, transition_into_next, xfade_dur)
SHOTS = [("s1", 0.3, 4.9, "fade", .3), ("s2", 1.0, 5.2, "fade", .25), ("s3", 1.6, 7.4, "fade", .4),
         ("s4", 0.8, 4.6, "fadewhite", .5), ("s5", 0.2, 5.5, "fadewhite", .45), ("s6", 0.4, 6.2, "fade", .4),
         ("s7", 0.4, 5.6, "fade", .5), ("s8", 0.3, 7.9, None, 0)]
inputs, fc, starts = [], [], []
t = 0.0
for i, (c, a, b, tr, xd) in enumerate(SHOTS):
    inputs += ["-i", f"clips/{c}.mp4"]
    fc.append(f"[{i}:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={FPS},scale=1080:1920,setsar=1,format=yuv420p[v{i}]")
    fc.append(f"[{i}:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
    starts.append(t); t += (b - a) - (xd if tr else 0)
total = starts[-1] + (SHOTS[-1][2] - SHOTS[-1][1])
# video xfade chain
cur = "v0"; off = 0.0
for i in range(len(SHOTS) - 1):
    c, a, b, tr, xd = SHOTS[i]
    off += (b - a) - xd
    nxt = f"x{i}"; fc.append(f"[{cur}][v{i+1}]xfade=transition={tr}:duration={xd}:offset={off:.3f}[{nxt}]"); cur = nxt
# grade: gentle contrast + teal/gold split, vignette, then title fade-in on the last shot
T0 = starts[-1] + 2.2
fc.append(f"[{cur}]eq=contrast=1.06:saturation=1.05,colorbalance=bs=.03:rh=.02:gh=.01:bh=-.02,vignette=PI/5[g]")
fc.append(f"[{len(SHOTS)}:v]format=rgba,fade=t=in:st={T0:.2f}:d=1.2:alpha=1[ti]")
fc.append(f"[g][ti]overlay=0:0:shortest=0,fade=t=out:st={total-0.6:.2f}:d=0.6[vout]")
inputs += ["-loop", "1", "-t", f"{total:.2f}", "-i", "kf/title.png"]
# native Veo audio: crossfade chain at the same offsets
cur = "a0"
for i in range(len(SHOTS) - 1):
    xd = SHOTS[i][4]; nxt = f"ax{i}"; fc.append(f"[{cur}][a{i+1}]acrossfade=d={xd}[{nxt}]"); cur = nxt
fc.append(f"[{cur}]volume=0.55[sfx]")
# music: tension 2.5-16.6 -> film 0, quiet 17.0-20.5 -> darkness, then 37.3-end from the catch (hard cut on the hit)
dark, catch = starts[3], starts[4] + 0.15
mi = len(SHOTS) + 1
inputs += ["-i", "music/score_0.mp3"]
fc.append(f"[{mi}:a]atrim=2.5:{2.5+dark+.3},asetpts=PTS-STARTPTS,afade=t=out:st={dark-.2:.2f}:d=0.5[m1]")
fc.append(f"[{mi}:a]atrim=17.0:{17.0+(catch-dark)+.3},asetpts=PTS-STARTPTS,volume=0.7,afade=t=in:d=0.4,adelay={int(dark*1000)}|{int(dark*1000)}[m2]")
fc.append(f"[{mi}:a]atrim=37.3:60.5,asetpts=PTS-STARTPTS,afade=t=in:d=0.05,adelay={int(catch*1000)}|{int(catch*1000)}[m3]")
fc.append(f"[m1][m2][m3]amix=inputs=3:normalize=0,volume=0.8[mus]")
fc.append(f"[mus][sfx]amix=inputs=2:normalize=0,atrim=0:{total:.2f},afade=t=out:st={total-1.0:.2f}:d=1.0,"
          f"alimiter=limit=0.85:level=disabled,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
       "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "kailash.mp4"]
subprocess.run(cmd, check=True)
print(json.dumps({"total": round(total, 2), "starts": [round(s, 2) for s in starts]}))
