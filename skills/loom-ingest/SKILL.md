---
name: loom-ingest
description: "Use when an agent needs to understand a Loom or video. Builds a timestamped transcript aligned with screen frames."
license: MIT
platforms: [linux, macos]
---

# loom-ingest: make a video readable

Downloads a video, transcribes the speech with timestamps, grabs one frame per spoken segment, and writes a manifest that lines up what was SAID with what was ON SCREEN.

Most AI agents can't watch a video. This rebuilds it as two aligned streams:

- **Speech:** a timestamped transcript from the OpenAI Whisper API
- **Visual:** one frame per transcript segment, taken at the segment's midpoint
- **Manifest:** `manifest.md`, interleaving `[mm:ss] text → frame path`

When someone says "make *this* bigger," the frame shows what "this" was.

## Prerequisites

- `python3` (3.9+)
- `ffmpeg` / `ffprobe`: audio extraction and frame capture
- `yt-dlp`: video download (only for URLs)
- `curl`: Whisper API call
- `OPENAI_API_KEY` in the environment (only for transcription; not needed with `--srt`)

## Usage

```bash
# From a Loom share link
python3 scripts/loom_ingest.py "https://www.loom.com/share/<id>"

# Custom output directory
python3 scripts/loom_ingest.py "<url>" --out /tmp/myrun

# Local video file (skip download)
python3 scripts/loom_ingest.py --video local.mp4

# Reuse an existing transcript (no API key needed)
python3 scripts/loom_ingest.py --video local.mp4 --srt local.srt
```

Paths are relative to this skill's folder.

## Output

| File | Description |
|---|---|
| `manifest.md` | Read this first: aligned transcript plus frame references |
| `frames/seg_NNN_MMmSSs.jpg` | One frame per spoken segment |
| `transcript.srt` | Raw SRT transcript |
| `transcript.json` | Raw Whisper response |
| `video.mp4` | Downloaded video |

## Procedure

1. Run the script with the video URL. Transcription takes from seconds to a few minutes.
2. Read `manifest.md`. For vague references ("make *this* bigger"), open the referenced frame to see what was on screen.
3. Summarize every distinct request with its timestamp.
4. If the human wants a durable checklist, build it from the manifest: each item gets a timestamp, a frame, and the target area.

## Pitfalls

- **API call fails (bad key, quota, network).** The video and `audio.mp3` are already in the output folder. Transcribe locally with open-source Whisper (`whisper audio.mp3 --model base.en --output_format srt --output_dir . --fp16 False`), then rerun with `--video video.mp4 --srt audio.srt`.
- **Frame count equals segment count.** A 7-minute video makes roughly 40-50 frames. Long videos make many.
- **Private or SSO-protected Looms won't download.** You need a public share link (`/share/<id>`).
- **Whisper is fast but weak on proper nouns.** Read for intent and double-check names.
- **Cost:** Whisper API pricing is per audio minute (about $0.006/min at the time of writing), so a 5-minute video costs a few cents. Check current pricing.
- **Privacy:** the audio is uploaded to OpenAI. Don't send recordings you aren't allowed to share with a third party.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests build a short synthetic video with `ffmpeg` and use a hand-written SRT, so they need no network access and no API key.
