#!/usr/bin/env python3
"""Tests for the scripted rubric item (the `check` field). Run: python3 test_suite_check.py"""

import glob
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA = os.path.join(ROOT, "vet", "references", "suite.schema.json")
WORKFLOW = os.path.join(ROOT, "vet", "references", "vet.workflow.js")
PLACEHOLDERS = {"{run}", "{bench}"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class SchemaTest(unittest.TestCase):
    def test_item_has_optional_string_check(self):
        item = load(SCHEMA)["$defs"]["item"]
        self.assertEqual(item["properties"]["check"]["type"], "string")
        self.assertNotIn("check", item["required"])


class SuiteTest(unittest.TestCase):
    def suites(self):
        return glob.glob(os.path.join(ROOT, "evals", "*", "suite.json"))

    def test_every_check_is_a_command_with_known_placeholders(self):
        for path in self.suites():
            for item in load(path)["rubric"]:
                if "check" not in item:
                    continue
                check = item["check"]
                self.assertIn("{run}", check, f"{path} {item['id']}")
                for name in re.findall(r"\{[a-z]+\}", check):
                    self.assertIn(name, PLACEHOLDERS, f"{path} {item['id']}")

    def test_ship_r5_and_r7_have_a_check(self):
        rubric = load(os.path.join(ROOT, "evals", "pdlc-ship", "suite.json"))["rubric"]
        by_id = {i["id"]: i for i in rubric}
        for rid in ("R5", "R7"):
            self.assertIn("check", by_id[rid], rid)
            self.assertIn("check_trailers.py", by_id[rid]["check"], rid)
        self.assertNotEqual(by_id["R5"]["check"], by_id["R7"]["check"])


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.js = read(WORKFLOW)

    def test_item_text_shows_the_check(self):
        self.assertIn("i.check", self.js)

    def test_grade_rules_tell_the_grader_to_copy_the_verdict(self):
        self.assertIn("scripted check", self.js)
        self.assertIn("{run}", self.js)
        self.assertIn("{bench}", self.js)

    def test_bench_directory_comes_from_args_or_vet_scripts(self):
        self.assertIn("args.benchDir", self.js)


if __name__ == "__main__":
    unittest.main()
