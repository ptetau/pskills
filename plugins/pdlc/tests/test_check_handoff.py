"""Tests for pdlc's handoff check. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/check_handoff.py"
spec = importlib.util.spec_from_file_location("check_handoff", SCRIPT)
check_handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_handoff)

TIME = "2026-11-01T10:00:00+13:00"

JOB = """# JOB-x · Do a thing

Status: active

## Interface

- `GET /a` · route · `app.py`
  - errors: `E1`{iface}

## Requirements

### JOB-x.R1 · One

Status: built · Intents: IN-0001

Show the page.{r1}

### JOB-x.R2 · Two

Status: proposed · Intents: IN-0001

Show at most 20 items{r2}. Then stop.

### JOB-x.R3 · Three

Status: proposed · Intents: IN-0001

Sort by name{r3}.

### JOB-x.R4 · Four

Status: proposed · Intents: IN-0001

Sort by date{r4}.
"""

ERRORS = """# DES-errors · Errors

Status: agreed · Default: yes

## Rule

| Code | Message |
|---|---|
| E1 | Bad input |{row}
"""

SECTIONS = ["Done", "Decided on defaults", "Open", "Look here", "Don't redo",
            "Next: do this first"]

L2 = "- JOB-x.R2: how many items? → 20 (assumed)"
L2B = "- JOB-x.R2: where is the limit shown? → on the page (assumed)"
LE = "- DES-errors: what is the message of E1? → Bad input (assumed)"
L3 = "- JOB-x.R3: how to sort? → by name (assumed)"
L4 = "- JOB-x.R4: how to sort? → by date (assumed)"


def job(iface="", r1="", r2="", r3="", r4=""):
    return JOB.format(iface=iface, r1=r1, r2=r2, r3=r3, r4=r4)


def handoff(id_, decided, stage="intake", next_="ready", title=None, time=True,
            drop=None, level="###", head="Handoff"):
    """The handoff text: title, time, and the six sections."""
    lines = [title or "%s · %s · %s → %s" % (head, id_, stage, next_), ""]
    if time:
        lines += ["Time: " + TIME, ""]
    for name in SECTIONS:
        if name == drop:
            continue
        lines += ["%s %s" % (level, name), ""]
        if name == "Decided on defaults":
            lines += decided
        else:
            lines += ["- none"]
        lines += [""]
    return "\n".join(lines)


def intent(decided, notes=None, **kw):
    notes = [d for d in decided if d != "- none"] if notes is None else notes
    return ("# IN-0001 · Thing\n\nStatus: specifying\n\n## Notes\n\n" + "\n".join(notes)
            + "\n\n## Handoff\n\n" + handoff("IN-0001", decided, **kw))


class HandoffCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.git("init", "-q")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                       cwd=self.root, check=True, capture_output=True)

    def put(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def start(self, job_text=None, errors=None):
        """Commit the specs as they are on HEAD."""
        self.put("pdlc/specs/jobs/JOB-x.md", job_text or job())
        self.put("pdlc/specs/design/DES-errors.md", errors or ERRORS.format(row=""))
        self.put("pdlc/inbox/IN-0001-thing.md", "# IN-0001 · Thing\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "start")

    def run_check(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_handoff.main(["check_handoff.py", *args], root=self.root)
        return code, out.getvalue()

    def intake(self, decided, **kw):
        self.put("pdlc/inbox/IN-0001-thing.md", intent(decided, **kw))
        return self.run_check("IN-0001", "--stage", "intake")

    def test_a_correct_intake_handoff_passes(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md",
                 job(r2=" (assumed)", r3=" (assumed)", r4=" (assumed)").replace(
                     "Then stop.", "Then stop (assumed)."))
        self.put("pdlc/specs/design/DES-errors.md", ERRORS.format(row=" E2 | Worse (assumed) |"))
        code, out = self.intake([L2, L3, L4, LE])
        self.assertEqual((code, out), (0, ""))

    def test_two_marks_in_one_requirement_and_one_in_a_design_spec_pass(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r2=" (assumed)").replace(
            "Then stop.", "Then stop (assumed)."))
        self.put("pdlc/specs/design/DES-errors.md", ERRORS.format(row=" E2 | Worse (assumed) |"))
        code, out = self.intake([L2, L2B, LE])
        self.assertEqual((code, out), (0, ""))

    def test_a_pointer_line_fails(self):
        self.start()
        for line in ("- see Notes", "- listed in the intent Notes"):
            code, out = self.intake([line])
            self.assertEqual(code, 1)
            self.assertIn("Decided on defaults", out)
            self.assertIn(line, out)

    def test_a_line_with_no_arrow_or_no_mark_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake(["- JOB-x.R3: how to sort? by name (assumed)"])
        self.assertEqual(code, 1)
        self.assertIn("form", out)
        code, out = self.intake(["- JOB-x.R3: how to sort? → by name"])
        self.assertEqual(code, 1)
        self.assertIn("form", out)

    def test_a_new_mark_with_no_line_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r2=" (assumed)", r3=" (assumed)"))
        code, out = self.intake([L2])
        self.assertEqual(code, 1)
        self.assertIn("JOB-x.R3", out)
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_a_line_with_no_new_mark_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake([L3, L4])
        self.assertEqual(code, 1)
        self.assertIn("JOB-x.R4", out)
        self.assertNotIn("JOB-x.R3", out)

    def test_none_fails_with_a_new_mark_and_passes_without_one(self):
        self.start()
        code, out = self.intake(["- none"])
        self.assertEqual((code, out), (0, ""))
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake(["- none"])
        self.assertEqual(code, 1)
        self.assertIn("JOB-x.R3", out)

    def test_a_mark_that_was_on_head_is_not_new(self):
        self.start(job(r3=" (assumed)"))
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)", r4=" (assumed)"))
        code, out = self.intake([L4])
        self.assertEqual((code, out), (0, ""))
        code, out = self.intake([L3, L4])
        self.assertEqual(code, 1)
        self.assertIn("JOB-x.R3", out)

    def test_a_mark_in_the_interface_belongs_to_the_spec(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(iface=" (assumed)"))
        code, out = self.intake(["- none"])
        self.assertEqual(code, 1)
        self.assertIn("JOB-x", out)
        code, out = self.intake(["- JOB-x.R1: what is the error? → E1 (assumed)"])
        self.assertEqual((code, out), (0, ""))

    def test_a_bad_title_time_or_section_fails(self):
        self.start()
        bad = [
            dict(title="Hand-off · IN-0001 · intake → ready"),
            dict(next_="change"),
            dict(stage="ready", next_="change"),
            dict(title="Handoff · IN-0002 · intake → ready"),
            dict(time=False),
            dict(drop="Look here"),
        ]
        for kw in bad:
            code, out = self.intake(["- none"], **kw)
            self.assertEqual(code, 1, kw)
            self.assertTrue(out.strip(), kw)
        code, out = self.intake(["- none"], next_="user")
        self.assertEqual((code, out), (0, ""))
        code, out = self.intake(["- none"], head="# Handoff")
        self.assertEqual((code, out), (0, ""))
        code, out = self.intake(["- none"], title="### Handoff · IN-0001 (thing) · intake → ready")
        self.assertEqual((code, out), (0, ""))

    def test_a_time_that_is_not_a_time_fails(self):
        self.start()
        text = intent(["- none"]).replace("Time: " + TIME, "Time: tomorrow")
        self.put("pdlc/inbox/IN-0001-thing.md", text)
        code, out = self.run_check("IN-0001", "--stage", "intake")
        self.assertEqual(code, 1)
        self.assertIn("Time:", out)

    def test_none_with_another_line_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake(["- none", L3])
        self.assertEqual(code, 1)
        self.assertIn("only line", out)

    def test_a_line_with_two_arrows_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake(["- JOB-x.R3: how to sort? → by name → or date (assumed)"])
        self.assertEqual(code, 1)
        self.assertIn("form", out)

    def test_a_changed_earlier_sentence_does_not_make_the_mark_new(self):
        self.start(job(r3=" (assumed)").replace("Sort by name", "One. Sort by name"))
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)").replace(
            "Sort by name", "Two. Sort by name"))
        code, out = self.intake(["- none"])
        self.assertEqual((code, out), (0, ""))

    def test_all_sections_missing_gives_one_line(self):
        self.start()
        text = "# IN-0001 · Thing\n\n## Notes\n\n## Handoff\n\nHandoff · IN-0001 · intake → ready\n\nTime: %s\n" % TIME
        self.put("pdlc/inbox/IN-0001-thing.md", text)
        code, out = self.run_check("IN-0001", "--stage", "intake")
        self.assertEqual(code, 1)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("`###` headings under `## Handoff`", out)

    def test_a_new_assumed_line_in_the_notes_must_be_in_decided_on_defaults(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        extra = "- JOB-x.R4: other? → yes (assumed)"
        code, out = self.intake([L3], notes=[L3, extra])
        self.assertEqual(code, 1)
        self.assertIn("this (assumed) line of the Notes is not in Decided on defaults: " + extra, out)
        # A line that was on HEAD already is not new.
        self.put("pdlc/inbox/IN-0001-thing.md", "# IN-0001 · Thing\n\n## Notes\n\n%s\n" % extra)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "notes")
        code, out = self.intake(["- none"], notes=[extra])
        self.assertEqual((code, out), (0, ""))

    def test_a_notes_line_with_the_same_id_is_named(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        note = "- JOB-x.R3: how to sort? → by name, then date (assumed)"
        code, out = self.intake([L3], notes=[note])
        self.assertEqual(code, 1)
        self.assertIn("Notes line with this ID: " + note, out)

    def test_the_sections_must_be_in_the_template_order(self):
        self.start()
        text = intent(["- none"])
        text = text.replace("### Open", "### XOpen").replace("### Look here", "### Open")
        text = text.replace("### XOpen", "### Look here")
        self.put("pdlc/inbox/IN-0001-thing.md", text)
        code, out = self.run_check("IN-0001", "--stage", "intake")
        self.assertEqual(code, 1)
        self.assertIn("order", out)

    def test_a_line_that_is_not_in_the_notes_fails(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        code, out = self.intake([L3], notes=["- JOB-x.R3: other → words (assumed)"])
        self.assertEqual(code, 1)
        self.assertIn("Notes", out)

    def test_a_change_handoff_is_read_for_a_ch_id(self):
        self.start()
        self.put("pdlc/specs/jobs/JOB-x.md", job(r3=" (assumed)"))
        path = "pdlc/changes/CH-0001-thing/handoff.md"
        self.put(path, handoff("CH-0001", [L3], stage="build", next_="verify", level="##"))
        code, out = self.run_check("CH-0001", "--stage", "build")
        self.assertEqual((code, out), (0, ""))
        self.put(path, handoff("CH-0001", ["- none"], stage="build", next_="verify", level="##"))
        code, out = self.run_check("CH-0001", "--stage", "build")
        self.assertEqual(code, 1)
        self.assertIn("JOB-x.R3", out)

    def test_exit_zero_prints_nothing_and_exit_one_prints_a_line_for_each_problem(self):
        self.start()
        code, out = self.intake(["- none"])
        self.assertEqual((code, out), (0, ""))
        self.put("pdlc/specs/jobs/JOB-x.md", job(r2=" (assumed)", r3=" (assumed)"))
        code, out = self.intake(["- none"], time=False, drop="Open")
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 4, out)
        self.assertTrue(all(line.strip() for line in lines))

    def test_a_missing_handoff_fails(self):
        self.start()
        code, out = self.run_check("IN-0001", "--stage", "intake")
        self.assertEqual(code, 1)
        self.assertIn("Handoff", out)


if __name__ == "__main__":
    unittest.main()
