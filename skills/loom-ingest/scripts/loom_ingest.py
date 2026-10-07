#!/usr/bin/env python3
"""loom_ingest: turn a Loom (or any) video into something an AI agent can read.

Downloads the video, extracts audio, transcribes it with the OpenAI Whisper API,
grabs one frame per transcript segment at its midpoint, and writes manifest.md
aligning what was said to what was on screen.

Usage:
    loom_ingest.py <url> [--out DIR]
    loom_ingest.py --video FILE [--srt FILE.srt] [--out DIR]

Deps: yt-dlp (URLs only), ffmpeg/ffprobe, curl.
Transcription needs OPENAI_API_KEY in the environment. It is not needed with --srt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions"


def get_openai_key() -> str:
    """Read the OpenAI API key from the environment."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        sys.exit("OPENAI_API_KEY is not set (needed for transcription; pass --srt to skip)")
    return key


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    """Run a command, raising on failure."""
    return subprocess.run(cmd, check=True, **kw)


def vid_id(url: str) -> str:
    """Extract a short id from a Loom share URL, or 'local'."""
    m = re.search(r"/share/([0-9a-f]{16,})", url or "")
    return m.group(1)[:16] if m else "local"


def download(url: str, out: Path) -> Path:
    """Download video via yt-dlp."""
    dest = out / "video.mp4"
    if dest.exists():
        print(f"  video already exists: {dest}")
        return dest

    print(f"  downloading: {url}")
    sh(["yt-dlp", "--no-playlist", "--no-update", "-o", str(out / "video.%(ext)s"), url])

    vids = sorted(out.glob("video.*"))
    v = next((p for p in vids if p.suffix in (".mp4", ".mkv", ".webm")), None)
    if not v:
        sys.exit("download failed: no video file produced")
    return v


def extract_audio(video: Path, out: Path) -> Path:
    """Extract audio as mono 16 kHz mp3 (a small upload for the API)."""
    mp3 = out / "audio.mp3"
    if mp3.exists():
        return mp3

    print("  extracting audio...")
    sh(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-ar", "16000", "-ac", "1",
         "-b:a", "64k", str(mp3)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return mp3


def segments_to_srt(segments: list[dict]) -> str:
    """Convert Whisper verbose_json segments to SRT text, skipping empty ones."""
    lines: list[str] = []
    n = 0
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        n += 1
        lines += [
            str(n),
            f"{fmt_srt_ts(seg.get('start', 0))} --> {fmt_srt_ts(seg.get('end', 0))}",
            text,
            "",
        ]
    return "\n".join(lines)


def transcribe_openai(audio: Path, api_key: str, out: Path) -> Path:
    """Transcribe via the OpenAI Whisper API and write transcript.srt."""
    srt = out / "transcript.srt"
    if srt.exists():
        print(f"  transcript already exists: {srt}")
        return srt

    print("  transcribing via OpenAI Whisper API...")

    # The auth header is passed on stdin (-H @-) so the key never appears
    # in the process list or shell history.
    result = subprocess.run(
        [
            "curl", "-sS", "-X", "POST", WHISPER_URL,
            "-H", "@-",
            "-F", f"file=@{audio}",
            "-F", "model=whisper-1",
            "-F", "response_format=verbose_json",
            "-F", "timestamp_granularities[]=segment",
        ],
        input=f"Authorization: Bearer {api_key}\n",
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        sys.exit(f"OpenAI API call failed: {result.stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        sys.exit(f"Failed to parse API response: {result.stdout[:500]}")

    if "error" in data:
        sys.exit(f"OpenAI API error: {data['error']}")

    (out / "transcript.json").write_text(json.dumps(data, indent=2))
    segments = data.get("segments", [])
    srt.write_text(segments_to_srt(segments))
    print(f"  {len(segments)} segments transcribed")
    return srt


def fmt_srt_ts(sec: float) -> str:
    """Format seconds as an SRT timestamp: HH:MM:SS,mmm."""
    total_ms = int(round(float(sec) * 1000))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(srt: Path):
    """Yield (idx, start_sec, end_sec, text) from an SRT file."""
    def to_sec(ts: str) -> float:
        h, m, rest = ts.split(":")
        s, ms = rest.replace(",", ".").split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms[:3].ljust(3, "0")) / 1000

    content = srt.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n").strip()
    for b in re.split(r"\n\s*\n", content):
        lines = [ln for ln in b.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        m = re.search(r"(\d\d:\d\d:\d\d[,\.]\d+)\s*-->\s*(\d\d:\d\d:\d\d[,\.]\d+)", lines[1])
        if not m:
            continue
        idx = lines[0].strip()
        text = " ".join(lines[2:]).strip()
        if text:
            yield idx, to_sec(m.group(1)), to_sec(m.group(2)), text


def frame_at(video: Path, sec: float, dest: Path):
    """Extract a single frame at the given timestamp."""
    sh(
        [
            "ffmpeg", "-y", "-ss", f"{sec:.2f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "3", str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def mmss(sec: float) -> str:
    """Format seconds as 00m00s."""
    return f"{int(sec // 60):02d}m{int(sec % 60):02d}s"


def build_manifest(source: str, segs: list, frame_names: list[str]) -> str:
    """Render manifest.md interleaving timestamps, frame paths, and speech."""
    lines = [
        "# Loom Ingest: speech aligned to frames",
        "",
        f"**Source:** {source}",
        f"**Segments:** {len(segs)}",
        "",
        "---",
        "",
    ]
    for (idx, start, end, text), fname in zip(segs, frame_names):
        lines += [f"## [{mmss(start)}–{mmss(end)}] {fname}", "", text, ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(description="Turn a Loom/video into an aligned transcript + frames")
    ap.add_argument("url", nargs="?", help="Loom/video URL")
    ap.add_argument("--video", help="Use a local video file (skip download)")
    ap.add_argument("--srt", help="Use a local .srt (skip transcription; no API key needed)")
    ap.add_argument("--out", help="Output dir (default /tmp/loom-<id>)")
    a = ap.parse_args(argv)

    if not a.url and not a.video:
        sys.exit("need a URL or --video")

    out = Path(a.out or f"/tmp/loom-{vid_id(a.url or a.video)}")
    (out / "frames").mkdir(parents=True, exist_ok=True)

    # Step 1: get the video
    video = Path(a.video) if a.video else download(a.url, out)

    # Step 2: get a transcript (only this step needs the API key)
    if a.srt:
        srt = Path(a.srt)
    else:
        audio = extract_audio(video, out)
        srt = transcribe_openai(audio, get_openai_key(), out)

    # Step 3: parse the transcript and extract one frame per segment
    segs = list(parse_srt(srt))
    print(f"  {len(segs)} segments → extracting frames...")

    frame_names = []
    for idx, start, end, _text in segs:
        fname = f"frames/seg_{idx.zfill(3)}_{mmss(start)}.jpg"
        frame_path = out / fname
        if not frame_path.exists():
            frame_at(video, (start + end) / 2, frame_path)
        frame_names.append(fname)

    (out / "manifest.md").write_text(build_manifest(a.url or a.video, segs, frame_names))

    print()
    print("DONE")
    print(f"OUT={out}")
    print(f"MANIFEST={out / 'manifest.md'}")
    print(f"FRAMES={out / 'frames'} ({len(segs)} frames)")


if __name__ == "__main__":
    main()
