"""BrainPass gate — stops autonomous burn of your LLM API budget.

The BrainPass librarian listens on 127.0.0.1 with no auth. Any local
process can hit /recall and spend your Groq/OpenAI/Anthropic budget —
whether that's an intentional cron, a buggy test loop, an IDE
autocomplete, a supply-chain surprise, or just a curious user.

This package gates the librarian so it only answers when a human is
actively driving an AI CLI (claude, cursor, gemini, windsurf, etc.).

Entry points:
    HumanSessionGateMixin  — insert into your BaseHTTPRequestHandler subclass
    GATED_POST/GET, OPEN_ALWAYS — populate with your endpoint lists

See docs/gate.md for architecture.
"""
__version__ = "1.0.0"
