"""Tests for pdlclib, the module that the pdlc bin scripts share.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
BIN = PLUGIN / "skills/init/references/bin"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pdlclib = load("pdlclib_under_test", BIN / "pdlclib.py")
hook = load("commits_hook", PLUGIN / "hooks/commits.py")

TEXT = """# CH-0001 · A change

Status: planned · Branch: `pdlc/CH-0001-x` · Intent: IN-0001 (poll-input-errors)

## Handoff

Done: yes

## Notes

Status: a note.
"""


class SectionAndField(unittest.TestCase):
    def test_section_returns_the_text_under_a_heading(self):
        self.assertEqual(pdlclib.section(TEXT, "Handoff").strip(), "Done: yes")

    def test_section_default_is_empty_text(self):
        self.assertEqual(pdlclib.section(TEXT, "Missing"), "")

    def test_section_default_can_be_none(self):
        self.assertIsNone(pdlclib.section(TEXT, "Missing", None))

    def test_field_is_bare(self):
        self.assertEqual(pdlclib.field(TEXT, "Intent"), "IN-0001")
        self.assertEqual(pdlclib.field(TEXT, "Branch"), "pdlc/CH-0001-x")
        self.assertEqual(pdlclib.field(TEXT, "Status"), "planned")
        self.assertIsNone(pdlclib.field(TEXT, "Base"))

    def test_same_results_as_the_hook(self):
        for title in ("Handoff", "Notes", "Missing"):
            self.assertEqual(pdlclib.section(TEXT, title), hook.section(TEXT, title))
        for name in ("Status", "Branch", "Intent", "Base"):
            self.assertEqual(pdlclib.field(TEXT, name), hook.field(TEXT, name))


class Owner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pdlc/changes/CH-0031-x").mkdir(parents=True)
        (self.root / "pdlc/inbox").mkdir(parents=True)
        (self.root / "pdlc/changes/CH-0031-x/change.md").write_text(
            "# CH-0031\n\nStatus: planned · Branch: pdlc/CH-0031-x\n")
        (self.root / "pdlc/inbox/IN-0012-name.md").write_text(
            "# IN-0012\n\nStatus: specifying · Branch: pdlc/IN-0012-name\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_change_branch(self):
        self.assertEqual(pdlclib.owner(self.root, "pdlc/CH-0031-x"), ("change", "CH-0031"))

    def test_intent_branch(self):
        self.assertEqual(pdlclib.owner(str(self.root), "pdlc/IN-0012-name"), ("intent", "IN-0012"))

    def test_unknown_branch(self):
        self.assertIsNone(pdlclib.owner(self.root, "main"))

    def test_same_results_as_the_hook(self):
        for branch in ("pdlc/CH-0031-x", "pdlc/IN-0012-name", "main"):
            self.assertEqual(pdlclib.owner(self.root, branch), hook.owner(str(self.root), branch))


class Trailers(unittest.TestCase):
    def test_trailers_last_occurrence_wins(self):
        body = "Text\n\nIntent: IN-0001\nIntent: IN-0002\nReq: JOB-a.1\n"
        self.assertEqual(pdlclib.trailers(body), {"Intent": "IN-0002", "Req": "JOB-a.1"})

    def test_trailers_reads_only_pdlc_keys_by_default(self):
        body = "Co-Authored-By: A <a@b>\nIntent: IN-0001\n"
        self.assertEqual(pdlclib.trailers(body), {"Intent": "IN-0001"})

    def test_trailers_any_key(self):
        body = "Co-Authored-By: A <a@b>\nIntent: IN-0001\n"
        self.assertEqual(pdlclib.trailers(body, keys=None),
                         {"Co-Authored-By": "A <a@b>", "Intent": "IN-0001"})

    def test_empty_body(self):
        self.assertEqual(pdlclib.trailers(""), {})
        self.assertEqual(pdlclib.trailers(None), {})

    def test_last_block_reads_the_last_paragraph(self):
        body = "Intent: IN-0001\n\nIntent: IN-0002\nCo-Authored-By: A <a@b>\n"
        self.assertEqual(pdlclib.last_block(body),
                         [("Intent", "IN-0002"), ("Co-Authored-By", "A <a@b>")])

    def test_last_block_split_by_blank_line_loses_the_pdlc_trailer(self):
        body = "Text\n\nIntent: IN-0001\n\nCo-Authored-By: A <a@b>\n"
        self.assertEqual(pdlclib.last_block(body), [("Co-Authored-By", "A <a@b>")])

    def test_last_block_is_empty_for_prose(self):
        self.assertEqual(pdlclib.last_block("Some text\n\nMore prose here\n"), [])
        self.assertEqual(pdlclib.last_block(""), [])

    def test_last_block_agrees_with_git(self):
        body = "Subject\n\nBody text\n\nIntent: IN-0001\nChange: CH-0001\nCo-Authored-By: A <a@b>\n"
        git = subprocess.run(["git", "interpret-trailers", "--parse"], input=body,
                             capture_output=True, text=True).stdout.splitlines()
        mine = ["%s: %s" % pair for pair in pdlclib.last_block(body)]
        self.assertEqual(mine, git)


class Git(unittest.TestCase):
    def test_git_returns_none_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(pdlclib.git(tmp, "rev-parse", "HEAD"))

    def test_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pdlc").mkdir()
            (Path(tmp) / "pdlc/config.md").write_text("x")
            (Path(tmp) / "a/b").mkdir(parents=True)
            self.assertEqual(pdlclib.project_root(Path(tmp) / "a/b"), str(Path(tmp).resolve()))
            self.assertIsNone(pdlclib.project_root("/"))


if __name__ == "__main__":
    unittest.main()
