# Contributing to BrainPass

This is a small, boring, intentionally-simple project. That's the whole point.
Keep it that way.

## Ground rules

- **Stdlib only in `src/librarian.py`.** No new pip dependencies. If you
  absolutely need one, make it optional and document the fallback.
- **No vector DB.** BrainPass does keyword search on purpose. If you want
  semantic search, fork it and call your fork BrainPass-Semantic.
- **Local-first.** Nothing should require a cloud account to run. LLM
  providers are pluggable; the core must work with a local Ollama.
- **No telemetry.** Ever.

## Submitting a PR

1. Fork, branch off `master`
2. Make your change
3. Run `./test.sh` — it boots the librarian against a temp HOME and hits the
   endpoints. Your PR has to leave it passing.
4. Update `docs/` if your change affects behavior
5. Open a PR with a short description and the motivation

## Good first PRs

- Fix a bug in `librarian.py`
- Improve a troubleshooting entry in the README
- Add a provider (e.g., Google Gemini, Cohere) — follow the existing
  `_call_openai_compatible` / `_call_anthropic` pattern
- Add a `launchd` plist for macOS users
- Improve the starter vault notes

## PRs that will be rejected

- Vector embeddings in core
- New dependencies outside stdlib
- Rewrites that change the single-file librarian into a package
- "Cloud sync" features
- Telemetry, analytics, phone-home
- Renaming things for taste

## License

By contributing, you agree your contribution is MIT-licensed.
