"""A small project on disk for the slice tests: a git repo, slice/ records, a stub module,
and unittest tests named by slice ID."""
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SLICE = PLUGIN / "bin" / "slice.py"
GUARD = PLUGIN / "hooks" / "guard.py"

CONFIG = """# slice config

- stack: python, unittest
- test command: `PYTHONPATH=src python3 -m unittest discover -s tests -v`
- result format: unittest
- tests folder: `tests`
- source folders: `src`
"""

SPEC = """# Spec: wordfreq

Status: ratified

## Decisions

- D1 (case): words are lower case.
"""

SLICES = """# Slices

## S1: Count words

- Story: As a user, I count the words of a text.
- Acceptance:
  - Given "a b a", the count of "a" is 2.
- Layers: core
- Status: red
- Test rounds: 0
- Review rounds: 0

## S2: Top words

- Story: As a user, I see the most common words.
- Acceptance:
  - Given "a b a", the top word is "a".
- Layers: core, cli
- Status: red
- Test rounds: 0
- Review rounds: 0
"""

INTERFACE = "# Interface\n\n## S1\n\n- count(text) -> dict\n\n## S2\n\n- top(text, n) -> list\n"

STUB = '''def count(text):
    return None


def top(text, n):
    return None
'''

TESTS = '''import unittest

import wordfreq


class Words(unittest.TestCase):
    def test_S1_counts_words(self):
        self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})

    def test_S1_empty_text(self):
        self.assertEqual(wordfreq.count(""), {})

    def test_S2_top_word(self):
        self.assertEqual(wordfreq.top("a b a", 1), ["a"])
'''

GOOD = '''from collections import Counter


def count(text):
    return dict(Counter(text.split()))


def top(text, n):
    return [w for w, _ in Counter(text.split()).most_common(n)]
'''


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


class Project:
    def __init__(self, config=CONFIG, slices=SLICES, tests=TESTS, stub=STUB):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "T")
        git(self.root, "config", "commit.gpgsign", "false")
        for rel, text in {"slice/config.md": config, "slice/spec.md": SPEC, "slice/slices.md": slices,
                          "slice/interface.md": INTERFACE, "src/wordfreq.py": stub,
                          "tests/test_wordfreq.py": tests}.items():
            self.write(rel, text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def read(self, rel):
        return (self.root / rel).read_text()

    def slice(self, *args):
        return subprocess.run([sys.executable, str(SLICE), *args], cwd=self.root, capture_output=True,
                              text=True)

    def close(self):
        self._tmp.cleanup()
