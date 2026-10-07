# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Report them privately through
GitHub: **Security** tab → **Report a vulnerability**. I aim to reply within 7 days.

## Scope

Most of this repo is documentation. The parts that run code:

- `skills/loom-ingest/scripts/loom_ingest.py`: calls `yt-dlp`, `ffmpeg`, and the OpenAI API. The API key is read from `OPENAI_API_KEY` and passed to `curl` on stdin, not on the command line.
- `skills/ios-shortcuts/scripts/generate_shortcut.py`: writes `.shortcut` plist files. It makes no network calls.

Secrets must never be committed. CI runs a secret scan on every push.
