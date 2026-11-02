"""Tests for pdlc.py, the command that writes the structured outputs of pdlc.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
SCRIPT = PLUGIN / "skills/init/references/bin/pdlc.py"
TRAILERS = PLUGIN / "skills/init/references/defaults/DES-pdlc-commit-trailers.md"
SUBCOMMANDS = ["commit", "message", "handoff", "stop", "set", "intent", "change"]
# The subcommands that still answer "not implemented".
STUBS = ["handoff", "stop", "set", "intent", "change"]
GIT_ENV = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign",
           "GIT_CONFIG_VALUE_0": "false"}


def run(*args, cwd=None, input=None, stdin=None):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=cwd, input=input, stdin=stdin, env=env)


def git(root, *args):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=str(root),
                          capture_output=True, text=True, check=True, env=env).stdout.strip()


INTENT = """# IN-0001 · Password reset

Status: specifying · Ticket: none · Branch: pdlc/IN-0001-reset · Added: 2026-10-10

## What and why

Let users reset a password.

## Requirements

- none yet

## Changes

- CH-0001 · email templates

## Acceptance checks

Acceptance-File: none
Acceptance-Locked: none
Acceptance-Passed: none

## Notes

- CAP-email.R1: how many tries? → three (assumed)

## Handoff

Handoff · IN-0001 · intake → ready
"""
CHANGE = """# CH-0001 · Email templates

Intent: IN-0001 · Scope: CAP-email · Status: testing · Ticket: none · Branch: pdlc/CH-0001-email · Base: main
Tests-Locked: none

## Requirements

### CAP-email.R1 · Send

- Given a name, when sent, then it is sent.

## Progress log
"""
CONFIG = """# pdlc config

## Adapters

- inbox: inbox-files

## Checks

- all: `pytest`
- acceptance file: `tests/acceptance/{intent}.py` (the acceptance checks)
- ID form in check names: `dotted`
"""


class Project(unittest.TestCase):
    """A temporary git project with one intent and one change. The branch is the change branch."""
    branch = "pdlc/CH-0001-email"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = r = Path(self.tmp.name)
        for path, text in {
            "pdlc/config.md": CONFIG,
            "pdlc/specs/design/DES-pdlc-commit-trailers.md": TRAILERS.read_text(),
            "pdlc/changes/CH-0001-email/change.md": CHANGE,
            "pdlc/inbox/IN-0001-reset.md": INTENT,
        }.items():
            self.write(path, text)
        git(r, "init", "-q", "-b", "main")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Set up pdlc")
        if self.branch != "main":
            git(r, "switch", "-qc", self.branch)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def read(self, path):
        return (self.root / path).read_text()

    def pdlc(self, *args, **kw):
        return run(*args, cwd=str(self.root), **kw)

    def log(self, fmt="%s", n=1):
        return git(self.root, "log", "-%d" % n, "--format=" + fmt)


class EntryPoint(unittest.TestCase):
    def test_each_subcommand_is_registered_and_not_implemented(self):
        for name in STUBS:
            done = run(name)
            self.assertEqual(done.returncode, 2, name)
            self.assertIn("not implemented", done.stdout + done.stderr, name)

    def test_extra_arguments_are_accepted_by_a_stub(self):
        done = run("handoff", "CH-0001", "build", "verify", "--bogus", "x")
        self.assertEqual(done.returncode, 2)
        self.assertIn("not implemented", done.stdout + done.stderr)

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(run().returncode, 2)

    def test_unknown_subcommand_is_a_usage_error(self):
        self.assertEqual(run("nope").returncode, 2)

    def test_help_lists_each_subcommand(self):
        done = run("--help")
        self.assertEqual(done.returncode, 0)
        for name in SUBCOMMANDS:
            self.assertIn(name, done.stdout)


def load_hook():
    import importlib.util
    spec = importlib.util.spec_from_file_location("commits_hook_for_cli", PLUGIN / "hooks/commits.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HARNESS = ["Co-Authored-By: Claude <noreply@anthropic.com>", "Claude-Session: https://x/y"]


def harness_args():
    out = []
    for line in HARNESS:
        out += ["--trailer", line]
    return out


class Commit(Project):
    def make(self, *args, touch="pdlc/changes/CH-0001-email/log.md", extra=True):
        if touch:
            self.counter = getattr(self, "counter", 0) + 1
            self.write(touch, "x%d\n" % self.counter)
        return self.pdlc("commit", *args, *(harness_args() if extra else []))

    def last_trailers(self):
        return git(self.root, "log", "-1", "--format=%(trailers:only,unfold)")

    def test_a_change_commit_has_one_trailer_block(self):
        done = self.make("tests", "CH-0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.log(), "Tests CH-0001")
        self.assertEqual(self.last_trailers().splitlines(),
                         ["Intent: IN-0001", "Change: CH-0001", *HARNESS])
        self.assertEqual(load_hook().problems(str(self.root)), [])

    def test_it_prints_the_hash_and_the_subject(self):
        done = self.make("start", "CH-0001")
        self.assertRegex(done.stdout, r"[0-9a-f]{7,} Start CH-0001")

    def test_each_kind_gives_a_subject_that_the_project_lists(self):
        cases = {
            "specify IN-0001": "Specify IN-0001: Password reset",
            "ready IN-0001": "Ready IN-0001: Password reset",
            "plan IN-0001": "Plan IN-0001: email templates",
            "acceptance IN-0001": "Acceptance IN-0001",
            "lock-acceptance IN-0001": "Lock acceptance IN-0001",
            "review-acceptance IN-0001": "Review acceptance IN-0001",
            "acceptance-reviewed IN-0001": "Acceptance reviewed IN-0001",
            "start CH-0001": "Start CH-0001",
            "tests CH-0001": "Tests CH-0001",
            "lock-tests CH-0001": "Lock tests CH-0001",
            "review-tests CH-0001": "Review tests CH-0001",
            "tests-reviewed CH-0001": "Tests reviewed CH-0001",
            "built CH-0001": "Built CH-0001",
            "visual-review CH-0001": "Visual review CH-0001",
            "verified CH-0001": "Verified CH-0001",
            "propose CH-0001": "Propose CH-0001",
            "verify CH-0001": "Verify CH-0001: round 1",
        }
        for command, subject in cases.items():
            with self.subTest(command=command):
                done = self.make(*command.split())
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(self.log(), subject)
                self.assertEqual(load_hook().problems(str(self.root)), [])

    def test_kinds_with_text(self):
        for command, subject in {
            ("build", "CH-0001", "--text", "add send"): "Build CH-0001: add send",
            ("update", "CH-0001", "--text", "set the base"): "Update CH-0001: set the base",
            ("update", "IN-0001", "--text", "note"): "Update IN-0001: note",
            ("send-back", "CH-0001", "--text", "build"): "Send back CH-0001: build",
            ("stop", "CH-0001", "--text", "a question"): "Stop CH-0001: a question",
        }.items():
            with self.subTest(command=command):
                extra = ["--req", "CAP-email.R1"] if command[0] == "build" else []
                touch = "src/a.py" if command[0] == "build" else "pdlc/changes/CH-0001-email/log.md"
                done = self.make(*command, *extra, touch=touch)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(self.log(), subject)

    def test_text_is_required_for_a_kind_that_needs_it(self):
        for kind in ("build", "update", "send-back", "stop"):
            done = self.make(kind, "CH-0001")
            self.assertEqual(done.returncode, 1, kind)
            self.assertIn("--text", done.stdout)

    def test_verify_counts_the_round(self):
        self.make("verify", "CH-0001")
        self.make("verify", "CH-0001")
        self.assertEqual(self.log(), "Verify CH-0001: round 2")

    def test_visual_review_adds_the_review_trailer(self):
        self.make("visual-review", "CH-0001")
        self.assertEqual(self.last_trailers().splitlines()[2],
                         "Review: pdlc/changes/CH-0001-email/review.gif")

    def test_req_is_required_for_a_file_outside_pdlc(self):
        done = self.make("build", "CH-0001", "--text", "x", touch="src/a.py")
        self.assertEqual(done.returncode, 1)
        self.assertIn("--req", done.stdout)
        self.assertEqual(self.log(), "Set up pdlc")

    def test_req_is_added_in_the_right_order(self):
        done = self.make("build", "CH-0001", "--text", "x", "--req", "CAP-email.R1", "--req",
                         "CAP-email.R2", "--ticket", "PROJ-8", touch="src/a.py")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.last_trailers().splitlines(),
                         ["Intent: IN-0001", "Change: CH-0001", "Req: CAP-email.R1, CAP-email.R2",
                          "Ticket: PROJ-8", *HARNESS])
        self.assertEqual(load_hook().problems(str(self.root)), [])

    def test_req_is_refused_for_a_pdlc_only_commit(self):
        done = self.make("tests", "CH-0001", "--req", "CAP-email.R1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("only pdlc/", done.stdout)

    def test_a_change_on_the_wrong_branch_is_refused(self):
        self.write("pdlc/changes/CH-0002-other/change.md",
                   CHANGE.replace("CH-0001", "CH-0002").replace("pdlc/CH-0001-email", "pdlc/CH-0002-other"))
        done = self.make("tests", "CH-0002")
        self.assertEqual(done.returncode, 1)
        self.assertIn("CH-0001", done.stdout)

    def test_an_unknown_change_is_refused(self):
        done = self.make("tests", "CH-0009")
        self.assertEqual(done.returncode, 1)

    def test_the_ticket_comes_from_the_header_when_it_is_not_given(self):
        text = self.read("pdlc/changes/CH-0001-email/change.md").replace("Ticket: none", "Ticket: PROJ-3")
        self.write("pdlc/changes/CH-0001-email/change.md", text)
        self.make("tests", "CH-0001")
        self.assertIn("Ticket: PROJ-3", self.last_trailers())

    def test_a_commit_on_main_for_an_intent_has_intent_only(self):
        git(self.root, "switch", "-q", "main")
        self.write("pdlc/inbox/IN-0001-reset.md", self.read("pdlc/inbox/IN-0001-reset.md") + "\nmore\n")
        done = self.make("specify", "IN-0001", touch=None)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.last_trailers().splitlines(), ["Intent: IN-0001", *HARNESS])

    def test_setup_has_no_pdlc_trailer(self):
        git(self.root, "switch", "-q", "main")
        done = self.make("setup", touch="notes.txt")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.log(), "Set up pdlc")
        self.assertEqual(self.last_trailers().splitlines(), HARNESS)

    def test_upgrade_and_board_subjects(self):
        git(self.root, "switch", "-q", "main")
        self.make("upgrade", touch="a.txt")
        self.assertEqual(self.log(), "Upgrade pdlc")
        self.make("board", touch="b.txt")
        self.assertEqual(self.log(), "Board: record card keys")

    def test_convention_uses_the_given_intent(self):
        git(self.root, "switch", "-q", "main")
        done = self.make("convention", "DES-style", "--intent", "IN-0001",
                         touch="pdlc/specs/design/DES-style.md")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.log(), "Convention DES-style")
        self.assertEqual(self.last_trailers().splitlines()[0], "Intent: IN-0001")

    def test_plan_runs_the_order_check_first(self):
        self.write("pdlc/changes/CH-0001-email/change.md", CHANGE)
        git(self.root, "switch", "-q", "main")
        # The intent lists CH-0002, which has no change spec: check_order.py fails.
        text = self.read("pdlc/inbox/IN-0001-reset.md").replace(
            "- CH-0001 · email templates", "- CH-0001 · email templates\n- CH-0002 · other")
        self.write("pdlc/inbox/IN-0001-reset.md", text)
        done = self.make("plan", "IN-0001", touch=None)
        self.assertEqual(done.returncode, 1)
        self.assertIn("CH-0002", done.stdout)
        self.assertEqual(self.log(), "Set up pdlc")

    def test_the_config_trailer_is_used_and_not_repeated(self):
        git(self.root, "config", "--add", "pdlc.trailer", HARNESS[0])
        git(self.root, "config", "--add", "pdlc.trailer", "Other-Thing: yes")
        done = self.make("tests", "CH-0001")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.last_trailers().splitlines(),
                         ["Intent: IN-0001", "Change: CH-0001", *HARNESS, "Other-Thing: yes"])

    def test_the_config_trailer_alone_is_enough(self):
        git(self.root, "config", "pdlc.trailer", HARNESS[0])
        done = self.make("tests", "CH-0001", extra=False)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.last_trailers().splitlines(), ["Intent: IN-0001", "Change: CH-0001", HARNESS[0]])

    def test_a_bad_trailer_is_refused(self):
        done = self.pdlc("commit", "tests", "CH-0001", "--trailer", "no colon here")
        self.assertEqual(done.returncode, 1)
        done = self.pdlc("commit", "tests", "CH-0001", "--trailer", "Intent: IN-0009")
        self.assertEqual(done.returncode, 1)

    def test_nothing_to_commit_is_refused(self):
        done = self.make("tests", "CH-0001", touch=None)
        self.assertEqual(done.returncode, 1)
        self.assertIn("nothing", done.stdout)

    def test_paths_limit_what_is_staged(self):
        self.write("pdlc/changes/CH-0001-email/a.md", "a\n")
        self.write("pdlc/changes/CH-0001-email/b.md", "b\n")
        done = self.pdlc("commit", "tests", "CH-0001", "--paths", "pdlc/changes/CH-0001-email/a.md")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(git(self.root, "show", "--name-only", "--format=", "HEAD"),
                         "pdlc/changes/CH-0001-email/a.md")
        self.assertIn("b.md", done.stdout)  # the status shows the stray file

    def test_a_stray_file_shows_in_the_status_after_the_commit(self):
        self.write("pdlc/changes/CH-0001-email/c.md", "c\n")
        git(self.root, "add", "-A")
        self.write("pdlc/changes/CH-0001-email/c.md", "c2\n")
        self.write("pdlc/changes/CH-0001-email/log.md", "l\n")
        done = self.pdlc("commit", "tests", "CH-0001", "--paths", "pdlc/changes/CH-0001-email/log.md")
        # c.md was staged before, so it is in the commit; its second edit stays in the tree.
        self.assertIn("c.md", done.stdout)

    def test_amend_keeps_the_files_and_fixes_the_message(self):
        self.make("tests", "CH-0001")
        files = git(self.root, "show", "--name-only", "--format=", "HEAD")
        before = self.log("%H", 1)
        done = self.pdlc("commit", "lock-tests", "CH-0001", "--amend", *harness_args())
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.log(), "Lock tests CH-0001")
        self.assertEqual(git(self.root, "show", "--name-only", "--format=", "HEAD"), files)
        self.assertNotEqual(self.log("%H", 1), before)
        self.assertEqual(git(self.root, "rev-list", "--count", "HEAD"), "2")

    def test_the_message_command_prints_only_the_message(self):
        done = self.pdlc("message", "tests", "CH-0001", *harness_args())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(),
                         ["Tests CH-0001", "", "Intent: IN-0001", "Change: CH-0001", *HARNESS])
        self.assertEqual(self.log(), "Set up pdlc")

    def test_the_subject_must_be_in_the_project_list(self):
        text = self.read("pdlc/specs/design/DES-pdlc-commit-trailers.md").replace("- `Tests <change>`", "- `Checks <change>`")
        self.write("pdlc/specs/design/DES-pdlc-commit-trailers.md", text)
        done = self.make("tests", "CH-0001")
        self.assertEqual(done.returncode, 1)
        self.assertIn("Tests CH-0001", done.stdout)

    def test_not_a_pdlc_project_exits_4(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run("commit", "tests", "CH-0001", cwd=empty).returncode, 4)

    def test_an_unknown_kind_is_a_usage_error(self):
        self.assertEqual(self.pdlc("commit", "nope").returncode, 2)

    def test_a_git_failure_exits_3(self):
        git(self.root, "switch", "-q", "main")
        self.write("pdlc/inbox/IN-0001-reset.md", self.read("pdlc/inbox/IN-0001-reset.md") + "x\n")
        hooks = self.root / ".git/hooks"
        hooks.mkdir(exist_ok=True)
        (hooks / "pre-commit").write_text("#!/bin/sh\nexit 1\n")
        (hooks / "pre-commit").chmod(0o755)
        done = self.pdlc("commit", "specify", "IN-0001")
        self.assertEqual(done.returncode, 3)


class Imports(unittest.TestCase):
    def test_no_bytecode_left_in_the_bin_folder(self):
        shutil.rmtree(SCRIPT.parent / "__pycache__", ignore_errors=True)
        run("handoff")
        self.assertFalse((SCRIPT.parent / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
