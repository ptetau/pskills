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
SUBCOMMANDS = ["commit", "message", "handoff", "stop", "set", "intent", "change", "start"]
# The subcommands that still answer "not implemented".
STUBS = []
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
    def test_a_stub_answers_not_implemented(self):
        for name in STUBS:
            done = run(name)
            self.assertEqual(done.returncode, 2, name)
            self.assertIn("not implemented", done.stdout + done.stderr, name)

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(run().returncode, 2)

    def test_unknown_subcommand_is_a_usage_error(self):
        self.assertEqual(run("nope").returncode, 2)

    def test_help_lists_each_subcommand(self):
        done = run("--help")
        self.assertEqual(done.returncode, 0)
        for name in SUBCOMMANDS:
            self.assertIn(name, done.stdout)


def _pdlclib():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pdlclib_for_cli", SCRIPT.parent / "pdlclib.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pdlclib_field(text, name):
    return _pdlclib().field(text, name)


def pdlclib_section(text, title):
    return _pdlclib().section(text, title)


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
            "propose CH-0001": "Propose CH-0001",
            "verify CH-0001": "Verify CH-0001: round 1",
            "verified CH-0001": "Verified CH-0001",
        }
        for command, subject in cases.items():
            with self.subTest(command=command):
                done = self.make(*command.split())
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(self.log(), subject)
                self.assertEqual(load_hook().problems(str(self.root)), [])

    def test_kinds_with_text(self):
        self.make("verify", "CH-0001")
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
        self.make("verify", "CH-0001")
        for kind in ("build", "update", "send-back", "stop"):
            done = self.make(kind, "CH-0001")
            self.assertEqual(done.returncode, 1, kind)
            self.assertIn("--text", done.stdout)

    def test_verify_counts_the_round(self):
        self.make("verify", "CH-0001")
        self.make("verify", "CH-0001")
        self.assertEqual(self.log(), "Verify CH-0001: round 2")

    def refused(self, *args):
        before = git(self.root, "rev-parse", "HEAD")
        done = self.make(*args, touch=None)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("commit the round first: python3 pdlc/bin/pdlc.py commit verify CH-0001",
                      done.stdout + done.stderr)
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.root, "diff", "--cached", "--name-only"), "")

    def test_verified_and_send_back_need_a_round_after_the_last_built(self):
        self.make("built", "CH-0001")
        self.refused("verified", "CH-0001")
        self.refused("send-back", "CH-0001", "--text", "build")
        self.make("verify", "CH-0001")
        self.assertEqual(self.make("verified", "CH-0001").returncode, 0)

    def test_a_refusal_stages_nothing(self):
        self.make("built", "CH-0001")
        self.write("pdlc/changes/CH-0001-email/log.md", "unstaged\n")
        done = self.pdlc("commit", "verified", "CH-0001", *harness_args())
        self.assertEqual(done.returncode, 1)
        self.assertEqual(git(self.root, "diff", "--cached", "--name-only"), "")

    def test_a_round_before_a_new_built_does_not_count(self):
        self.make("verify", "CH-0001")
        self.make("built", "CH-0001")
        self.refused("verified", "CH-0001")
        self.make("verify", "CH-0001")
        self.assertEqual(self.log(), "Verify CH-0001: round 2")
        self.assertEqual(self.make("send-back", "CH-0001", "--text", "build").returncode, 0)

    def test_a_send_back_ends_its_round(self):
        self.make("verify", "CH-0001")
        self.make("send-back", "CH-0001", "--text", "build")
        self.refused("verified", "CH-0001")

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

    def test_the_merge_message_names_the_base_and_has_intent_and_change(self):
        done = self.pdlc("message", "merge", "CH-0001", "--base", "main", *harness_args())
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.splitlines(),
                         ["Merge main into CH-0001", "", "Intent: IN-0001", "Change: CH-0001", *HARNESS])

    def test_the_merge_message_works_for_git_merge(self):
        git(self.root, "switch", "-q", "main")
        self.write("base.txt", "base\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Base")
        git(self.root, "switch", "-q", self.branch)
        self.write("mine.txt", "mine\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Mine")
        message = self.pdlc("message", "merge", "CH-0001", "--base", "main").stdout
        (Path(self.tmp.name) / "msg.txt").write_text(message)
        git(self.root, "merge", "--no-ff", "-q", "-F", str(Path(self.tmp.name) / "msg.txt"), "main")
        self.assertEqual(self.log("%s"), "Merge main into CH-0001")
        self.assertIn("Change: CH-0001", self.log("%B"))

    def test_merge_needs_a_base(self):
        self.assertEqual(self.pdlc("message", "merge", "CH-0001").returncode, 1)

    def test_base_is_only_for_merge(self):
        self.assertEqual(self.pdlc("message", "tests", "CH-0001", "--base", "main").returncode, 2)

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


SPEC_MARK = """# JOB-x · Do a thing

Status: active

## Requirements

### JOB-x.R1 · One

Status: proposed · Intents: IN-0001

Show at most 20 items{mark}.
"""


class Handoff(Project):
    def hand(self, id_, stage, next_, data, extra=()):
        return self.pdlc("handoff", id_, stage, next_, "--json", "-", *extra, input=json.dumps(data))

    def handoff_text(self):
        return self.read("pdlc/changes/CH-0001-email/handoff.md")

    def check(self, id_, stage):
        done = subprocess.run([sys.executable, str(SCRIPT.parent / "check_handoff.py"), id_, "--stage", stage],
                              cwd=str(self.root), capture_output=True, text=True)
        return done.stdout

    def commit_all(self, subject="Update CH-0001: x"):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", subject)

    def test_a_change_handoff_has_the_title_time_and_six_sections(self):
        done = self.hand("CH-0001", "build", "verify", {"passed": 4, "total": 5, "next": "Verify it.",
                                                         "done": ["Built CAP-email.R1 (send)."]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.handoff_text()
        lines = text.splitlines()
        self.assertEqual(lines[0], "# Handoff · CH-0001 · build → verify")
        self.assertRegex(lines[1], r"^Time: \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        heads = [l for l in lines if l.startswith("## ")]
        self.assertEqual(heads, ["## Done", "## Decided on defaults", "## Open", "## Look here",
                                 "## Don't redo", "## Next: do this first"])
        self.assertIn("- 4 of 5 checks pass.", text)
        self.assertIn("- Built CAP-email.R1 (send).", text)
        self.assertIn("Run `/pdlc:verify`. Verify it.", text)
        self.assertEqual(self.check("CH-0001", "build"), "")
        self.assertIn("handoff.md", done.stdout)

    def test_each_empty_list_gives_none(self):
        self.hand("CH-0001", "build", "verify", {"passed": 1, "total": 1, "next": "Go."})
        text = self.handoff_text()
        self.assertIn("## Decided on defaults\n\n- none", text)
        self.assertIn("## Open\n\n- none", text)
        self.assertIn("## Look here\n\n- none", text)
        self.assertIn("## Don't redo\n\n- none", text)

    def test_a_missing_required_key_exits_1_and_writes_nothing(self):
        for stage, next_, keys in [
            ("acceptance", "tests", {"failing": 1, "total": 2, "lock": "abc"}),
            ("tests", "build", {"lock": "abc"}),
            ("build", "verify", {"passed": 1}),
            ("show", "user", {"link": "x", "frames": 3, "shown": 2}),
        ]:
            with self.subTest(stage=stage):
                done = self.hand("CH-0001", stage, next_, dict(keys, next="Go."))
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                self.assertFalse((self.root / "pdlc/changes/CH-0001-email/handoff.md").exists())

    def test_acceptance_to_tests_writes_its_keys(self):
        done = self.hand("IN-0001", "acceptance", "tests", {
            "failing": 3, "total": 3, "lock": "abc1234", "next": "Write the checks.",
            "gives": [{"change": "CH-0001", "needs": "the send function"}]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/inbox/IN-0001-reset.md")
        self.assertIn("3 of 3 acceptance checks fail", text)
        self.assertIn("abc1234", text)
        self.assertIn("CH-0001", text.split("## Handoff")[1])
        self.assertEqual(self.check("IN-0001", "acceptance"), "")

    def test_tests_to_build_lists_the_checks(self):
        done = self.hand("CH-0001", "tests", "build", {
            "lock": "abc1234", "next": "Build.",
            "checks": [{"check": "tests/test_send.py::test_CAP_email_R1", "req": "CAP-email.R1"}]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.handoff_text()
        self.assertIn("- tests/test_send.py::test_CAP_email_R1 (proves CAP-email.R1)", text)
        self.assertIn("abc1234", text)

    def test_verify_to_show_reads_the_results(self):
        self.write("pdlc/changes/CH-0001-email/review/security/result.md", "Result: pass\n\nRemit: security\n")
        self.write("pdlc/changes/CH-0001-email/review/quality/result.md", "Result: fail\n\nRemit: quality\n")
        self.write("pdlc/inbox/IN-0001-reset.md",
                   self.read("pdlc/inbox/IN-0001-reset.md").replace("Acceptance-Passed: none", "Acceptance-Passed: abc1234"))
        done = self.hand("CH-0001", "verify", "show", {"next": "Show."})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.handoff_text()
        self.assertIn("- security: pass", text)
        self.assertIn("- quality: fail", text)
        self.assertIn("abc1234", text)

    def test_verify_to_show_needs_the_results(self):
        done = self.hand("CH-0001", "verify", "show", {"next": "Show."})
        self.assertEqual(done.returncode, 1)

    def test_show_to_user(self):
        done = self.hand("CH-0001", "show", "user", {"link": "https://x/pr/1", "frames": 6, "shown": 3,
                                                      "total": 3, "next": "Merge it."})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("https://x/pr/1", self.handoff_text())

    def test_to_user_needs_the_open_triple(self):
        done = self.hand("CH-0001", "build", "user", {"next": "Answer.", "open": ["just a note"]})
        self.assertEqual(done.returncode, 1)
        done = self.hand("CH-0001", "build", "user", {"next": "Answer.", "open": {"reason": "r", "decide": "d"}})
        self.assertEqual(done.returncode, 1)
        done = self.hand("CH-0001", "build", "user", {"next": "Answer.", "open": {
            "reason": "The check fails.", "decide": "Change the limit?", "recommend": "Yes, to 30."}})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.handoff_text()
        self.assertIn("- Reason: The check fails.", text)
        self.assertIn("- Decision: Change the limit?", text)
        self.assertIn("- Recommended answer: Yes, to 30.", text)
        self.assertEqual(self.check("CH-0001", "build"), "")

    def test_a_build_can_send_a_wrong_check_back(self):
        for target in ("tests", "acceptance"):
            done = self.hand("CH-0001", "build", target, {"next": "A check is wrong: fix it."})
            self.assertEqual(done.returncode, 0, target + done.stdout + done.stderr)
            self.assertEqual(self.check("CH-0001", "build"), "")

    def test_a_pair_the_stage_does_not_permit_exits_1(self):
        done = self.hand("CH-0001", "build", "show", {"next": "x"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("build", done.stdout)
        self.assertFalse((self.root / "pdlc/changes/CH-0001-email/handoff.md").exists())

    def test_an_intent_handoff_replaces_the_handoff_section_only(self):
        before = self.read("pdlc/inbox/IN-0001-reset.md")
        done = self.hand("IN-0001", "intake", "ready", {"next": "Check it.", "done": ["Wrote the specs."]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/inbox/IN-0001-reset.md")
        self.assertEqual(text.split("## Handoff")[0], before.split("## Handoff")[0])
        body = text.split("## Handoff")[1]
        self.assertIn("Handoff · IN-0001 · intake → ready\nTime: ", body)
        self.assertIn("### Done", body)
        self.assertNotIn("# Handoff", body)
        self.assertEqual(self.check("IN-0001", "intake"), "")

    def test_a_decided_item_is_in_the_handoff_and_once_in_the_notes(self):
        self.write("pdlc/specs/jobs/JOB-x.md", SPEC_MARK.format(mark=" (assumed)"))
        data = {"next": "Check it.", "decided": [
            {"id": "JOB-x.R1", "question": "How many items?", "answer": "At most 20"}]}
        for _ in range(2):
            done = self.hand("IN-0001", "intake", "ready", data)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/inbox/IN-0001-reset.md")
        line = "- JOB-x.R1: How many items? → At most 20 (assumed)"
        self.assertEqual(text.count(line), 2)  # one in the handoff and one in the notes
        self.assertIn(line, text.split("## Notes")[1].split("## Handoff")[0])
        self.assertEqual(self.check("IN-0001", "intake"), "")

    def test_a_new_mark_with_no_decided_item_exits_1_and_restores_the_files(self):
        self.write("pdlc/specs/jobs/JOB-x.md", SPEC_MARK.format(mark=" (assumed)"))
        before = self.read("pdlc/inbox/IN-0001-reset.md")
        done = self.hand("IN-0001", "intake", "ready", {"next": "Check it."})
        self.assertEqual(done.returncode, 1)
        self.assertIn("JOB-x.R1", done.stdout)
        self.assertEqual(self.read("pdlc/inbox/IN-0001-reset.md"), before)

    def test_ready_keeps_the_decided_lines_of_the_earlier_handoff(self):
        self.write("pdlc/specs/jobs/JOB-x.md", SPEC_MARK.format(mark=" (assumed)"))
        self.hand("IN-0001", "intake", "ready", {"next": "Check it.", "decided": [
            {"id": "JOB-x.R1", "question": "How many items?", "answer": "At most 20"}]})
        self.commit_all("Specify IN-0001: Password reset")
        done = self.hand("IN-0001", "ready", "change", {"next": "Plan."})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        body = self.read("pdlc/inbox/IN-0001-reset.md").split("## Handoff")[1]
        self.assertIn("- JOB-x.R1: How many items? → At most 20 (assumed)", body)
        self.assertNotIn("### Decided on defaults\n\n- none", body)
        self.assertEqual(self.check("IN-0001", "ready"), "")

    def test_the_change_decided_line_goes_to_the_intent_notes(self):
        self.write("pdlc/specs/jobs/JOB-x.md", SPEC_MARK.format(mark=" (assumed)"))
        done = self.hand("CH-0001", "build", "verify", {"passed": 1, "total": 1, "next": "Go.", "decided": [
            {"id": "JOB-x.R1", "question": "How many items?", "answer": "At most 20"}]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("- JOB-x.R1: How many items? → At most 20 (assumed)",
                      self.read("pdlc/inbox/IN-0001-reset.md").split("## Notes")[1])

    def test_a_json_object_with_a_wrong_type_exits_1(self):
        done = self.hand("CH-0001", "build", "verify", {"passed": 1, "total": 1, "next": "Go.", "done": "text"})
        self.assertEqual(done.returncode, 1)

    def test_next_is_required(self):
        done = self.hand("CH-0001", "build", "verify", {"passed": 1, "total": 1})
        self.assertEqual(done.returncode, 1)

    def test_an_unknown_id_exits_1(self):
        done = self.hand("CH-0009", "build", "verify", {"passed": 1, "total": 1, "next": "Go."})
        self.assertEqual(done.returncode, 1)
        done = self.hand("IN-0009", "intake", "ready", {"next": "Go."})
        self.assertEqual(done.returncode, 1)

    def test_json_from_a_file(self):
        path = self.root / "h.json"
        path.write_text(json.dumps({"passed": 1, "total": 1, "next": "Go."}))
        done = self.pdlc("handoff", "CH-0001", "build", "verify", "--json", str(path))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_json_from_a_terminal_exits_2_at_once(self):
        import pty
        master, slave = pty.openpty()
        try:
            done = run("handoff", "CH-0001", "build", "verify", "--json", "-", cwd=str(self.root), stdin=slave)
        finally:
            os.close(master)
            os.close(slave)
        self.assertEqual(done.returncode, 2)

    def test_invalid_json_exits_2_with_its_line(self):
        done = self.pdlc("handoff", "CH-0001", "build", "verify", "--json", "-", input='{"a": 1,\n "b": }')
        self.assertEqual(done.returncode, 2)
        self.assertIn("line 2", done.stderr)

    def test_the_stage_must_be_known(self):
        done = self.pdlc("handoff", "CH-0001", "nope", "verify", "--json", "-", input="{}")
        self.assertEqual(done.returncode, 2)


OPEN = {"reason": "The limit conflicts with R2.", "decide": "Which limit holds?",
        "recommend": "Use 20, as R2 says."}


class Stop(Project):
    def stop(self, id_="CH-0001", stage="build", data=None, extra=()):
        data = {"open": OPEN} if data is None else data
        return self.pdlc("stop", id_, "--stage", stage, "--json", "-", *extra, *harness_args(),
                         input=json.dumps(data))

    def test_it_writes_the_handoff_and_the_stop_commit(self):
        done = self.stop()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.log(), "Stop CH-0001: The limit conflicts with R2.")
        self.assertTrue(self.log().startswith("Stop "))
        text = git(self.root, "show", "HEAD:pdlc/changes/CH-0001-email/handoff.md")
        self.assertIn("# Handoff · CH-0001 · build → user", text)
        self.assertIn("- Reason: The limit conflicts with R2.", text)
        self.assertIn("- Decision: Which limit holds?", text)
        self.assertIn("- Recommended answer: Use 20, as R2 says.", text)
        self.assertEqual(git(self.root, "log", "-1", "--format=%(trailers:only,unfold)").splitlines(),
                         ["Intent: IN-0001", "Change: CH-0001", *HARNESS])
        self.assertEqual(load_hook().problems(str(self.root)), [])
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_it_prints_the_open_text_for_the_reply(self):
        done = self.stop()
        self.assertIn("- Reason: The limit conflicts with R2.", done.stdout)
        self.assertIn("- Recommended answer: Use 20, as R2 says.", done.stdout)

    def test_an_intent_stop(self):
        git(self.root, "switch", "-q", "main")
        done = self.stop("IN-0001", "ready")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.log(), "Stop IN-0001: The limit conflicts with R2.")
        self.assertIn("ready → user", git(self.root, "show", "HEAD:pdlc/inbox/IN-0001-reset.md"))

    def test_the_open_triple_is_required_and_nothing_is_written(self):
        done = self.stop(data={"open": {"reason": "r"}})
        self.assertEqual(done.returncode, 1)
        done = self.stop(data={})
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.log(), "Set up pdlc")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")

    def test_a_commit_problem_leaves_no_handoff(self):
        done = self.stop(extra=["--trailer", "bad trailer"])
        self.assertEqual(done.returncode, 1)
        self.assertFalse((self.root / "pdlc/changes/CH-0001-email/handoff.md").exists())
        done = self.stop(extra=["--trailer", "Note: ok"])
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_dirty_spec_file_is_refused_and_nothing_is_committed(self):
        self.write("pdlc/specs/capabilities/CAP-email.md", CAP_EMAIL)
        done = self.stop()
        self.assertEqual(done.returncode, 1)
        self.assertIn("commit the stage first: python3 pdlc/bin/pdlc.py commit <stage> <id>", done.stdout + done.stderr)
        self.assertIn("pdlc/specs/capabilities/CAP-email.md", done.stdout + done.stderr)
        self.assertEqual(self.log(), "Set up pdlc")
        self.assertFalse((self.root / "pdlc/changes/CH-0001-email/handoff.md").exists())
        self.assertEqual(git(self.root, "status", "--porcelain"), "?? pdlc/specs/capabilities/")

    def test_a_dirty_app_file_is_refused(self):
        self.write("src/a.py", "x\n")
        done = self.stop()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.log(), "Set up pdlc")

    def test_a_dirty_handoff_and_intent_are_not_refused(self):
        self.hand_first()
        done = self.stop()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.log(), "Stop CH-0001: The limit conflicts with R2.")

    def hand_first(self):
        data = {"passed": 1, "total": 1, "next": "Go."}
        self.pdlc("handoff", "CH-0001", "build", "verify", "--json", "-", input=json.dumps(data))

    def test_a_next_text_is_optional(self):
        done = self.stop(data={"open": OPEN, "next": "Answer, then run /pdlc:ship."})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Answer, then run /pdlc:ship.", git(self.root, "show", "HEAD:pdlc/changes/CH-0001-email/handoff.md"))


CAP_EMAIL = """# CAP-email · Send email

Status: active

## Interface

- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js` · proposed
  - in: the name of a template, and an email address
  - out: the ID of the sent email
  - errors: none
- `other()` · function · `src/other.js` · proposed
  - in: nothing
  - errors: none

### Test seams

- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js` · proposed
  - in: a folder
  - errors: none

## Requirements

### CAP-email.R1 · Send

Status: ready · Intents: IN-0001

- Given a name, when sent, then it is sent.

### CAP-email.R2 · Other

Status: ready · Intents: IN-0001

- Given nothing, when called, then it returns.
"""
CHANGE_WITH_INTERFACE = CHANGE.replace("## Progress log", """## Interface

- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`
  - in: the name of a template, and an email address
  - out: the ID of the sent email
  - errors: none

### Test seams

- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`
  - in: a folder
  - errors: none

## Progress log""")


class StartTests(Project):
    """`pdlc.py start` works out Branch and Base from "Stacked changes", and makes the branch."""
    branch = "pdlc/IN-0001-reset"

    def setUp(self):
        super().setUp()
        planned = CHANGE.replace("Status: testing", "Status: planned").replace(
            "Branch: pdlc/CH-0001-email · Base: main", "Branch: none · Base: main")
        self.write("pdlc/changes/CH-0001-email/change.md", planned)
        self.write("pdlc/changes/CH-0002-sms/change.md",
                   planned.replace("CH-0001", "CH-0002").replace("Email templates", "Sms"))
        self.write("pdlc/inbox/IN-0001-reset.md", INTENT.replace(
            "- CH-0001 \u00b7 email templates", "- CH-0001 \u00b7 email templates\n- CH-0002 \u00b7 sms"))
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Plan IN-0001: email templates, sms")

    def fields(self, folder):
        return self.read("pdlc/changes/%s/change.md" % folder)

    def test_the_first_change_starts_from_the_intent_branch(self):
        intent_tip = git(self.root, "rev-parse", "HEAD")
        done = self.pdlc("start", "CH-0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(git(self.root, "branch", "--show-current"), "pdlc/CH-0001-email")
        text = self.fields("CH-0001-email")
        self.assertIn("Status: testing", text)
        self.assertIn("Branch: pdlc/CH-0001-email \u00b7 Base: pdlc/IN-0001-reset", text)
        self.assertEqual(self.log(), "Start CH-0001")
        self.assertEqual(git(self.root, "rev-parse", "HEAD~1"), intent_tip)

    def test_the_second_change_starts_from_the_first_change_branch(self):
        self.assertEqual(self.pdlc("start", "CH-0001").returncode, 0)
        git(self.root, "switch", "-q", "pdlc/IN-0001-reset")
        first_tip = git(self.root, "rev-parse", "pdlc/CH-0001-email")
        done = self.pdlc("start", "CH-0002")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(git(self.root, "branch", "--show-current"), "pdlc/CH-0002-sms")
        self.assertIn("Branch: pdlc/CH-0002-sms \u00b7 Base: pdlc/CH-0001-email", self.fields("CH-0002-sms"))
        self.assertEqual(git(self.root, "rev-parse", "HEAD~1"), first_tip)

    def test_a_second_change_after_a_merged_first_starts_from_main(self):
        self.assertEqual(self.pdlc("start", "CH-0001").returncode, 0)
        git(self.root, "switch", "-q", "main")
        git(self.root, "merge", "-q", "--no-edit", "pdlc/CH-0001-email")
        git(self.root, "switch", "-q", "pdlc/IN-0001-reset")
        done = self.pdlc("start", "CH-0002")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Base: main", self.fields("CH-0002-sms"))

    def test_the_first_change_with_no_intent_branch_starts_from_main(self):
        git(self.root, "switch", "-q", "main")
        git(self.root, "merge", "-q", "--ff-only", "pdlc/IN-0001-reset")
        text = self.read("pdlc/inbox/IN-0001-reset.md").replace("Branch: pdlc/IN-0001-reset", "Branch: none")
        self.write("pdlc/inbox/IN-0001-reset.md", text)
        git(self.root, "commit", "-qam", "Update IN-0001: no branch")
        done = self.pdlc("start", "CH-0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Base: main", self.fields("CH-0001-email"))

    def test_an_existing_branch_keeps_its_base_and_makes_no_commit(self):
        self.assertEqual(self.pdlc("start", "CH-0001").returncode, 0)
        git(self.root, "switch", "-q", "main")
        before = git(self.root, "rev-parse", "pdlc/CH-0001-email")
        done = self.pdlc("start", "CH-0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(git(self.root, "branch", "--show-current"), "pdlc/CH-0001-email")
        self.assertEqual(git(self.root, "rev-parse", "HEAD"), before)
        self.assertIn("Base: pdlc/IN-0001-reset", self.fields("CH-0001-email"))

    def test_a_change_before_its_predecessor_has_started_is_refused(self):
        done = self.pdlc("start", "CH-0002")
        self.assertEqual(done.returncode, 1)
        self.assertIn("CH-0001", done.stdout)
        self.assertEqual(git(self.root, "branch", "--show-current"), "pdlc/IN-0001-reset")


class SetTests(Project):
    def setUp(self):
        super().setUp()
        self.write("pdlc/specs/capabilities/CAP-email.md", CAP_EMAIL)
        self.write("pdlc/changes/CH-0001-email/change.md", CHANGE_WITH_INTERFACE)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Update CH-0001: fixtures")

    def set(self, *args):
        return self.pdlc("set", *args)

    def head(self):
        return git(self.root, "rev-parse", "HEAD")

    def test_it_sets_the_status_and_leaves_the_rest(self):
        before = self.read("pdlc/changes/CH-0001-email/change.md")
        done = self.set("CH-0001", "--status", "building")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = self.read("pdlc/changes/CH-0001-email/change.md")
        self.assertEqual(after, before.replace("Status: testing", "Status: building"))
        self.assertIn("Status", done.stdout)

    def test_a_wrong_status_exits_1_and_nothing_is_written(self):
        before = self.read("pdlc/changes/CH-0001-email/change.md")
        done = self.set("CH-0001", "--status", "merged-ish", "--branch", "pdlc/CH-0001-other")
        self.assertEqual(done.returncode, 1)
        self.assertIn("planned", done.stdout)
        self.assertEqual(self.read("pdlc/changes/CH-0001-email/change.md"), before)

    def test_an_intent_status_is_not_a_change_status(self):
        self.assertEqual(self.set("CH-0001", "--status", "ready").returncode, 1)
        self.assertEqual(self.set("IN-0001", "--status", "planned").returncode, 1)
        self.assertEqual(self.set("IN-0001", "--status", "ready").returncode, 0)
        self.assertIn("Status: ready ·", self.read("pdlc/inbox/IN-0001-reset.md"))

    def test_the_readme_statuses_govern(self):
        self.write("pdlc/README.md", "# pdlc\n\n## Statuses\n\n- Intent: new → hatching → done. Also paused.\n"
                   "- Change: planned → testing. Also cancelled.\n- Requirement: proposed → ready.\n")
        self.assertEqual(self.set("IN-0001", "--status", "hatching").returncode, 0)
        self.assertEqual(self.set("IN-0001", "--status", "specifying").returncode, 1)

    def test_branch_base_and_ticket(self):
        done = self.set("CH-0001", "--branch", "pdlc/CH-0001-x", "--base", "pdlc/IN-0001-reset", "--ticket", "PROJ-9")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/changes/CH-0001-email/change.md")
        self.assertIn("Ticket: PROJ-9 · Branch: pdlc/CH-0001-x · Base: pdlc/IN-0001-reset", text)

    def test_a_revision_becomes_a_full_hash(self):
        self.assertEqual(self.set("CH-0001", "--tests-locked", "HEAD").returncode, 0)
        self.assertIn("Tests-Locked: %s\n" % self.head(), self.read("pdlc/changes/CH-0001-email/change.md"))

    def test_the_word_acceptance_stays_a_word(self):
        self.assertEqual(self.set("CH-0001", "--tests-locked", "acceptance").returncode, 0)
        self.assertIn("Tests-Locked: acceptance\n", self.read("pdlc/changes/CH-0001-email/change.md"))

    def test_an_unknown_revision_exits_3(self):
        self.assertEqual(self.set("CH-0001", "--tests-locked", "nonesuch123").returncode, 3)

    def test_acceptance_fields_of_an_intent(self):
        done = self.set("IN-0001", "--acceptance-locked", "HEAD", "--acceptance-passed", "HEAD",
                        "--acceptance-file", "auto")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/inbox/IN-0001-reset.md")
        self.assertIn("Acceptance-File: tests/acceptance/IN-0001.py\n", text)
        self.assertIn("Acceptance-Locked: %s\n" % self.head(), text)
        self.assertIn("Acceptance-Passed: %s\n" % self.head(), text)

    def test_the_auto_file_uses_the_id_form_of_the_project(self):
        self.write("pdlc/config.md", CONFIG.replace("`dotted`", "`underscored`"))
        self.set("IN-0001", "--acceptance-file", "auto")
        self.assertIn("Acceptance-File: tests/acceptance/IN_0001.py\n", self.read("pdlc/inbox/IN-0001-reset.md"))

    def test_a_path_is_written_as_it_is(self):
        self.set("IN-0001", "--acceptance-file", "tests/a.py")
        self.assertIn("Acceptance-File: tests/a.py\n", self.read("pdlc/inbox/IN-0001-reset.md"))

    def test_a_field_the_file_does_not_have_exits_1(self):
        self.assertEqual(self.set("IN-0001", "--tests-locked", "HEAD").returncode, 1)
        self.assertEqual(self.set("CH-0001", "--acceptance-locked", "HEAD").returncode, 1)

    def test_reqs_sets_each_requirement_of_the_change_only(self):
        done = self.set("CH-0001", "--reqs", "built")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        spec = self.read("pdlc/specs/capabilities/CAP-email.md")
        self.assertIn("### CAP-email.R1 · Send\n\nStatus: built · Intents: IN-0001", spec)
        self.assertIn("### CAP-email.R2 · Other\n\nStatus: ready · Intents: IN-0001", spec)

    def with_steps(self):
        text = self.read("pdlc/changes/CH-0001-email/change.md")
        steps = ("## Steps\n\n### Step 1 \u00b7 Send \u00b7 [ ]\n\n- Requirement: CAP-email.R1\n"
                 "- Done when: the check passes\n\n### Step 2 \u00b7 README \u00b7 [ ]\n\n"
                 "- Requirement: none\n\n## Progress log\n\n- 2026-01-01 \u00b7 planned\n")
        self.write("pdlc/changes/CH-0001-email/change.md", text.replace("## Progress log\n", steps))
        return "pdlc/changes/CH-0001-email/change.md"

    def test_reqs_built_ticks_the_steps_and_logs_progress(self):
        path = self.with_steps()
        done = self.set("CH-0001", "--reqs", "built")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read(path)
        self.assertNotIn("[ ]", text)
        self.assertEqual(text.count("\u00b7 [x]"), 2)
        log = text.split("## Progress log")[1].strip().splitlines()
        self.assertEqual(log[0], "- 2026-01-01 \u00b7 planned")
        self.assertEqual(len(log), 2)
        self.assertRegex(log[1], r"^- \d{4}-\d{2}-\d{2} \u00b7 built: all checks pass$")

    def test_reqs_built_twice_changes_nothing_more(self):
        path = self.with_steps()
        self.set("CH-0001", "--reqs", "built")
        once = self.read(path)
        self.assertEqual(self.set("CH-0001", "--reqs", "built").returncode, 0)
        self.assertEqual(self.read(path), once)

    def test_reqs_built_ticks_bullet_steps_too(self):
        path = self.with_steps()
        self.write(path, self.read(path).replace("- Requirement: none\n", "- Requirement: none\n- [ ] extra\n"))
        self.set("CH-0001", "--reqs", "built")
        self.assertNotIn("[ ]", self.read(path))

    def test_other_statuses_leave_steps_and_log_alone(self):
        path = self.with_steps()
        before = self.read(path)
        self.set("CH-0001", "--reqs", "verified")
        self.assertEqual(self.read(path), before)

    def test_reqs_skips_a_requirement_that_the_change_retires(self):
        path = "pdlc/changes/CH-0001-email/change.md"
        self.write(path, self.read(path).replace(
            "## Progress log", "### CAP-email.R2 \u00b7 Other (retire)\n\n- Given nothing, then it goes.\n\n## Progress log", 1))
        spec_path = "pdlc/specs/capabilities/CAP-email.md"
        self.write(spec_path, self.read(spec_path).replace("### CAP-email.R2 · Other\n\nStatus: ready · Intents: IN-0001\n", ""))
        done = self.set("CH-0001", "--reqs", "verified")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_one_requirement(self):
        self.set("CH-0001", "--req", "CAP-email.R2=verified")
        self.assertIn("Status: verified · Intents", self.read("pdlc/specs/capabilities/CAP-email.md").split("R2")[1])

    def test_a_wrong_requirement_status_exits_1(self):
        self.assertEqual(self.set("CH-0001", "--reqs", "finished").returncode, 1)
        self.assertEqual(self.set("CH-0001", "--req", "CAP-email.R9=built").returncode, 1)

    def test_unpropose_removes_only_the_marks_of_this_change(self):
        done = self.set("CH-0001", "--unpropose")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        spec = self.read("pdlc/specs/capabilities/CAP-email.md")
        self.assertIn("`send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`\n", spec)
        self.assertIn("`EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`\n", spec)
        self.assertIn("`other()` · function · `src/other.js` · proposed", spec)
        self.assertEqual(spec.count("proposed"), 1)  # only the mark of other() stays
        self.assertNotIn("send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js` · proposed", spec)

    def test_several_options_in_one_call(self):
        done = self.set("CH-0001", "--status", "in review", "--reqs", "verified", "--unpropose")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Status: in review ·", self.read("pdlc/changes/CH-0001-email/change.md"))

    def test_it_makes_no_commit(self):
        self.set("CH-0001", "--status", "building")
        self.assertEqual(self.log(), "Update CH-0001: fixtures")

    def test_an_unknown_id_exits_1(self):
        self.assertEqual(self.set("CH-0009", "--status", "building").returncode, 1)

    def test_an_id_with_no_option_is_a_usage_error(self):
        self.assertEqual(self.set("CH-0001").returncode, 2)


class IntentTests(Project):
    def intent(self, *args):
        return self.pdlc("intent", *args)

    def test_new_takes_the_next_free_id_and_writes_the_file(self):
        done = self.intent("new", "--name", "Export to CSV", "--what", "Users export the list.")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("IN-0002", done.stdout)
        path = self.root / "pdlc/inbox/IN-0002-export-to-csv.md"
        text = path.read_text()
        self.assertTrue(text.startswith("# IN-0002 · Export to CSV\n"))
        self.assertRegex(text, r"Status: new · Ticket: none · Branch: none · Added: \d{4}-\d\d-\d\d")
        self.assertIn("## What and why\n\nUsers export the list.", text)
        for title in ("Requirements", "Changes", "Acceptance checks", "Notes"):
            self.assertIn("## %s\n" % title, text)
        self.assertIn("Acceptance-File: none", text)
        self.assertNotIn("Awaits approval", text)

    def test_the_next_id_counts_changes_and_branches_too(self):
        self.write("pdlc/changes/CH-0004-x/change.md", CHANGE.replace("IN-0001", "IN-0007").replace("CH-0001", "CH-0004"))
        done = self.intent("new", "--name", "Next", "--what", "x")
        self.assertIn("IN-0008", done.stdout)

    def test_awaits_goes_first_in_the_notes(self):
        done = self.intent("new", "--name", "Dark mode", "--what", "A dark theme.", "--awaits", "The user says yes.")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = (self.root / "pdlc/inbox/IN-0002-dark-mode.md").read_text()
        self.assertTrue(text.split("## Notes")[1].strip().startswith("Awaits approval: The user says yes."))

    def test_migrate(self):
        done = self.intent("new", "--migrate", "JOB-list", "DES-errors")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = (self.root / "pdlc/inbox/IN-0002-migrate-job-list-to-des-errors.md").read_text()
        self.assertIn("# IN-0002 · Migrate JOB-list to DES-errors", text)
        self.assertIn("JOB-list", text.split("## What and why")[1])

    def test_new_needs_a_name_and_text(self):
        self.assertEqual(self.intent("new", "--name", "x").returncode, 2)
        self.assertEqual(self.intent("new", "--what", "x").returncode, 2)

    def test_new_needs_the_inbox_files_adapter(self):
        self.write("pdlc/config.md", CONFIG.replace("inbox-files", "inbox-github"))
        done = self.intent("new", "--name", "x", "--what", "y")
        self.assertEqual(done.returncode, 1)
        self.assertIn("inbox-files", done.stdout)
        self.assertFalse(list((self.root / "pdlc/inbox").glob("IN-0002*")))

    def test_status(self):
        self.assertEqual(self.intent("IN-0001", "--status", "ready").returncode, 0)
        self.assertEqual(self.intent("IN-0001", "--status", "planned").returncode, 1)
        self.assertIn("Status: ready ·", self.read("pdlc/inbox/IN-0001-reset.md"))

    def test_requirements_replace_the_placeholder_and_change_in_place(self):
        done = self.intent("IN-0001", "--req", "CAP-email.R1=added", "--req", "JOB-x.R2=changed")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/inbox/IN-0001-reset.md")
        part = text.split("## Requirements")[1].split("## Changes")[0]
        self.assertEqual([l for l in part.splitlines() if l.strip()], ["- CAP-email.R1: added", "- JOB-x.R2: changed"])
        self.intent("IN-0001", "--req", "CAP-email.R1=retiring")
        part = self.read("pdlc/inbox/IN-0001-reset.md").split("## Requirements")[1].split("## Changes")[0]
        self.assertEqual([l for l in part.splitlines() if l.strip()], ["- CAP-email.R1: retiring", "- JOB-x.R2: changed"])

    def test_a_wrong_requirement_word_exits_1(self):
        self.assertEqual(self.intent("IN-0001", "--req", "CAP-email.R1=new").returncode, 1)
        self.assertEqual(self.intent("IN-0001", "--req", "CAP-email.R1").returncode, 1)

    def test_was_and_readme_go_to_the_notes_once(self):
        for _ in range(2):
            done = self.intent("IN-0001", "--was", "CAP-email.R1", "old words", "new words",
                               "--readme", "Run it", "CAP-email.R1")
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        notes = self.read("pdlc/inbox/IN-0001-reset.md").split("## Notes")[1].split("## Handoff")[0]
        self.assertEqual(notes.count('- CAP-email.R1: was "old words", now "new words"'), 1)
        self.assertEqual(notes.count('- README: "Run it" → CAP-email.R1'), 1)
        self.assertIn("how many tries", notes)

    def test_an_unknown_intent_exits_1(self):
        self.assertEqual(self.intent("IN-0009", "--status", "ready").returncode, 1)


JOB_LIST = """# JOB-list · List things

Status: active

## Interface

- `list [--top N]` · command · `src/cli.py` · proposed
  - in: an optional number N
  - out: on standard output, one line for each item. The exit code is 0.
  - errors: none

## Requirements

### JOB-list.R1 · Top

Status: proposed · Intents: IN-0001

- Given --top 2, when run, then two lines show.
"""
NEW_CHANGE = {
    "delivers": "Users get an email when they reset a password.",
    "reqs": ["CAP-email.R2", "CAP-email.R1"],
    "interface": ["send(template: TemplateName, to: Email) -> SentId", "EMAIL_OUTBOX_DIR"],
    "relies": ["CAP-store (used, not changed)"],
    "files": ["src/email.js"],
    "check_files": ["tests/test_email.py"],
    "checks": {"CAP-email.R1": "test_CAP_email_R1_send", "CAP-email.R2": "manual check"},
    "manual": ["CAP-email.R2 · Given nothing, when called, then it returns. · Open the page."],
}


class ChangeNew(Project):
    branch = "main"

    def setUp(self):
        super().setUp()
        shutil.rmtree(self.root / "pdlc/changes/CH-0001-email")
        self.write("pdlc/inbox/IN-0001-reset.md",
                   self.read("pdlc/inbox/IN-0001-reset.md").replace("- CH-0001 · email templates", "- none yet"))
        self.write("pdlc/specs/capabilities/CAP-email.md", CAP_EMAIL)
        self.write("pdlc/specs/jobs/JOB-list.md", JOB_LIST)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Update IN-0001: fixtures")

    def new(self, data=None, scope="CAP-email", name="Email templates", **change):
        body = dict(NEW_CHANGE if data is None else data, **change)
        for key in [k for k, v in body.items() if v is None]:
            del body[key]
        return self.pdlc("change", "new", "IN-0001", "--scope", scope, "--name", name, "--json", "-",
                         input=json.dumps(body))

    def spec(self):
        return self.read("pdlc/changes/CH-0001-email-templates/change.md")

    def test_it_writes_the_header_and_the_sections_in_order(self):
        done = self.new()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("CH-0001", done.stdout)
        text = self.spec()
        lines = text.splitlines()
        self.assertEqual(lines[0], "# CH-0001 · Email templates")
        self.assertEqual(lines[2], "Intent: IN-0001 · Scope: CAP-email · Status: planned · Ticket: none · "
                                   "Branch: none · Base: main")
        self.assertEqual(lines[3], "Tests-Locked: none")
        heads = [l for l in lines if l.startswith("## ")]
        self.assertEqual(heads, ["## Delivers", "## Requirements", "## Relies on", "## Interface", "## Files",
                                 "## Check files", "## Steps", "## Manual checks", "## Progress log"])
        self.assertIn("Users get an email when they reset a password.", text)
        self.assertEqual(pdlclib_field(text, "Status"), "planned")

    def test_a_retiring_requirement_gets_the_retire_mark(self):
        spec = self.root / "pdlc/specs/capabilities/CAP-email.md"
        spec.write_text(spec.read_text().replace("### CAP-email.R2 \u00b7 Other\n\nStatus: ready", "### CAP-email.R2 \u00b7 Other\n\nStatus: retiring"))
        done = self.new()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.spec()
        self.assertIn("### CAP-email.R2 \u00b7 Other (retire)\n", text)
        self.assertIn("### CAP-email.R1 \u00b7 Send\n", text)
        self.assertIn("\u00b7 Other \u00b7 [ ]", text)

    def test_the_next_free_change_id(self):
        self.write("pdlc/changes/CH-0004-x/change.md", CHANGE.replace("CH-0001", "CH-0004"))
        done = self.new()
        self.assertIn("CH-0005", done.stdout)
        self.assertTrue((self.root / "pdlc/changes/CH-0005-email-templates/change.md").exists())

    def test_requirements_are_copied_word_for_word_in_number_order(self):
        self.new()
        part = pdlclib_section(self.spec(), "Requirements")
        self.assertEqual(part.strip(), "### CAP-email.R1 · Send\n\n- Given a name, when sent, then it is sent.\n\n"
                                       "### CAP-email.R2 · Other\n\n- Given nothing, when called, then it returns.")
        self.assertNotIn("Intents:", self.spec())

    def test_relies_on_has_the_fixed_entries_and_the_extra_ones(self):
        self.new()
        part = pdlclib_section(self.spec(), "Relies on")
        self.assertEqual([l for l in part.splitlines() if l.strip()], [
            "- DES-writing-style (conventions to follow)", "- DES-pdlc-check-tagging (conventions to follow)",
            "- DES-errors (conventions to follow)", "- CAP-store (used, not changed)"])

    def test_interface_entries_are_copied_without_the_proposed_mark(self):
        self.new()
        part = pdlclib_section(self.spec(), "Interface")
        self.assertIn("- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`\n"
                      "  - in: the name of a template, and an email address\n"
                      "  - out: the ID of the sent email\n  - errors: none", part)
        self.assertNotIn("proposed", self.spec())
        self.assertNotIn("other()", part)
        seams = part.split("### Test seams")[1]
        self.assertIn("- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`\n  - in: a folder", seams)
        self.assertNotIn("send(", seams)

    def test_steps_have_one_for_each_requirement(self):
        self.new()
        part = pdlclib_section(self.spec(), "Steps")
        self.assertIn("### Step 1 · Send · [ ]\n\n- Requirement: CAP-email.R1\n- Check: test_CAP_email_R1_send\n"
                      "- Done when: the check passes", part)
        self.assertIn("### Step 2 · Other · [ ]\n\n- Requirement: CAP-email.R2\n- Check: manual check", part)

    def test_files_check_files_and_manual_checks(self):
        self.new()
        self.assertIn("- src/email.js", pdlclib_section(self.spec(), "Files"))
        self.assertIn("- tests/test_email.py", pdlclib_section(self.spec(), "Check files"))
        self.assertIn("CAP-email.R2 · Given nothing", pdlclib_section(self.spec(), "Manual checks"))
        done = self.new(manual=[], check_files=[], name="Other name")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/changes/CH-0002-other-name/change.md")
        self.assertEqual(pdlclib_section(text, "Manual checks").strip(), "none")
        self.assertEqual(pdlclib_section(text, "Check files").strip(), "- none")

    def test_a_job_change_gets_the_readme_step_last(self):
        data = dict(NEW_CHANGE, reqs=["JOB-list.R1"], interface=["list [--top N]"], relies=[],
                    checks={"JOB-list.R1": "test_JOB_list_R1"}, files=["src/cli.py"],
                    readme_done="The README names the --top flag and how to run the checks.")
        done = self.new(data, scope="JOB-list", name="List things")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        text = self.read("pdlc/changes/CH-0001-list-things/change.md")
        steps = pdlclib_section(text, "Steps")
        self.assertTrue(steps.strip().endswith("- Done when: The README names the --top flag and how to run the checks."))
        self.assertIn("### Step 2 · README · [ ]", steps)
        self.assertIn("- README.md", pdlclib_section(text, "Files"))

    def test_a_job_change_needs_readme_done(self):
        data = dict(NEW_CHANGE, reqs=["JOB-list.R1"], interface=["list [--top N]"], relies=[],
                    checks={"JOB-list.R1": "test_JOB_list_R1"})
        self.assertEqual(self.new(data, scope="JOB-list").returncode, 1)

    def test_the_change_is_added_to_the_intent_changes(self):
        self.new()
        part = pdlclib_section(self.read("pdlc/inbox/IN-0001-reset.md"), "Changes")
        self.assertEqual([l for l in part.splitlines() if l.strip()], ["- CH-0001 · Email templates"])
        self.new(name="Second")
        part = pdlclib_section(self.read("pdlc/inbox/IN-0001-reset.md"), "Changes")
        self.assertEqual([l for l in part.splitlines() if l.strip()],
                         ["- CH-0001 · Email templates", "- CH-0002 · Second"])

    def test_the_file_passes_the_order_check(self):
        self.new()
        done = subprocess.run([sys.executable, str(SCRIPT.parent / "check_order.py"), "IN-0001"],
                              cwd=str(self.root), capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def test_a_check_name_without_its_requirement_id_exits_1_and_writes_nothing(self):
        before = self.read("pdlc/inbox/IN-0001-reset.md")
        done = self.new(checks={"CAP-email.R1": "test_send", "CAP-email.R2": "manual check"})
        self.assertEqual(done.returncode, 1)
        self.assertIn("CAP-email.R1", done.stdout)
        self.assertEqual(list((self.root / "pdlc/changes").iterdir()), [])
        self.assertEqual(self.read("pdlc/inbox/IN-0001-reset.md"), before)

    def test_the_underscored_form_of_the_id_is_accepted(self):
        done = self.new(checks={"CAP-email.R1": "test_CAP_email_R1", "CAP-email.R2": "CAP-email.R2 works"})
        self.assertEqual(done.returncode, 0, done.stdout)

    def test_each_requirement_needs_a_check(self):
        self.assertEqual(self.new(checks={"CAP-email.R1": "test_CAP_email_R1"}).returncode, 1)

    def test_a_missing_key_exits_1(self):
        for key in ("delivers", "reqs", "checks", "files", "check_files", "interface", "relies", "manual"):
            with self.subTest(key=key):
                done = self.new(**{key: None})
                self.assertEqual(done.returncode, 1, done.stdout + done.stderr)

    def test_an_entry_that_no_spec_has_exits_1(self):
        done = self.new(interface=["nothing()"])
        self.assertEqual(done.returncode, 1)
        self.assertIn("nothing()", done.stdout)

    def test_a_requirement_that_no_spec_has_exits_1(self):
        done = self.new(reqs=["CAP-email.R9"], checks={"CAP-email.R9": "CAP_email_R9"})
        self.assertEqual(done.returncode, 1)

    def test_an_unknown_scope_or_intent_exits_1(self):
        self.assertEqual(self.new(scope="CAP-nothing").returncode, 1)
        done = self.pdlc("change", "new", "IN-0009", "--scope", "CAP-email", "--name", "x", "--json", "-",
                         input=json.dumps(NEW_CHANGE))
        self.assertEqual(done.returncode, 1)

    def test_it_makes_no_commit(self):
        self.new()
        self.assertEqual(self.log(), "Update IN-0001: fixtures")


class Imports(unittest.TestCase):
    def test_no_bytecode_left_in_the_bin_folder(self):
        shutil.rmtree(SCRIPT.parent / "__pycache__", ignore_errors=True)
        run("commit")
        self.assertFalse((SCRIPT.parent / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
