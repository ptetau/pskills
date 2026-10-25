"""Tests for pdlc's merge check. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/check_merge.py"
spec = importlib.util.spec_from_file_location("check_merge", SCRIPT)
check_merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_merge)

CAPABILITY = """# CAP-email · Sending email

Status: active

## Requirements

### CAP-email.R1 · Send plain email

Status: {r1} · Intents: IN-0001

- Given an address, when we send, then one email goes out.

### CAP-email.R2 · Send from a template

Status: {r2} · Intents: IN-0002

- Given a template, when we send, then the values are filled in.
"""

CHANGE = """# CH-0001 · Email templates

Intent: IN-0002 · Scope: CAP-email · Status: {status} · Ticket: none · Branch: {branch} · Base: main
{lock}
## Requirements

{reqs}

## Relies on

- DES-writing-style

## Check files

{checks}
"""

CONFIG = """# pdlc config

## Reviews

- remits: {remits}
"""

INTENT = """# IN-0002 · Password reset

Status: building · Ticket: none · Branch: none · Added: 2026-10-10

## Changes

- CH-0001 · Email templates
- CH-0002 · Send the reset
"""

ALL = ["tests", "specification", "security", "quality", "compliance", "privacy"]

WRONG_VERSIONS = "Wrong versions:\n- CAP-email.R2 fills values · leaves the values out · fails\n"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


class MergeCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pdlc/specs/capabilities").mkdir(parents=True)
        self.change = self.root / "pdlc/changes/CH-0001-email-templates"
        self.change.mkdir(parents=True)
        self.config(ALL)
        self.passed(ALL)
        (self.root / "pdlc/inbox").mkdir()
        (self.root / "pdlc/inbox/IN-0002-password-reset.md").write_text(
            INTENT.replace("- CH-0002 · Send the reset\n", ""))

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, remits):
        (self.root / "pdlc/config.md").write_text(CONFIG.format(remits=", ".join(remits)))

    def reviewed_lock(self, sha):
        """A tests packet built from the change spec while it carried this lock."""
        folder = self.change / "review/tests"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "packet.md").write_text("## The change spec\n\nTests-Locked: %s\n" % sha)

    def passed(self, remits, result="pass", change=None, wrong=WRONG_VERSIONS):
        for remit in remits:
            folder = (change or self.change) / "review" / remit
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "result.md").write_text("Result: %s\n\nProblems: none\n\n%s" % (result, wrong))

    def write(self, r1="verified", r2="verified", reqs="### CAP-email.R2 · Send from a template",
              status="in review", branch="none", lock="", checks="none"):
        (self.root / "pdlc/specs/capabilities/CAP-email.md").write_text(
            CAPABILITY.format(r1=r1, r2=r2))
        self.write_change(reqs, status, branch, lock, checks)

    def write_change(self, reqs, status="in review", branch="none", lock="", checks="none"):
        (self.change / "change.md").write_text(
            CHANGE.format(status=status, reqs=reqs, branch=branch, lock=lock, checks=checks))

    def run_check(self, *args, branch=None):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_merge.main(["check_merge.py", *args], root=self.root, branch=branch)
        return code, out.getvalue()

    # Requirements

    def test_passes_when_every_requirement_is_verified(self):
        self.write(r2="verified")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_fails_when_a_requirement_is_only_built(self):
        self.write(r2="built")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CAP-email.R2 is built, not verified", out)

    def test_ignores_requirements_the_change_does_not_list(self):
        self.write(r1="proposed", r2="verified")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_fails_when_a_listed_requirement_is_missing_from_its_spec(self):
        self.write(reqs="### CAP-email.R9 · Does not exist")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CAP-email.R9 is not in its spec", out)

    def test_a_missing_status_does_not_borrow_the_next_requirements_status(self):
        self.write(r2="verified")
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        text = path.read_text().replace("Status: verified · Intents: IN-0001\n", "", 1)
        text += "\n### CAP-email.R3 · Later\n\nStatus: verified · Intents: IN-0003\n"
        path.write_text(text)
        self.write_change("### CAP-email.R1 · Send plain email")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CAP-email.R1 is missing", out)

    def test_retired_requirement_must_be_gone_from_its_spec(self):
        self.write(reqs="### CAP-email.R2 · Send from a template (retire)")
        self.assertEqual(self.run_check("CH-0001")[0], 1)
        self.write(reqs="### CAP-email.R7 · Old thing (retire)")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_fails_when_the_change_lists_no_requirements(self):
        self.write(reqs="None.")
        self.assertEqual(self.run_check("CH-0001")[0], 1)

    # The assumption marker is written one way

    def test_passes_with_the_plain_marker(self):
        self.write(reqs="### CAP-email.R2 · Send from a template\n\n- Given 3 tries (assumed), then stop.")
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        path.write_text(path.read_text().replace("the values are filled in.",
                                                 "the values are filled in (assumed)."))
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_passes_with_any_marker_that_starts_with_assumed(self):
        self.write(reqs="### CAP-email.R2 · Send from a template\n\n"
                        "- Given 3 tries (assumed limit), then stop (assumed: each retry is slow).")
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        path.write_text(path.read_text().replace("the values are filled in.",
                                                 "the values are filled in (assumed: a new name)."))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_fails_on_emphasis_around_the_marker_in_the_change_spec(self):
        self.write(reqs="### CAP-email.R2 · Send from a template\n\n"
                        "- Given 3 tries *(assumed)*, then stop _(assumed: a reason)_.")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn('change.md: write "*(assumed)*" so it starts with "(assumed"', out)
        self.assertIn('change.md: write "_(assumed: a reason)_" so it starts with "(assumed"', out)

    def test_fails_on_a_marker_that_does_not_start_with_assumed_in_a_requirement(self):
        self.write()
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        path.write_text(path.read_text().replace("the values are filled in.",
                                                 "the values are filled in (name assumed)."))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn('CAP-email.R2: write "(name assumed)" so it starts with "(assumed"', out)

    def test_ignores_the_marker_in_requirements_the_change_does_not_list(self):
        self.write()
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        path.write_text(path.read_text().replace("one email goes out.",
                                                 "one email goes out *(assumed)*."))
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # Finding the change

    def test_unknown_change_fails(self):
        self.write()
        self.assertEqual(self.run_check("CH-0099")[0], 1)

    def test_no_argument_checks_only_changes_in_review(self):
        self.write(r2="built", status="building")
        self.assertEqual(self.run_check()[0], 0)
        self.write(r2="built", status="in review")
        self.assertEqual(self.run_check()[0], 1)

    def test_no_argument_checks_the_change_for_the_current_branch_whatever_its_status(self):
        self.write(r2="built", status="building", branch="pdlc/CH-0001-email-templates")
        code, out = self.run_check(branch="pdlc/CH-0001-email-templates")
        self.assertEqual(code, 1)
        self.assertIn("FAIL CH-0001", out)

    def test_no_argument_finds_the_change_whose_branch_is_in_backticks(self):
        self.write(r2="built", status="building", branch="`pdlc/CH-0001-email-templates`")
        code, out = self.run_check(branch="pdlc/CH-0001-email-templates")
        self.assertEqual(code, 1)
        self.assertIn("FAIL CH-0001", out)

    def test_a_branch_with_no_change_spec_checks_changes_in_review(self):
        self.write(r2="verified", status="in review", branch="pdlc/CH-0001-email-templates")
        self.assertEqual(self.run_check(branch="some-other-branch")[0], 0)

    # Reviews

    def test_fails_when_a_configured_remit_has_no_result(self):
        self.write()
        (self.change / "review/privacy/result.md").unlink()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("privacy review has no result", out)

    def test_a_missing_result_gives_the_command_that_makes_it(self):
        self.write()
        (self.change / "review/compliance/result.md").unlink()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("compliance review has no result", out)
        self.assertIn("python3 pdlc/bin/make_packets.py CH-0001 compliance", out)

    def test_fails_when_a_remit_did_not_pass(self):
        self.write()
        self.passed(["security"], result="fail")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("security review did not pass", out)

    def test_only_configured_remits_are_required(self):
        self.write()
        self.config(["tests", "specification"])
        (self.change / "review/privacy/result.md").unlink()
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # Locked tests

    def locked_repo(self):
        test_file = self.root / "test/email.test.js"
        test_file.parent.mkdir()
        test_file.write_text("test('CAP-email.R2 fills values', () => {})\n")
        git(self.root, "init", "-q")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "tests")
        return test_file, git(self.root, "rev-parse", "HEAD")

    def test_fails_when_check_files_are_not_locked(self):
        self.write(checks="- test/email.test.js")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("tests are not locked", out)

    def test_passes_when_locked_check_files_are_unchanged(self):
        _, sha = self.locked_repo()
        self.write(checks="- test/email.test.js", lock="Tests-Locked: %s\n" % sha)
        self.reviewed_lock(sha)
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_fails_when_a_check_file_changed_after_the_lock(self):
        test_file, sha = self.locked_repo()
        self.write(checks="- test/email.test.js", lock="Tests-Locked: %s\n" % sha)
        test_file.write_text("test('CAP-email.R2 fills values', () => { /* weakened */ })\n")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "edit")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("changed after the tests were locked: test/email.test.js", out)

    def test_reads_the_newest_lock_when_an_old_one_is_left(self):
        test_file, old = self.locked_repo()
        test_file.write_text("test('CAP-email.R2 fills values', () => { /* fixed */ })\n")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "relock")
        new = git(self.root, "rev-parse", "HEAD")
        self.write(checks="- test/email.test.js",
                   lock="Tests-Locked: %s\nTests-Locked: %s\n" % (old, new))
        self.reviewed_lock(new)
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # The tests review must be of the current lock

    def relocked_repo(self):
        test_file, old = self.locked_repo()
        test_file.write_text("test('CAP-email.R2 fills values', () => { /* fixed */ })\n")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "relock")
        new = git(self.root, "rev-parse", "HEAD")
        self.write(checks="- test/email.test.js", lock="Tests-Locked: %s\n" % new)
        return old, new

    def test_fails_when_the_tests_review_is_of_an_older_lock(self):
        old, _ = self.relocked_repo()
        self.reviewed_lock(old)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("tests review is not of the current lock", out)

    def test_fails_when_the_tests_review_has_no_packet(self):
        self.relocked_repo()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("tests review is not of the current lock", out)

    def test_a_short_hash_in_the_packet_matches_the_lock(self):
        _, new = self.relocked_repo()
        self.reviewed_lock(new[:7])
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_no_tests_remit_needs_no_tests_review_of_the_lock(self):
        self.relocked_repo()
        self.config(["specification"])
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # The tests review names a wrong version for each check

    def test_fails_when_the_tests_review_lists_no_wrong_versions(self):
        _, new = self.relocked_repo()
        self.reviewed_lock(new)
        self.passed(["tests"], wrong="Wrong versions:\n- none\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn('tests review lists no "Wrong versions"', out)

    def test_fails_when_a_check_passes_a_wrong_version(self):
        _, new = self.relocked_repo()
        self.reviewed_lock(new)
        weak = "## Wrong versions\n\n- CAP-email.R2 fills values · fills them in any order · passes\n"
        self.passed(["tests"], wrong=weak)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("a check passes a wrong version: CAP-email.R2 fills values", out)

    def test_a_re_review_needs_wrong_versions_when_a_check_changed(self):
        old, new = self.relocked_repo()
        self.reviewed_lock(new)
        packet = self.change / "review/tests/packet.md"
        packet.write_text("## Re-review\n\nEarlier review: %s\n\n" % old + packet.read_text())
        self.passed(["tests"], wrong="Wrong versions:\n- none\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn('tests review lists no "Wrong versions"', out)

    def test_a_re_review_needs_no_wrong_versions_when_no_check_changed(self):
        _, new = self.relocked_repo()
        (self.root / "notes.txt").write_text("not a check\n")
        self.commit_all("an unrelated commit")
        later = git(self.root, "rev-parse", "HEAD")
        self.write(checks="- test/email.test.js", lock="Tests-Locked: %s\n" % later)
        self.reviewed_lock(later)
        packet = self.change / "review/tests/packet.md"
        packet.write_text("## Re-review\n\nEarlier review: %s\n\n" % new + packet.read_text())
        self.passed(["tests"], wrong="Wrong versions:\n- none\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_a_re_review_still_fails_a_check_that_passes_a_wrong_version(self):
        old, new = self.relocked_repo()
        self.reviewed_lock(new)
        packet = self.change / "review/tests/packet.md"
        packet.write_text("## Re-review\n\nEarlier review: %s\n\n" % old + packet.read_text())
        self.passed(["tests"], wrong="Wrong versions:\n- CAP-email.R2 fills values · skips one · passes\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("a check passes a wrong version", out)

    def test_a_change_with_no_checks_needs_no_wrong_versions(self):
        self.write(checks="none")
        self.passed(["tests"], wrong="")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # The branch must merge into main

    def commit_all(self, message):
        git(self.root, "add", "-A")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message)

    def branched_repo(self):
        """main, and a change branch that marked CAP-email.R2 verified."""
        self.write(r2="ready")
        git(self.root, "init", "-q", "-b", "main")
        self.commit_all("start")
        git(self.root, "switch", "-qc", "pdlc/CH-0001-email-templates")
        self.write(r2="verified")
        self.commit_all("verified")
        git(self.root, "switch", "-q", "main")

    def test_fails_when_the_branch_conflicts_with_main(self):
        self.branched_repo()
        spec = self.root / "pdlc/specs/capabilities/CAP-email.md"
        spec.write_text(spec.read_text().replace("Status: ready · Intents: IN-0002",
                                                 "Status: proposed · Intents: IN-0002, IN-0003"))
        self.commit_all("a newer intent edits the same requirement on main")
        git(self.root, "switch", "-q", "pdlc/CH-0001-email-templates")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("conflicts with main: pdlc/specs/capabilities/CAP-email.md", out)

    def test_passes_when_the_branch_merges_into_main_cleanly(self):
        self.branched_repo()
        (self.root / "README.md").write_text("Something new on main.\n")
        self.commit_all("unrelated work on main")
        git(self.root, "switch", "-q", "pdlc/CH-0001-email-templates")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    # An intent's changes merge together

    FIRST = "pdlc/CH-0001-email-templates"
    SECOND = "pdlc/CH-0002-send-reset"

    def write_second(self, status, branch):
        """CH-0002, the second change of IN-0002, with its reviews passed."""
        folder = self.root / "pdlc/changes/CH-0002-send-reset"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "change.md").write_text(
            CHANGE.format(status=status, reqs="### CAP-email.R1 · Send plain email",
                          branch=branch, lock="", checks="none")
            .replace("CH-0001 · Email templates", "CH-0002 · Send the reset"))
        self.passed(ALL, change=folder)

    def stacked_repo(self):
        """IN-0002 planned on main as CH-0001 then CH-0002; CH-0001 in review on its branch."""
        self.write(r1="ready", r2="ready", status="planned")
        (self.root / "pdlc/inbox/IN-0002-password-reset.md").write_text(INTENT)
        self.write_second("planned", "none")
        git(self.root, "init", "-q", "-b", "main")
        self.commit_all("plan IN-0002")
        git(self.root, "switch", "-qc", self.FIRST)
        self.write(r1="ready", r2="verified", branch=self.FIRST)
        self.commit_all("CH-0001 in review")

    def stack_second(self, status):
        """CH-0002's branch, on top of CH-0001's, with CH-0002 at this status."""
        git(self.root, "switch", "-qc", self.SECOND, self.FIRST)
        self.write(r1="verified", r2="verified", branch=self.FIRST)
        self.write_second(status, self.SECOND)
        self.commit_all("CH-0002 " + status)

    def test_fails_when_another_change_of_the_intent_has_no_branch(self):
        self.stacked_repo()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CH-0002 of IN-0002 is not ready (no branch)", out)

    def test_fails_when_another_change_of_the_intent_is_still_building(self):
        self.stacked_repo()
        self.stack_second("building")
        git(self.root, "switch", "-q", self.FIRST)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CH-0002 of IN-0002 is not ready (status: building)", out)

    def test_a_header_field_is_its_value_without_a_name_in_brackets_or_backticks(self):
        header = ("Intent: IN-0001 (poll-input-errors) · Scope: CAP-http-plumbing · "
                  "Status: in review · Ticket: none · Branch: `pdlc/CH-0001-x` · Base: main")
        self.assertEqual(check_merge.field(header, "Intent"), "IN-0001")
        self.assertEqual(check_merge.field(header, "Branch"), "pdlc/CH-0001-x")
        self.assertEqual(check_merge.field(header, "Status"), "in review")
        self.assertEqual(check_merge.field(header, "Base"), "main")

    def test_fails_when_another_change_is_building_and_the_intent_has_its_name(self):
        self.stacked_repo()
        self.stack_second("building")
        git(self.root, "switch", "-q", self.FIRST)
        spec = self.change / "change.md"
        spec.write_text(spec.read_text().replace("Intent: IN-0002", "Intent: IN-0002 (password-reset)"))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CH-0002 of IN-0002 is not ready (status: building)", out)

    def test_fails_when_the_intent_of_the_change_is_not_in_the_inbox(self):
        self.write()
        (self.root / "pdlc/inbox/IN-0002-password-reset.md").unlink()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("IN-0002 is not in pdlc/inbox", out)

    def test_passes_when_every_change_of_the_intent_is_in_review(self):
        self.stacked_repo()
        self.stack_second("in review")
        git(self.root, "switch", "-q", self.FIRST)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)
        git(self.root, "switch", "-q", self.SECOND)
        code, out = self.run_check("CH-0002")
        self.assertEqual(code, 0, out)

    def test_reads_another_change_from_its_own_branch(self):
        self.stacked_repo()
        self.stack_second("in review")
        git(self.root, "switch", "-q", self.FIRST)
        self.write(r1="ready", r2="built", status="building", branch=self.FIRST)
        self.commit_all("CH-0001 sent back to build")
        git(self.root, "switch", "-q", self.SECOND)
        code, out = self.run_check("CH-0002")
        self.assertEqual(code, 1)
        self.assertIn("CH-0001 of IN-0002 is not ready (status: building)", out)

    def test_reads_another_change_from_a_remote_branch(self):
        self.stacked_repo()
        self.stack_second("in review")
        sha = git(self.root, "rev-parse", "HEAD")
        git(self.root, "switch", "-q", self.FIRST)
        git(self.root, "update-ref", "refs/remotes/origin/" + self.SECOND, sha)
        git(self.root, "branch", "-qD", self.SECOND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_a_change_merged_into_main_counts_as_ready_when_its_branch_is_gone(self):
        self.stacked_repo()
        self.stack_second("in review")
        git(self.root, "switch", "-q", "main")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "-q", "--no-ff",
            "-m", "merge CH-0001", self.FIRST)
        git(self.root, "branch", "-qD", self.FIRST)
        git(self.root, "switch", "-q", self.SECOND)
        code, out = self.run_check("CH-0002")
        self.assertEqual(code, 0, out)

    def test_in_ci_a_merged_change_is_read_from_origin_main(self):
        self.stacked_repo()
        self.stack_second("in review")
        git(self.root, "switch", "-q", "main")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "-q", "--no-ff",
            "-m", "merge CH-0001", self.FIRST)
        git(self.root, "switch", "-q", self.SECOND)
        git(self.root, "update-ref", "refs/remotes/origin/main", "main")
        git(self.root, "branch", "-qD", self.FIRST, "main")
        code, out = self.run_check("CH-0002")
        self.assertNotIn("CH-0001 of IN-0002 is not ready", out)

    # A merged change's branch takes no new commits

    def merged_and_recorded(self):
        """CH-0001's branch merged into main, and main says it merged."""
        self.branched_repo()
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "-q", "--no-ff",
            "-m", "merge CH-0001", "pdlc/CH-0001-email-templates")
        self.write_change("### CAP-email.R2 · Send from a template", status="merged")
        self.commit_all("Record merges")
        git(self.root, "switch", "-q", "pdlc/CH-0001-email-templates")

    def test_fails_when_a_merged_change_has_new_commits_on_its_branch(self):
        self.merged_and_recorded()
        (self.root / "late-fix.txt").write_text("a fix after the merge\n")
        self.commit_all("late fix")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("CH-0001 already merged; new commits on its branch won't reach main. "
                      "Start a new change.", out)

    def test_a_merged_change_with_no_new_commits_passes(self):
        self.merged_and_recorded()
        code, out = self.run_check("CH-0001")
        self.assertNotIn("already merged", out)
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
