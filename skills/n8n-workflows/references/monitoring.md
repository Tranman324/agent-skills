# n8n Monitoring Setup

A two-layer monitoring model: an in-n8n error handler for workflow failures, plus an external watchdog for when n8n itself is down. The main skill's safety boundary governs everything here.

## Error Handler Workflow

One shared workflow catches every other workflow's failures.

- **Flow:** `Error Trigger → Format Alert → Send Alert → Validate Response`
- **Destination:** a chat webhook or similar, read from an env var (for example `$env.ALERTS_WEBHOOK_URL`), never hardcoded in workflow JSON
- **Linked to:** every active workflow via `settings.errorWorkflow`

### Alert format

- Workflow name and ID
- Failed node name
- Error message
- Execution link
- Timestamp

Keep payloads to metadata. Never include customer, health, finance, or HR data in an alert.

### Hardening

- Alert formatting falls back gracefully when the error has no message.
- Response validation catches a dead or rejected webhook.
- The webhook URL lives in env, so rotating it doesn't mean editing workflows.

### Linking a workflow to the error handler

```json
{
  "settings": {
    "errorWorkflow": "<error-handler-id>"
  }
}
```

Exception: the error handler itself. Linking it to itself creates recursion; monitor it externally instead.

## External Health Check

n8n can't alert you that n8n is down. Run a small deterministic watchdog outside it (system cron or a systemd timer), for example every 15 minutes:

- **Checks:** service is active, local API responds, new failed executions since last run, and critical schedules have fired recently (schedule liveness)
- **Behavior:** silent on success; alerts on state change and then hourly while still broken (dedupe, so one outage isn't 100 messages)
- **State:** a small state file holding the last status and last-seen execution ID
- **Secrets:** reads the API key and webhook URL from runtime sources, never from the script body

## Health Check Commands

```bash
# Service state
systemctl is-active n8n.service

# Version (resolve the service's binary if n8n isn't on PATH)
n8n --version

# Recent non-successful executions (read-only)
sqlite3 -readonly -header -column "$N8N_DB" \
  "SELECT e.id, w.name, e.status, e.mode, e.startedAt, e.stoppedAt
   FROM execution_entity e
   JOIN workflow_entity w ON w.id = e.workflowId
   WHERE e.status != 'success' AND e.deletedAt IS NULL
   ORDER BY e.startedAt DESC
   LIMIT 25;"
```

## Inventory Audit

Periodically confirm every active workflow has an error handler and a sticky note:

```sql
SELECT id, name,
       json_extract(settings, '$.errorWorkflow') AS errorWorkflow,
       nodes LIKE '%n8n-nodes-base.stickyNote%' AS hasStickyNote
FROM workflow_entity
WHERE active = 1 AND isArchived = 0
ORDER BY name;
```

## Scenarios to Test

| Scenario | Expected result |
|---|---|
| Workflow fails with an error message | Alert with full context |
| Workflow fails with no message | Alert still sent (graceful fallback) |
| Watchdog run, n8n healthy | Silent |
| Watchdog run, n8n down | Alert sent |
| n8n stays down | Hourly reminder, not one alert per run |
| n8n recovers | One recovery notice |

## Secret Hygiene

Never store plaintext API keys, webhook URLs, or credential values in markdown or Git. Record labels, env var names, scopes, and how to retrieve them.

## Verification

An HTTP `2xx` from the webhook is not proof a person saw the alert. After setup, trigger each scenario above and confirm the alert actually arrived at the intended destination.
