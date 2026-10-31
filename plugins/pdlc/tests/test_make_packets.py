"""Tests for pdlc's review packet builder. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/make_packets.py"
spec = importlib.util.spec_from_file_location("make_packets", SCRIPT)
make_packets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_packets)

CHANGE = """# CH-0001 · Spanish greeting

Intent: IN-0001 · Scope: CAP-greeting · Status: building · Ticket: none · Branch: pdlc/CH-0001-es · Base: main

## Requirements

### CAP-greeting.R2 · Greets in Spanish

- Given lang es, when greeting Ana, then the text is "Hola, Ana!"

## Relies on

- DES-writing-style

## Interface

- `greet(name, lang)` in `src/greet.js`

## Files

- src/greet.js

## Check files

- test/greet.test.js
"""


def git(root, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                   check=True, capture_output=True)


class PacketRepo(unittest.TestCase):
    """A change branch with a check and code, ready for packets."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        for path, text in {
            "pdlc/config.md": "## Reviews\n\n- remits: tests, specification, security\n",
            "pdlc/reviews/tests.md": "# Remit: tests\nJudge the checks.\n",
            "pdlc/reviews/specification.md": "# Remit: specification\nJudge the spec.\n",
            "pdlc/reviews/security.md": "# Remit: security\nJudge safety.\n",
            "pdlc/specs/capabilities/CAP-greeting.md":
                "# CAP-greeting · Greets in English\n\nStatus: active\n\n## What it is for\n\n"
                "Greets people in English only.\n\n## Requirements\n\n### CAP-greeting.R2 · Greets in Spanish\n\n"
                "Status: built · Intents: IN-0001\n\nSays hola.\n\n### CAP-greeting.R3 · Other\n\nNot this one.\n",
            "pdlc/specs/design/DES-writing-style.md": "# DES-writing-style\nWrite plainly.\n",
            "src/greet.js": "export const greet = (n) => `Hello, ${n}!`;\n",
            "README.md": "# Greeter\n\nThe greeter has one behavior.\n",
            "test/greet.test.js": "// old test\n",
        }.items():
            (r / path).parent.mkdir(parents=True, exist_ok=True)
            (r / path).write_text(text)
        git(r, "init", "-q", "-b", "main"); git(r, "add", "-A"); git(r, "commit", "-qm", "base")
        git(r, "switch", "-q", "-c", "pdlc/CH-0001-es")
        self.folder = r / "pdlc/changes/CH-0001-es"
        self.folder.mkdir(parents=True)
        (self.folder / "change.md").write_text(CHANGE)
        (self.folder / "frames").mkdir()
        (self.folder / "frames/01.png").write_bytes(b"png")
        (r / "test/greet.test.js").write_text("test('CAP-greeting.R2 hola', () => {}) // SECRET-TEST\n")
        (r / "src/greet.js").write_text("export const greet = (n, l) => l === 'es' ? `Hola, ${n}!` : `Hello, ${n}!`; // SECRET-CODE\n")
        git(r, "add", "-A"); git(r, "commit", "-qm", "work")

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, remit):
        return (self.folder / "review" / remit / "packet.md").read_text()


class Packets(PacketRepo):
    def test_makes_one_packet_per_configured_remit(self):
        self.assertEqual(make_packets.main(["x", "CH-0001"], root=self.root), 0)
        made = sorted(p.name for p in (self.folder / "review").iterdir())
        self.assertEqual(made, ["security", "specification", "tests"])

    def test_every_packet_has_its_remit_and_the_spec(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        for remit in ["tests", "specification", "security"]:
            text = self.packet(remit)
            self.assertIn("# Remit: %s" % remit, text)
            self.assertIn("Given lang es", text)
            self.assertIn("Says hola.", text)
            self.assertNotIn("Not this one.", text)

    def test_only_the_specification_packet_has_the_writing_rules(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        self.assertIn("Write plainly.", self.packet("specification"))
        self.assertNotIn("Write plainly.", self.packet("tests"))
        self.assertNotIn("Write plainly.", self.packet("security"))

    def test_every_packet_has_the_title_and_summary_of_the_spec_it_covers(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        for remit in ["tests", "specification", "security"]:
            text = self.packet(remit)
            self.assertIn("# CAP-greeting · Greets in English", text)
            self.assertIn("Greets people in English only.", text)
            self.assertEqual(text.count("Says hola."), 1)

    def test_tests_packet_has_the_tests_and_no_code(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        text = self.packet("tests")
        self.assertIn("SECRET-TEST", text)
        self.assertNotIn("SECRET-CODE", text)

    def test_code_packets_have_the_code_and_no_tests(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        for remit in ["specification", "security"]:
            text = self.packet(remit)
            self.assertIn("SECRET-CODE", text)
            self.assertNotIn("SECRET-TEST", text)

    def test_only_the_specification_packet_points_to_the_frames(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        self.assertIn("frames/01.png", self.packet("specification"))
        self.assertNotIn("frames/01.png", self.packet("security"))

    def test_only_the_specification_packet_has_the_writing_check(self):
        make_packets.main(["x", "CH-0001"], root=self.root)
        text = self.packet("specification")
        self.assertIn("## Writing check", text)
        self.assertIn("pdlc/changes/CH-0001-es/change.md", text)
        self.assertIn("No findings.", text)
        self.assertNotIn("## Writing check", self.packet("security"))
        self.assertNotIn("## Writing check", self.packet("tests"))

    def test_the_writing_check_covers_the_text_this_change_wrote(self):
        r = self.root
        (r / "README.md").write_text((r / "README.md").read_text() + "It picks a color.\n")
        (self.folder / "change.md").write_text(CHANGE + "\nThe greeting box is gray.\n")
        (self.folder / "handoff.md").write_text("The center of the handoff.\n")
        git(r, "add", "-A"); git(r, "commit", "-qm", "more")
        make_packets.main(["x", "CH-0001"], root=self.root)
        text = self.packet("specification")
        self.assertIn('README.md:4 · NZ spelling · "color" is US spelling · write "colour"', text)
        self.assertIn('change.md:27 · NZ spelling · "gray" is US spelling · write "grey"', text)
        self.assertNotIn("behaviour", text)
        self.assertNotIn("centre", text)

    def test_compliance_gets_a_pass_result_and_no_packet_when_it_does_not_apply(self):
        (self.root / "pdlc/reviews/compliance.md").write_text("# Remit: compliance\n\n- Rules: none listed yet.\n")
        make_packets.main(["x", "CH-0001", "compliance"], root=self.root)
        folder = self.folder / "review/compliance"
        self.assertFalse((folder / "packet.md").exists())
        self.assertIn("Result: pass", (folder / "result.md").read_text())

    def test_compliance_gets_a_packet_when_a_dependency_file_changed(self):
        (self.root / "pdlc/reviews/compliance.md").write_text("# Remit: compliance\n\n- Rules: none listed yet.\n")
        (self.root / "requirements.txt").write_text("requests==2.32.0\n")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "dependency")
        make_packets.main(["x", "CH-0001", "compliance"], root=self.root)
        self.assertIn("requests==2.32.0", self.packet("compliance"))

    def test_compliance_gets_a_packet_when_the_project_lists_rules(self):
        (self.root / "pdlc/reviews/compliance.md").write_text("# Remit: compliance\n\n- Rules: keep a record of each processing activity.\n")
        make_packets.main(["x", "CH-0001", "compliance"], root=self.root)
        self.assertIn("# Remit: compliance", self.packet("compliance"))

    def test_reads_the_scope_and_the_base_in_backticks_or_with_a_name(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace("Scope: CAP-greeting", "Scope: `CAP-greeting`")
                          .replace("Base: main", "Base: `main` (the default branch)"))
        self.assertEqual(make_packets.main(["x", "CH-0001", "security"], root=self.root), 0)
        self.assertIn("Greets people in English only.", self.packet("security"))

    def test_verify_makes_every_configured_remit_except_tests(self):
        (self.root / "pdlc/config.md").write_text(
            "## Reviews\n\n- remits: tests, specification, security, compliance\n")
        (self.root / "pdlc/reviews/compliance.md").write_text("# Remit: compliance\n\n- Rules: none listed yet.\n")
        self.assertEqual(make_packets.main(["x", "CH-0001", "--verify"], root=self.root), 0)
        made = sorted(p.name for p in (self.folder / "review").iterdir())
        self.assertEqual(made, ["compliance", "security", "specification"])
        self.assertIn("Result: pass", (self.folder / "review/compliance/result.md").read_text())
        self.assertTrue((self.folder / "review/security/packet.md").exists())

    def test_a_missing_base_branch_stops_instead_of_sending_empty_packets(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace("Base: main", "Base: no-such-branch"))
        self.assertEqual(make_packets.main(["x", "CH-0001"], root=self.root), 1)
        self.assertFalse((self.folder / "review").exists())

    def test_can_make_a_single_remit(self):
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertEqual([p.name for p in (self.folder / "review").iterdir()], ["tests"])

    def test_a_change_with_tests_locked_acceptance_gets_no_tests_packet(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace(
            "\n## Requirements", "Tests-Locked: acceptance\n\n## Requirements", 1)
            .replace("## Check files\n\n- test/greet.test.js", "## Check files\n\n- none"))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(make_packets.main(["x", "CH-0001"], root=self.root), 0)
        made = sorted(p.name for p in (self.folder / "review").iterdir())
        self.assertEqual(made, ["security", "specification"])
        self.assertIn("CH-0001 uses the acceptance checks of its intent (Tests-Locked: acceptance). "
                      "Their packet comes from python3 pdlc/bin/make_packets.py IN-0001.", out.getvalue())

    def test_a_tests_remit_that_the_user_names_is_left_out_for_tests_locked_acceptance(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace(
            "\n## Requirements", "Tests-Locked: acceptance\n\n## Requirements", 1))
        with redirect_stdout(io.StringIO()):
            make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertFalse((self.folder / "review").exists())

    def test_a_hash_lock_still_gets_a_tests_packet(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace(
            "\n## Requirements", "Tests-Locked: acceptance\nTests-Locked: abcdef1\n\n## Requirements", 1))
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertTrue((self.folder / "review/tests/packet.md").exists())

    def test_a_new_packet_removes_the_old_result(self):
        old = self.folder / "review/tests/result.md"
        old.parent.mkdir(parents=True)
        old.write_text("Result: pass\n")
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertFalse(old.exists())
        self.assertTrue((self.folder / "review/tests/packet.md").exists())


def head(root):
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                          text=True, check=True).stdout.strip()


class ReReview(PacketRepo):
    """A second review of a remit for the same change judges only what changed."""

    def lock(self):
        """Lock the checks as they are now: commit, and copy the hash into the change spec."""
        sha = head(self.root)
        change = self.folder / "change.md"
        lines = [l for l in change.read_text().splitlines() if not l.startswith("Tests-Locked:")]
        lines.insert(3, "Tests-Locked: %s" % sha)
        change.write_text("\n".join(lines) + "\n")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "lock")
        return sha

    def review(self, remit, result):
        """Make the remit's packet, write its result, and commit both."""
        make_packets.main(["x", "CH-0001", remit], root=self.root)
        (self.folder / "review" / remit / "result.md").write_text(result)
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "review " + remit)

    def edit(self, path, text):
        (self.root / path).write_text(text)
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "edit " + path)

    def test_a_first_review_says_where_it_was_made_and_is_no_re_review(self):
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        text = self.packet("security")
        self.assertIn("Made at: %s" % head(self.root), text)
        self.assertNotIn("## Re-review", text)

    def test_a_tests_re_review_has_the_earlier_problems_and_the_checks_diff_since_the_earlier_lock(self):
        self.edit("test/other.test.js", "test('CAP-greeting.R2 other', () => {}) // UNCHANGED-CHECK\n")
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace("- test/greet.test.js",
                                                     "- test/greet.test.js\n- test/other.test.js"))
        first = self.lock()
        self.review("tests", "Result: fail\n\nProblems:\n- test/greet.test.js:1 · no case for Bob · "
                             "CAP-greeting.R2 (greets in Spanish)\n\n"
                             "Wrong versions:\n- CAP-greeting.R2 hola · says hello · fails\n")
        self.edit("test/greet.test.js", "test('CAP-greeting.R2 hola', () => {}) // SECRET-TEST\n"
                                        "test('CAP-greeting.R2 Bob', () => {}) // NEW-CHECK\n")
        self.lock()
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        text = self.packet("tests")
        rereview = text.split("## Re-review", 1)[1].split("# Remit: tests", 1)[0]
        self.assertIn("Earlier review: %s" % first, rereview)
        self.assertIn("no case for Bob", rereview)
        self.assertIn("+test('CAP-greeting.R2 Bob'", rereview)
        self.assertNotIn("UNCHANGED-CHECK", rereview)
        self.assertIn('"Wrong versions" line only for each check that changed', rereview)
        self.assertNotIn("SECRET-CODE", text)

    def test_a_code_re_review_has_the_earlier_problems_and_the_code_diff_since_the_earlier_packet(self):
        self.review("security", "Result: fail\n\nProblems:\n- src/greet.js:1 · builds HTML from the name · rule\n\n"
                                "Follow-ups:\n- none\n")
        self.edit("src/greet.js", "export const greet = (n, l) => escape(n); // SECRET-CODE FIXED\n")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        rereview = self.packet("security").split("## Re-review", 1)[1].split("# Remit:", 1)[0]
        self.assertIn("builds HTML from the name", rereview)
        self.assertIn("+export const greet = (n, l) => escape(n);", rereview)
        self.assertNotIn("Follow-ups", rereview)
        self.assertNotIn("SECRET-TEST", self.packet("security"))

    def test_a_re_review_with_no_earlier_problems_says_none(self):
        self.review("quality", "Result: pass\n\nProblems:\n- none\n\nNotes:\n- fine\n")
        make_packets.main(["x", "CH-0001", "quality"], root=self.root)
        rereview = self.packet("quality").split("## Re-review", 1)[1].split("# Remit:", 1)[0]
        self.assertIn("### Earlier problems\n\nnone", rereview)
        self.assertIn("Nothing changed.", rereview)

    def test_a_failed_result_with_no_problems_heading_goes_in_whole(self):
        self.review("security", "Result: fail\n\n**Issues**\n\n1. src/greet.js:1 · unsafe · rule\n")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        rereview = self.packet("security").split("## Re-review", 1)[1].split("# Remit:", 1)[0]
        self.assertIn("1. src/greet.js:1 · unsafe · rule", rereview)

    def test_problems_under_an_emphasised_heading_are_found(self):
        self.review("security", "Result: fail\n\n**Problems:**\n- src/greet.js:1 · unsafe · rule\n\n"
                                "**Notes:**\n- SECRET-NOTE\n")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        rereview = self.packet("security").split("## Re-review", 1)[1].split("# Remit:", 1)[0]
        self.assertIn("- src/greet.js:1 · unsafe · rule", rereview)
        self.assertNotIn("SECRET-NOTE", rereview)

    def test_the_earlier_result_is_found_in_git_after_its_file_is_gone(self):
        self.review("security", "Result: fail\n\nProblems:\n- src/greet.js:1 · unsafe · rule\n")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        self.assertIn("## Re-review", self.packet("security"))
        self.assertIn("unsafe", self.packet("security"))

    def test_an_earlier_review_of_an_unknown_commit_gives_a_first_review(self):
        target = self.folder / "review/security"
        target.mkdir(parents=True)
        (target / "packet.md").write_text("Made at: deadbeefdeadbeef\n")
        (target / "result.md").write_text("Result: fail\n\nProblems:\n- old · rule\n")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        self.assertNotIn("## Re-review", self.packet("security"))

    def test_a_specification_re_review_checks_the_writing_only_on_lines_changed_since(self):
        self.edit("README.md", (self.root / "README.md").read_text() + "It picks a color.\n")
        self.review("specification", "Result: pass\n\nProblems:\n- none\n")
        self.edit("README.md", (self.root / "README.md").read_text() + "The box is gray.\n")
        make_packets.main(["x", "CH-0001", "specification"], root=self.root)
        text = self.packet("specification")
        writing = text.split("## Writing check", 1)[1]
        self.assertIn('"gray" is US spelling', writing)
        self.assertNotIn('"color" is US spelling', writing)
        self.assertIn("+The box is gray.", text.split("## Re-review", 1)[1].split("# Remit:", 1)[0])

    def test_a_specification_re_review_marks_the_frames_that_did_not_change(self):
        self.review("specification", "Result: pass\n\nProblems:\n- none\n")
        (self.folder / "frames/02.png").write_bytes(b"new frame")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "new frame")
        make_packets.main(["x", "CH-0001", "specification"], root=self.root)
        text = self.packet("specification")
        self.assertIn("frames/01.png (unchanged since the earlier review)", text)
        self.assertIn("frames/02.png\n", text + "\n")
        self.assertNotIn("frames/02.png (unchanged", text)

    def test_a_code_re_review_still_leaves_out_the_writing_rules(self):
        self.review("security", "Result: fail\n\nProblems:\n- src/greet.js:1 · unsafe · rule\n")
        make_packets.main(["x", "CH-0001", "security", "specification"], root=self.root)
        self.assertIn("## Re-review", self.packet("security"))
        self.assertNotIn("Write plainly.", self.packet("security"))
        self.assertIn("Write plainly.", self.packet("specification"))

    def test_a_compliance_result_that_the_script_wrote_gives_a_first_review_later(self):
        (self.root / "pdlc/reviews/compliance.md").write_text("# Remit: compliance\n\n- Rules: none listed yet.\n")
        make_packets.main(["x", "CH-0001", "compliance"], root=self.root)
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "review compliance")
        self.edit("requirements.txt", "requests==2.32.0\n")
        make_packets.main(["x", "CH-0001", "compliance"], root=self.root)
        text = self.packet("compliance")
        self.assertIn("requests==2.32.0", text)
        self.assertNotIn("## Re-review", text)


INTENT = """# IN-0001 · Spanish greeting

Status: building · Ticket: none · Branch: pdlc/IN-0001-es · Added: 2026-10-10

## Requirements

- CAP-greeting.R2 · Greets in Spanish

## Changes

- CH-0001 · Spanish greeting

## Acceptance checks

Acceptance-File: acceptance/IN-0001.acceptance.js
Acceptance-Locked: {lock}
Acceptance-Passed: none

## Notes

- none
"""


class AcceptancePacket(PacketRepo):
    """The tests packet for the acceptance checks of an intent."""

    def setUp(self):
        super().setUp()
        r = self.root
        config = r / "pdlc/config.md"
        config.write_text(config.read_text() + "\n## Checks\n\n"
                          "- acceptance file: `acceptance/{intent}.acceptance.js` (the note)\n")
        (r / "acceptance").mkdir()
        (r / "acceptance/IN-0001.acceptance.js").write_text(
            "test('IN-0001 CAP-greeting.R2 says hola', () => {}) // ACCEPT-CHECK\n")
        self.intent_file = r / "pdlc/inbox/IN-0001-es.md"
        self.intent_file.parent.mkdir(parents=True)
        self.intent_file.write_text(INTENT.format(lock="none"))
        git(r, "add", "-A"); git(r, "commit", "-qm", "Acceptance IN-0001")
        self.lock = head(r)
        self.intent_file.write_text(INTENT.format(lock=self.lock))
        git(r, "add", "-A"); git(r, "commit", "-qm", "Lock acceptance IN-0001")
        self.review = r / "pdlc/acceptance/IN-0001-es/review/tests"

    def acceptance_packet(self):
        return (self.review / "packet.md").read_text()

    def test_an_intent_gets_a_tests_packet_for_its_acceptance_checks(self):
        self.assertEqual(make_packets.main(["x", "IN-0001"], root=self.root), 0)
        text = self.acceptance_packet()
        self.assertIn("# Remit: tests", text)
        self.assertIn("Acceptance-Locked: %s" % self.lock, text)
        self.assertIn("ACCEPT-CHECK", text)
        self.assertIn("Says hola.", text)
        self.assertIn("`greet(name, lang)` in `src/greet.js`", text)
        self.assertNotIn("Not this one.", text)

    ONE_CHANGE = "The intent lists one change. These checks are also the checks of that change."

    def test_an_intent_packet_with_one_change_says_its_checks_serve_the_change(self):
        make_packets.main(["x", "IN-0001"], root=self.root)
        self.assertIn(self.ONE_CHANGE, self.acceptance_packet())

    def test_an_intent_packet_with_two_changes_does_not_say_so(self):
        self.intent_file.write_text(INTENT.format(lock=self.lock).replace(
            "- CH-0001 · Spanish greeting", "- CH-0001 · Spanish greeting\n- CH-0002 · More greetings"))
        make_packets.main(["x", "IN-0001"], root=self.root)
        self.assertNotIn("also the checks of that change", self.acceptance_packet())

    def test_the_acceptance_packet_has_no_code_and_no_component_checks(self):
        make_packets.main(["x", "IN-0001"], root=self.root)
        text = self.acceptance_packet()
        self.assertNotIn("SECRET-CODE", text)
        self.assertNotIn("SECRET-TEST", text)
        self.assertNotIn("Write plainly.", text)

    def test_the_acceptance_packet_is_a_re_review_after_a_new_lock(self):
        make_packets.main(["x", "IN-0001"], root=self.root)
        (self.review / "result.md").write_text(
            "Result: fail\n\nProblems:\n- acceptance/IN-0001.acceptance.js:1 · no case for Bob · "
            "CAP-greeting.R2 (greets in Spanish)\n")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "Review acceptance IN-0001")
        first = self.lock
        (self.root / "acceptance/IN-0001.acceptance.js").write_text(
            "test('IN-0001 CAP-greeting.R2 says hola', () => {}) // ACCEPT-CHECK\n"
            "test('IN-0001 CAP-greeting.R2 Bob', () => {}) // ACCEPT-BOB\n")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "Acceptance IN-0001")
        self.lock = head(self.root)
        self.intent_file.write_text(INTENT.format(lock=self.lock))
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "Lock acceptance IN-0001")
        make_packets.main(["x", "IN-0001"], root=self.root)
        rereview = self.acceptance_packet().split("## Re-review", 1)[1].split("# Remit: tests", 1)[0]
        self.assertIn("Earlier review: %s" % first, rereview)
        self.assertIn("no case for Bob", rereview)
        self.assertIn("+test('IN-0001 CAP-greeting.R2 Bob'", rereview)

    def test_the_acceptance_packet_shows_the_checks_that_the_lock_took_from_earlier_intents(self):
        r = self.root
        (r / "acceptance/IN-0000.acceptance.js").write_text(
            "test('IN-0000 CAP-greeting.R1 hello', () => {})\n"
            "test('IN-0000 CAP-greeting.R2 says hi', () => {}) // OLD-LINE\n")
        git(r, "add", "-A"); git(r, "commit", "-qm", "an earlier intent")
        (r / "acceptance/IN-0000.acceptance.js").write_text("test('IN-0000 CAP-greeting.R1 hello', () => {})\n")
        (r / "acceptance/IN-0001.acceptance.js").write_text(
            "test('IN-0001 CAP-greeting.R2 says hola', () => {}) // ACCEPT-CHECK\n")
        git(r, "add", "-A"); git(r, "commit", "-qm", "Acceptance IN-0001")
        self.intent_file.write_text(INTENT.format(lock=head(r)))
        git(r, "add", "-A"); git(r, "commit", "-qm", "Lock acceptance IN-0001")
        make_packets.main(["x", "IN-0001"], root=r)
        moved = self.acceptance_packet().split("## Checks removed from earlier intents", 1)[1]
        self.assertIn("-test('IN-0000 CAP-greeting.R2 says hi', () => {}) // OLD-LINE", moved)

    def test_an_intent_with_no_acceptance_file_gets_no_packet(self):
        self.intent_file.write_text(INTENT.format(lock="none").replace(
            "Acceptance-File: acceptance/IN-0001.acceptance.js", "Acceptance-File: none"))
        self.assertEqual(make_packets.main(["x", "IN-0001"], root=self.root), 1)
        self.assertFalse(self.review.exists())

    def test_code_packets_leave_out_the_acceptance_checks(self):
        make_packets.main(["x", "CH-0001", "security", "specification"], root=self.root)
        for remit in ["security", "specification"]:
            text = self.packet(remit)
            self.assertIn("SECRET-CODE", text)
            self.assertNotIn("ACCEPT-CHECK", text)

    def test_code_packets_leave_out_a_file_named_as_acceptance_checks_without_the_config_line(self):
        (self.root / "pdlc/config.md").write_text("## Reviews\n\n- remits: security\n")
        (self.root / "tests").mkdir()
        (self.root / "tests/acceptance_IN_0001.py").write_text("# ACCEPT-PY\n")
        git(self.root, "add", "-A"); git(self.root, "commit", "-qm", "more")
        make_packets.main(["x", "CH-0001", "security"], root=self.root)
        self.assertNotIn("ACCEPT-PY", self.packet("security"))


if __name__ == "__main__":
    unittest.main()
