# MULTI AGENT: a movie-teaser cut (34 s, 1080x1350)

A cinematic teaser for OpenAI's Responses API **Multi-agent** beta: a dark particle universe, trailer title cards,
hard silences, "braam" hits and a title drop, ending on a billing-block "cast" of the API's parts.

| Time | Beat |
|---|---|
| 0–5 | Cold open: one lone star, tasks orbiting it. "EVERY AGENT / HAS WORKED ALONE. / ONE TASK AT A TIME." Heartbeat and an accelerating clock |
| 5.0 | Hard cut to black and silence |
| 5.3 | "UNTIL NOW." braam, white flash, warp-speed stars |
| 6.6–8.6 | `multi_agent: { "enabled": true }` types out; a shockwave fires from `true` |
| 8.6–11.5 | The star splits into a constellation: /root → researcher, coder, reviewer → docs. "ONE REQUEST. A WHOLE TEAM." |
| 11.5–14.5 | Hyperspace: three subagent light lanes in parallel, progress counters, `max_concurrent_subagents = 3` |
| 14.6–18 | Six hits, one per hosted action, each with its own light graphic |
| 18–20.5 | "EVERY MOVE. ON THE RECORD." The new output item types over data rain |
| 20.5–23 | Everything spirals into one point, "INTO ONE ANSWER.", white-out, silence |
| 23.4–27.5 | Title drop: **MULTI AGENT**, OpenAI Responses API, NOW IN BETA, with flare and sweep |
| 27.5–30.5 | "THE CAST": billing block of flags, actions, output items and fine print |
| 30.5–34 | "STOP PROMPTING AN AGENT. START DIRECTING A TEAM." Save CTA and disclaimer |

Files: `multi_agent_teaser.mp4` (upload this), `poster.png` (thumbnail), `LINKEDIN_POST.md`, `contact_sheet.png`,
and the source: `index.html` (canvas 2D world with bloom, 3D projection and particles; every frame is a pure
function of t; open with `?play` to preview), `render.mjs` (Playwright → ffmpeg) and `score.py` (procedural trailer
sound design).

Rebuild: `npm install && pip install numpy scipy && python3 score.py && node render.mjs video silent.mp4`, then
loudnorm `mix_raw.wav` to −14 LUFS (see the ffmpeg lines in the other folders) and mux.

Measured: no frozen stretches, −15.0 LUFS integrated, 6.8 LU range (trailer dynamics), true peak −2.0 dBFS.
Facts come from OpenAI's Multi-agent guide as quoted publicly (Oct 2026); it's a beta, so re-check before posting.
The end card says it's an independent explainer, not affiliated with OpenAI; no OpenAI logos are used.
