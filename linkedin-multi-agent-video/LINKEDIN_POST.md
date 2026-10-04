# LinkedIn post copy

## Main post (paste with the video)

One API request.
A whole team of AI agents. 🤖🤖🤖

OpenAI just added **Multi-agent** to the Responses API (beta), and it quietly changes how we build agents.

Before: one agent, one thread, every step in sequence.
Now: set one flag and the model spawns its own subagents, runs them in parallel, and merges their work into one answer.

What's actually in it:
→ `multi_agent: { enabled: true }` turns it on (opt in with the `responses_multi_agent=v1` beta)
→ The root agent is `/root`; subagents get paths like `/root/researcher`
→ `max_concurrent_subagents` defaults to 3 and counts the whole tree
→ 6 hosted actions: spawn_agent, send_message, followup_task, wait_agent, interrupt_agent, list_agents
→ The API runs that orchestration, not your client code
→ New output items (multi_agent_call, multi_agent_call_output, agent_message) let you see every step

Good to know before you ship:
• Server-side compaction is turned on automatically
• reasoning.summary, max_tool_calls and /responses/compact aren't supported in multi-agent mode yet

The hard part of agents used to be the orchestration code.
Now it's deciding what work to split.

What would you hand to a team of subagents first? 👇

♻️ Repost if your team builds with LLMs.

#AI #OpenAI #AIAgents #MultiAgent #LLM #DeveloperTools #GenerativeAI

---

## Short alternative (for a punchier feed post)

You no longer write the orchestration loop.

OpenAI's Responses API now has Multi-agent (beta): one flag, and the model spawns its own subagents, runs up to 3 in parallel by default, and merges their results into one final answer.

36 seconds, everything you need to know 👆

What's the first workflow you'd split across agents?

#AIAgents #OpenAI #LLM

---

## Posting tips for reach
- Upload the MP4 natively; don't post a YouTube link (native video gets far more reach).
- The video has no voiceover and every point is on screen, so it works muted (most feed views are).
- Put the docs link in the **first comment**, not in the post: https://developers.openai.com/api/docs/guides/responses-multi-agent
- Post Tue–Thu, 8–10 am in your audience's time zone, and reply to every comment in the first hour.
- Use `poster.png` as the thumbnail ("Edit video" → thumbnail).
