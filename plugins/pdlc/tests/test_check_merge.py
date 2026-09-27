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

ALL = ["tests", "specification", "security", "quality", "compliance", "privacy"]


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

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, remits):
        (self.root / "pdlc/config.md").write_text(CONFIG.format(remits=", ".join(remits)))

    def passed(self, remits, result="pass"):
        for remit in remits:
            folder = self.change / "review" / remit
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "result.md").write_text("Result: %s\n\nProblems: none\n" % result)

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
        self.assertEqual(self.run_check("CH-0001")[0], 0)


if __name__ == "__main__":
    unittest.main()
