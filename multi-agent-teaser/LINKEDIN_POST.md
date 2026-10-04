# LinkedIn post copy (teaser cut)

## Main post

Every AI agent has worked alone.
One task at a time.

Until now. 🎬

OpenAI's Responses API just got **Multi-agent** (beta): flip one flag and the model spawns its own team of subagents, runs them in parallel, and merges everything into one final answer.

The cast:
🎯 `multi_agent: { enabled: true }`: one flag
🌳 `/root` plus its subagents (`/root/researcher`, `/root/coder`, …)
⚡ `max_concurrent_subagents`: 3 by default, across the whole tree
🎬 6 hosted actions: spawn_agent · send_message · followup_task · wait_agent · interrupt_agent · list_agents
🧾 New output items: multi_agent_call · multi_agent_call_output · agent_message
✅ `/root` delivers the message with phase "final_answer"

Fine print: opt in with the `responses_multi_agent=v1` beta. Server-side compaction is automatic. reasoning.summary, max_tool_calls and /responses/compact aren't supported yet.

Stop prompting an agent.
Start directing a team.

Which workflow are you splitting across agents first? 👇

#AI #AIAgents #OpenAI #MultiAgent #LLM #GenerativeAI #BuildInPublic

---

## Short version

Every AI agent has worked alone. Until now.

Multi-agent just landed in the OpenAI Responses API (beta): one flag → a whole team of subagents, running in parallel, merged into one answer.

34-second teaser 🎬👆 Docs in the first comment.

#AIAgents #OpenAI #LLM

---

## Posting tips
- Upload the MP4 natively; don't post a link. Post the docs link as the first comment:
  https://developers.openai.com/api/docs/guides/responses-multi-agent
- Thumbnail: `poster.png` (the "MULTI AGENT" title frame).
- The cards carry the story, so it works muted. The sound design is built for headphones; the "UNTIL NOW" and title hits land on beat.
- Post Tue–Thu morning in your audience's time zone, and reply to comments in the first hour.
