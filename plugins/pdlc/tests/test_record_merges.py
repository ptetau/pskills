"""Tests for pdlc's merge recorder. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/record_merges.py"
spec = importlib.util.spec_from_file_location("record_merges", SCRIPT)
record_merges = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record_merges)

INTENT = """# IN-0001 · Password reset

Status: {status} · Ticket: none · Branch: none · Added: 2026-10-10

## Changes

- CH-0001 · Email templates
- CH-0002 · Send the reset

## Notes

Status: this line is a note, not the header.
"""

CHANGE = """# {id} · A change

Intent: IN-0001 · Scope: CAP-email · Status: {status} · Ticket: none · Branch: {branch} · Base: main

## Requirements

### CAP-email.R1 · Send plain email
"""

FIRST = "pdlc/CH-0001-email-templates"
SECOND = "pdlc/CH-0002-send-reset"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


class RecordMerges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@t")
        git(self.root, "config", "user.name", "t")
        self.write_intent("building")
        self.write_change("CH-0001-email-templates", "planned", "none")
        self.write_change("CH-0002-send-reset", "planned", "none")
        self.commit_all("Plan IN-0001")
        # CH-0001 in review on its branch, CH-0002 in review on a branch stacked on it.
        git(self.root, "switch", "-qc", FIRST)
        self.write_change("CH-0001-email-templates", "in review", FIRST)
        self.commit_all("Propose CH-0001")
        git(self.root, "switch", "-qc", SECOND)
        self.write_change("CH-0002-send-reset", "in review", SECOND)
        self.commit_all("Propose CH-0002")
        git(self.root, "switch", "-q", "main")

    def tearDown(self):
        self.tmp.cleanup()

    def write_intent(self, status):
        path = self.root / "pdlc/inbox/IN-0001-password-reset.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(INTENT.format(status=status))

    def write_change(self, folder, status, branch):
        path = self.root / "pdlc/changes" / folder / "change.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(CHANGE.format(id=folder[:7], status=status, branch=branch))

    def commit_all(self, message):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", message)

    def merge(self, branch):
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge " + branch, branch)

    def status_of(self, path):
        return record_merges.field((self.root / path).read_text(), "Status")

    def run_record(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = record_merges.main(["record_merges.py"], root=self.root)
        return code, out.getvalue()

    def test_sets_a_merged_change_to_merged_and_commits_on_main(self):
        self.merge(FIRST)
        code, out = self.run_record()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status_of("pdlc/changes/CH-0001-email-templates/change.md"), "merged")
        self.assertIn("CH-0001", out)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertEqual(git(self.root, "log", "-1", "--format=%s"), "Record merges")
        self.assertEqual(git(self.root, "log", "-1", "--format=%(trailers:key=Intent,valueonly)"),
                         "IN-0001")

    def test_leaves_a_change_whose_branch_has_not_merged(self):
        self.merge(FIRST)
        self.run_record()
        self.assertEqual(self.status_of("pdlc/changes/CH-0002-send-reset/change.md"), "planned")
        self.assertEqual(self.status_of("pdlc/inbox/IN-0001-password-reset.md"), "building")

    def test_sets_the_intent_to_done_when_all_its_changes_merged(self):
        self.merge(SECOND)
        code, out = self.run_record()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status_of("pdlc/changes/CH-0001-email-templates/change.md"), "merged")
        self.assertEqual(self.status_of("pdlc/changes/CH-0002-send-reset/change.md"), "merged")
        intent = (self.root / "pdlc/inbox/IN-0001-password-reset.md").read_text()
        self.assertEqual(record_merges.field(intent, "Status"), "done")
        self.assertIn("Status: this line is a note, not the header.", intent)
        self.assertIn("IN-0001", out)

    def test_commits_nothing_when_nothing_merged(self):
        before = git(self.root, "rev-parse", "HEAD")
        code, out = self.run_record()
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertIn("Nothing to record", out)

    def test_records_each_merge_once(self):
        self.merge(SECOND)
        self.run_record()
        after_first = git(self.root, "rev-parse", "HEAD")
        code, out = self.run_record()
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), after_first)

    def test_never_writes_to_a_change_branch(self):
        tips = {b: git(self.root, "rev-parse", b) for b in (FIRST, SECOND)}
        self.merge(SECOND)
        self.run_record()
        self.assertEqual({b: git(self.root, "rev-parse", b) for b in (FIRST, SECOND)}, tips)

    def test_refuses_to_run_off_main(self):
        self.merge(FIRST)
        git(self.root, "switch", "-q", SECOND)
        before = git(self.root, "rev-parse", "HEAD")
        code, out = self.run_record()
        self.assertEqual(code, 1)
        self.assertIn("main", out)
        self.assertEqual(git(self.root, "rev-parse", "--abbrev-ref", "HEAD"), SECOND)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.root, "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
