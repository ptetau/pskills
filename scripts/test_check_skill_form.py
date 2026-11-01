#!/usr/bin/env python3
"""Tests for check_skill_form.py. Run: python3 scripts/test_check_skill_form.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_skill_form as csf  # noqa: E402

FM = "---\nname: demo\ndescription: x\n---\n\n"
GOOD = FM + """# pdlc demo

## Goal

The thing is done.

## Inputs

- The item.

## Outputs

- A file.

## Constraints

- One rule.

## Done when

- The file exists.
"""

STAGE_BLOCK = """- Goal: write it.
- Inputs: the spec.
- Outputs: the file.
- Done when: the file exists.
"""

STAGES = GOOD.replace("## Done when", "## Stages\n\n### 1. Write\n\n" + STAGE_BLOCK + "\n## Done when")


def problems(text, budgets=None):
    return csf.check("/x/demo/SKILL.md", text, budgets or {})


class Form(unittest.TestCase):
    def test_good(self):
        self.assertEqual(problems(GOOD), [])

    def test_good_with_stages(self):
        self.assertEqual(problems(STAGES), [])

    def test_missing_section(self):
        out = problems(GOOD.replace("## Inputs\n\n- The item.\n\n", ""))
        self.assertTrue(any('missing section "## Inputs"' in p for p in out))

    def test_wrong_order(self):
        text = GOOD.replace("## Inputs", "## TMP").replace("## Outputs", "## Inputs").replace("## TMP", "## Outputs")
        self.assertTrue(any("out of order" in p for p in problems(text)))

    def test_unknown_section(self):
        self.assertTrue(any("unknown section" in p for p in problems(GOOD + "\n## Notes\n\nx\n")))

    def test_heading_in_code_fence_ignored(self):
        self.assertEqual(problems(GOOD + "\n```\n## Notes\n```\n"), [])

    def test_constraints_limit(self):
        nine = GOOD.replace("- One rule.\n", "".join(f"- Rule {i}.\n" for i in range(9)))
        self.assertTrue(any("9 items" in p for p in problems(nine)))
        eight = GOOD.replace("- One rule.\n", "".join(f"- Rule {i}.\n" for i in range(8)))
        self.assertEqual(problems(eight), [])

    def test_stage_without_labels(self):
        self.assertTrue(any("no labels" in p for p in problems(STAGES.replace(STAGE_BLOCK, "Write it.\n"))))

    def test_stage_missing_label(self):
        out = problems(STAGES.replace("- Inputs: the spec.\n", ""))
        self.assertTrue(any('missing label "Inputs"' in p for p in out))

    def test_stage_label_order(self):
        out = problems(STAGES.replace("- Goal: write it.\n- Inputs: the spec.", "- Inputs: the spec.\n- Goal: write it."))
        self.assertTrue(any("out of order" in p for p in out))

    def test_stage_too_long(self):
        extra = "- Constraints: a.\n\nMore.\n\nEven more.\n"
        out = problems(STAGES.replace(STAGE_BLOCK, STAGE_BLOCK + extra))
        self.assertTrue(any("at most 6" in p for p in out))

    def test_stage_wrapped_lines_count_once(self):
        out = problems(STAGES.replace("- Goal: write it.", "- Goal: write it\n  and more\n  and more."))
        self.assertEqual(out, [])

    def test_no_front_matter(self):
        self.assertIn("no front matter", problems(GOOD[len(FM):]))

    def test_empty_stages_section(self):
        out = problems(GOOD.replace("## Done when", "## Stages\n\nNone.\n\n## Done when"))
        self.assertTrue(any('no "###" stage' in p for p in out))


class Budget(unittest.TestCase):
    def test_under(self):
        self.assertEqual(problems(GOOD, {"demo": 500}), [])

    def test_over(self):
        self.assertTrue(any("budget 10" in p for p in problems(GOOD, {"demo": 10})))

    def test_no_budget_only_form(self):
        self.assertEqual(problems(GOOD, {"other": 1}), [])

    def test_front_matter_not_counted(self):
        words = len(GOOD[len(FM):].split())
        self.assertEqual(problems(GOOD, {"demo": words}), [])
        self.assertTrue(problems(GOOD, {"demo": words - 1}))

    def test_budget_file_covers_pdlc_skills(self):
        with open(os.path.join(HERE, "skill_budgets.json")) as f:
            budgets = json.load(f)
        skills = os.path.join(HERE, "..", "plugins", "pdlc", "skills")
        for name in os.listdir(skills):
            self.assertIn(name, budgets)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, os.path.join(HERE, "check_skill_form.py"), *args],
                              capture_output=True, text=True)

    def test_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "demo"))
            path = os.path.join(d, "demo", "SKILL.md")
            with open(path, "w") as f:
                f.write(GOOD)
            self.assertEqual(self.run_cli(path).returncode, 0)
            with open(path, "w") as f:
                f.write(GOOD.replace("## Goal", "## Aim"))
            r = self.run_cli(path)
            self.assertEqual(r.returncode, 1)
            self.assertIn("missing section", r.stdout)
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("--nope", "x").returncode, 2)
        self.assertEqual(self.run_cli("/no/such/file").returncode, 2)


if __name__ == "__main__":
    unittest.main()
