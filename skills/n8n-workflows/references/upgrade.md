# Upgrading a Native n8n Install (npm global + systemd)

Assumes n8n was installed with `npm install -g n8n`, runs as `n8n.service`, and uses SQLite under `$N8N_USER_FOLDER/.n8n/`. An upgrade is a change to a live system: get the owner's approval first.

1. **Pick the version.** Check the security advisory's fixed version for the branch you run (`n8n --version`). Prefer the `stable` tag's patch release.
2. **Export while running:**
   ```bash
   BK="$N8N_USER_FOLDER/backups/pre-<ver>-$(date +%Y%m%d-%H%M%S)"
   mkdir -p "$BK" && chmod 700 "$BK"
   N8N_USER_FOLDER="$N8N_USER_FOLDER" n8n export:workflow --all --backup --output="$BK/workflows/"
   N8N_USER_FOLDER="$N8N_USER_FOLDER" n8n export:credentials --all --backup --output="$BK/credentials/"   # stays encrypted
   ```
   Load the service's env file first if n8n needs it to start the CLI.
3. **Stop and snapshot:** `systemctl stop n8n`, then `sqlite3 "$N8N_DB" 'PRAGMA wal_checkpoint(TRUNCATE)'`. Copy `database.sqlite`, `.n8n/config` (holds the encryption key), the env file, and the unit file into `$BK`. Confirm `PRAGMA integrity_check` returns `ok` on the copy and the SHA-256 matches the original.
4. **Install:** move the old package aside (for rollback), then `npm install -g n8n@<ver>`. Expect a few minutes.
5. **Start and verify:** start the service, wait for `/healthz` to return `200`, and check the journal for the version-change and migration lines. Then confirm a scheduled workflow and a webhook workflow both run.

**Rollback:** stop, restore the old package directory, restore `database.sqlite` from the backup (migrations are forward-only), start.

**Pitfalls:**
- An external watchdog may restart n8n during the upgrade window. That's harmless, but expect an extra start in the journal, or pause the watchdog first.
- Workflows with `saveDataSuccessExecution: none` can show `running` rows that are actually finished (see the main skill). That is not an upgrade regression.
- `Failed to start Python task runner` at boot is expected if no workflow uses Python Code nodes.
