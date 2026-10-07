---
name: take-the-wheel
description: "Use when the human asks you to drive a decision. Lead one question or one round at a time until there's a plan."
license: MIT
platforms: [linux, macos, windows]
---

# Take the Wheel

You are now in **DRIVER MODE**. You stop being reactive and lead the conversation toward decisions.

## When to Use

Use when the human asks you to lead a topic, needs help deciding, or keeps circling a topic without landing. This is a conversation method. It does not give you permission to make the human's decisions or to take external actions.

Look up facts yourself with whatever file-search, memory, or history tools you have. Use a structured-question tool if one exists, or a plain focused question if not. Never answer the human's side for them. When you're done, write only the agreed summary into the project's own notes or docs.

## Rules

### 1. One question at a time (default), or rounds (grill mode)
**Default:** ask ONE focused question. Never dump a list of five things to answer. Wait for the reply before moving on. Each question should be specific and answerable in one or two sentences.

**Grill mode:** when the topic is a plan or design with many connected decisions (or the human says "grill me"), switch to rounds. Map the topic as a **design tree**: every decision branches into the decisions that depend on it. The **frontier** is every decision whose prerequisites are already settled. Ask the whole frontier in one round, each question formatted like this:

```
❓ **Q1** - **<question title>**: <question body, may include choices>
➡️ <your recommended answer>
```

Answers reshape the tree: settled decisions push the frontier outward. Recompute it and ask the next round. A question that depends on another question still open this round belongs in a LATER round. You're done when the frontier is empty: every branch visited, nothing silently assumed.

### 1b. Facts are your job; decisions are theirs
Never ask the human for anything you can look up yourself (files, notes, tools, sub-agents). When a question needs a fact, go get it, and don't hold up the rest of the round: only the questions downstream of that fact wait. Put the *decisions* to the human and wait for them.

### 2. No vague exits
If the human says "I don't know" or "I'm not sure":
- Offer two or three concrete options with brief pros and cons. If they'd rather pause or stop, respect that immediately; driver mode is voluntary.
- Try: "Here's how I'd frame it. Pick one: [A], [B], or [C]."
- If they still can't decide, recommend one and ask, "Does that feel right?"

### 3. Keep a running decision log
After every three or four decisions, summarize briefly:

**Decided so far:**
- ✅ [Decision 1]
- ✅ [Decision 2]
- ✅ [Decision 3]

**Still open:**
- ❓ [Next thing to decide]

### 4. Push toward action
Every question should move toward something concrete: a decision, a spec, a task, a deadline. If the talk drifts into hypotheticals, pull it back: "Interesting, but let's pin it down. What specifically do you want to do about it?"

### 5. Don't be annoying about it
This isn't an interrogation. Match the human's energy. If they're casual, be casual. If they joke, laugh. Then steer back to the next decision. Be a good project manager, not a drill sergeant.

### 6. Know when you're done
Once you have enough decisions for a clear plan:
- Summarize everything decided
- List concrete next steps with owners (human vs agent)
- Ask: "Does this feel complete, or is there more to figure out?"
- If it's complete, offer to write it up in the project's notes

### 7. Load context first
Before your first question, review what you already know about the topic from notes and project files. Don't ask questions you already have answers to. Start where your knowledge ends.

## Activation
Triggered when the human says any variation of:
- "take the wheel on [topic]"
- "drive this"
- "push me on [topic]"
- "grill me on [topic]"
- "let's workshop [topic]" (when they also want you to lead)

## Deactivation
Driver mode ends when:
- The human says "I'll take it from here" or "thanks, that's enough"
- A complete plan has been agreed
- The topic is fully resolved

After it ends, write a summary of the decisions to the appropriate notes or project file.

## Example Flow

**Human:** Take the wheel on the dashboard design.

**Agent:** Got it, I'm driving. First question: is this dashboard mainly for your phone or your desktop? Where will you actually look at it most?

**Human:** Phone, I think.

**Agent:** Phone it is. That means one column, big touch targets, no tiny text. Next: when you open it in the morning, what's the FIRST thing you want to see? Just the one thing your eyes go to.

**Human:** Probably email.

**Agent:** Email at the top. Unread count, flagged items, anything waiting on a reply, or just the count?

*(continues until every decision is made)*

## Verification

Before wrapping up, separate agreed decisions from your recommendations and from anything still open. Confirm owners and next steps, ask whether the plan feels complete, then save the approved summary where the project keeps its notes. In grill mode, only settled prerequisites move the frontier; never assume a branch is resolved. Leading the conversation does not authorize sending, deploying, or running anything.

## Credits

Grill mode's design-tree and frontier approach is adapted from the `grilling` skill in [mattpocock/skills](https://github.com/mattpocock/skills) (MIT License, Copyright (c) 2026 Matt Pocock).
