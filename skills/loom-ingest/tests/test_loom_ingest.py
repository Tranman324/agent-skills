"""Offline tests for loom_ingest. No network or API key needed.

Builds a short synthetic test-pattern video with ffmpeg and a hand-written SRT,
then runs the full pipeline with --video and --srt.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "loom_ingest.py"

spec = importlib.util.spec_from_file_location("loom_ingest", SCRIPT)
li = importlib.util.module_from_spec(spec)
spec.loader.exec_module(li)

HAS_FFMPEG = shutil.which("ffmpeg") is not None

SAMPLE_SRT = """1
00:00:00,000 --> 00:00:01,500
Here is the settings page.

2
00:00:01,500 --> 00:00:03,000
Make this button bigger.

3
00:00:03,000 --> 00:00:03,500


4
00:00:03,500 --> 00:00:04,000
And move the logo left.
"""


class PureFunctions(unittest.TestCase):
    def test_fmt_srt_ts(self):
        self.assertEqual(li.fmt_srt_ts(0), "00:00:00,000")
        self.assertEqual(li.fmt_srt_ts(61.5), "00:01:01,500")
        self.assertEqual(li.fmt_srt_ts(3725.042), "01:02:05,042")
        # Float noise must not produce 999 ms or drop a second
        self.assertEqual(li.fmt_srt_ts(2.3), "00:00:02,300")
        self.assertEqual(li.fmt_srt_ts(59.9999), "00:01:00,000")

    def test_mmss(self):
        self.assertEqual(li.mmss(0), "00m00s")
        self.assertEqual(li.mmss(125.9), "02m05s")

    def test_vid_id(self):
        self.assertEqual(li.vid_id("https://www.loom.com/share/0123456789abcdef0123"), "0123456789abcdef")
        self.assertEqual(li.vid_id("local.mp4"), "local")
        self.assertEqual(li.vid_id(None), "local")

    def test_segments_to_srt_round_trip(self):
        segs = [
            {"start": 0.0, "end": 1.25, "text": " Hello there. "},
            {"start": 1.25, "end": 2.0, "text": "   "},
            {"start": 2.0, "end": 3.5, "text": "Second line."},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.srt"
            p.write_text(li.segments_to_srt(segs))
            parsed = list(li.parse_srt(p))
        self.assertEqual(
            parsed,
            [("1", 0.0, 1.25, "Hello there."), ("2", 2.0, 3.5, "Second line.")],
        )

    def test_parse_srt_skips_empty_and_handles_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.srt"
            p.write_bytes(SAMPLE_SRT.replace("\n", "\r\n").encode())
            parsed = list(li.parse_srt(p))
        self.assertEqual([s[0] for s in parsed], ["1", "2", "4"])
        self.assertEqual(parsed[1], ("2", 1.5, 3.0, "Make this button bigger."))

    def test_missing_key_exits_cleanly(self):
        old = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(SystemExit) as cm:
                li.get_openai_key()
            self.assertIn("OPENAI_API_KEY", str(cm.exception))
        finally:
            if old is not None:
                os.environ["OPENAI_API_KEY"] = old

    def test_no_hardcoded_credentials_or_private_paths(self):
        src = SCRIPT.read_text()
        self.assertNotRegex(src, r"/(root|home)/")
        self.assertNotRegex(src, r"sk-[A-Za-z0-9]{10,}")


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class EndToEnd(unittest.TestCase):
    def test_pipeline_with_local_video_and_srt(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            video = d / "in.mp4"
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=4:size=160x120:rate=10",
                 "-pix_fmt", "yuv420p", str(video)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            srt = d / "in.srt"
            srt.write_text(SAMPLE_SRT)
            out = d / "out"

            env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "--video", str(video), "--srt", str(srt), "--out", str(out)],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("DONE", r.stdout)

            frames = sorted(p.name for p in (out / "frames").glob("*.jpg"))
            self.assertEqual(frames, ["seg_001_00m00s.jpg", "seg_002_00m01s.jpg", "seg_004_00m03s.jpg"])
            for f in frames:
                self.assertGreater((out / "frames" / f).stat().st_size, 0)

            manifest = (out / "manifest.md").read_text()
            self.assertIn("**Segments:** 3", manifest)
            self.assertIn("## [00m01s–00m03s] frames/seg_002_00m01s.jpg", manifest)
            self.assertIn("Make this button bigger.", manifest)


if __name__ == "__main__":
    unittest.main()
