# Librarian Job Manual

## Core Functions

### RECALL (Primary)
Accept raw message + topic → search vault → compile context → return with citations.

Input: POST /recall {"message": "...", "topic": "..."}
Output: {"result": "compiled context", "sources": [...]}

### QUERY
GET /query?q=topic

### STATUS
GET /status — health check

## Search Priority

1. Daily logs (today, yesterday)
2. Topic files matching keywords
3. People files
4. Projects if mentioned

## Skip Filter

Skip recall for:
- Single words: "ok", "cool", "hi", "yes", "no"
- Bare URLs
- Slash commands
- Empty messages
- Very short (< 10 chars)

## Citation Format

Use [1], [2], etc. matching source order.

## Session Cache

- Track retrieved topics
- Don't re-fetch same topic
- Persist to disk
- Clear on restart

## Topic File

Write compiled result to /tmp/brainpass-topic.txt for injection.
