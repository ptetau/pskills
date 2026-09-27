"""Tests for pdlc's merge check. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
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

Intent: IN-0002 · Scope: CAP-email · Status: {status} · Ticket: none · Branch: none

## Requirements

{reqs}

## Relies on

- DES-writing-style
"""


class MergeCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pdlc/specs/capabilities").mkdir(parents=True)
        (self.root / "pdlc/changes").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, r1="verified", r2="verified", reqs="### CAP-email.R2 · Send from a template",
              status="in review"):
        (self.root / "pdlc/specs/capabilities/CAP-email.md").write_text(
            CAPABILITY.format(r1=r1, r2=r2))
        (self.root / "pdlc/changes/CH-0001-email-templates.md").write_text(
            CHANGE.format(status=status, reqs=reqs))

    def write_change(self, reqs, status="in review"):
        (self.root / "pdlc/changes/CH-0001-email-templates.md").write_text(
            CHANGE.format(status=status, reqs=reqs))

    def run_check(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_merge.main(["check_merge.py", *args], root=self.root)
        return code, out.getvalue()

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

    def test_retired_requirement_must_be_gone_from_its_spec(self):
        self.write(reqs="### CAP-email.R2 · Send from a template (retire)")
        self.assertEqual(self.run_check("CH-0001")[0], 1)
        self.write(reqs="### CAP-email.R7 · Old thing (retire)")
        self.assertEqual(self.run_check("CH-0001")[0], 0)

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

    def test_fails_when_the_change_lists_no_requirements(self):
        self.write(reqs="None.")
        self.assertEqual(self.run_check("CH-0001")[0], 1)

    def test_unknown_change_fails(self):
        self.write()
        self.assertEqual(self.run_check("CH-0099")[0], 1)

    def test_no_argument_checks_only_changes_in_review(self):
        self.write(r2="built", status="building")
        self.assertEqual(self.run_check()[0], 0)
        self.write(r2="built", status="in review")
        self.assertEqual(self.run_check()[0], 1)


if __name__ == "__main__":
    unittest.main()
