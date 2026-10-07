---
name: n8n-workflows
description: "Use when building, changing, or debugging n8n workflows. Enforces error handling, docs, backups, and safe changes."
license: MIT
platforms: [linux]
---

# n8n Workflow Operations

## When to Use

Operational standards for creating, modifying, deploying, or debugging self-hosted n8n workflows: error-handler linkage, sticky-note documentation, webhook registration, backups before modification, and platform-node-first design. Use it whenever n8n work comes up, including troubleshooting and health checks.

## Safety Boundary

- Every write (workflow update, activation, restart, credential change, DB maintenance) needs explicit approval from the workflow owner for that exact target. Reading and inspecting do not.
- A `401`/`403` means stop and fix the permission or project scope. Never use direct database access to get around API authorization.
- Never read, print, or copy credential payloads, API keys, webhook URLs, or the `user_api_keys` table into chat, docs, or Git.
- After every approved write, read back the exact target, then prove the intended result (execution ran, alert arrived). A `200` response or an `active` flag alone is not proof.
- Keep workflow scopes separate (for example business vs personal). Shared infrastructure such as an error handler must not leak sensitive payloads across scopes.

## Configuration

Set these for your install. Examples below use them instead of hardcoded values.

| Variable | Meaning | Example |
|---|---|---|
| `N8N_URL` | Base URL of the n8n instance | `http://localhost:5678` |
| `N8N_API_KEY` | API key from a secret store; never echo it | (from your secret manager) |
| `N8N_USER_FOLDER` | n8n user folder (holds `.n8n/`) | `/opt/n8n` |
| `N8N_DB` | SQLite database path | `$N8N_USER_FOLDER/.n8n/database.sqlite` |
| `N8N_BACKUP_DIR` | Where workflow exports go | `$N8N_USER_FOLDER/backups` |

## Pre-Flight (run before any n8n work)

1. Read `references/monitoring.md` and `references/api.md` (relative to this skill).
2. **Search before building.** Look for an existing n8n template or community workflow first. Adapt one if it exists; build from scratch only when nothing usable exists.
3. Verify n8n is running: `systemctl is-active n8n.service` (or your container's health check).
4. Check the version: `n8n --version`. If it differs from the version you last validated against, flag it. DB schema, API behavior, and node types change between releases.

## Enforcement Tiers

### Tier 1: Mandatory (every workflow)
- Error-handler linkage (`settings.errorWorkflow`), except on the error handler itself (prevents recursion)
- Sticky-note documentation
- Backup before modify
- Descriptive node names (no defaults)
- Naming convention (short name + two-layer tags)
- "Save successful production executions" left enabled

### Tier 2: Conditional (AI workflows)
Applies when the workflow uses AI Agent nodes, Basic LLM Chain nodes, or HTTP Request nodes that call LLM providers.
- Call a token-logging sub-workflow after every AI response
- Route token and cost data to that shared logging component

## Design Principles

### Platform nodes first
Preference order:

1. **Service-specific node** (Supabase, Slack, OpenAI, Anthropic, Gmail, and so on): built-in retry, managed credentials, better errors, auto-pagination
2. **Generic platform node** (HTTP Request, IF, Set, Switch, Merge, Split In Batches): reliable and visible in the execution log, but you own auth and retry
3. **Code node**: last resort, only for real programming

Code nodes are harder to debug, show no data previews, and break more often on upgrades. Use them only when no platform node fits (binary processing, shell work), when the logic would be worse as a 5+ node chain, or for looped processing with per-item conditions.

Use HTTP Request nodes only when no service node exists or the service node hides a field you need (such as raw token-usage metadata).

During review, flag Code nodes that could be platform nodes and HTTP Request nodes that could be service nodes.

### Credential shells
Credentials live in n8n as **shells**: correct type and name (`Service · Context`) with placeholder values until the owner fills them in.

1. **Building a workflow:** wire it to an existing credential shell by ID. The workflow is structurally complete before secrets exist.
2. **No shell yet:** prepare the type, name, and required fields, and hand that request to the owner. The owner creates and fills it in the n8n editor.
3. **Owner fills in real values** whenever ready; every workflow using the shell picks them up.
4. **Never swap in a Code node or raw HTTP call just because a credential is empty.** Use the proper node with the shell.

List existing shells (names and types only, never payloads):
```bash
sqlite3 -readonly "$N8N_DB" "SELECT id, name, type FROM credentials_entity;"
```

### One workflow, one job
If you can't describe a workflow in one sentence without "and," split it using "Execute Sub-workflow."

- Over 15-20 nodes or 3+ branching paths is a refactor candidate
- Each sub-workflow has a defined input shape and output
- Failures stay isolated to one sub-workflow
- Reusable logic (validation, notification formatting, enrichment) lives in shared sub-workflows, not copy-paste

### Retrieve, mold, output
Most workflows follow three phases: **Retrieve** data, **Mold** it (transform, filter, enrich), then **Output** results. It's not a rigid rule, but it simplifies most designs.

### Validate input early
Put an IF or Switch node right after the trigger to check the payload's shape. This catches garbage, missing fields, and wrong types before anything downstream runs. It matters most for webhooks that accept outside input.

### Graceful degradation
When a non-critical path fails (enrichment, logging, notification), use "Continue On Fail" with a fallback value. Reserve hard failures for critical paths (payments, data writes, auth).

### Rate-limit awareness
Add Wait nodes between sequential calls to the same external API. Respect `429` responses and back off.

### Keep it simple
Solve the 98% case first. Handle edge cases when they actually happen. Growing complexity is a signal to split, not to add branches.

## Naming Conventions

### Workflow names
Short and descriptive, with no status prefixes or domain brackets: `Card Scanner`, `Error Handler`, `Security Scan`, `Token Logger`. For variants, append with a middot: `Token Logger · Test`. Categorize with tags, not names.

### Tags (two layers)
- **Org scope:** who owns it (for example `business`, `personal`)
- **Functional category:** `tools`, `it-ops`, `infra`, `finance`, `hr`

Example: `Card Scanner` gets `business` + `tools`. `Error Handler` gets `infra` (document its owner and allowed scopes, since it is shared).

### Node names
Rename every node from its default to say what it does. Bad: `HTTP Request 4`, `IF`, `Code1`. Good: `Fetch Invoice PDF`, `Filter: Active Customers Only`, `Send Alert: Failure`, `Parse Webhook Payload`.

### Credential names
`Service · Context`, for example `OpenAI · Business` vs `OpenAI · Personal`, or `Chat Webhook · Alerts`.

## On Create / Modify

### 1. Back up first
Export the current JSON before any change:
```bash
mkdir -p "$N8N_BACKUP_DIR"
curl --fail --silent --show-error "$N8N_URL/api/v1/workflows/${WORKFLOW_ID:?set workflow ID}" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY:?set API key}" \
  -o "$N8N_BACKUP_DIR/${WORKFLOW_ID}-$(date +%Y%m%d-%H%M%S).json"
```
Confirm the export is valid, complete JSON for the right workflow ID before changing anything. If you keep version history in Git, use a private repo and strip secrets, webhook URLs, and customer payloads first.

### 2. Add a sticky note
Every workflow gets a sticky note as its first visual element:
```
WORKFLOW: [Name]
---
PURPOSE: [One sentence]
TRIGGER: [Webhook / Schedule / Manual / Error Trigger]
OWNER: [Name or team]

CREDENTIALS:
- [Credential name] -- [What it's for]

DEPENDENCIES:
- [Sub-workflows called]
- [External services hit]

KILL SWITCH:
- Safe to deactivate: [Yes/No]
- Impact if paused: [What stops working]
- Recovery steps: [How to resume]

WHEN IT BREAKS:
1. Check [specific thing]
2. Check [specific thing]
3. Execution history: [link to your n8n executions view]

LAST UPDATED: [Date]
```

Webhook workflows add:
```
WEBHOOK: [Full path]
USAGE: [Frequency, e.g. "Infrequent; silence is normal."]
CALLERS: [What sends to this webhook]
```

AI workflows add:
```
AI USAGE:
- Provider: [Anthropic / OpenAI / Gemini]
- Model: [model ID]
- Token Logger: [Yes]
- Estimated cost per execution: [rough estimate]
```

### 3. Link the error handler (every workflow)
Set `settings.errorWorkflow` to your error-handler workflow's ID after confirming its alert destination is correct. Skip the error handler itself and monitor it externally.

Via API:
```json
{ "settings": { "errorWorkflow": "<error-handler-id>" } }
```

Some n8n versions reject `errorWorkflow` in a `PUT` body. If so, use the editor. Direct DB edits are a last resort under the maintenance gate in `references/api.md`, never a way around an auth refusal.

### 4. Link the token logger (AI workflows only)
After each AI response, add an "Execute Sub-workflow" node pointing at your token-logger workflow:
```json
{
  "provider": "anthropic",
  "model": "<model-id>",
  "input_tokens": "{{ from API response usage }}",
  "output_tokens": "{{ from API response usage }}",
  "workflow_name": "{{ $workflow.name }}",
  "execution_id": "{{ $execution.id }}",
  "timestamp": "{{ $now.toISO() }}"
}
```
The logger owns cost calculation and storage; the parent only passes raw data. Set "Continue On Fail" on this call so logging never kills the parent.

### 5. Webhook setup
- **Registration:** confirm a Webhook node is registered in `webhook_entity`. CLI imports do not register webhooks automatically. See `references/api.md`.
- **Respond immediately:** for heavy processing, return `200` early with a Respond to Webhook node, then continue. Otherwise callers time out and retry, which creates duplicates.
- **URL stability:** editing and saving a Webhook node can change its URL. Every caller then needs an update, so list callers in the sticky note.

### 6. Document credentials
Record each new credential's type, required fields, and source in the sticky note. Propose required environment variable names to the operator; changing the env file or credentials is a separate approved step. Creating or filling credentials in the editor is a manual setup step for the owner.

### 7. Retries for external calls
- Default intent: 3 retries with backoff, using n8n's node-level retry settings. A fixed "Wait Between Tries" is not exponential; build explicit backoff if you need it.
- Critical paths: retry, then alert on final failure.
- Non-critical paths: retry, then continue on final failure.

### 8. Dead-letter queue for critical workflows
When retries run out on a critical path, don't just alert and drop the payload. Route failed items to a dead-letter store (a table, a sheet, or a dedicated workflow) for review or replay. This is required for financial data, customer records, and anything irreversible.

### 9. Keep execution saving on
Make sure the workflow doesn't override the global default for saving successful executions. You'll want them when debugging "it used to work."

### 10. Test before activating
- Run the happy path with realistic, synthetic payloads ("Execute Once")
- Pin node outputs so you don't re-run expensive upstream calls while testing downstream nodes
- Test failure paths on purpose: bad input, expired credentials, timeouts
- Exercise every IF/Switch branch, not just the happy one
- For webhooks, test with dummy data before pointing real callers at it
- For schedules, confirm the cron fires when you expect, in the timezone you expect
- Trigger a deliberate failure to prove the error handler fires
- For AI workflows, confirm the token logger received data

### 11. Canvas layout
Group related nodes and fence logical sections ("Retrieve," "Transform," "Output") with sticky notes. A canvas that looks like spaghetti is one nobody will debug.

## Maintenance

### Model ID staleness
Providers retire model IDs. HTTP Request nodes that call LLM APIs hardcode model IDs in their body. After a provider release:
1. Find affected workflows read-only: `sqlite3 -readonly "$N8N_DB" "SELECT id, name FROM workflow_entity WHERE nodes LIKE '%<old-model-id>%';"`
2. Update through the editor or API after a backup; DB edits only under the maintenance gate.
3. Update the token logger's pricing table if pricing changed.
4. Verify the exact workflow, model, and a real execution afterward.

### Webhook health
Outbound webhook URLs stored in env vars (chat alerts and similar) can be deleted or regenerated without notice. When a workflow fails at its delivery step, check that URL first.

## Known Pitfalls

**Zombie workflows: setting `active=0` in the DB does not stop a loaded trigger.** n8n's activation registry doesn't re-read the raw flag. Deactivate through the editor, API, or CLI (`n8n update:workflow --id=<ID> --active=false`), restart if required, then prove it by watching `execution_entity` across at least two trigger windows.

**Execute Command hangs when the child holds stdin open.** n8n keeps a pipe on the command's stdin. A script that reads or inherits stdin never sees EOF, and the execution sits in `running` forever. Fix: append `< /dev/null` to the command.

**Many `404` errors across many workflows usually means one dead webhook env var.** If workflows post alerts through a shared `$env.*_WEBHOOK` variable, test that URL first (`404` means it was deleted). Recreate it, update the env file, restart, and re-test. Don't debug each workflow separately.

**Stuck `running` execution rows: filter `deletedAt IS NULL` first.** With `saveDataSuccessExecution: none`, n8n finishes the run and soft-deletes it; the row can keep `status='running'` until the next hard-delete pass. Those rows are normal. Only rows with `deletedAt IS NULL` are truly stuck.

**Audit the deployed version, not the editor draft.** Resolve `activeVersionId` against `workflow_history` before tracing production behavior. The editable nodes can differ from what runs.

**Read cron fields and the effective timezone.** Six-field cron includes seconds. Take the timezone from workflow settings and the service environment, then cross-check against execution timestamps.

**Trace real callers before declaring a dependency.** Follow active nodes into the scripts and endpoints they call. Unused env vars and comments don't prove a live dependency.

**Don't replay previews or cancelled runs blindly.** Inspect the send logic and any delivery ledger first. A cancelled run may have partially delivered already.

**Copy-pasted nodes carry baggage.** A duplicated node keeps its old credential binding, webhook ID, and settings. Check every field after pasting.

**`PUT` can strip credential references.** Some versions drop credential bindings from responses or fail validation on credential-dependent workflows. Compare bindings before and after, and prefer the editor for those changes.

**Sub-workflow errors don't bubble up automatically.** The parent's error handler won't fire unless you propagate the error. Test the whole chain.

**Webhook workflows need both activation fields.** `active = 1` and a valid `activeVersionId` must both be set, or the webhook silently stops receiving.

## On Debug

1. **Check execution history** via the API, filtered by workflow and failed status (see `references/api.md`).
2. **Check the error handler's own executions.** If no alert fired, the handler may be broken.
3. **Check the alert destination** (chat channel, email). Did the alert actually land?
4. **Read the workflow's sticky note** for its specific troubleshooting steps.
5. **Check service health:** `systemctl is-active n8n.service`
6. **Check logs:** `journalctl -u n8n.service -n 50 --no-pager`
7. **Review node names.** Flag defaults for a later approved rename; don't rename during inspection.
8. **AI workflows:** if the token logger shows recent entries but the workflow looks broken, the AI call worked and downstream processing failed.

## Version Awareness

On any n8n version change, re-verify:
- The Error Trigger data shape your handler reads
- API endpoint behavior
- The `webhook_entity` schema
- That `activeVersionId` is still required for webhook workflows
- Webhook URLs
- Node types that may be renamed or deprecated

See `references/upgrade.md` for a backup-first upgrade procedure.

## Verification

After setup, verify input rejection, every branch, the happy path, failure paths, sub-workflow error propagation, real alert receipt, and token-logger receipt. Use isolated synthetic fixtures. Verify retries, backoff, and the dead-letter path without repeating irreversible actions (use idempotency keys for financial or customer writes). Verify webhook registration, early response, caller stability, and schedule timezone.
