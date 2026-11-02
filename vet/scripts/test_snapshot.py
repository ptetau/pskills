#!/usr/bin/env python3
"""Tests for snapshot.py. Run: python3 test_snapshot.py"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snapshot  # noqa: E402

ENV = {
    **os.environ,
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "commit.gpgsign",
    "GIT_CONFIG_VALUE_0": "false",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}


def sh(cwd, *args):
    subprocess.run(args, cwd=cwd, env=ENV, check=True, capture_output=True)


def write(path, text="x\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = os.path.realpath(self.tmp.name)
        main = os.path.join(base, "main")
        os.makedirs(main)
        sh(main, "git", "init", "-q")
        write(os.path.join(main, "a.txt"))
        sh(main, "git", "add", "-A")
        sh(main, "git", "commit", "-qm", "base")
        self.root = os.path.join(base, "wt")
        sh(main, "git", "worktree", "add", "-q", "-b", "run", self.root)
        write(os.path.join(self.root, "b.txt"))
        sh(self.root, "git", "add", "-A")
        sh(self.root, "git", "commit", "-qm", "root change\n\nBody line.\n\nTrailer: yes")
        proj = os.path.join(self.root, "proj")
        os.makedirs(proj)
        sh(proj, "git", "init", "-q")
        write(os.path.join(proj, "p.txt"))
        sh(proj, "git", "add", "-A")
        sh(proj, "git", "commit", "-qm", "proj first\n\nWhy: because.\n\nCo-Authored-By: A <a@a>")
        write(os.path.join(proj, ".vet-tmp", "cap.py"))
        write(os.path.join(proj, "deep", ".vet-capture", "x.md"))
        write(os.path.join(self.root, ".vet-tmp", "ready.py"))
        write(os.path.join(self.root, ".vet-capture", "P01-r01.md"))
        self.out = snapshot.render(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_heading(self):
        self.assertTrue(self.out.startswith("## Repos"))

    def test_lists_repos(self):
        self.assertIn("### .", self.out)
        self.assertIn("### proj", self.out)

    def test_full_bodies(self):
        for s in ("root change", "Body line.", "Trailer: yes", "proj first", "Why: because.", "Co-Authored-By: A <a@a>"):
            self.assertIn(s, self.out)

    def test_root_excludes_base_commit(self):
        self.assertNotIn("\nbase\n", self.out)

    def test_status_empty_and_no_vet_paths(self):
        self.assertNotIn("??", self.out)
        self.assertNotIn(".vet-tmp", self.out)
        self.assertNotIn(".vet-capture", self.out)

    def test_real_untracked_file_shows(self):
        write(os.path.join(self.root, "proj", "new.txt"))
        self.assertIn("?? new.txt", snapshot.render(self.root))

    def test_never_commits(self):
        n = subprocess.run(["git", "-C", self.root, "rev-list", "--count", "HEAD"],
                           capture_output=True, text=True).stdout.strip()
        self.assertEqual(n, "2")


if __name__ == "__main__":
    unittest.main()
