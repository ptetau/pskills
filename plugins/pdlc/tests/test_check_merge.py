"""Tests for pdlc's merge check. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

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

NOT_FOUND = "    - `TEMPLATE_NOT_FOUND` · `no template named <name>` · raises `TemplateNotFound`\n"
INVALID = "    - `INVALID_ADDRESS` · `not a valid email address: <address>` · raises `InvalidAddress`\n"
SEND = ("- `send(template: TemplateName, to: Email) -> SentId` · function · `src/email.js`\n"
        "  - in: a template and an address\n"
        "  - errors:\n" + NOT_FOUND + INVALID)

DES_ERRORS = """# DES-errors · The project's error codes

Status: agreed

| Code | Meaning | Whose fault | Retry helps? |
|---|---|---|---|
| `TEMPLATE_NOT_FOUND` | no such template | caller | no |
| `INVALID_ADDRESS` | bad address | caller | no |
| `TOP_INVALID` | bad --top | caller | no |
"""

WRONG_VERSIONS = "Wrong versions:\n- CAP-email.R2 fills values · leaves the values out · fails\n"


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          check=True).stdout.strip()


class MergeCheck(unittest.TestCase):
    """The checks of one change. The class AcceptanceGate tests the acceptance checks of the
    intent, so these tests leave them out."""

    def setUp(self):
        stub = mock.patch.object(check_merge, "acceptance_problems", return_value=[], create=True)
        stub.start()
        self.addCleanup(stub.stop)
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

    # Interface

    def interface(self, change=None, spec=None, job=None, relies=""):
        """Append an Interface section to the change spec, and to CAP-email or a job spec.
        A value of None adds no section. An empty string adds an empty section. Call it
        after write(). The text in `relies` goes under "Relies on" in the change spec."""
        def add(path, body):
            if body is not None:
                path.write_text(path.read_text() + "\n## Interface\n\n" + body)

        add(self.change / "change.md", change)
        add(self.root / "pdlc/specs/capabilities/CAP-email.md", spec)
        (self.root / "pdlc/specs/design").mkdir(parents=True, exist_ok=True)
        (self.root / "pdlc/specs/design/DES-errors.md").write_text(DES_ERRORS)
        if job is not None:
            jobs = self.root / "pdlc/specs/jobs"
            jobs.mkdir(parents=True, exist_ok=True)
            (jobs / "JOB-reset.md").write_text("# JOB-reset · Reset a password\n\nStatus: active\n")
            add(jobs / "JOB-reset.md", job)
        if relies:
            path = self.change / "change.md"
            path.write_text(path.read_text().replace("- DES-writing-style\n",
                                                     "- DES-writing-style\n" + relies))

    def test_passes_when_each_interface_entry_is_in_its_spec(self):
        self.write()
        self.interface(change=SEND, spec=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_fails_when_an_interface_entry_is_not_in_its_spec(self):
        self.write()
        self.interface(change=SEND, spec="- none\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("`send(template: TemplateName, to: Email) -> SentId` is not in the "
                      "Interface of CAP-email", out)

    def test_an_entry_in_the_requirements_of_the_spec_does_not_count(self):
        self.write()
        path = self.root / "pdlc/specs/capabilities/CAP-email.md"
        path.write_text(path.read_text().replace("- Given a template, when we send, then the values are filled in.",
                                                 SEND))
        self.interface(change=SEND, spec="")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("is not in the Interface of CAP-email", out)

    def test_finds_an_entry_in_a_spec_under_relies_on(self):
        self.write()
        self.interface(change=SEND, spec="", job=SEND, relies="- JOB-reset (used, not changed)\n")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_ignores_a_spec_that_the_change_does_not_name(self):
        self.write()
        self.interface(change=SEND, spec="", job=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("is not in the Interface of CAP-email", out)

    def test_checks_the_entries_under_test_seams(self):
        self.write()
        seam = ("### Test seams\n\n"
                "- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`\n"
                "  - errors: none\n")
        self.interface(change=SEND + "\n" + seam, spec=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("EMAIL_OUTBOX_DIR", out)

    def test_fails_when_the_error_codes_differ(self):
        self.write()
        self.interface(change=SEND.replace(INVALID, ""), spec=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertEqual(out.count("\n  - "), 1, out)
        self.assertIn("Interface entry `send(template: TemplateName, to: Email) -> SentId` lacks "
                      "the error `INVALID_ADDRESS` ·", out)
        self.assertIn("that CAP-email has", out)

    def test_fails_when_the_spec_entry_is_still_proposed(self):
        self.write()
        self.interface(change=SEND, spec=SEND.replace("src/email.js`", "src/email.js` · proposed", 1))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("is still proposed in CAP-email", out)

    def test_a_retiring_spec_entry_still_matches(self):
        self.write()
        self.interface(change=SEND, spec=SEND.replace("src/email.js`", "src/email.js` · retiring", 1))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_spaces_in_the_name_do_not_matter(self):
        self.write()
        self.interface(change=SEND.replace("template: Tem", "template:  Tem"), spec=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_skips_the_check_when_the_scope_spec_has_no_interface_section(self):
        self.write()
        self.interface(change=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_an_interface_of_none_needs_nothing(self):
        self.write()
        self.interface(change="- none\n", spec="")
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def test_reads_entries_with_their_errors(self):
        text = ("# CAP-email\n\n## Interface\n\n"
                + SEND + "- `ping()` · function · `src/ping.js`\n  - out: nothing\n\n"
                "### Test seams\n\n"
                "- `EMAIL_OUTBOX_DIR` · seam: outside vendor · `src/email.js`\n"
                "  - Errors:\n"
                "    - `OUTBOX_MISSING` · `no outbox` · raises `OutboxMissing`\n\n"
                "## Requirements\n\n- `later()` is not an entry.\n")
        found = check_merge.interface_entries(text)
        self.assertEqual(list(found), ["send(template: TemplateName, to: Email) -> SentId",
                                       "ping()", "EMAIL_OUTBOX_DIR"])
        first, triples, problems = found["send(template: TemplateName, to: Email) -> SentId"]
        self.assertEqual(triples, {
            ("TEMPLATE_NOT_FOUND", "no template named <name>", "raises TemplateNotFound"),
            ("INVALID_ADDRESS", "not a valid email address: <address>", "raises InvalidAddress")})
        self.assertEqual(problems, [])
        self.assertEqual(found["ping()"][1], frozenset())
        self.assertEqual(found["EMAIL_OUTBOX_DIR"][1],
                         {("OUTBOX_MISSING", "no outbox", "raises OutboxMissing")})

    def test_a_proposed_mark_before_other_text_still_counts(self):
        self.write()
        self.interface(change=SEND, spec=SEND.replace("src/email.js`", "src/email.js` · proposed (assumed)", 1))
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("is still proposed in CAP-email", out)

    def test_an_error_line_wrapped_onto_a_deeper_line_is_one_item(self):
        wrapped = SEND.replace("`no template named <name>` · raises", "`no template named <name>` ·\n"
                               "      raises")
        self.write()
        self.interface(change=SEND, spec=wrapped)
        self.assertEqual(self.run_check("CH-0001")[0], 0)
        self.write()
        self.interface(change=SEND.replace(INVALID, ""), spec=wrapped)
        self.assertEqual(self.run_check("CH-0001")[0], 1)

    # The strict error form

    TOOL_ERRORS = ("  - errors:\n"
                   "    - `TOP_INVALID` · `error: --top needs a whole number greater than zero` · exit 2\n"
                   "    - no code · `usage: wordfreq [--top N] FILE` · exit 2\n"
                   "    - no code · `error: cannot read FILE` · exit 1\n")

    def tool(self, errors, name="`wordfreq [--top N] FILE`", kind="command"):
        return "- %s · %s · `wordfreq/cli.py`\n  - in: a path\n%s" % (name, kind, errors)

    def both(self, change_errors, spec_errors=None, **kw):
        self.write()
        self.interface(change=self.tool(change_errors, **kw),
                       spec=self.tool(self.TOOL_ERRORS if spec_errors is None else spec_errors, **kw))
        return self.run_check("CH-0001")

    def test_three_errors_pass_when_the_change_and_the_spec_agree(self):
        code, out = self.both(self.TOOL_ERRORS)
        self.assertEqual(code, 0, out)

    def test_a_different_message_is_one_problem_that_names_the_entry_and_the_field(self):
        code, out = self.both(self.TOOL_ERRORS.replace("greater than zero", "above zero"))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("\n  - "), 1, out)
        self.assertIn("`wordfreq [--top N] FILE`", out)
        self.assertIn("the message `error: --top needs a whole number above zero`", out)
        self.assertIn("CAP-email has `error: --top needs a whole number greater than zero`", out)

    def test_a_different_exit_is_one_problem_that_names_the_entry_and_the_field(self):
        code, out = self.both(self.TOOL_ERRORS.replace("cannot read FILE` · exit 1",
                                                       "cannot read FILE` · exit 3"))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("\n  - "), 1, out)
        self.assertIn("the result exit 3", out)
        self.assertIn("CAP-email has exit 1", out)

    def test_a_missing_error_is_one_problem(self):
        errors = "".join(self.TOOL_ERRORS.splitlines(True)[:-1])
        code, out = self.both(errors)
        self.assertEqual(code, 1)
        self.assertEqual(out.count("\n  - "), 1, out)
        self.assertIn("lacks the error", out)
        self.assertIn("error: cannot read FILE", out)

    def test_an_extra_error_is_one_problem(self):
        code, out = self.both(self.TOOL_ERRORS, "".join(self.TOOL_ERRORS.splitlines(True)[:-1]))
        self.assertEqual(code, 1)
        self.assertEqual(out.count("\n  - "), 1, out)
        self.assertIn("has the error", out)

    def test_errors_none_passes(self):
        code, out = self.both("  - errors: none\n", "  - errors: none\n")
        self.assertEqual(code, 0, out)

    def test_errors_none_with_prose_is_a_form_problem(self):
        prose = "  - errors: none. A wrong argument count gives a usage line.\n"
        code, out = self.both(prose, "  - errors: none\n")
        self.assertEqual(code, 1)
        self.assertIn("`wordfreq [--top N] FILE`", out)
        self.assertIn("not in the form", out)

    def test_errors_none_with_lines_under_it_is_a_form_problem(self):
        code, out = self.both("  - errors: none\n    - `TOP_INVALID` · `x` · exit 2\n",
                              "  - errors: none\n")
        self.assertEqual(code, 1)
        self.assertIn("not in the form", out)

    def test_the_old_form_is_a_form_problem_that_shows_the_new_form(self):
        code, out = self.both("  - errors: `TOP_INVALID`, `USAGE`\n")
        self.assertEqual(code, 1)
        self.assertIn("`wordfreq [--top N] FILE`", out)
        self.assertIn("old form", out)
        self.assertIn("- `CODE` · `exact message` · exit 2", out)

    def test_the_old_form_in_the_spec_is_a_form_problem_too(self):
        code, out = self.both(self.TOOL_ERRORS, "  - errors: `TOP_INVALID`, `USAGE`\n")
        self.assertEqual(code, 1)
        self.assertIn("CAP-email", out)
        self.assertIn("old form", out)

    def test_an_errors_line_with_no_items_is_a_form_problem(self):
        code, out = self.both("  - errors:\n", "  - errors:\n")
        self.assertEqual(code, 1)
        self.assertIn("no error lines", out)

    def test_an_item_that_is_not_in_the_form_is_a_form_problem(self):
        code, out = self.both("  - errors:\n    - `TOP_INVALID` · exit 2\n")
        self.assertEqual(code, 1)
        self.assertIn("not in the form", out)

    def test_a_result_that_is_not_exit_status_or_raises_is_a_form_problem(self):
        code, out = self.both("  - errors:\n    - `TOP_INVALID` · `x` · fails\n")
        self.assertEqual(code, 1)
        self.assertIn("not in the form", out)

    def test_no_code_passes_and_a_code_that_des_errors_lacks_fails(self):
        code, out = self.both(self.TOOL_ERRORS)
        self.assertEqual(code, 0, out)
        unknown = self.TOOL_ERRORS.replace("TOP_INVALID", "TOP_BOGUS")
        code, out = self.both(unknown, unknown)
        self.assertEqual(code, 1)
        self.assertIn("error code `TOP_BOGUS`, which is not a row of DES-errors", out)

    def test_status_for_a_route_and_raises_for_a_function_pass(self):
        route = ("  - errors:\n"
                 "    - `INVALID_ADDRESS` · `error: the email address is not valid` · status 400\n"
                 "    - no code · `not found` · status 404\n")
        code, out = self.both(route, route, name="`POST /reset`", kind="route")
        self.assertEqual(code, 0, out)
        func = ("  - errors:\n"
                "    - no code · no message · raises `KeyError`\n"
                "    - no code · `bad key` · raises KeyError\n")
        code, out = self.both(func, func, name="`lookup(key)`", kind="function")
        self.assertEqual(code, 0, out)

    def test_a_message_with_a_backtick_uses_a_double_backtick_span(self):
        errors = "  - errors:\n    - `TOP_INVALID` · ``error: use `--top 3` here`` · exit 2\n"
        code, out = self.both(errors, errors)
        self.assertEqual(code, 0, out)
        code, out = self.both(errors, errors.replace("use `--top 3` here", "use `--top 4` here"))
        self.assertEqual(code, 1)

    def test_the_legacy_skips_still_return_no_problem(self):
        old = "  - errors: `TOP_INVALID`, `USAGE`\n"
        self.write()
        self.interface(change=self.tool(old))  # the scope spec has no Interface heading
        self.assertEqual(self.run_check("CH-0001")[0], 0)
        self.write()
        path = self.change / "change.md"
        path.write_text(path.read_text().replace("Scope: CAP-email", "Scope: DES-errors"))
        self.interface(change=self.tool(old))  # no candidate spec has an Interface heading
        self.assertEqual(self.run_check("CH-0001")[0], 0)

    def test_skips_the_check_when_no_candidate_spec_has_an_interface_section(self):
        self.write()
        path = self.change / "change.md"
        path.write_text(path.read_text().replace("Scope: CAP-email", "Scope: DES-errors"))
        self.interface(change=SEND)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

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

    # A hash lock keeps its tests review

    def test_a_hash_lock_still_needs_its_tests_review(self):
        _, new = self.relocked_repo()
        self.reviewed_lock(new)
        (self.change / "review/tests/result.md").unlink()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("tests review has no result", out)

    def test_a_hash_lock_after_an_acceptance_lock_needs_its_tests_review(self):
        _, new = self.relocked_repo()
        self.write(checks="- test/email.test.js",
                   lock="Tests-Locked: acceptance\nTests-Locked: %s\n" % new)
        self.reviewed_lock(new)
        (self.change / "review/tests/result.md").unlink()
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("tests review has no result", out)

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


# The acceptance checks of the intent

ACCEPTANCE_FILE = "acceptance/IN-0002.acceptance.js"
ACCEPTANCE_REVIEW = "pdlc/acceptance/IN-0002-password-reset/review/tests"

ACCEPTED_INTENT = """# IN-0002 · Password reset

Status: building · Ticket: none · Branch: pdlc/IN-0002-password-reset · Added: 2026-10-10

## Requirements

- CAP-email.R1 · Send plain email
- CAP-email.R2 · Send from a template

## Changes

{changes}

## Acceptance checks

Acceptance-File: {file}
Acceptance-Locked: {lock}
Acceptance-Passed: {passed}

The acceptance stage writes the file and the lock. Verify of the last change writes the pass.
"""

ACCEPTANCE_WRONG = ("Wrong versions:\n"
                    "- IN-0002 CAP-email.R2 sends from a template · sends no email · fails\n")


class AcceptanceGate(unittest.TestCase):
    """A change merges only when the acceptance checks of its intent are locked, reviewed at
    the lock, and recorded as passing at the top of the stack of the intent."""

    INTENT_BRANCH = "pdlc/IN-0002-password-reset"
    FIRST = "pdlc/CH-0001-email-templates"
    SECOND = "pdlc/CH-0002-send-reset"
    THIRD = "pdlc/CH-0003-show-all"
    NAMES = {"CH-0001": "CH-0001-email-templates", "CH-0002": "CH-0002-send-reset",
             "CH-0003": "CH-0003-show-all"}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, path, text):
        (self.root / path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / path).write_text(text)

    def commit(self, message):
        git(self.root, "add", "-A")
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", message)
        return git(self.root, "rev-parse", "HEAD")

    def intent(self, lock="none", passed="none", file=ACCEPTANCE_FILE):
        changes = "\n".join("- %s · %s" % (c, self.NAMES[c].split("-", 2)[2]) for c in self.changes)
        self.put("pdlc/inbox/IN-0002-password-reset.md", ACCEPTED_INTENT.format(
            changes=changes, file=file, lock=lock, passed=passed))

    def review(self, lock, result="pass", wrong=ACCEPTANCE_WRONG):
        self.put(ACCEPTANCE_REVIEW + "/packet.md",
                 "# Review packet · IN-0002-password-reset · tests\n\nAcceptance-Locked: %s\n" % lock)
        self.put(ACCEPTANCE_REVIEW + "/result.md", "Result: %s\n\nProblems: none\n\n%s" % (result, wrong))

    def change(self, change, status, branch, reqs, lock="", tests_review=True, checks="none",
               base="main"):
        """A change spec. A change with "Tests-Locked: acceptance" has no tests review of its
        own, so a test passes tests_review=False for it."""
        folder = "pdlc/changes/%s" % self.NAMES[change]
        self.put(folder + "/change.md", CHANGE.format(status=status, reqs=reqs, branch=branch,
                                                      lock=lock, checks=checks)
                 .replace("# CH-0001 · Email templates", "# %s · %s" % (change, self.NAMES[change]))
                 .replace("Base: main", "Base: %s" % base))
        if tests_review:
            self.put(folder + "/review/tests/result.md", "Result: pass\n\nProblems: none\n")

    def start(self, changes=("CH-0001",)):
        """main with the plan, then the intent branch with the acceptance checks, locked and
        reviewed. Returns the lock."""
        self.changes = list(changes)
        self.put("pdlc/config.md", CONFIG.format(remits="tests"))
        self.put("pdlc/specs/capabilities/CAP-email.md", CAPABILITY.format(r1="ready", r2="ready"))
        self.put("src/email.js", "// sends email\n")
        for change in self.changes:
            self.change(change, "planned", "none", "### CAP-email.R2 · Send from a template",
                        tests_review=False)
        self.intent()
        git(self.root, "init", "-q", "-b", "main")
        self.commit("Plan IN-0002")
        git(self.root, "switch", "-qc", self.INTENT_BRANCH)
        self.put(ACCEPTANCE_FILE, "test('IN-0002 CAP-email.R2 sends from a template', () => {})\n")
        lock = self.commit("Acceptance IN-0002")
        self.intent(lock=lock)
        self.commit("Lock acceptance IN-0002")
        self.review(lock)
        self.commit("Review acceptance IN-0002")
        self.lock = lock
        return lock

    def build(self, change, branch, start, reqs, r1="ready", r2="verified", **options):
        """The change on its own branch, in review, with its code. The options go to change()."""
        git(self.root, "switch", "-qc", branch, start)
        self.change(change, "in review", branch, reqs, **options)
        self.put("pdlc/specs/capabilities/CAP-email.md", CAPABILITY.format(r1=r1, r2=r2))
        self.put("src/email.js", (self.root / "src/email.js").read_text() + "// %s\n" % change)
        return self.commit("Build " + change)

    def build_first(self, **options):
        return self.build("CH-0001", self.FIRST, self.INTENT_BRANCH,
                          "### CAP-email.R2 · Send from a template", **options)

    def record_pass(self, sha=None):
        sha = sha or git(self.root, "rev-parse", "HEAD")
        self.intent(lock=self.lock, passed=sha)
        self.commit("Verified")
        return sha

    def run_check(self, change="CH-0001"):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_merge.main(["check_merge.py", change], root=self.root)
        return code, out.getvalue()

    def test_passes_when_the_acceptance_checks_are_locked_reviewed_and_passed(self):
        self.start()
        self.build_first()
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_fails_when_the_acceptance_checks_are_not_locked(self):
        self.start()
        self.build_first()
        self.intent(lock="none")
        self.commit("lock removed")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance checks of IN-0002 are not locked", out)

    def test_fails_when_the_acceptance_review_is_of_an_older_lock(self):
        self.start()
        self.build_first()
        self.review(git(self.root, "rev-parse", "main"))
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance review of IN-0002 is not of the current lock %s" % self.lock, out)

    def test_fails_when_the_acceptance_review_did_not_pass(self):
        self.start()
        self.build_first()
        self.review(self.lock, result="fail")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance review of IN-0002 did not pass", out)

    def test_fails_when_the_acceptance_review_has_no_result(self):
        self.start()
        self.build_first()
        (self.root / ACCEPTANCE_REVIEW / "result.md").unlink()
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance review of IN-0002 has no result", out)
        self.assertIn("python3 pdlc/bin/make_packets.py IN-0002", out)

    def test_fails_when_the_acceptance_review_lists_no_wrong_versions(self):
        self.start()
        self.build_first()
        self.review(self.lock, wrong="Wrong versions:\n- none\n")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('acceptance review of IN-0002 lists no "Wrong versions"', out)

    def test_fails_when_an_acceptance_check_passes_a_wrong_version(self):
        self.start()
        self.build_first()
        self.review(self.lock, wrong="Wrong versions:\n- IN-0002 CAP-email.R2 · any email · passes\n")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance review of IN-0002: a check passes a wrong version", out)

    def test_fails_when_the_acceptance_file_changed_after_the_lock(self):
        self.start()
        self.build_first()
        self.put(ACCEPTANCE_FILE, "test('IN-0002 CAP-email.R2 weakened', () => {})\n")
        self.commit("weaken")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("changed after the acceptance checks were locked: %s" % ACCEPTANCE_FILE, out)

    def test_fails_until_the_acceptance_checks_passed_at_the_top_of_the_stack(self):
        self.start()
        self.build_first()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance checks of IN-0002 are not ready: no Acceptance-Passed at the top "
                      "of the stack (CH-0001)", out)

    def test_fails_when_app_files_changed_after_the_acceptance_checks_passed(self):
        self.start()
        self.build_first()
        self.record_pass()
        self.put("src/email.js", "// changed after the pass\n")
        self.commit("late change")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("files changed after the acceptance checks of IN-0002 passed: src/email.js", out)

    def test_pdlc_records_can_change_after_the_acceptance_checks_passed(self):
        self.start()
        self.build_first()
        self.record_pass()
        self.put("pdlc/changes/CH-0001-email-templates/handoff.md", "# Handoff\n")
        self.commit("Propose CH-0001")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_fails_when_the_pass_is_older_than_the_lock(self):
        self.start()
        self.build_first()
        passed = self.record_pass()
        self.put(ACCEPTANCE_FILE, "test('IN-0002 CAP-email.R2 corrected', () => {})\n")
        self.lock = self.commit("Acceptance IN-0002")
        self.intent(lock=self.lock, passed=passed)
        self.review(self.lock)
        self.commit("Lock acceptance IN-0002")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Acceptance-Passed %s of IN-0002 does not come after its lock" % passed, out)

    def test_in_ci_the_top_is_read_from_its_branch_and_not_from_a_merge_with_main(self):
        self.start()
        self.build_first()
        self.record_pass()
        git(self.root, "switch", "-q", "main")
        self.put("src/other.js", "// another intent merged\n")
        self.commit("work of another intent on main")
        git(self.root, "switch", "-q", "--detach", self.FIRST)
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "merge", "-q", "--no-ff",
            "-m", "the merge commit that CI checks out", "main")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def stack(self, passed):
        """CH-0001 in review, and CH-0002 in review on top of it. The pass is on CH-0002 only."""
        self.start(changes=("CH-0001", "CH-0002"))
        self.build_first()
        self.build("CH-0002", self.SECOND, self.FIRST, "### CAP-email.R1 · Send plain email",
                   r1="verified")
        if passed:
            self.record_pass()
        git(self.root, "switch", "-q", self.FIRST)

    def test_a_lower_change_reads_the_pass_at_the_top_of_the_stack(self):
        self.stack(passed=True)
        self.assertIn("Acceptance-Passed: none",
                      (self.root / "pdlc/inbox/IN-0002-password-reset.md").read_text())
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 0, out)

    def out_of_order_stack(self, passed=True):
        """CH-0001, then CH-0003 on top of it, then CH-0002 on top of that. The branch of
        CH-0001 still lists the changes in number order. The list is right only on the top
        branch, which also holds the pass."""
        self.start(changes=("CH-0001", "CH-0002", "CH-0003"))
        self.build_first(base=self.INTENT_BRANCH)
        self.build("CH-0003", self.THIRD, self.FIRST, "### CAP-email.R1 · Send plain email",
                   r1="verified", base=self.FIRST)
        self.build("CH-0002", self.SECOND, self.THIRD, "### CAP-email.R1 · Send plain email",
                   r1="verified", base=self.THIRD)
        self.changes = ["CH-0001", "CH-0003", "CH-0002"]
        if passed:
            self.record_pass()
        git(self.root, "switch", "-q", self.FIRST)

    def test_the_top_of_the_stack_follows_the_base_links_not_the_number_order(self):
        self.out_of_order_stack()
        listed = (self.root / "pdlc/inbox/IN-0002-password-reset.md").read_text()
        self.assertLess(listed.index("CH-0002"), listed.index("CH-0003"))  # the stale list
        for change in ("CH-0001", "CH-0003"):
            git(self.root, "switch", "-q", {"CH-0001": self.FIRST, "CH-0003": self.THIRD}[change])
            code, out = self.run_check(change)
            self.assertEqual(code, 0, out)

    def test_an_out_of_order_stack_is_not_ready_until_its_top_passed(self):
        self.out_of_order_stack(passed=False)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("no Acceptance-Passed at the top of the stack (CH-0002)", out)

    def test_a_lower_change_is_not_ready_until_the_top_of_the_stack_passed(self):
        self.stack(passed=False)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("acceptance checks of IN-0002 are not ready: no Acceptance-Passed at the top "
                      "of the stack (CH-0002)", out)

    def test_a_change_that_only_retires_needs_no_acceptance_checks(self):
        self.start()
        git(self.root, "switch", "-qc", self.FIRST, self.INTENT_BRANCH)
        self.change("CH-0001", "in review", self.FIRST, "### CAP-email.R7 · Old thing (retire)")
        self.intent(lock="none", file="none")
        self.commit("Verified")
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    # Tests-Locked: acceptance. The acceptance checks are also the checks of the only change.

    BY_ACCEPTANCE = {"lock": "Tests-Locked: acceptance\n", "tests_review": False}

    def test_the_only_change_can_use_the_acceptance_checks(self):
        self.start()
        self.build_first(**self.BY_ACCEPTANCE)
        self.record_pass()
        self.assertFalse((self.root / "pdlc/changes/CH-0001-email-templates/review/tests").exists())
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_tests_locked_acceptance_fails_for_an_intent_with_two_changes(self):
        self.start(changes=("CH-0001", "CH-0002"))
        self.build_first(**self.BY_ACCEPTANCE)
        self.build("CH-0002", self.SECOND, self.FIRST, "### CAP-email.R1 · Send plain email",
                   r1="verified")
        self.record_pass()
        git(self.root, "switch", "-q", self.FIRST)
        code, out = self.run_check("CH-0001")
        self.assertEqual(code, 1)
        self.assertIn("Tests-Locked: acceptance is only for the only change of an intent. "
                      "IN-0002 lists CH-0001, CH-0002. Run /pdlc:tests", out)

    def test_tests_locked_acceptance_fails_with_check_files(self):
        self.start()
        self.build_first(lock="Tests-Locked: acceptance\n", tests_review=False,
                         checks="- test/email.test.js")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('Tests-Locked: acceptance needs "- none" under "Check files"', out)
        self.assertNotIn("tests are not locked", out)

    def test_tests_locked_acceptance_needs_an_acceptance_lock(self):
        self.start()
        self.build_first(**self.BY_ACCEPTANCE)
        self.intent(lock="none")
        self.commit("lock removed")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("Tests-Locked: acceptance needs the acceptance checks of IN-0002 locked", out)

    def test_tests_locked_acceptance_still_needs_a_passed_acceptance_review(self):
        self.start()
        self.build_first(**self.BY_ACCEPTANCE)
        self.review(self.lock, result="fail")
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("acceptance review of IN-0002 did not pass", out)

    def test_tests_locked_acceptance_still_needs_the_acceptance_pass_at_the_top(self):
        self.start()
        self.build_first(**self.BY_ACCEPTANCE)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("no Acceptance-Passed at the top of the stack (CH-0001)", out)

    def test_a_tests_review_result_is_not_needed_but_the_other_remits_are(self):
        self.start()
        self.put("pdlc/config.md", CONFIG.format(remits="tests, specification"))
        self.build_first(**self.BY_ACCEPTANCE)
        self.record_pass()
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("specification review has no result", out)
        self.assertNotIn("tests review has no result", out)


if __name__ == "__main__":
    unittest.main()
