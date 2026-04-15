# BrainPass 🧠

**Your Agent's Memory System — Obsidian + NotebookLM + LLM of Choice**

BrainPass gives any AI agent (Claude, GPT, local LLMs) persistent memory using a structured Obsidian vault, NotebookLM for retrieval, and a configurable LLM layer.

## What It Does

- **Persistent Memory** — Your agent remembers across sessions
- **Cited Recall** — Every answer cites exact sources
- **Knowledge Graph** — Obsidian vault with linked notes
- **Plug & Play LLM** — Use Claude, GPT, Kimi, local models, whatever

## Architecture

```
User → Agent → BrainPass Librarian (port 7778)
                    ↓
            Obsidian Vault + NotebookLM
                    ↓
           Your Choice of LLM API
```

## Quick Start

1. **Clone and configure**
   ```bash
   git clone https://github.com/YOUR_USERNAME/BrainPass.git
   cd BrainPass
   cp config/.env.example config/.env
   # Edit .env with your API keys
   ```

2. **Set up Obsidian vault**
   - Open Obsidian
   - "Open another vault" → select `BrainPass/vault/`

3. **Start the librarian**
   ```bash
   ./install.sh
   systemctl --user start brainpass-librarian
   ```

4. **Configure your agent**
   - Point to `http://127.0.0.1:7778/recall`
   - See `docs/AGENT_INTEGRATION.md`

## Requirements

- Obsidian (free)
- NotebookLM account (free)
- LLM API key (OpenAI, Anthropic, Groq, or local)
- Python 3.10+

## Documentation

- `docs/INSTALL.md` — Full installation guide
- `docs/CONFIGURATION.md` — Customize for your LLM
- `docs/AGENT_INTEGRATION.md` — Hook into your agent
- `docs/TEMPLATES.md` — Vault structure explained

## Security

- **NO credentials in repo** — All keys in `.env`
- **Local-first** — Your data stays on your machine
- **Audit friendly** — Everything is plaintext markdown

## License

MIT — Build your own brain.

---

*Built with love. Inspired by Gia.*
