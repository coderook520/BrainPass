# Agent Integration

BrainPass does nothing until your AI knows it exists. This doc is the
copy-paste for every tool that can talk to a local HTTP endpoint.

## The magic instruction

Drop this into your AI's system prompt, custom instructions, or `CLAUDE.md`:

```
You have access to a persistent memory system called BrainPass running at
http://127.0.0.1:7778. It stores my notes, preferences, projects, and past
conversations as markdown files in an Obsidian vault.

BEFORE answering any question about me, my work, my preferences, or anything
we've discussed previously, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<my question>", "topic": "<main topic>"}

Read the returned notes and answer using them as source of truth. Always cite
which file(s) you pulled from. If BrainPass returns nothing relevant, say
"I checked your notes and didn't find anything about that." Never make up
answers.

When I tell you something worth remembering, suggest which file it should
land in (daily/, projects/, people/, topics/).
```

## Per-tool placement

### Claude Code

The magic instruction goes in your project's `CLAUDE.md` (for repo-scoped
behavior) or `~/.claude/CLAUDE.md` (for global behavior). Claude Code can call
local HTTP via `Bash`, so it works without further plumbing.

### Claude Desktop

Settings → Profile → "What should Claude know about you?" — paste the magic
instruction. Claude Desktop cannot reach localhost by default, so this is only
useful if you expose the librarian publicly (not recommended) or pair with a
local tool via MCP.

### ChatGPT (web)

Settings → Personalization → Custom Instructions → "How would you like ChatGPT
to respond?" — paste the magic instruction. ChatGPT's servers cannot reach
your localhost, so this only works in combination with a local client that
proxies requests (Open WebUI, LibreChat, chatgpt-cli, etc).

### Open WebUI / Ollama web frontends

Paste the magic instruction into the system prompt field of your chat or your
model's Modelfile. These clients run locally, so they can hit
`http://127.0.0.1:7778` directly.

### LangChain

Register `/recall` as a tool:

```python
from langchain.tools import Tool
import requests

def brainpass_recall(question: str) -> str:
    resp = requests.post(
        "http://127.0.0.1:7778/recall",
        json={"message": question, "topic": question[:100]},
        timeout=30,
    )
    data = resp.json()
    return data.get("result") or "No relevant notes found."

brainpass_tool = Tool(
    name="brainpass_recall",
    func=brainpass_recall,
    description=(
        "Query the user's personal memory system. Use this BEFORE answering "
        "any question about the user, their work, or anything you've "
        "discussed before."
    ),
)
```

Then include `brainpass_tool` in your agent's tools list and make sure your
agent's system prompt tells it to check memory first.

### AutoGen / CrewAI

Same pattern — register a tool that POSTs to `/recall`, document it in the
agent's role/backstory as "always query memory first."

### Raw curl (for scripts and shell agents)

```bash
RECALL=$(curl -sf -X POST http://127.0.0.1:7778/recall \
  -H 'Content-Type: application/json' \
  -d "$(jq -n --arg m "$USER_Q" '{message: $m, topic: $m}')")

CONTEXT=$(echo "$RECALL" | jq -r '.result // empty')
```

Feed `$CONTEXT` into your LLM call as part of the system message.

## Verifying the integration works

1. Ask your AI something it shouldn't know: "what's in my ripfire project?"
2. If it answers with generic nonsense → the magic instruction isn't in place.
3. If it answers "I checked your notes and didn't find anything" → integration
   works, vault is empty, time to start writing notes.
4. If it answers with citations from actual files → ship it, you're done.

## Debugging

**Agent says it can't reach localhost.** You're probably running the AI
outside your machine (ChatGPT web, Claude Desktop without MCP). Use a local
client instead.

**Agent ignores BrainPass.** The magic instruction wasn't strong enough. Add
the word `MUST` in caps. Add a penalty clause: "If you answer without
checking BrainPass I will be very disappointed."

**Agent hallucinates notes.** Your vault is probably empty so BrainPass
returns nothing, and the agent fills the gap. Start writing real notes.
