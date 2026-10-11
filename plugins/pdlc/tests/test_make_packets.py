"""Tests for pdlc's review packet builder. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import subprocess
import tempfile
import unittest
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


class Packets(unittest.TestCase):
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
            self.assertIn("Write plainly.", text)

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

    def test_a_missing_base_branch_stops_instead_of_sending_empty_packets(self):
        change = self.folder / "change.md"
        change.write_text(change.read_text().replace("Base: main", "Base: no-such-branch"))
        self.assertEqual(make_packets.main(["x", "CH-0001"], root=self.root), 1)
        self.assertFalse((self.folder / "review").exists())

    def test_can_make_a_single_remit(self):
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertEqual([p.name for p in (self.folder / "review").iterdir()], ["tests"])

    def test_a_new_packet_removes_the_old_result(self):
        old = self.folder / "review/tests/result.md"
        old.parent.mkdir(parents=True)
        old.write_text("Result: pass\n")
        make_packets.main(["x", "CH-0001", "tests"], root=self.root)
        self.assertFalse(old.exists())
        self.assertTrue((self.folder / "review/tests/packet.md").exists())


if __name__ == "__main__":
    unittest.main()
