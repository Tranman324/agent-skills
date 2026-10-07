"""Repo-wide checks: every skill is well-formed, and nothing private or secret slipped in."""
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
EXPECTED = {"gate-audit", "ios-shortcuts", "loom-ingest", "n8n-workflows", "take-the-wheel"}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".txt", ""}


def text_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts and p.suffix in TEXT_SUFFIXES:
            yield p


def frontmatter(path: Path) -> dict:
    text = path.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path} has no frontmatter"
    return yaml.safe_load(m.group(1))


class Structure(unittest.TestCase):
    def test_exact_skill_set(self):
        self.assertEqual({p.name for p in SKILLS.iterdir() if p.is_dir()}, EXPECTED)

    def test_frontmatter(self):
        for name in EXPECTED:
            with self.subTest(skill=name):
                fm = frontmatter(SKILLS / name / "SKILL.md")
                self.assertEqual(fm["name"], name)
                self.assertTrue(fm["description"].startswith("Use when"), fm["description"])
                self.assertLessEqual(len(fm["description"]), 200)
                self.assertEqual(fm.get("license"), "MIT")

    def test_relative_links_resolve(self):
        for md in ROOT.rglob("*.md"):
            if ".git" in md.parts:
                continue
            for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)\s]+)\)", md.read_text()):
                with self.subTest(file=str(md.relative_to(ROOT)), link=target):
                    self.assertTrue((md.parent / target.split("#")[0]).exists())

    def test_referenced_skill_files_exist(self):
        for name in EXPECTED:
            skill = SKILLS / name
            for ref in re.findall(r"`((?:references|scripts)/[\w./-]+)`", (skill / "SKILL.md").read_text()):
                with self.subTest(skill=name, ref=ref):
                    self.assertTrue((skill / ref).exists())


SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9_-]{20,}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{30,}",
    r"xox[abpr]-[A-Za-z0-9-]{10,}",
    r"AKIA[0-9A-Z]{16}",
    r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"\b[a-f0-9]{48,}\b",
]
PRIVATE_PATTERNS = [
    r"/root/", r"/home/[a-z]", r"\bopenclaw\b", r"\bhermes\b", r"ts\.net\b",
    r"\b\d{17,20}\b",                     # chat platform snowflake IDs
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b",       # IPv4 addresses
    r"[\w.+-]+@(?!example\.(?:com|org|net)\b)[\w-]+\.[\w.]+",  # emails outside example.*
]
ALLOWED_IPS = {"127.0.0.1", "0.0.0.0"}


class Hygiene(unittest.TestCase):
    def test_no_secrets(self):
        for p in text_files():
            text = p.read_text(errors="ignore")
            for pat in SECRET_PATTERNS:
                with self.subTest(file=str(p.relative_to(ROOT)), pattern=pat):
                    self.assertIsNone(re.search(pat, text))

    def test_no_private_infrastructure(self):
        for p in text_files():
            if p == Path(__file__).resolve():
                continue
            text = p.read_text(errors="ignore")
            for pat in PRIVATE_PATTERNS:
                hits = [h for h in re.findall(pat, text, re.I) if h not in ALLOWED_IPS]
                with self.subTest(file=str(p.relative_to(ROOT)), pattern=pat):
                    self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
