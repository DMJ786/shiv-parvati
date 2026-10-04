# LinkedIn video: OpenAI Responses API "Multi-agent"

A 34.5 s, 1080x1350 (4:5), 30 fps explainer built with the
[motion-video-kit](https://github.com/echris6/motion-video-kit) `business-motion-film` workflow:
storyboard → code-built motion (deterministic HTML, every frame a pure function of t) →
independent-critic Gauntlet → measured quality bar.

| File | What |
|---|---|
| `multi_agent_linkedin.mp4` | **Upload this.** Master with score + sound design |
| `multi_agent_linkedin_no_audio.mp4` | Same picture, no audio (swap in your own licensed track) |
| `poster.png` | Thumbnail (end card) |
| `LINKEDIN_POST.md` | Post copy, short variant, posting tips |
| `contact_sheet.png` | Frames sampled across the final cut |
| `STORYBOARD.md` | Beats, the persistent actor, and the facts used |
| `index.html` | The composition (open with `?play` to preview in a browser) |
| `render.mjs` / `score.py` | Frame renderer (Playwright → ffmpeg) and procedural 120 BPM score + SFX |

## Rebuild
```sh
npm install                       # playwright-core; uses a local Chromium (edit executablePath in render.mjs)
pip install numpy scipy
python3 score.py                  # music.wav + sfx.wav
node render.mjs video silent.mp4  # 1035 frames
ffmpeg -i music.wav -i sfx.wav -filter_complex "[0][1]amix=inputs=2:normalize=0,alimiter=limit=0.7:attack=2:release=60:level=disabled,loudnorm=I=-14:TP=-2:LRA=7[a]" -map "[a]" -ar 48000 mix.wav
ffmpeg -i silent.mp4 -i mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart multi_agent_linkedin.mp4
```

## Gauntlet ledger
| Round | Found | Changed |
|---|---|---|
| Self-check (stills) | Empty lower half on the hook; CTA text over the outgoing card; stray edge on collapse | Re-laid out the hook, re-timed the CTA, edges fade on collapse |
| Measure | Frozen time 6.8 s (target ≈ 1 s) | Camera push that resets only under transitions, plus data pulses along the edges → **0.0 s** |
| Critic 1 (fresh agent) | Static hook, empty containers at 6.0/22.0/27.2/29.0, action counter rolled back, dot launched from the wrong code line, small text, ghosted crossfades, too long | Tree is the hero from frame 0 and shrinks into the agent orb; content fills as containers grow; counter fixed; dot mapped through the camera; larger type; overlaps removed; cut 36 → 34.5 s with the score re-timed |
| Critic 2 (fresh agent, item-by-item verification) | Most items fixed; CTA tree touched the headline; docs edge crossed a label; /root label close to the subtitle | CTA re-laid out, labels on opaque pills, docs node moved, /root label beside the node |
| Final check | Interrupt marker visible in the top-left corner outside the tree scenes | Hidden outside the tree; corners verified |

Measured on the final file: frozen time 0.0 s, −13.5 LUFS integrated, true peak −1.6 dBFS, LRA 2.5 LU.
Limits: the critics sampled frames (every 0.25 s plus dense windows around transitions), not every frame;
nobody listened to the audio, only measured it. The score is procedural (no stock library was reachable);
swap in a licensed track if you prefer.

## Facts and honesty
Feature details come from OpenAI's Multi-agent guide as quoted in public search results and developer issue
threads (Oct 2026); the docs site itself was not directly reachable from the build machine. It's a beta,
so re-check names before posting. The on-screen run ("Fix the flaky test suite") is an illustrative example.
The end card says: independent explainer, not affiliated with OpenAI. No OpenAI logos are used.
