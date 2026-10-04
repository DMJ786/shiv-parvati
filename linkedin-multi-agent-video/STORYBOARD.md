# Storyboard — "One request. A whole team of agents." (planned at 36 s; final cut 34.5 s, see README)

Persistent actor: the agent node / tree. It is born from the `True` token of the code card,
grows into the tree, collapses into the final answer card, and returns as the CTA glyph.

| Time | Viewer sees | Business job | Transition out (what survives) |
|---|---|---|---|
| 0.0–3.0 | Badge "NEW · OpenAI Responses API". "One request." then "A whole team / of AI agents." punch in; faint tree glyph behind | Hook: promise in 2 s | Type flies through camera; S2 already underneath |
| 3.0–6.0 | Single agent node + 6-step task list ticking one row at a time | Problem: sequential single agent | List exits right; node slides centre and grows into code card |
| 6.0–9.5 | Python code card; `multi_agent={"enabled": True}` typed + highlighted, callout "one flag" | The mechanism: one flag + beta header | `True` token becomes the /root node, card drops away |
| 9.5–13.5 | `spawn_agent` chip; edges draw to /root/researcher, /root/coder, /root/reviewer, then /root/researcher/docs | Model spawns its own subagent tree, path-addressed | Tree stays |
| 13.5–17.0 | Progress bars fill in parallel; 4th agent "queued" until a slot frees; `max_concurrent_subagents = 3` readout | Parallelism + the real default limit | Bars fade, tree stays |
| 17.0–22.0 | Carousel of 6 hosted actions; tree reacts to each (message dot, task chip, wait ring, interrupt, list flash) | Hosted orchestration: no client code | Tree dims |
| 22.0–25.5 | `response.output` log: multi_agent_call, multi_agent_call_output, agent_message (encrypted), message phase final_answer | Observability: 3 new item types | Log drops, tree returns |
| 25.5–29.0 | Results flow up edges, children retract, /root grows into the answer card | Synthesis into one answer | Card survives |
| 29.0–32.5 | Same card becomes "Know before you ship" checklist (beta header, auto compaction, unsupported params) | Practical, save-worthy detail | Card flies through camera |
| 32.5–36.0 | Tree glyph + "Stop prompting one agent. Start running a team." + docs path + save CTA + disclaimer | CTA on mute | End |

Facts used (from OpenAI's Multi-agent guide as indexed/quoted publicly, Oct 2026):
- `multi_agent.enabled` lets the root agent spawn a tree of subagents; root is `/root`, children use hierarchical paths.
- Beta: `client.beta.responses` with `betas=["responses_multi_agent=v1"]`, or header `OpenAI-Beta: responses_multi_agent=v1`.
- `max_concurrent_subagents` default 3, counts all descendants, excludes root.
- Hosted actions: spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents.
- New output items: multi_agent_call, multi_agent_call_output, agent_message (encrypted). Final answer = /root message with phase "final_answer".
- Server-side compaction auto-enabled; /responses/compact, reasoning.summary, max_tool_calls not supported.
