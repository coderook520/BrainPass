<div align="center">

<img src="https://img.shields.io/badge/BrainPass-8B5CF6?style=for-the-badge&logo=obsidian&logoColor=white&labelColor=1E1B4B" alt="BrainPass" height="44">

### your AI finally remembers shit.

**works with any AI. Claude, GPT, Gemini, Llama, Mistral, Ollama, LM Studio — if it speaks text, BrainPass gives it memory.**

<br>

<img src="https://img.shields.io/badge/works_with-any_AI-10B981?style=for-the-badge&labelColor=1E1B4B">

<img src="https://img.shields.io/badge/Claude-CC785C?style=flat-square&logo=anthropic&logoColor=white">
<img src="https://img.shields.io/badge/GPT-412991?style=flat-square&logo=openai&logoColor=white">
<img src="https://img.shields.io/badge/Gemini-4285F4?style=flat-square&logo=google&logoColor=white">
<img src="https://img.shields.io/badge/Llama-0467DF?style=flat-square&logo=meta&logoColor=white">
<img src="https://img.shields.io/badge/Mistral-FF7000?style=flat-square">
<img src="https://img.shields.io/badge/Ollama-000000?style=flat-square">
<img src="https://img.shields.io/badge/LM_Studio-6C47FF?style=flat-square">
<img src="https://img.shields.io/badge/any_OpenAI--compatible-gray?style=flat-square">

<br>

<img src="https://img.shields.io/badge/v2.1-5_engine_brain-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/ships-today-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/setup-10_minutes-8B5CF6?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/runs_on-your_laptop-6366F1?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/cost-$0_to_start-3B82F6?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/python-3.10+-1E40AF?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/license-MIT-0EA5E9?style=flat-square&labelColor=1E1B4B">

</div>

---

## what BrainPass actually is

Short version: your AI is a goldfish. BrainPass is the assistant standing next to the goldfish, handing it a briefing packet 50 milliseconds before it opens its mouth.

### the goldfish thing

Every LLM — Claude, GPT, Kimi, Llama, whoever — resets to zero the second you close the tab. No persistence. You could spend three hours explaining your business, walk away, come back, and it's a stranger.

You can't fix that. No amount of prompting teaches a stateless model to "remember." The weights are frozen. The context window is finite and expensive. Anyone selling you "AI memory" is selling you a summary their backend compresses your life into.

What you *can* fix is making the goldfish's forgetting **irrelevant**.

### Marcus and Sarah

Picture a boardroom. Marcus is brilliant. Solves anything you throw at him. But he has no memory — if you pause for breath, he forgets who you are, what company you run, what you were just saying.

Without help, every conversation is:

> **you:** "About the Johnson wireframes..."
> **Marcus:** "Who's Johnson? What project? Sorry, no context."

You paste the same brief. Re-introduce the same people. Re-explain the same decisions. Groundhog Day with a genius.

Now put **Sarah** next to him. Three superpowers:

1. Access to the filing cabinet in the corner of the room (your Obsidian vault)
2. She can scan 10,000 documents in 50 milliseconds
3. She doesn't wait to be asked

You start talking. Sarah dashes to the cabinet, pulls the Johnson folder, grabs Tuesday's meeting notes, snags yesterday's Slack thread, slaps a briefing on Marcus's desk before he opens his mouth.

> **Marcus** *(flipping the packet):* "Right — you're 80% done on the mobile breakpoint, Sarah Chen needs it Friday EOD, she prefers Slack, and she sounded stressed in your Tuesday call. Want me to unstick the nav component?"

Marcus didn't remember anything. He's still a goldfish. But Sarah fed him every detail 0.05 seconds before he needed it, and from your side it feels like talking to someone who's been in every meeting.

**That's BrainPass.**

- **You** are the person in the room.
- **Marcus** is whatever LLM you're pointed at (swap anytime).
- **Sarah** is the librarian running on `127.0.0.1:7778`.
- **The filing cabinet** is your Obsidian vault — markdown files on your disk.

### why this beats "AI memory" features

ChatGPT and friends sell "memory" that's a compressed summary sitting on their servers. It loses nuance. You can't audit it. You can't edit it. If they change the policy tomorrow it's gone.

BrainPass doesn't summarize. It *retrieves*. The full note. The exact thread. The complete spec. Fresh, every time.

You own the cabinet. You switch AIs whenever. You delete anything. You audit every byte your AI has access to. It's your disk.

**10 minutes** to install. **$0** if you use Groq's free tier. Works with Claude, GPT, Kimi, Llama, or local models — swap anytime.

<p align="center"><code>notes + search + your LLM = memory that survives</code></p>

---

## easiest install — hand it to your AI

You don't have to read this README. Clone the repo, open the folder in whatever AI coding tool you use — Claude Code, Cursor, Warp, Windsurf, Aider, Continue, whatever — and say:

> **"Read `SETUP-WITH-YOUR-AI.md` and set this up for me."**

Your AI will read the runbook, walk you through a 10-minute conversation, ask which LLM you want running behind the librarian (it'll recommend Groq's free tier), grab an API key from you, run the installer, start the service, wire itself into BrainPass, write your first note with you, and prove recall works. You answer like five questions total and hit enter.

If you'd rather install it manually — or you don't have an AI tool to hand the repo to — the rest of this README is the human version.

---

## how it actually works

You write notes in Obsidian (or literally any text editor — it's just markdown). A tiny Python service sits on `localhost:7778` and waits. When your AI has a question about you, it hits that service. The service searches your notes, grabs what's relevant, stuffs it into your LLM with your question, and hands back the answer. With citations.

```
you → "what am I supposed to finish by Friday?"
       │
       ▼
(UserPromptSubmit hook fires automatically — before your AI sees the message)
       │
       ▼
brainpass-inject.sh → POST localhost:7778/recall
                            │
                            ▼
       BrainPass searches ~/BrainPass/vault/ in ~50ms
                            │
                            ▼
       finds: projects/johnson.md, daily/2026-04-12.md
                            │
                            ▼
       feeds them to the librarian's runner LLM with your question
                            │
                            ▼
       compiles a cited briefing and injects it into the conversation
                            │
                            ▼
your AI ← sees your message + BrainPass briefing, reads both, answers
              │
              ▼
you ← "wireframes — mobile breakpoint still open. Sarah needs
       them Friday EOD per projects/johnson.md."
```

That's it. No LangChain. No $20/month SaaS middleman. Just a librarian, a stack of notes, and a ~100-line shell hook that fires on every message so your AI never has to remember to check.

### v2.1 — five-engine brain

BrainPass doesn't just keyword search your notes. It runs **five engines** that work together:

| # | engine | what it does | how it works |
|---|---|---|---|
| 1 | **BM25** | keyword search | classic text matching — fast, reliable, always on, zero dependencies |
| 2 | **Semantic** *(optional)* | meaning search | ChromaDB + vector embeddings — finds notes that *mean* the same thing even with completely different words |
| 3 | **Knowledge Graph** | entity search | SQLite graph of every person, project, and concept in your vault — finds related notes through connections, not keywords |
| 4 | **Dream Engine** | creative insights | generates speculative connections between unrelated notes while idle — sandboxed in `.dreams/`, never contaminates real data |
| 5 | **Predictive Pre-fetch** | anticipation | learns what you ask about next using Markov chains — pre-fetches bonus context before you even type |

Search results from engines 1-3 are combined using **Reciprocal Rank Fusion (RRF)** — the same merge algorithm Google uses. A note that shows up in all three engines ranks higher than one that only matches keywords.

**Conflict detection** — when your notes contradict each other (different dates, different claims about the same thing), BrainPass flags it instead of silently picking one.

**Dream Engine** — while the librarian is idle, it picks random entities from your knowledge graph, asks the LLM to find non-obvious connections, and saves them to `vault/.dreams/`. Dreams are **completely sandboxed** — main search never sees them. Browse them with `GET /dreams` when you want inspiration. If a dream turns out to be a real insight, move it to the real vault yourself.

**Predictive Pre-fetch** — tracks topic transitions (after asking about X, you usually ask about Y). After a few queries, it starts pre-fetching the predicted next topic and appends it as bonus context. Gets smarter every query. No training step. Just a JSON file counting transitions.

Everything is **optional and graceful**:
- No chromadb? BM25 + knowledge graph + dreams + predictions still work.
- No API key? BM25 keyword search still works standalone.
- Turn off dreams? Set `DREAM_ENABLED=false` in `.env`.
- Nothing ever crashes the service. Every engine fails independently.

### what makes it automatic

The piece that turns BrainPass from *"AI has to remember to call /recall"* into *"AI just always knows"* is a `UserPromptSubmit` hook at `~/BrainPass/hooks/brainpass-inject.sh`. You register it once with your AI tool (Claude Code's `settings.json`, Warp's pre-prompt script, etc.) and from then on every single message you send fires it first — it grabs your prompt, hits the librarian, gets the compiled notes back, and drops them into the conversation *before* your AI sees your message. Your AI doesn't have to know BrainPass exists. It just reads a conversation that already has the right context in it.

If your tool doesn't support pre-hooks (most web UIs), there's a fallback: paste a "always check BrainPass first" instruction into your system prompt. Works, but you're trusting the model to actually do it. The hook is the real wire.

---

## the stack

<div align="center">

<img src="https://img.shields.io/badge/Obsidian-8B5CF6?style=flat-square&logo=obsidian&logoColor=white">
<img src="https://img.shields.io/badge/ChromaDB-FF6F61?style=flat-square">
<img src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white">
<img src="https://img.shields.io/badge/Python_3.10+-3B82F6?style=flat-square&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/Your_LLM-EC4899?style=flat-square">

</div>

| piece | what it is | why |
|---|---|---|
| **Obsidian** | free markdown notebook | your notes, your disk, your links |
| **ChromaDB** *(optional)* | vector embedding database | semantic search — finds notes by meaning, not just keywords |
| **SQLite** | embedded graph database | knowledge graph — maps every entity and relationship in your vault |
| **Librarian** | ~1700 lines of Python | 5 engines: BM25 + semantic + graph + dreams + predictions |
| **Your LLM** | Claude / GPT / Kimi / Llama / whatever | swap it anytime, notes don't care |
| **NotebookLM** *(optional)* | Google's smart search | free tier, lazy setup, good recall |

Boring tech on purpose. Stable libraries. Runs on your laptop. No cloud required.

---

## install

### 1. clone & run the installer

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
./install.sh
```

You now have `~/BrainPass/` with a vault, a config folder, a systemd service, and a fresh `.env` template.

### 2. drop in an API key

Open `~/BrainPass/config/.env` and pick one provider. Groq has a free tier and is fastest to get going:

```bash
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

Or swap in `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / point at your local Ollama — same file.

### 3. give your agent a personality

Open `~/BrainPass/config/identity/SOUL.md`. This is the forever-system-prompt your AI will read on every call. Make it yours:

```markdown
# my agent

You're my personal assistant. Speak casually. Check my notes
before answering anything about me or my projects. Cite sources.
If you don't find the answer in the notes, say so — don't guess.

## about me
- building a rust CLI called ripfire
- I hate long explanations unless I ask
- timezone: America/Chicago
- call me by my first name
```

### 4. open the vault in Obsidian

Launch Obsidian → **Open folder as vault** → pick `~/BrainPass/vault/`. You'll see `daily/`, `projects/`, `people/`, `topics/`, `sources/`. Make a note in any of them. Save.

### 5. start the librarian

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian
curl http://127.0.0.1:7778/status
```

Should come back `{"status": "ok", ...}`. Done. The librarian is alive.

---

## the one step everyone skips

> [!IMPORTANT]
> **If you skip this step, BrainPass does nothing.** Installing it isn't enough. Your LLM has no idea the librarian exists until you tell it. This is the #1 reason people think BrainPass is broken.

Paste this block into your AI's system prompt / custom instructions / `CLAUDE.md` / whatever the personality slot is called in the tool you're using:

```
You have access to a memory system called BrainPass running at
http://127.0.0.1:7778. It contains my notes, preferences, projects,
and past conversations as markdown files.

BEFORE answering any question about me, my work, my preferences, or
anything we've discussed before, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<my question>", "topic": "<main topic>"}

Read the returned notes and answer using them as source of truth.
Always cite which file(s) you pulled from. If BrainPass returns
nothing relevant, say "I checked your notes and didn't find anything
about that." Never make up answers.

When I tell you something worth remembering, suggest which file it
should land in (daily/, projects/, people/, topics/).
```

### where to paste it

| tool | where |
|---|---|
| **Claude Code** | `CLAUDE.md` at your repo root, or `~/.claude/CLAUDE.md` globally |
| **Claude Desktop** | Settings → Project Instructions |
| **ChatGPT** | Settings → Custom Instructions → "How should ChatGPT respond?" |
| **Ollama / Open WebUI** | System Prompt field in chat settings |
| **LangChain / AutoGen / CrewAI** | System message + register `/recall` as a tool |

---

## writing notes that don't suck

BrainPass is only as smart as what you feed it. Five rules:

1. **one idea per file** — `projects/ripfire-cli.md`, not `projects.md`
2. **name files like you'd search** — future you types "sarah", future you wants `people/sarah.md` to exist
3. **date your daily notes** — `daily/2026-04-15.md`. Non-negotiable.
4. **link aggressively** — `[[ripfire-cli]]` in a daily note. Obsidian builds the graph for free.
5. **write short** — your LLM is not your therapist. Facts. Dates. Names. Done.

Example of a note that earns its keep (`people/sarah.md`):

```markdown
# Sarah Chen
- PM on ripfire project
- only works Tue/Thu
- Slack > email, always
- met at DesignCamp 2025
- birthday: Mar 3
- [[ripfire-cli]] for project context
```

---

## troubleshooting

<details>
<summary><b>librarian won't start</b></summary>

```bash
journalctl --user -u brainpass-librarian -n 50
```
99% of the time: missing API key in `~/BrainPass/config/.env`. Second most common: wrong `LLM_PROVIDER` / `LLM_MODEL` combo.
</details>

<details>
<summary><b>my AI isn't using BrainPass</b></summary>

Did you paste the magic instruction into your AI's system prompt? Probably not. Do it.
</details>

<details>
<summary><b>vault shows 0 files</b></summary>

You haven't written any notes. Open Obsidian, make a note, save. Try again.
</details>

<details>
<summary><b>it's slow</b></summary>

It's not BrainPass — search is ~50ms. It's your LLM's response time. Try a smaller / faster model, or Groq's free tier.
</details>

<details>
<summary><b>I want to switch LLMs</b></summary>

Edit `~/BrainPass/config/.env`, swap `LLM_PROVIDER` and `LLM_MODEL`, restart: `systemctl --user restart brainpass-librarian`. Your notes stay. Your AI doesn't forget.
</details>

---

## security

Your data is yours. That's not a marketing line, it's the architecture:

- **No credentials in this repo.** `.env` is gitignored. Fresh clones have zero secrets.
- **Vault lives on your disk.** Markdown files in `~/BrainPass/vault/`. Doesn't leave unless you send it.
- **Librarian binds to `127.0.0.1` only.** Not reachable from the internet unless you change that on purpose.
- **NotebookLM is opt-in.** Google only sees your notes if you upload them yourself.

If you can read the files in `~/BrainPass/`, you can audit every byte your AI has access to. No black box.

---

## architecture, for the curious

```
┌─────────────────────────────────────────────┐
│              your LLM                       │
│     (Claude / GPT / Kimi / local)           │
└──────────────────┬──────────────────────────┘
                   │ POST /recall
                   ▼
┌─────────────────────────────────────────────┐
│          BrainPass Librarian                │
│        (Python HTTP on :7778)               │
│                                             │
│  ┌─────────┐ ┌──────────┐ ┌─────────────┐  │
│  │  BM25   │ │ Semantic │ │  Knowledge  │  │
│  │ keyword │ │ ChromaDB │ │    Graph    │  │
│  └────┬────┘ └────┬─────┘ └──────┬──────┘  │
│       └───────────┼──────────────┘          │
│                   ▼                         │
│         ┌─────────────────┐                 │
│         │   RRF Merge +   │                 │
│         │   Conflict Det  │                 │
│         └────────┬────────┘                 │
│                  │                          │
│  ┌───────────────┼───────────────┐          │
│  │               │               │          │
│  ▼               ▼               ▼          │
│ Dream       Predictive      Compiled        │
│ Engine      Pre-fetch       Briefing        │
│ (.dreams/)  (bonus ctx)     (citations)     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│          your Obsidian vault                │
│        (markdown in ~/BrainPass/)           │
│  daily/  projects/  people/                 │
│  topics/  sources/  .dreams/ (sandboxed)    │
└─────────────────────────────────────────────┘
```

~1700 lines of Python. Five engines. Zero SaaS dependencies. Just good plumbing.

---

## API endpoints

| method | path | what it does |
|---|---|---|
| GET | `/health` | is the librarian alive? |
| GET | `/status` | full system status — engines, docs, health flags |
| GET | `/query?q=...` | search + compile in one call |
| POST | `/recall` | full 3-phase recall (decode → search → compile) |
| POST | `/clear-cache` | wipe session cache |
| GET | `/dreams` | browse sandboxed dream insights |
| GET | `/predictions?topic=...` | see predicted next topics |

---

## who this is for

- devs tired of re-explaining their stack every new chat
- builders who want their AI to actually know the project
- anyone who's watched an LLM hallucinate their own preferences back at them
- people who trust their own disk more than someone else's cloud
- anyone who wants their AI to get smarter the more they use it
- people who want AI memory without giving their data to a corporation

---

## what makes BrainPass different

| feature | ChatGPT memory | Mem0 / MemGPT | BrainPass |
|---|---|---|---|
| your data stays local | no | depends | **yes, always** |
| works with any LLM | no | some | **all of them** |
| you can audit everything | no | kinda | **yes, it's markdown** |
| search engines | 1 (summary) | 1 (vector) | **5 (BM25 + semantic + graph + dreams + predictions)** |
| conflict detection | no | no | **yes** |
| predictive pre-fetch | no | no | **yes** |
| dream engine | no | no | **yes (sandboxed)** |
| cost | $20/mo | varies | **$0 (Groq free tier)** |
| setup time | built-in | 30+ min | **10 min** |

---

<div align="center">

### star it. fork it. break it. ship your own brain.

<br>

<img src="https://img.shields.io/badge/MIT-license-0EA5E9?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/PRs-welcome-EC4899?style=flat-square&labelColor=1E1B4B">
<img src="https://img.shields.io/badge/made_for-people_tired_of_repeating_themselves-8B5CF6?style=flat-square&labelColor=1E1B4B">

<br><br>

*five engines. zero SaaS. your notes, your disk, your brain. just a librarian who never sleeps.*

</div>
