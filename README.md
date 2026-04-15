# BrainPass 🧠

**Give your AI a real memory. One it actually uses. One you can read.**

---

## TL;DR

AI models forget everything the moment you close the chat. BrainPass fixes that. It gives your AI a **notebook** (Obsidian), a **librarian** (NotebookLM or plain file search), and a **voice** (any LLM you want — Claude, GPT, Kimi, local models). You write notes once, the AI reads them forever, and every answer it gives you comes with a citation so you can check its work.

Install it in about ten minutes. Works on Linux, Mac, and Windows (with WSL).

---

## What Is This, Really?

Imagine you had a super-smart friend, but every time you talked to them they forgot who you were, what you were working on, and everything you'd ever told them. Annoying, right? That's how AI chatbots work by default. Every new conversation starts from zero.

BrainPass is the fix. Think of it like this:

- You have a **notebook** where you write down things you want the AI to remember. Your goals. Your projects. People in your life. Your preferences. Stuff that matters to you.
- You have a **librarian** who reads that notebook and can find any note in a fraction of a second.
- You have an **AI** that, instead of guessing or making stuff up, asks the librarian first — "hey, what do we know about this?" — and only then answers you.

Three parts. They're all standard tools. You probably already have most of them.

| Part | What it is | What it does |
|---|---|---|
| **Obsidian** | A free notebook app | You write notes. They're just markdown files on your computer. |
| **NotebookLM** | A free Google tool (optional) | Google reads your notes and lets you search them with natural language. |
| **Librarian** | A tiny program BrainPass gives you | Sits in the background, answers questions from your AI by looking in your notebook. |
| **Your LLM** | Whatever AI you want | Claude, GPT-4, Kimi, Llama — BrainPass doesn't care. |

You put these four things together and suddenly your AI has **memory that survives across every chat, forever, that you fully control**.

---

## Why You'd Want This

- **The AI stops making stuff up.** Instead of guessing, it reads your notes first. Every answer cites a source file.
- **You stop repeating yourself.** You wrote "I'm allergic to peanuts" once. Your AI remembers forever.
- **Your data stays on your computer.** Not OpenAI's servers. Not Anthropic's. Yours. Markdown files in a folder you own.
- **You can switch AIs without losing your memory.** Claude down today? Point BrainPass at GPT-4. Groq having a bad day? Swap to local Llama. Your notes don't care.
- **It's auditable.** If your AI says something weird, you can open the exact note it read and see why. No black box.

---

## How It Works (The Flow)

Here's what happens when you ask your AI a question with BrainPass running:

```
You ask: "What am I supposed to do for the Johnson project this week?"
     │
     ▼
Your AI says: "Hold on, let me check the notebook."
     │
     ▼
AI calls BrainPass's librarian at http://127.0.0.1:7778/recall
     │
     ▼
Librarian searches your Obsidian vault for notes about "Johnson project"
     │
     ▼
Librarian finds: projects/johnson.md, daily/2026-04-12.md
     │
     ▼
Librarian sends those notes to your chosen LLM with your question
     │
     ▼
LLM reads the notes and answers you, citing the files
     │
     ▼
You get: "According to projects/johnson.md, you owe them the wireframes
          by Friday, and from daily/2026-04-12.md, you agreed to meet
          Sarah on Thursday at 2pm to go over them."
```

That's the whole magic. No vector database rituals, no fine-tuning, no rebuilding anything. Just notes + a search + an LLM.

---

## What You Need Before You Start

1. **A computer.** Linux or Mac works out of the box. Windows works through WSL (Windows Subsystem for Linux).
2. **Python 3.10 or newer.** If you don't have it: `sudo apt install python3` (Linux) or download from python.org (Mac/Windows).
3. **Obsidian.** Free, download from [obsidian.md](https://obsidian.md).
4. **An LLM API key.** Pick one:
   - **Groq** (free tier, fast) — [console.groq.com](https://console.groq.com)
   - **OpenAI** — [platform.openai.com](https://platform.openai.com)
   - **Anthropic** — [console.anthropic.com](https://console.anthropic.com)
   - **Local model** — no key needed, but you need Ollama or similar running.
5. **A NotebookLM account.** (Optional but recommended.) Free. [notebooklm.google.com](https://notebooklm.google.com)

That's it. Total cost to get started: **$0** if you use Groq's free tier.

---

## Installation

### Step 1 — Clone the repo

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
```

### Step 2 — Run the installer

```bash
./install.sh
```

The installer creates a folder at `~/BrainPass/` with your vault, copies a config template, and sets up a background service so the librarian starts automatically.

### Step 3 — Add your API key

Open `~/BrainPass/config/.env` in any text editor and fill in the one you're using:

```bash
# Pick ONE of these. Leave the others blank.
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Which LLM to use (match the key above)
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-120b
```

### Step 4 — Tell the librarian who your agent is

Open `~/BrainPass/config/identity/SOUL.md` and write a short description of how you want your AI to behave. Example:

```markdown
# My Agent's Identity

You are my personal assistant. You help me with writing, research, and
planning. You speak casually, like a friend. You always check my notes
before answering. If you don't find an answer in the notes, say so
clearly instead of guessing.

## My Preferences
- I prefer short answers unless I ask for detail.
- I hate emojis in responses.
- I'm working on a novel called "Glasswater".
- Call me by my first name.
```

This file is what makes your AI **yours**. It's the personality. Edit it any time.

### Step 5 — Open your vault in Obsidian

- Launch Obsidian.
- Click **Open another vault** → **Open folder as vault**.
- Choose `~/BrainPass/vault/`.
- You'll see five starter folders: `daily`, `topics`, `people`, `projects`, `sources`. Start writing notes in whichever ones make sense to you.

### Step 6 — Start the librarian

```bash
systemctl --user start brainpass-librarian
systemctl --user enable brainpass-librarian  # auto-start on boot
```

Check it's alive:

```bash
curl http://127.0.0.1:7778/status
```

You should see something like `{"status": "ok", "provider": "groq", "vault_files": 0}`. Done. The librarian is running.

---

## Connecting Your AI to BrainPass

This is the part most people miss. Installing BrainPass isn't enough — **you have to tell your AI that BrainPass exists and how to use it.** The way you do that depends on which AI you're using, but the message you give it is the same.

### The Magic Instruction (copy-paste this to your AI)

Paste this into your AI's system prompt, custom instructions, or the first message of a new chat:

```
You have access to a persistent memory system called BrainPass running at
http://127.0.0.1:7778. It stores notes about me, my projects, my preferences,
and our past conversations in an Obsidian vault.

BEFORE answering any question about me, my work, or anything we've discussed
previously, you MUST query BrainPass first:

  POST http://127.0.0.1:7778/recall
  Body: {"message": "<the user's question>", "topic": "<main topic>"}

The response will contain relevant notes from my vault. Read them, then
answer my question using those notes as your source of truth. Always cite
which file(s) you got the answer from.

If BrainPass returns nothing relevant, say so out loud: "I checked the
notebook and didn't find anything about that." Never make up answers.

When I tell you something new worth remembering, tell me which file it
should go in (daily/, topics/, projects/, or people/) so I can write it
down.
```

### Per-AI Setup

**Claude (Claude Code, Claude.ai, Claude API):**
Put the magic instruction in your project's `CLAUDE.md` file or in Claude's system prompt.

**ChatGPT (GPT-4, custom GPTs):**
Put the magic instruction in "Custom Instructions" → "How would you like ChatGPT to respond?"

**Open WebUI / Ollama / local models:**
Put it in the system prompt field of your chat.

**Any agent framework (LangChain, AutoGen, CrewAI):**
Add `http://127.0.0.1:7778/recall` as a tool your agent can call. The magic instruction goes in the agent's system message.

---

## Writing Good Notes

BrainPass is only as good as what you put in it. A few rules of thumb:

1. **One idea per file.** Don't cram everything into one mega-note. Break it up.
2. **Name files like a human would search.** `projects/johnson-wireframes.md` beats `proj_01.md`.
3. **Date your daily notes.** `daily/2026-04-15.md`. Future you will thank you.
4. **Link between notes.** Obsidian supports `[[other-note]]` syntax. Use it. The more your notes connect, the smarter your AI gets.
5. **Write for your AI the way you'd brief a new assistant.** Short sentences. Clear facts. Dates when they matter.

Example of a good note (`people/sarah.md`):

```markdown
# Sarah Chen

- Project manager on Johnson wireframes
- Works Tue/Thu only
- Prefers Slack over email
- Birthday: March 3
- Met her at DesignCamp 2025
- Married to Dave (also a PM)
```

---

## Troubleshooting

**"The librarian won't start."**
Check the logs: `journalctl --user -u brainpass-librarian -n 50`. Most common issue: missing API key in `.env`.

**"My AI isn't using BrainPass."**
Did you give it the magic instruction? Most likely no. AIs won't call tools you don't tell them about.

**"It says my vault has 0 files."**
You haven't written any notes yet. Open Obsidian, make a note in any folder, save it. Try again.

**"It's slow."**
If you're using the cloud LLM, your bottleneck is the LLM's response time, not BrainPass. If you're using local models, try a smaller one or a faster machine.

**"I want to switch LLMs."**
Edit `~/BrainPass/config/.env`, change `LLM_PROVIDER` and `LLM_MODEL`, restart the librarian: `systemctl --user restart brainpass-librarian`. Your notes don't move.

---

## What BrainPass Is Not

- **Not a chatbot.** It's the memory *behind* a chatbot. You still need an AI to talk to.
- **Not a vector database.** It uses plain keyword search. Fast, simple, and good enough for personal notebooks. If you want embeddings later, you can add them.
- **Not cloud-hosted.** It runs on your machine. That's the point.
- **Not a replacement for thinking.** If you write garbage notes, you get garbage answers. Write good notes.

---

## Documentation

- `docs/INSTALL.md` — The long-form install guide with every edge case
- `docs/PAPER.md` — The technical/academic write-up
- `docs/USE_CASES.md` — Real examples of what people use it for

---

## Security

- No credentials live in this repo. Ever. All keys go in `.env` which is `.gitignore`'d.
- Your vault is markdown on your filesystem. It doesn't leave unless you send it.
- The librarian only binds to `127.0.0.1` (localhost) by default. It's not reachable from the internet unless you change that on purpose.
- If you use NotebookLM, understand that Google reads those notes. Don't put secrets in the vault if that's a problem.

---

## License

MIT. Build your own brain. Fork it. Modify it. Ship it. Just don't blame us if your AI starts talking back.

---

*BrainPass is the open-source version of an agent memory system that's been running in production on one very specific setup for months. It works. It's boring tech on purpose. No vector DB trickery, no LangChain lock-in, no paid SaaS middleman. Just notes and a librarian.*
