"""Tests for pdlc's writing check. Run: python3 -m unittest discover plugins/pdlc/tests

Each test runs the script as a command, the way an agent or make_packets.py runs it.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/check_writing.py"


def sentence(first, words):
    """A sentence of exactly this many words, starting with the first one."""
    return " ".join([first] + ["word"] * (words - 2) + ["end."])


def git(root, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                   check=True, capture_output=True)


class WritingCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.root,
                              capture_output=True, text=True)

    def check(self, text):
        """Checks one file that holds the text. Returns the exit code and the findings."""
        (self.root / "doc.md").write_text(text)
        done = self.run_script("doc.md")
        return done.returncode, [l for l in done.stdout.splitlines() if l.startswith("doc.md:")]

    def assertNothingFound(self, text):
        code, found = self.check(text)
        self.assertEqual((code, found), (0, []))

    # Rule 1: sentence length

    def test_a_description_of_more_than_25_words_is_found(self):
        code, found = self.check(sentence("The", 26) + "\n")
        self.assertEqual(code, 1)
        self.assertEqual(len(found), 1)
        self.assertIn("· sentence length · 26 words", found[0])
        self.assertNothingFound(sentence("The", 25) + "\n")

    def test_an_instruction_of_more_than_20_words_is_found(self):
        code, found = self.check(sentence("Run", 21) + "\n")
        self.assertEqual(len(found), 1)
        self.assertIn("· sentence length · instruction of 21 words", found[0])
        self.assertNothingFound(sentence("Run", 20) + "\n")
        self.assertNothingFound(sentence("The", 21) + "\n")

    def test_a_sentence_does_not_end_at_e_g(self):
        code, found = self.check(sentence("The", 20).replace("end.", "e.g. word ") + sentence("x", 10) + "\n")
        self.assertEqual(len(found), 1)
        self.assertIn("· 31 words", found[0])

    def test_a_sentence_over_several_lines_is_counted_whole_and_found_on_its_first_line(self):
        words = sentence("The", 30).split(" ")
        code, found = self.check("Intro.\n\n" + " ".join(words[:15]) + "\n" + " ".join(words[15:]) + "\n")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("doc.md:3 · sentence length · 30 words"))

    # Rule 2: NZ spelling

    def test_us_spelling_is_found_with_the_nz_form(self):
        code, found = self.check("We organize the color at the center, then analyze it.\n")
        self.assertEqual(code, 1)
        self.assertEqual(len(found), 4)
        for us, nz in [("organize", "organise"), ("color", "colour"), ("center", "centre"),
                       ("analyze", "analyse")]:
            self.assertTrue(any('"%s"' % us in f and '"%s"' % nz in f for f in found), us)

    def test_the_suggestion_keeps_the_case(self):
        code, found = self.check("Color first. ORGANIZATION next.\n")
        self.assertIn('"Colour"', found[0])
        self.assertIn('"ORGANISATION"', found[1])

    def test_every_listed_us_form_is_found(self):
        pairs = {"behavior": "behaviour", "favor": "favour", "honor": "honour", "labor": "labour",
                 "neighbor": "neighbour", "flavor": "flavour", "humor": "humour", "rumor": "rumour",
                 "theater": "theatre", "fiber": "fibre", "liter": "litre", "catalog": "catalogue",
                 "defense": "defence", "gray": "grey", "traveled": "travelled",
                 "canceled": "cancelled", "labeled": "labelled", "modeling": "modelling",
                 "fulfill": "fulfil", "enrollment": "enrolment", "prioritized": "prioritised",
                 "summarizing": "summarising", "realization": "realisation", "colors": "colours"}
        code, found = self.check("\n\n".join("A %s here." % us for us in pairs) + "\n")
        self.assertEqual(len(found), len(pairs))
        for f, nz in zip(found, pairs.values()):
            self.assertIn('write "%s"' % nz, f)

    def test_words_that_keep_ize_are_not_found(self):
        self.assertNothingFound("Check the size, then seize the prize. The boat may capsize.\n"
                                "The page was resized. Maize grows here.\n")

    # Rule 5: an ID alone

    def test_an_id_alone_is_found(self):
        code, found = self.check("This conflicts with R3.\n\nRead IN-0001 first.\n\n"
                                 "See CAP-email.R3 for that.\n\nAsk about CH-0031 and DES-errors.\n")
        self.assertEqual(code, 1)
        self.assertEqual(len(found), 5)
        self.assertTrue(all("· ID alone ·" in f for f in found))
        self.assertIn('"R3"', found[0])

    def test_an_id_with_its_name_is_not_found(self):
        self.assertNothingFound(
            "This conflicts with CAP-email.R3 (the reset link expires after one hour).\n\n"
            "CH-0001 · Spanish greeting is next.\n\n"
            "IN-0001: add a greeting.\n\n"
            "R3 — the reset link expires.\n\n"
            'R3 "the reset link expires" holds.\n\n'
            "The reset rules (CAP-email.R3, CAP-email.R4) hold.\n\n"
            "Its branch is pdlc/CH-0001-greeting.\n")

    def test_a_list_of_ids_is_not_running_text(self):
        self.assertNothingFound("## Relies on\n\n- DES-writing-style\n- Capabilities: CAP-email, CAP-store\n")

    # Rule 6: conversation

    def test_conversation_is_found(self):
        code, found = self.check("As you asked, the limit is 10.\n\nI've set the limit.\n\n"
                                 "The limit changed in this round.\n")
        self.assertEqual(code, 1)
        self.assertEqual(len(found), 3)
        self.assertTrue(all("· conversation ·" in f for f in found))
        self.assertIn('"As you asked"', found[0])

    def test_here_is_is_conversation_only_at_the_start_of_a_sentence(self):
        code, found = self.check("Here is the plan.\n\nWhat is left out here is never built.\n")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith('doc.md:1 · conversation · "Here is"'))

    def test_facts_are_not_conversation(self):
        self.assertNothingFound("Maximum: 10 items. Ask the user one short question at a time.\n\n"
                                "Use it when the user wants a plan.\n")

    # What it skips

    def test_fenced_code_is_skipped(self):
        self.assertNothingFound("Text.\n\n```\nThe color of R3, as you asked.\n```\n\n"
                                "````md\n```\nThe gray of R4.\n```\n````\n")

    def test_inline_code_is_skipped(self):
        self.assertNothingFound("Run `colorize --as-you-asked R3` and ``organize `x` R4`` now.\n")

    def test_a_line_with_the_marker_is_skipped(self):
        self.assertNothingFound("This conflicts with R3, as you asked. <!-- writing: ok -->\n")
        code, found = self.check("This conflicts with R3, as you asked.\n")
        self.assertEqual(len(found), 2)

    def test_the_marker_skips_a_long_sentence_that_ends_on_its_line(self):
        words = sentence("The", 30).split(" ")
        self.assertNothingFound(" ".join(words[:15]) + "\n" + " ".join(words[15:])
                                + " <!-- writing: ok -->\n")

    def test_a_heading_may_hold_an_id_alone(self):
        self.assertNothingFound("# CH-0001 · Spanish greeting\n\n### CAP-email.R3\n\n## R4\n")

    def test_a_table_row_may_hold_an_id_alone(self):
        self.assertNothingFound("| Requirement | Result |\n|---|---|\n| CAP-email.R3 | pass |\n")

    def test_a_trailer_line_may_hold_an_id_alone(self):
        self.assertNothingFound("Intent: IN-0012\nChange: CH-0031\nReq: CAP-email.R3, CAP-email.R4\n\n"
                                "Status: proposed · Intents: IN-0012\n")

    def test_a_placeholder_is_not_an_id(self):
        self.assertNothingFound("Write the handoff for IN-xxxx in CH-xxxx-name, from CAP-x.R1 "
                                "and the DES-pdlc-* specs.\n\nFill in CAP-name and IN-0000.\n")

    def test_quoted_text_urls_and_html_comments_are_skipped(self):
        self.assertNothingFound('Not: "As you asked, R3 is gray."\n\n'
                                "See https://example.com/color/R3 and [the guide](docs/color.md).\n\n"
                                "<!-- as you asked,\nthe color -->Done.\n")

    def test_front_matter_is_skipped_except_the_description(self):
        code, found = self.check("---\nname: colorize\ntools: Read\ndescription: >\n"
                                 "  Picks a color.\n---\n\nText.\n")
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith("doc.md:5 · NZ spelling"))

    # Output and exit code

    def test_each_finding_is_one_line_with_file_line_rule_what_and_suggestion(self):
        code, found = self.check("Title.\n\nThe gray box.\n")
        self.assertEqual(found, ['doc.md:3 · NZ spelling · "gray" is US spelling · write "grey"'])

    def test_the_exit_code_is_1_with_findings_and_0_without(self):
        (self.root / "bad.md").write_text("The color.\n")
        (self.root / "good.md").write_text("The colour.\n")
        bad = self.run_script("bad.md")
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(bad.stdout.splitlines()[-1], "1 finding: 1 NZ spelling.")
        good = self.run_script("good.md")
        self.assertEqual(good.returncode, 0)
        self.assertEqual(good.stdout.splitlines()[-1], "No findings.")

    def test_a_folder_means_every_md_file_in_it(self):
        (self.root / "docs/deep").mkdir(parents=True)
        (self.root / "docs/a.md").write_text("The color.\n")
        (self.root / "docs/deep/b.md").write_text("The gray.\n")
        (self.root / "docs/c.txt").write_text("The center.\n")
        out = self.run_script("docs").stdout
        self.assertIn("docs/a.md:1", out)
        self.assertIn("docs/deep/b.md:1", out)
        self.assertNotIn("c.txt", out)

    def test_with_no_paths_it_checks_the_text_files_changed_on_the_branch(self):
        (self.root / "old.md").write_text("The color.\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "switch", "-q", "-c", "topic")
        (self.root / "new.md").write_text("The gray.\n")
        (self.root / "code.py").write_text("# The center.\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "work")
        out = self.run_script().stdout
        self.assertIn("new.md:1", out)
        self.assertNotIn("old.md", out)
        self.assertNotIn("code.py", out)

    def test_with_no_main_it_checks_every_md_file_here(self):
        (self.root / "sub").mkdir()
        (self.root / "a.md").write_text("The color.\n")
        (self.root / "sub/b.md").write_text("The gray.\n")
        out = self.run_script().stdout
        self.assertIn("a.md:1", out)
        self.assertIn("b.md:1", out)

    def test_since_reports_only_the_lines_changed_since_that_branch(self):
        (self.root / "doc.md").write_text("The color.\n")
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "base")
        git(self.root, "switch", "-q", "-c", "topic")
        (self.root / "doc.md").write_text("The color.\nThe gray.\n")
        git(self.root, "commit", "-qam", "work")
        out = self.run_script("--since", "main", "doc.md").stdout
        self.assertIn("doc.md:2", out)
        self.assertNotIn("doc.md:1", out)


if __name__ == "__main__":
    unittest.main()
