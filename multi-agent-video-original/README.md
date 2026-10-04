# "Stop prompting an agent. Start managing a team." (original design)

A 33.5 s, 1080x1350 (4:5), 30 fps LinkedIn video explaining OpenAI's Responses API **Multi-agent** beta,
designed from scratch: a warm paper look with kinetic word slams, sticky-note "agents", hand-drawn strings,
rubber stamps for the 6 hosted actions, and a receipt printer for the output items, cut with whip pans on a 120 BPM beat.

| File | What |
|---|---|
| `multi_agent_team.mp4` | **Upload this.** Video with original marimba score and sound design |
| `multi_agent_team_no_audio.mp4` | Same picture, no audio |
| `poster.png` | Thumbnail (end card) |
| `LINKEDIN_POST.md` | Post copy and posting tips |
| `contact_sheet.png` | Frames across the cut |
| `index.html` | The composition; open with `?play` to preview in a browser |
| `render.mjs` / `score.py` | Frame renderer (Playwright → ffmpeg) and procedural score + SFX |

## Beats
| Time | Scene |
|---|---|
| 0–2.5 | "ONE / API / CALL." slams → "One API call. *A whole team of agents.*" |
| 2.5–5.5 | One agent buried under a queue of task notes |
| 5.5–8 | `multi_agent.enabled` switch flips false → true; code card; the switch knob becomes `/root` |
| 8–12 | `/root` hires researcher, coder, reviewer (+ a docs grandchild), pinned with strings |
| 12–15.5 | Race: 1 agent step-by-step vs 3 subagents in parallel; `max_concurrent_subagents = 3` default |
| 15.5–20.5 | Six stamps: spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents |
| 20.5–24 | Receipt prints `response.output`: multi_agent_call, multi_agent_call_output, agent_message (encrypted), final message |
| 24–27 | Subagents fold into `/root`, which becomes the "One answer" card |
| 27–30 | Fine print: beta header, auto compaction, unsupported params |
| 30–33.5 | "Stop prompting an agent. *Start managing a team.*" + save CTA + disclaimer |

## Rebuild
```sh
npm install && pip install numpy scipy
python3 score.py && node render.mjs video silent.mp4
ffmpeg -i music.wav -i sfx.wav -filter_complex "[0][1]amix=inputs=2:normalize=0,alimiter=limit=0.7:attack=2:release=60:level=disabled,loudnorm=I=-14:TP=-2:LRA=7[a]" -map "[a]" -ar 48000 mix.wav
ffmpeg -i silent.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart multi_agent_team.mp4
```
Measured: no frozen stretches, −14.5 LUFS integrated, true peak −1.9 dBFS.

Facts come from OpenAI's Multi-agent guide as quoted in public sources (Oct 2026); it's a beta, so re-check before posting.
The end card says it's an independent explainer, not affiliated with OpenAI; no OpenAI logos are used.
