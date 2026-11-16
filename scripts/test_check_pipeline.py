"""Tests for check_pipeline.py. Run: python3 scripts/test_check_pipeline.py"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_pipeline.py"
PLUGIN = ROOT / "plugins" / "pdlc"


def run(plugin):
    done = subprocess.run([sys.executable, str(SCRIPT), "--plugin", str(plugin)], capture_output=True, text=True)
    return done.returncode, done.stdout


class CheckPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plugin = self.tmp / "pdlc"
        shutil.copytree(PLUGIN, self.plugin, ignore=shutil.ignore_patterns("__pycache__", "tests"))

    def edit(self, rel, old, new):
        path = self.plugin / rel
        text = path.read_text()
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1))

    def fails(self, rule, word):
        code, out = run(self.plugin)
        self.assertEqual(code, 1, out)
        self.assertTrue(any((" · %s · " % rule) in l and word in l for l in out.splitlines()), out)

    def test_the_real_plugin_passes(self):
        self.assertEqual(run(PLUGIN), (0, ""))

    def test_a_skill_with_an_unknown_kind_fails(self):
        self.edit("skills/build/SKILL.md", "pdlc.py commit built", "pdlc.py commit finished")
        self.fails(1, "finished")

    def test_an_unknown_subcommand_or_option_fails(self):
        self.edit("skills/build/SKILL.md", "pdlc.py commit built", "pdlc.py ship built")
        self.fails(2, "ship")

    def test_an_unknown_option_fails(self):
        self.edit("skills/build/SKILL.md", "pdlc.py set CH-xxxx --reqs built", "pdlc.py set CH-xxxx --reqs built --force")
        self.fails(2, "--force")

    def test_a_call_with_an_id_and_no_required_option_fails(self):
        self.edit("skills/ship/SKILL.md", "pdlc.py stop <ID> --stage <stage>", "pdlc.py stop <ID>")
        self.fails(2, "--stage")

    def test_an_unknown_transition_fails(self):
        self.edit("skills/build/SKILL.md", "pdlc.py handoff CH-xxxx build tests", "pdlc.py handoff CH-xxxx build show")
        self.fails(3, "build → show")

    def test_a_pair_that_no_skill_names_fails(self):
        self.edit("skills/acceptance/SKILL.md", ", or `acceptance build` after a send-back", "")
        self.fails(3, "acceptance → build")

    def test_an_unknown_status_fails(self):
        self.edit("skills/show/SKILL.md", '--status "in review"', '--status "reviewing"')
        self.fails(4, "reviewing")

    def test_a_status_that_a_script_needs_with_no_producer_fails(self):
        self.edit("skills/show/SKILL.md", 'pdlc.py set IN-xxxx --status "in review"', "pdlc.py set IN-xxxx --ticket none")
        self.fails(5, "in review")

    def test_a_field_that_no_template_holds_fails(self):
        self.edit("skills/verify/SKILL.md", "--acceptance-passed", "--acceptance-seen")
        self.fails(6, "--acceptance-seen")

    def test_a_subject_in_the_design_spec_with_no_kind_fails(self):
        self.edit("skills/init/references/defaults/DES-pdlc-commit-trailers.md", "- `Propose <change>` (show)",
                  "- `Propose <change>` (show)\n- `Ponder <change>` (nobody)")
        self.fails(1, "Ponder")


if __name__ == "__main__":
    unittest.main()
