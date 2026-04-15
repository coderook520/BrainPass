# BrainPass Installation Guide

## Prerequisites

- Python 3.10+
- Obsidian (desktop app)
- Git (optional, for cloning)
- API key from Groq, OpenAI, or Anthropic

## Step-by-Step Installation

### 1. Clone or Download

```bash
git clone https://github.com/coderook520/BrainPass.git
cd BrainPass
```

### 2. Configure Environment

```bash
cp config/.env.example config/.env
# Edit config/.env with your API keys
nano config/.env
```

### 3. Set Agent Identity

```bash
cp config/identity/SOUL.md.template config/identity/SOUL.md
# Edit with your agent's persona
nano config/identity/SOUL.md
```

### 4. Run Installer

```bash
chmod +x install.sh
./install.sh
```

### 5. Start Service

```bash
systemctl --user start brainpass-librarian
systemctl --user status brainpass-librarian
```

### 6. Verify

```bash
curl http://127.0.0.1:7778/status
```

### 7. Connect Obsidian

1. Open Obsidian
2. "Open another vault"
3. Select `~/BrainPass/vault/`
4. Start writing!

## Troubleshooting

**Port in use:** Change `LIBRARIAN_PORT` in `config/.env`

**API errors:** Verify keys in `config/.env`

**Permission denied:** Ensure `librarian.py` is executable

## Next Steps

- Read `docs/PAPER.md` for architecture details
- Customize `vault/` structure for your needs
- Integrate with your agent (see `docs/AGENT_INTEGRATION.md`)
