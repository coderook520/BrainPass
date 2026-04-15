# what BrainPass actually is

Short version: your AI is a goldfish. BrainPass is the assistant standing next to the goldfish, handing it a briefing packet 50 milliseconds before it opens its mouth.

## the goldfish thing

Every LLM — Claude, GPT, Kimi, Llama, whoever — resets to zero the second you close the tab. No persistence. You could spend three hours explaining your business, walk away, come back, and it's a stranger.

You can't fix that. No amount of prompting teaches a stateless model to "remember." The weights are frozen. The context window is finite and expensive. Anyone selling you "AI memory" is selling you a summary their backend compresses your life into.

What you *can* fix is making the goldfish's forgetting **irrelevant**.

## Marcus and Sarah

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

## why this beats "AI memory" features

ChatGPT and friends sell "memory" that's a compressed summary sitting on their servers. It loses nuance. You can't audit it. You can't edit it. If they change the policy tomorrow it's gone.

BrainPass doesn't summarize. It *retrieves*. The full note. The exact thread. The complete spec. Fresh, every time.

You own the cabinet. You switch AIs whenever. You delete anything. You audit every byte your AI has access to. It's your disk.

That's the whole thing. Everything else is plumbing.
