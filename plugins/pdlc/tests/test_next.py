"""Tests for `pdlc.py next`: the next stage and its target, from the records.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
SCRIPT = PLUGIN / "skills/init/references/bin/pdlc.py"
TRAILERS = PLUGIN / "skills/init/references/defaults/DES-pdlc-commit-trailers.md"
GIT_ENV = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign", "GIT_CONFIG_VALUE_0": "false"}


def intent(n, status="new", changes=(), locked="none", handoff=None, notes="", time="2026-10-10T10:00:00Z"):
    lines = ["# IN-%04d · Thing" % n, "", "Status: %s · Ticket: none · Branch: none · Added: 2026-10-10" % status,
             "", "## What and why", "", "Words.", "", "## Changes", ""]
    lines += ["- %s · name" % c for c in changes] or ["- none yet"]
    lines += ["", "## Acceptance checks", "", "Acceptance-File: none", "Acceptance-Locked: %s" % locked,
              "Acceptance-Passed: none", "", "## Notes", ""]
    if notes:
        lines += [notes, ""]
    if handoff:
        lines += ["## Handoff", "", "Handoff · IN-%04d · %s" % ((n,) + handoff), "Time: " + time, ""]
    return "\n".join(lines) + "\n"


def with_open(text, reason):
    return text + "\n### Open\n\n- Reason: %s\n- Decision: x\n- Recommended answer: y\n" % reason


def change(n, intent_n, status="planned", branch="none"):
    return ("# CH-%04d · name\n\nIntent: IN-%04d · Scope: CAP-x · Status: %s · Ticket: none · "
            "Branch: %s · Base: main\nTests-Locked: none\n\n## Requirements\n" % (n, intent_n, status, branch))


def handoff_file(n, stage, nxt, reason=None, time="2026-10-10T10:00:00Z"):
    text = "# Handoff · CH-%04d · %s → %s\nTime: %s\n\n## Done\n\n- x\n" % (n, stage, nxt, time)
    text += "\n## Open\n\n" + ("- Reason: %s\n- Decision: x\n- Recommended answer: y\n" % reason if reason else "- none\n")
    return text


class Next(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("pdlc/config.md", "# pdlc config\n")
        self.write("pdlc/specs/design/DES-pdlc-commit-trailers.md", TRAILERS.read_text())
        env = dict(os.environ, **GIT_ENV)
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-qm", "Set up pdlc"]):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=str(self.root),
                           check=True, capture_output=True, env=env)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def git(self, *args):
        self.clock = getattr(self, "clock", 0) + 1
        date = "2026-10-10T10:%02d:00+00:00" % self.clock
        env = dict(os.environ, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date, **GIT_ENV)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=str(self.root),
                       check=True, capture_output=True, env=env)

    def git_out(self, *args):
        return subprocess.run(["git", *args], cwd=str(self.root), capture_output=True, text=True).stdout.strip()

    def commit_all(self, message="Records"):
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def on_branch(self, name, base, write):
        """Make or extend the branch `name` from `base`, run `write` there, commit, and return to main."""
        self.commit_all()
        exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/" + name],
                                cwd=str(self.root)).returncode == 0
        self.git("switch", "-q", name) if exists else self.git("switch", "-q", "-c", name, base)
        write()
        self.commit_all("On " + name)
        self.git("switch", "-q", "main")

    def put_intent(self, n, **kw):
        self.write("pdlc/inbox/IN-%04d-thing.md" % n, intent(n, **kw))

    def put_intent_branch(self, n, **kw):
        """The intent as the intent branch has it; main keeps its own copy."""
        self.on_branch("pdlc/IN-%04d-thing" % n, "main", lambda: self.put_intent(n, **kw))

    def put_change(self, n, intent_n, status="planned", handoff=None, base="main", time=None):
        """A planned change stays on main. Any other state lives on the branch of the change."""
        self.write("pdlc/changes/CH-%04d-name/change.md" % n, change(n, intent_n))
        if status == "planned" and not handoff:
            return
        name = "pdlc/CH-%04d-name" % n

        def write():
            self.write("pdlc/changes/CH-%04d-name/change.md" % n, change(n, intent_n, status, name))
            path = self.root / ("pdlc/changes/CH-%04d-name/handoff.md" % n)
            if handoff:
                self.write("pdlc/changes/CH-%04d-name/handoff.md" % n,
                           handoff_file(n, *handoff, **({"time": time} if time else {})))
            elif path.exists():
                path.unlink()
        self.on_branch(name, base, write)

    def next(self, *args):
        env = dict(os.environ, **GIT_ENV)
        done = subprocess.run([sys.executable, str(SCRIPT), "next", *args], cwd=str(self.root),
                              capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done.stdout.strip()

    def test_no_intent_is_done(self):
        self.assertEqual(self.next(), "done")

    def test_new_intent_needs_intake(self):
        self.put_intent(1)
        self.assertEqual(self.next(), "intake IN-0001")

    def test_specifying_needs_ready(self):
        self.put_intent(1, status="specifying", handoff=("intake → ready",))
        self.assertEqual(self.next(), "ready IN-0001")

    def test_ready_without_changes_needs_change(self):
        self.put_intent(1, status="ready")
        self.assertEqual(self.next(), "change IN-0001")

    def test_changes_without_locked_acceptance_need_acceptance(self):
        self.put_intent(1, status="ready", changes=["CH-0001"])
        self.put_change(1, 1)
        self.assertEqual(self.next(), "acceptance IN-0001")

    def test_planned_change_needs_tests(self):
        self.put_intent(1, status="ready", changes=["CH-0001", "CH-0002"], locked="abc123")
        self.put_change(1, 1)
        self.put_change(2, 1)
        self.assertEqual(self.next(), "tests CH-0001")

    def test_stage_follows_the_handoff_of_the_change(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        for status, handoff, want in [
            ("testing", None, "tests CH-0001"),
            ("building", ("tests", "build"), "build CH-0001"),
            ("building", ("build", "verify"), "verify CH-0001"),
            ("building", ("verify", "show"), "show CH-0001"),
            ("in review", ("verify", "show"), "show CH-0001"),
            ("building", ("verify", "build"), "build CH-0001"),
            ("building", ("build", "tests"), "tests CH-0001"),
            ("building", ("build", "acceptance"), "acceptance IN-0001"),
        ]:
            self.put_change(1, 1, status, handoff)
            self.assertEqual(self.next(), want, (status, handoff))

    def test_next_change_starts_after_the_first_is_proposed(self):
        self.put_intent(1, status="building", changes=["CH-0001", "CH-0002"], locked="abc123")
        self.put_change(1, 1, "in review", ("show", "user"))
        self.put_change(2, 1)
        self.assertEqual(self.next(), "tests CH-0002")

    def test_each_change_proposed_is_done(self):
        self.put_intent(1, status="in review", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "in review", ("show", "user"))
        self.assertEqual(self.next(), "done")

    def test_a_proposed_change_in_a_building_intent_is_done(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "in review", ("show", "user"))
        self.assertEqual(self.next(), "done")

    def test_skips_finished_paused_and_awaiting_intents(self):
        self.put_intent(1, status="done")
        self.put_intent(2, status="paused")
        self.put_intent(3, status="new", notes="- Awaits approval: the user says go")
        self.put_intent(4, status="new")
        self.assertEqual(self.next(), "intake IN-0004")

    def test_the_oldest_intent_comes_first(self):
        self.put_intent(2)
        self.put_intent(1, status="specifying", handoff=("intake → ready",))
        self.assertEqual(self.next(), "ready IN-0001")

    def test_stopped_change_reports_its_reason(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "building", ("build", "user", "Third failed build."))
        self.assertEqual(self.next(), "stopped CH-0001: Third failed build.")

    def test_stopped_intent_reports_its_reason(self):
        text = intent(1, status="specifying", handoff=("ready → user",))
        self.write("pdlc/inbox/IN-0001-thing.md", with_open(text, "R1 contradicts R2."))
        self.assertEqual(self.next(), "stopped IN-0001: R1 contradicts R2.")

    def test_resume_repeats_the_stage_that_stopped(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "building", ("build", "user", "Third failed build."))
        self.assertEqual(self.next("--resume"), "build CH-0001")

    def test_a_named_intent_limits_the_search(self):
        self.put_intent(1)
        self.put_intent(2, status="ready")
        self.assertEqual(self.next("IN-0002"), "change IN-0002")

    def test_a_change_id_names_its_intent(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1)
        self.assertEqual(self.next("CH-0001"), "tests CH-0001")

    def test_main_reads_the_intent_and_change_from_their_branches(self):
        self.put_intent(1, status="building", changes=["CH-0001"])
        self.put_intent_branch(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "in review", ("show", "user"), base="pdlc/IN-0001-thing")
        self.assertEqual(self.git_out("branch", "--show-current"), "main")
        self.assertIn("Acceptance-Locked: none", (self.root / "pdlc/inbox/IN-0001-thing.md").read_text())
        self.assertEqual(self.next(), "done")

    def test_a_change_with_no_branch_is_planned_on_main(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1)
        self.write("pdlc/changes/CH-0001-name/change.md", change(1, 1, "building"))
        self.assertEqual(self.next(), "tests CH-0001")

    def test_a_stop_at_show_is_stopped_not_proposed(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123")
        self.put_change(1, 1, "in review", ("show", "user", "Third failed visual review."))
        self.assertEqual(self.next(), "stopped CH-0001: Third failed visual review.")
        self.assertEqual(self.next("--resume"), "show CH-0001")

    def send_back(self, stage):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123",
                        handoff=("acceptance → " + stage,), time="2026-10-10T11:00:00Z")
        self.put_change(1, 1, "building", ("build", "acceptance"), time="2026-10-10T10:30:00Z")
        return self.next()

    def test_a_send_back_to_acceptance_goes_to_build(self):
        self.assertEqual(self.send_back("build"), "build CH-0001")

    def test_a_send_back_to_acceptance_goes_to_tests(self):
        self.assertEqual(self.send_back("tests"), "tests CH-0001")

    def test_an_old_acceptance_handoff_does_not_hide_a_new_send_back(self):
        self.put_intent(1, status="building", changes=["CH-0001"], locked="abc123",
                        handoff=("acceptance → tests",), time="2026-10-10T09:00:00Z")
        self.put_change(1, 1, "building", ("build", "acceptance"), time="2026-10-10T10:30:00Z")
        self.assertEqual(self.next(), "acceptance IN-0001")

    def test_outside_a_project_exits_4(self):
        with tempfile.TemporaryDirectory() as empty:
            done = subprocess.run([sys.executable, str(SCRIPT), "next"], cwd=empty, capture_output=True, text=True)
            self.assertEqual(done.returncode, 4)


if __name__ == "__main__":
    unittest.main()
