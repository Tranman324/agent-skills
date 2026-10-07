# n8n API and Database Reference

Generic reference for a self-hosted n8n instance. Set `N8N_URL`, `N8N_API_KEY`, and `N8N_DB` as described in the main skill. The main skill's safety boundary governs everything here.

## API Access

- **Endpoint:** `$N8N_URL/api/v1/`
- **Auth header:** `X-N8N-API-KEY: <your key>`
- **Scopes:** create the key with the minimum scopes the task needs (for example `workflow:read`, `workflow:list`, `execution:read`, `execution:list`). Add write scopes only for approved change work.
- Some versions return `Forbidden` on endpoints such as `/tags` or `POST /workflows/{id}/activate` even for scoped keys. Stop and fix the key's scope or project. Do not fall back to database edits.

**Secret hygiene:** never store a plaintext API key in markdown, chat, or exported examples. Load it from an environment variable or secret manager. Do not echo it.

## Common API Calls

### List workflows
```bash
set -o pipefail
curl --fail --silent --show-error "$N8N_URL/api/v1/workflows" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY:?set API key}" \
  | jq '[.data[] | {id, name, active}]'
```
List calls return one page. Follow `nextCursor` until it is empty before claiming a full inventory.

### Get workflow details
```bash
curl --fail --silent --show-error "$N8N_URL/api/v1/workflows/${WORKFLOW_ID:?set workflow ID}" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY:?set API key}"
```

### Update workflow
```bash
curl --fail --silent --show-error -X PUT "$N8N_URL/api/v1/workflows/${WORKFLOW_ID:?set workflow ID}" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY:?set API key}" \
  -H "Content-Type: application/json" \
  --data-binary @reviewed-workflow-update.json
```
`reviewed-workflow-update.json` is a payload you build from the backup export and review. It must keep the existing nodes, connections, settings, credentials, and ownership. A near-empty body can overwrite a real workflow.

**Quirk (2.x):** `PUT` may reject `settings.binaryMode` with `400 settings must NOT have additional properties`. Drop that key; n8n keeps the stored value. If you rename a node, rename its key in `connections` too.

**Quirk:** `PUT` can strip credential references from responses and may fail validation on credential-dependent workflows. Prefer the editor for those changes.

### Get failed executions
```bash
curl --fail --silent --show-error "$N8N_URL/api/v1/executions?workflowId=${WORKFLOW_ID:?set workflow ID}&status=error&limit=5" \
  -H "X-N8N-API-KEY: ${N8N_API_KEY:?set API key}"
```

## Database Access

**When to use the DB:** read-only inventory and health checks, activation-state inspection, webhook registration checks, and rare cases the API can't cover.

**Writes are maintenance, not a shortcut.** A DB write needs explicit owner approval for the exact target, a restorable backup, a schema check against your version, and n8n stopped. Never use it to get around an API permission refusal.

```bash
# Read-only query (safe while running)
sqlite3 -readonly "$N8N_DB" "SELECT id, name, active FROM workflow_entity;"

# Approved maintenance only: stop, back up, change, start, verify
systemctl stop n8n.service
cp "$N8N_DB" "$N8N_DB.bak-$(date +%Y%m%d-%H%M%S)"
# ... approved change ...
systemctl start n8n.service
```

### Key tables

| Table | Purpose |
|---|---|
| `workflow_entity` | Workflow definitions, active state, settings, current version |
| `webhook_entity` | Registered webhook paths |
| `workflow_history` | Version history; active workflows point `activeVersionId` at a valid version |
| `execution_entity` | Execution metadata and status |
| `execution_data` | Execution payloads and results (may contain sensitive data) |
| `credentials_entity` | Credential names and types (payloads are encrypted; never print them) |
| `user_api_keys` | API key records; never read or print |

### Activation state check

```sql
SELECT id, name, active, triggerCount,
       activeVersionId IS NOT NULL AS hasActiveVersion,
       versionId = activeVersionId AS activeVersionMatches
FROM workflow_entity
WHERE isArchived = 0
ORDER BY name;
```

### Activating a workflow via the DB (maintenance only)

Prefer the editor or API. If approved maintenance requires it, confirm `versionId` resolves to the intended `workflow_history` row first, then read back the flags and prove the trigger fires after restart.

```sql
UPDATE workflow_entity
SET active = 1,
    activeVersionId = versionId
WHERE id = '<WORKFLOW_ID>';
```

### Registering a webhook (maintenance only)

```sql
INSERT INTO webhook_entity (workflowId, webhookPath, method, node, webhookId)
VALUES ('<WORKFLOW_ID>', '<PATH>', '<METHOD>', '<NODE_NAME>', '<WEBHOOK_ID>');
```

- `webhookPath`: the `path` parameter from the Webhook node
- `method`: `GET` or `POST`, from the Webhook node
- `node`: the Webhook node's name
- `webhookId`: the Webhook node's ID

Check that the path is unique before inserting.

### Setting the error workflow (maintenance only)

```sql
UPDATE workflow_entity
SET settings = json_set(settings, '$.errorWorkflow', '<ERROR_HANDLER_ID>')
WHERE id = '<WORKFLOW_ID>';
```

## Token Logger Input Schema

```json
{
  "provider": "anthropic",
  "model": "<model-id>",
  "input_tokens": 1500,
  "output_tokens": 350,
  "workflow_name": "parent-workflow-name",
  "execution_id": "abc123"
}
```

The token logger computes cost from a pricing table and writes to your logging store.

## Credentials

n8n uses both credential shells and runtime environment variables. A placeholder shell does not automatically mean a workflow is broken; some workflows read secrets from env vars instead. Check the node before declaring a credential stale.

Name credentials `Service · Context`. Keep a list of shell names and types in your private runbook, never values.

Typical env var names (document names only, never values):
- Alert webhooks, e.g. `ALERTS_WEBHOOK_URL`
- Database or backend keys, e.g. `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- Provider keys, e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

## Node Configuration Notes

- Don't broaden node exclusions or env access just to make something work. Blocked nodes need a separate least-privilege review.
- Execute Command nodes behave differently in Docker and native installs (filesystem and process scope). Verify paths on your install.
- Treat Code nodes as sandboxed pure-JS transforms, not a way to reach the filesystem or secrets.
- SQL above matches the 2.x schema. Test it on a copy of the database before any approved maintenance.
