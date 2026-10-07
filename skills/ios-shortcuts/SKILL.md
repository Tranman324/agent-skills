---
name: ios-shortcuts
description: "Use when building Apple Shortcuts automations. Generates .shortcut files and enforces validation, docs, and testing."
license: MIT
platforms: [linux, macos]
---

# iOS Shortcuts Operations

Operational skill for Apple Shortcuts lifecycle. Enforces quality, reliability, and documentation standards.

## Pre-Flight (run before any Shortcuts work)

1. **Search before building.** Before creating from scratch, check if it exists:
   - RoutineHub (routinehub.co) — largest curated library
   - Matthew Cassinelli (matthewcassinelli.com/shortcuts) — ex-Apple team, ~1500+ shortcuts
   - MacStories Shortcuts Archive — power-user focused
   - `web_search` for "iOS Shortcut [use case] site:routinehub.co OR site:reddit.com/r/shortcuts"`
   - If a community shortcut exists, evaluate before building custom. Modify > rebuild.

2. **Determine mode:**
   - **Personal** — your own devices; config may be set directly in the shortcut, optimize for speed
   - **Shareable** — use Import Questions for config, add error handling for all paths, document prerequisites

3. **Load references as needed:**
   - Action dictionary: `read references/action-dictionary.md` (relative to this skill)
   - Webhook patterns: `read references/webhook-patterns.md` (relative to this skill)

## Enforcement Standards

### Naming Convention
Format: `[Category] Shortcut Name`

Categories: `[Home]`, `[Work]`, `[Health]`, `[Finance]`, `[Dev]`, `[Utility]`, `[n8n]`

Examples:
- `[n8n] Voice Memo Upload`
- `[Work] Timesheet Submit`
- `[Health] Log Pet Weight`
- `[Utility] Clean Screenshot`
- `[Home] Grocery List to Notes`

For shareable shortcuts, drop the category prefix — use a clean user-facing name instead.

### Input Validation (mandatory)
Shortcuts has **no try/catch.** Every shortcut that accepts input must validate it.

**Pattern — always do this:**
```
1. If [Shortcut Input] [Has any value]
2.   → proceed with main logic
3. Otherwise
4.   → If [Clipboard] [Has any value]
5.       → use clipboard as fallback
6.     Otherwise
7.       → Alert: "No input provided. Share from another app or copy to clipboard."
8.       → Stop This Shortcut
9.     End If
10. End If
```

For Share Sheet shortcuts, check input → clipboard fallback → user alert. Never silently fail.

### Error Handling
Since there's no exception handling:

- **Validate before acting.** Check that URLs are reachable, files exist, variables have values before using them.
- **Use If blocks around every API call.** Check the response before using it.
- **Alert on failure.** Use `Show Alert` with a specific error message, not a generic one. Include what failed and what to try.
- **For complex shortcuts:** Add `Show Alert` debug checkpoints during development. Remove or convert to notifications for production.
- **Non-critical failures:** Use `Show Alert` with cancel disabled to inform but continue. Don't kill the entire shortcut for a logging failure.

### Documentation
Every shortcut delivered must include a comment or description covering:
- **Purpose** — one sentence, what it does
- **Trigger** — how it runs (Share Sheet, widget, Siri voice, automation, manual)
- **Dependencies** — apps, APIs, or other shortcuts required
- **Webhook callers** (if applicable) — what n8n workflows or services it connects to
- **Permissions** — what it needs access to (photos, location, clipboard, etc.)

For the generator: use the `comment` action type as the first action in every shortcut.

## On Build (execute in order)

When creating or modifying a shortcut, follow these steps sequentially:

1. **Search community libraries** — check RoutineHub, Cassinelli, MacStories, r/shortcuts. If something close exists, modify it instead of building from scratch.
2. **Determine mode** — personal (hardcode config) or shareable (Import Questions for config).
3. **Add documentation comment** — first action is a `comment` with purpose, trigger, dependencies, permissions, and webhook callers.
4. **Add input validation** — If block checking Shortcut Input → clipboard fallback → alert. No exceptions for shortcuts that accept input.
5. **Build actions** — use generator or manual construction. Follow design principles.
6. **Name correctly** — `[Category] Shortcut Name` for personal; clean name for shareable.
7. **Run production checklist** — every item below must pass.
8. **Test on target device** — run on the actual iPhone/Mac, not just the generator output.
9. **Deliver** — hand the unsigned .shortcut file to the user. They sign it on a Mac with `shortcuts sign -i file.shortcut -o signed.shortcut`, then import it.

For modifications: always test the existing shortcut first to confirm current behavior before changing anything.

## Generator

Use `scripts/generate_shortcut.py` (relative to this skill) to build `.shortcut` files programmatically.

### Two interfaces:

**1. Python API (for complex shortcuts):**
```python
from generate_shortcut import ShortcutBuilder

from generate_shortcut import ref_variable

b = ShortcutBuilder(icon_color="blue", icon_glyph="globe")
b.set_input_types("text", "url")
b.add_share_sheet()
b.add_import_question("API Key:", "apiKey")
b.add_action("get_url", url="https://api.example.com/items", method="POST",
             headers=[{"key": "Authorization", "value": ["Bearer ", ref_variable("apiKey")], "type": "text"}])
b.add_action("notification", body="Done!", title="Success")
b.save("my-shortcut.shortcut")
```

**2. JSON definition (for templated shortcuts):**
```bash
python3 scripts/generate_shortcut.py definition.json output.shortcut
```

See `references/action-dictionary.md` for all available actions, parameters, icons, and content types.

Use `raw` action type as escape hatch for any action not in the registry — pass full `WFWorkflowActionIdentifier` and parameters dict.

### Signing (required for iOS 15+)

iOS 15+ requires shortcuts to be signed with Apple Encrypted Archives before import. Unsigned `.shortcut` files will show "Importing unsigned shortcut files is not supported." There is no way to sign on Linux — it requires the macOS `shortcuts sign` CLI (ships with macOS Monterey+).

**Signing workflow:**
1. Generator builds an unsigned `.shortcut` (any OS)
2. Copy the unsigned file to a Mac
3. On the Mac, run:
   ```bash
   shortcuts sign -i unsigned.shortcut -o signed.shortcut
   ```
4. Import `signed.shortcut` on iPhone (AirDrop to self, or open from Files)

**One-liner for Mac Terminal:**
```bash
# Sign and open in one step (macOS)
shortcuts sign -i ~/Downloads/my-shortcut.shortcut -o ~/Downloads/my-shortcut-signed.shortcut && open ~/Downloads/my-shortcut-signed.shortcut
```

**Signing modes** (set with `--mode`):
- `people-who-know-me` (default) — shareable with contacts
- `anyone` — shareable with anyone via link

### Delivery
Generated `.shortcut` files are **unsigned** and need signing before import:
- Copy unsigned file to a Mac → sign → import on iPhone
- For shareable shortcuts: sign with `--mode anyone`, then share via iCloud link
- Store unsigned files in workspace for version control

## Third-Party App Actions

The generator covers Apple's built-in Shortcuts actions. Third-party app actions (Drafts, OmniFocus, Bear, Toolbox Pro, Scriptable, etc.) are registered on-device when the app is installed — they can't be discovered remotely.

**To use third-party app actions:**
1. **User identifies the app and desired action.** The user knows what apps they have and what those apps offer in the Shortcuts action picker (tap "Apps" in the editor).
2. **Research the app's Shortcuts intents.** Many apps document their action identifiers. Search: `web_search "[app name] Shortcuts actions intents"`.
3. **Use the `raw` action type** in the generator with the exact identifier (e.g., `com.agiletortoise.Drafts4.CreateDraftIntent`) and parameter dict.
4. **The shortcut imports fine without the app installed.** iOS resolves app actions at runtime, not import time. If the app is missing, the action fails when *run*, not when imported.

**When the user asks for a shortcut involving a specific app:**
- Ask which app and what it should do
- Research the app's published Shortcuts intents
- If no documentation exists, ask the user to export an existing shortcut that uses that app's actions — parse the plist to extract the identifiers and parameters
- Build using `raw` with the discovered identifiers

## Design Principles

### Stable primitives over clever hacks
Build around: text, dates, files, dictionaries, standard share extensions, HTTP requests.
Avoid: screen coordinates, private URL schemes, undocumented hooks, app-specific intents that change between iOS versions.

Shortcuts that depend on undocumented behavior break on iOS updates. If you can't explain the shortcut in 5 minutes, it's too clever.

### Small and composable
If a shortcut does two distinct things, split it into two shortcuts connected by `Run Shortcut`. Benefits:
- Test each piece independently
- Reuse components across workflows
- Isolate failures — one breaking doesn't kill the other

### Background automation: design for unreliability
iOS background triggers (time, location, WiFi, battery) are "best effort." The privacy stack can silently block execution. Rules:
- Always enable "Allow Running without Asking" for automations
- Prefer explicit triggers (widget, Siri, Share Sheet) for critical workflows
- For background automations: add a notification at the start so you can tell if it actually ran
- After iOS updates: test all automations. Permission resets are common.

### Rate limit awareness
`Repeat` loops with `Get Contents of URL` inside can hammer APIs fast. Add `Wait` actions (1-2 seconds) between iterations. Respect 429 responses from external services.

### Webhook timeout
iOS Shortcuts HTTP timeout is ~30 seconds, not configurable. For long operations, have the server respond 200 immediately and process async. Notify via push when done.

## Known Pitfalls

- **No try/catch.** Design around it with If blocks. This is the #1 pain point.
- **Variable type coercion is implicit.** A JPEG can be passed as its filename instead of file data. Use `View Content Graph` to inspect types during debugging.
- **Wait action has hard limits.** For longer waits, use Focus mode triggers as a workaround.
- **Share Sheet data passing can break between iOS versions.** Test after updates.
- **Clipboard is the only way to insert text into another app.** No direct text injection.
- **Widget/Watch memory limits.** Complex shortcuts may show "Unable to Load." Add `Continue Shortcut in App` near the start as a workaround.
- **Cross-device sync varies.** A shortcut working on iPhone may fail on iPad/Mac due to different available actions, apps, or permissions. Document device requirements.
- **Edited Shortcut URLs change.** If sharing via iCloud link, re-editing and re-sharing generates a new URL. Old links stop working.
- **Siri voice triggers are unreliable** for complex actions. Reserve for low-risk (timers, playlists, simple sends). Avoid voice for anything destructive or involving money.
- **iOS updates can reset "Allow Running without Asking."** Check automation permissions after every major update.

## Production Readiness Checklist

Before delivering any shortcut, verify:

- [ ] **Input validated** — checks for empty input, falls back gracefully
- [ ] **Offline degradation** — works without network (if applicable) or alerts cleanly
- [ ] **No destructive actions without confirmation** — delete/send/purchase always gets an Alert first
- [ ] **Error messages are specific** — user can tell what failed, not just "an error occurred"
- [ ] **Secrets stored safely** — API keys via Import Questions, never typed into a shared or exported shortcut. Import Question values are stored unencrypted in the shortcut, so treat the file itself as a secret
- [ ] **Tested on target device** — ran on the actual iPhone/Mac it'll be used on
- [ ] **Documentation complete** — purpose, trigger, dependencies, permissions documented
- [ ] **Webhook callers documented** — if it hits n8n, both sides know about the coupling
- [ ] **Named descriptively** — follows naming convention, no "Untitled Shortcut 3"
- [ ] **Debug artifacts removed** — no leftover Show Alert checkpoints in production version

## Debugging Guide

When a shortcut fails:

1. **Run manually from Shortcuts app** — watch each action highlight as it executes. Note where it stops.
2. **Add Show Alert checkpoints** — place before and after suspected failure point. Include the variable value in the alert text.
3. **Check View Content Graph** — inspect the data type being passed between actions. Type coercion is the most common silent bug.
4. **Split and isolate** — if the shortcut is long, extract the failing section into a standalone shortcut. Test with known-good input.
5. **Check permissions** — Settings → Shortcuts → verify the shortcut has access to what it needs.
6. **Check iOS version** — if it worked before an update, check release notes for Shortcuts changes.
7. **For webhook failures** — test the URL directly with `curl` from a terminal. Verify n8n workflow is active and the webhook URL hasn't changed.
8. **For background automation failures** — check Settings → Shortcuts → Automations → verify "Run without asking" is on. Add a notification as the first action to confirm it fires.
9. **Logger app ($10)** — for complex shortcuts, Alex Hay's Logger provides a real console with background logging, severity filtering, and iCloud sync. Worth it for heavy Shortcuts development.

## Helper Apps

- **Logger** ($10) — debugging console for Shortcuts. Background logging, severity levels, iCloud sync.
- **Toolbox Pro** — 130+ additional actions not available natively
- **Scriptable** — full JavaScript execution on iOS, bridgeable with Shortcuts
- **Data Jar** — persistent key-value storage accessible from Shortcuts
- **Charty** — chart generation from Shortcuts data

## Version Awareness

Skill validated against: **iOS 18 / macOS 15 (Sequoia)**. Generator targets `WFWorkflowClientRelease: 18.0`, `WFWorkflowMinimumClientVersion: 1300`. Signing requires macOS Monterey+ (`shortcuts sign` CLI).

On iOS version change, verify:
- Share Sheet data passing still works (broke in iOS 26 beta)
- Background automation "Run without asking" toggle persists
- Action identifiers haven't been renamed or deprecated
- New actions added (check Apple release notes for Shortcuts changes)
- Import Questions still function for shareable shortcuts
- Webhook timeout behavior unchanged (~30s)

## Key Paths

| What | Path |
|------|------|
| Generator script | `scripts/generate_shortcut.py` (relative to this skill) |
| Action dictionary | `references/action-dictionary.md` (relative to this skill) |
| Webhook patterns | `references/webhook-patterns.md` (relative to this skill) |
| Default output | working directory or specified path |
| Signing | macOS `shortcuts sign -i <unsigned> -o <signed>` (Monterey+) |