# agent-skills

[![ci](https://github.com/Tranman324/agent-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/Tranman324/agent-skills/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Five skills I use every day with AI coding and ops agents. Each one is a `SKILL.md`
playbook (the `name` / `description` frontmatter format used by Claude Code and similar
agent runtimes), plus scripts and tests where the skill needs real code.

They came out of running agents against production systems. Most of the rules exist
because something broke once.

| Skill | What it does | Code |
|---|---|---|
| [`ios-shortcuts`](skills/ios-shortcuts) | Generates Apple Shortcuts (`.shortcut` binary plists) from Python or JSON, with a validator and build standards | Python generator, 15 tests |
| [`loom-ingest`](skills/loom-ingest) | Turns a Loom or any video into a timestamped transcript lined up with screen frames, so a text-only agent can "watch" it | Python + ffmpeg, 8 tests |
| [`gate-audit`](skills/gate-audit) | Merge-gate review: three independent audits (spec, bugs, adversarial) pinned to one commit, with evidence rules | Playbook |
| [`n8n-workflows`](skills/n8n-workflows) | Standards for changing self-hosted n8n safely: backups, error handling, credentials, monitoring, upgrades | Playbook + references |
| [`take-the-wheel`](skills/take-the-wheel) | Has the agent lead a decision one question at a time, or in dependency-ordered rounds, until there's a plan | Playbook |

## Use

Copy a skill folder into your agent's skills directory, for example:

```bash
cp -r skills/gate-audit ~/.claude/skills/
```

The agent loads it when the `description` matches the task.

## Tests

Needs Python 3.10+ and `ffmpeg` (for loom-ingest). No network or API keys required.

```bash
python3 -m unittest discover -s tests            # repo structure and safety checks
python3 -m unittest discover -s skills/ios-shortcuts/tests
python3 -m unittest discover -s skills/loom-ingest/tests
```

## Notes

- Everything here is generic. Hosts, IDs, and examples are placeholders (`example.com`, `$N8N_URL`).
- Secrets come from environment variables or Apple Shortcuts Import Questions. Nothing is hardcoded.
- Two skills adapt ideas from [mattpocock/skills](https://github.com/mattpocock/skills). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## License

[MIT](LICENSE)
