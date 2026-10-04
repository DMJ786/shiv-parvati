import json, soundfile as sf, numpy as np
from kokoro_onnx import Kokoro
k = Kokoro("kokoro.onnx", "voices.bin")
VOICE, SPEED = "af_heart", 1.0
LINES = [
 ("L1", "Every AI agent you've built... has worked alone. One task, at a time."),
 ("L2", "Until now."),
 ("L3", "OpenAI's Responses API now has Multi-agent. Flip one flag..."),
 ("L4", "and the model spawns its own team of subagents, under one root agent."),
 ("L5", "They work in parallel. Up to three at a time, by default."),
 ("L6", "The API runs the teamwork for you. Spawn. Message. Follow up. Wait. Interrupt. List."),
 ("L7", "Every step is recorded in the response, so you see who did what."),
 ("L8", "Then the root agent merges it all into one answer."),
 ("L9", "Multi-agent. Now in beta."),
 ("L10", "Check the docs for what's supported today."),
 ("L11", "Stop prompting an agent. Start directing a team."),
]
out = {}
for lid, text in LINES:
    s, sr = k.create(text, voice=VOICE, speed=SPEED, lang="en-us")
    nz = np.where(np.abs(s) > 0.01)[0]; s = s[max(0, nz[0] - 600): nz[-1] + 2400]
    sf.write(f"{lid}.wav", s, sr); out[lid] = {"text": text, "dur": round(len(s) / sr, 2), "sr": sr}
    print(lid, out[lid]["dur"], text)
json.dump(out, open("vo_dur.json", "w"), indent=1)
print("total speech", round(sum(v["dur"] for v in out.values()), 2))
