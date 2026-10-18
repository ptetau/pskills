"""Tests for pdlc's commit check hook. Run: python3 -m unittest discover plugins/pdlc/tests"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
HOOK = PLUGIN / "hooks/commits.py"
WRITING = PLUGIN / "skills/init/references/bin/check_writing.py"
TRAILERS = PLUGIN / "skills/init/references/defaults/DES-pdlc-commit-trailers.md"

CHANGE = "# CH-0001 · Email templates\n\nIntent: IN-0001 · Scope: CAP-email · Status: testing · " \
         "Ticket: none · Branch: pdlc/CH-0001-email · Base: main\n"
INTENT = "# IN-0001 · Password reset\n\nStatus: specifying · Ticket: none · " \
         "Branch: pdlc/IN-0001-reset · Added: 2026-10-10\n"


def git(root, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=root,
                          capture_output=True, text=True, check=True).stdout.strip()


class CommitHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        for path, text in {
            "pdlc/config.md": "# pdlc config\n",
            "pdlc/specs/design/DES-pdlc-commit-trailers.md": TRAILERS.read_text(),
            "pdlc/changes/CH-0001-email/change.md": CHANGE,
            "pdlc/inbox/IN-0001-reset.md": INTENT,
        }.items():
            (r / path).parent.mkdir(parents=True, exist_ok=True)
            (r / path).write_text(text)
        git(r, "init", "-q", "-b", "main")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Set up pdlc")
        git(r, "switch", "-qc", "pdlc/CH-0001-email")

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, subject, trailers="Intent: IN-0001\nChange: CH-0001", path="pdlc/changes/CH-0001-email/log.md"):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(target.read_text() + "x\n" if target.exists() else "x\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "%s\n\n%s" % (subject, trailers) if trailers else subject)

    def hook(self, command="git commit -m done"):
        call = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(self.root)}
        run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(call),
                             capture_output=True, text=True, timeout=30)
        return run.returncode, run.stderr

    # Subjects

    def test_a_listed_subject_with_its_trailers_passes(self):
        self.commit("Lock tests CH-0001")
        self.assertEqual(self.hook(), (0, ""))

    def test_a_subject_not_in_the_list_is_named(self):
        self.commit("Lock tests CH-0001 again")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn('"Lock tests CH-0001 again"', err)
        self.assertIn("DES-pdlc-commit-trailers", err)
        self.assertIn("git commit --amend", err)

    def test_a_subject_naming_another_change_is_named(self):
        self.commit("Tests CH-0002", "Intent: IN-0001\nChange: CH-0001\nReq: CAP-email.R1",
                    path="tests/test_CAP_email.py")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("CH-0002", err)

    def test_an_intent_stage_subject_passes_on_the_intent_branch(self):
        git(self.root, "switch", "-qc", "pdlc/IN-0001-reset", "main")
        self.commit("Specify IN-0001: password reset", "Intent: IN-0001", path="pdlc/inbox/IN-0001-reset.md")
        self.assertEqual(self.hook(), (0, ""))

    def test_every_subject_a_skill_names_is_in_the_list(self):
        shapes = re.findall(r"`([^`]+)`", TRAILERS.read_text().split("## Subjects", 1)[1].split("\n## ", 1)[0])
        named = set()
        for skill in (PLUGIN / "skills").glob("*/SKILL.md"):
            named.update(re.findall(r'"((?:[A-Z][a-z]+ )(?:[a-z]+ )?(?:CH|IN)-xxxx[^"]*)"', skill.read_text()))
        self.assertGreater(len(named), 10)
        for subject in named:
            with self.subTest(subject=subject):
                self.assertTrue(any(self.fits(subject, shape) for shape in shapes),
                                "%r is in no shape of DES-pdlc-commit-trailers" % subject)

    @staticmethod
    def fits(subject, shape):
        """True when a skill's subject, with CH-xxxx and <...> in it, has this shape."""
        words = re.sub(r"<[^>]+>", "<>", " ".join(subject.split()))
        words = words.replace("CH-xxxx", "<change>").replace("IN-xxxx", "<intent>")
        return re.sub(r"<(?!change>|intent>)[^>]+>", "<>", shape) == words

    # Trailers

    def test_a_commit_on_a_change_branch_needs_its_change_trailer(self):
        self.commit("Start CH-0001", "Intent: IN-0001")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("Change: CH-0001", err)

    def test_a_commit_with_no_intent_trailer_is_named(self):
        self.commit("Start CH-0001", "Change: CH-0001")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("Intent", err)

    def test_trailers_count_when_another_paragraph_follows_them(self):
        self.commit("Start CH-0001", "Intent: IN-0001\nChange: CH-0001\n\nGenerated with a tool\n\n"
                    "Co-Authored-By: Someone <s@example.com>")
        self.assertEqual(self.hook(), (0, ""))

    def test_a_commit_that_changes_code_needs_req(self):
        self.commit("Build CH-0001: send from a template", path="src/email.py")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("Req", err)

    def test_a_commit_that_changes_code_with_req_passes(self):
        self.commit("Build CH-0001: send from a template",
                    "Intent: IN-0001\nChange: CH-0001\nReq: CAP-email.R1", path="src/email.py")
        self.assertEqual(self.hook(), (0, ""))

    def test_a_commit_that_changes_only_pdlc_files_carries_no_req(self):
        self.commit("Verified CH-0001", "Intent: IN-0001\nChange: CH-0001\nReq: CAP-email.R1")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("Req", err)

    # What it leaves alone

    def test_a_command_that_is_not_a_commit_is_left_alone(self):
        self.commit("wip", "")
        self.assertEqual(self.hook("git status")[0], 0)

    def test_a_branch_no_spec_names_is_left_alone(self):
        git(self.root, "switch", "-qc", "feature/other", "main")
        self.commit("wip", "")
        self.assertEqual(self.hook()[0], 0)

    def test_a_merge_commit_is_left_alone(self):
        git(self.root, "switch", "-qc", "side", "main")
        self.commit("Side work", "", path="side.txt")
        git(self.root, "switch", "-q", "pdlc/CH-0001-email")
        self.commit("Start CH-0001")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge branch 'side'", "side")
        self.assertEqual(self.hook("git merge side")[0], 0)

    def test_an_older_commit_after_a_switch_is_left_alone(self):
        self.commit("wip", "")
        git(self.root, "switch", "-q", "main")
        git(self.root, "switch", "-q", "pdlc/CH-0001-email")
        self.assertEqual(self.hook()[0], 0)

    def test_outside_a_pdlc_project_it_does_nothing(self):
        (self.root / "pdlc/config.md").unlink()
        self.commit("wip", "")
        self.assertEqual(self.hook()[0], 0)

    def test_hooks_json_runs_it_after_every_bash_call(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
        after = [h for entry in hooks.get("PostToolUse", []) if entry["matcher"] == "Bash"
                 for h in entry["hooks"]]
        self.assertTrue(any("hooks/commits.py" in h["command"] for h in after))


LONG = " ".join(["word"] * 30) + "."
LONGER = " ".join(["other"] * 32) + "."


class WritingHook(unittest.TestCase):
    """The writing part of the hook reports the findings in the text that a commit wrote, once."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        for path, text in {
            "pdlc/config.md": "# pdlc config\n",
            "pdlc/specs/design/DES-pdlc-commit-trailers.md": TRAILERS.read_text(),
            "pdlc/specs/jobs/JOB-email.md": "# JOB-email \u00b7 Send mail\n\nStatus: active\n\n## Who and why\n\nA person sends mail.\n",
            "pdlc/changes/CH-0001-email/change.md": CHANGE,
        }.items():
            (r / path).parent.mkdir(parents=True, exist_ok=True)
            (r / path).write_text(text)
        (r / "pdlc/bin").mkdir()
        shutil.copy(WRITING, r / "pdlc/bin/check_writing.py")
        git(r, "init", "-q", "-b", "main")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Set up pdlc")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((target.read_text() if target.exists() else "") + text)

    def commit(self, subject, amend=False):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", *(["--amend"] if amend else []), "-m", subject)

    def hook(self):
        call = {"tool_name": "Bash", "tool_input": {"command": "git commit -m x"}, "cwd": str(self.root)}
        run = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(call),
                             capture_output=True, text=True, timeout=60)
        return run.returncode, run.stderr

    def test_a_long_sentence_in_a_spec_is_reported_on_main(self):
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("1 writing finding", err)
        self.assertIn("JOB-email.md", err)
        self.assertIn("sentence length", err)
        self.assertIn("git commit --amend", err)

    def test_the_same_findings_are_reported_once(self):
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        self.assertEqual(self.hook()[0], 2)
        self.assertEqual(self.hook(), (0, ""))
        self.commit("Specify IN-0001: mail again", amend=True)
        self.assertEqual(self.hook(), (0, ""))

    def test_a_new_set_of_findings_is_reported_again(self):
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        self.assertEqual(self.hook()[0], 2)
        self.write("pdlc/specs/jobs/JOB-email.md", LONGER + "\n")
        self.commit("Specify IN-0001: mail", amend=True)
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("2 writing findings", err)

    def test_at_most_three_sets_are_reported_for_one_parent(self):
        for n in range(4):
            self.write("pdlc/specs/jobs/JOB-email.md", "\n" + " ".join(["w%d" % n] * (30 + n)) + ".\n")
            self.commit("Specify IN-0001: mail", amend=n > 0)
            self.assertEqual(self.hook()[0], 2 if n < 3 else 0, "report %d" % n)

    def test_a_line_from_an_older_commit_is_not_reported(self):
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        self.hook()
        self.write("pdlc/specs/jobs/JOB-email.md", "\nA short new line.\n")
        self.commit("Ready IN-0001: mail")
        self.assertEqual(self.hook(), (0, ""))

    def test_review_folders_and_plugin_files_are_not_checked(self):
        self.write("pdlc/changes/CH-0001-email/review/tests/packet.md", LONG + "\n")
        self.write("pdlc/templates/change.md", LONG + "\n")
        self.write("pdlc/README.md", LONG + "\n")
        self.commit("Review tests CH-0001")
        self.assertEqual(self.hook(), (0, ""))

    def test_a_handoff_finding_and_a_trailer_problem_come_together(self):
        git(self.root, "switch", "-qc", "pdlc/CH-0001-email")
        self.write("pdlc/changes/CH-0001-email/handoff.md", "# Handoff\n\nThe R3 checks pass.\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "Tests reviewed CH-0001\n\nIntent: IN-0001")
        code, err = self.hook()
        self.assertEqual(code, 2)
        self.assertIn("Change: CH-0001", err)
        self.assertIn('"R3" has no name', err)

    def test_without_the_writing_script_only_the_trailers_are_checked(self):
        (self.root / "pdlc/bin/check_writing.py").unlink()
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        self.assertEqual(self.hook(), (0, ""))

    def test_the_record_keeps_the_working_tree_clean(self):
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Specify IN-0001: mail")
        self.hook()
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertTrue((self.root / ".git/pdlc-writing-reported").exists())

    def test_a_merge_commit_gets_no_writing_check(self):
        git(self.root, "switch", "-qc", "side")
        self.write("pdlc/specs/jobs/JOB-email.md", "\n" + LONG + "\n")
        self.commit("Side")
        git(self.root, "switch", "-q", "main")
        self.write("pdlc/inbox/IN-0001-mail.md", "# IN-0001 \u00b7 Mail\n")
        self.commit("Specify IN-0001: mail")
        git(self.root, "merge", "-q", "--no-ff", "-m", "Merge side", "side")
        self.assertEqual(self.hook(), (0, ""))


if __name__ == "__main__":
    unittest.main()
