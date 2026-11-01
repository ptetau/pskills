#!/usr/bin/env python3
"""Tests for compare_vet.py. Run: python3 test_compare_vet.py"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_vet  # noqa: E402

H = {c: c * 64 for c in "abcdef"}


def result(**over):
    r = {
        "skillSha256": H["a"], "skillTreeSha256": H["b"], "workflowSha256": H["c"],
        "suiteSha256": H["d"],
        "config": {"prompts": ["P01"], "runs": 4, "wave": 2,
                   "agents": {"preset": "lean"}, "sessionModel": "claude-opus-5-5"},
        "scores": {"quality": 80.0, "stability": 80.0, "overall": 80.0, "usableRuns": 4,
                   "confidence": "normal"},
        "items": [{"id": "R1", "weight": 3, "criterion": "c", "passRate": 90.0}],
    }
    r.update(over)
    return r


def run_cli(base, cand, *extra):
    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, r in (("b.json", base), ("c.json", cand)):
            path = os.path.join(d, name)
            with open(path, "w") as f:
                json.dump(r, f)
            paths.append(path)
        buf = io.StringIO()
        code = None
        with contextlib.redirect_stdout(buf):
            try:
                compare_vet.main(paths + list(extra))
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()


class CompareTest(unittest.TestCase):
    def test_workflow_hash_mismatch_is_not_comparable(self):
        out = compare_vet.compare(result(), result(workflowSha256=H["e"]))
        self.assertFalse(out["comparable"])
        self.assertTrue(any(d.startswith("workflowSha256") for d in out["differences"]))
        code, text = run_cli(result(), result(workflowSha256=H["e"]))
        self.assertEqual(code, 2)
        self.assertIn("NOT COMPARABLE", text)

    def test_missing_workflow_hash_warns_and_compares(self):
        old = result()
        del old["workflowSha256"]
        out = compare_vet.compare(old, result())
        self.assertTrue(out["comparable"])
        self.assertTrue(any("workflowSha256 is missing in the baseline" in w for w in out["warnings"]))
        code, text = run_cli(old, result(skillSha256=H["e"]))
        self.assertEqual(code, 0)
        self.assertIn("WARN  workflowSha256 is missing", text)

    def test_both_missing_warns_for_each_side(self):
        a, b = result(), result()
        del a["workflowSha256"], b["workflowSha256"]
        out = compare_vet.compare(a, b)
        self.assertEqual(sum("workflowSha256 is missing" in w for w in out["warnings"]), 2)

    def test_info_line_when_skill_differs(self):
        cand = result(skillSha256=H["e"], skillTreeSha256=H["f"])
        out = compare_vet.compare(result(), cand)
        self.assertEqual(len(out["info"]), 1)
        self.assertIn("skillSha256 differs, skillTreeSha256 differs", out["info"][0])
        self.assertFalse(any("same skill text" in w for w in out["warnings"]))
        code, text = run_cli(result(), cand)
        self.assertEqual(code, 0)
        self.assertIn("INFO  skillSha256 differs", text)
        self.assertIn("NO REGRESSION", text)

    def test_only_tree_differs(self):
        out = compare_vet.compare(result(), result(skillTreeSha256=H["f"]))
        self.assertIn("skillSha256 same, skillTreeSha256 differs", out["info"][0])
        self.assertFalse(any("same skill text" in w for w in out["warnings"]))

    def test_warns_when_both_hashes_are_the_same(self):
        out = compare_vet.compare(result(), result())
        self.assertTrue(any("measure the same skill text" in w for w in out["warnings"]))
        code, text = run_cli(result(), result())
        self.assertEqual(code, 0)
        self.assertIn("WARN  skillSha256 and skillTreeSha256 are the same", text)

    def test_missing_tree_hash_is_unknown_not_same(self):
        old = result()
        del old["skillTreeSha256"]
        out = compare_vet.compare(old, result())
        self.assertIn("skillTreeSha256 unknown", out["info"][0])
        self.assertFalse(any("same skill text" in w for w in out["warnings"]))

    def pinned_warns(self, cand):
        out = compare_vet.compare(result(), cand)
        return [w for w in out["warnings"] if "models not pinned" in w]

    def test_pinned_models_give_no_warning(self):
        cand = result()
        cand["config"]["sessionModel"] = "claude-opus-5-5"
        cand["config"]["agents"] = {"preset": "lean", "run": {"model": "session"},
                                    "grade": {"model": "claude-sonnet-5-5"}}
        base = copy.deepcopy(cand)
        out = compare_vet.compare(base, cand)
        self.assertEqual([w for w in out["warnings"] if "models not pinned" in w], [])

    def test_session_role_without_session_model_warns(self):
        cand = result()
        cand["config"]["agents"] = {"preset": "lean", "run": {"model": "session"}}
        del cand["config"]["sessionModel"]
        base = copy.deepcopy(cand)
        out = compare_vet.compare(base, cand)
        self.assertTrue(any("models not pinned; scores may not be comparable" in w
                            for w in out["warnings"]))
        code, text = run_cli(base, cand)
        self.assertIn("WARN  models not pinned; scores may not be comparable", text)
        self.assertEqual(code, 0)

    def test_alias_model_warns(self):
        for where in ("sessionModel", "role"):
            cand = result()
            cand["config"]["sessionModel"] = "claude-opus-5-5"
            cand["config"]["agents"] = {"preset": "lean", "run": {"model": "session"}}
            if where == "sessionModel":
                cand["config"]["sessionModel"] = "Opus"
            else:
                cand["config"]["agents"]["grade"] = {"model": "sonnet"}
            base = copy.deepcopy(cand)
            out = compare_vet.compare(base, cand)
            self.assertTrue(any("models not pinned" in w for w in out["warnings"]), where)

    def test_candidate_only_alias_warns(self):
        cand = result()
        cand["config"]["agents"] = {"preset": "lean", "run": {"model": "opus"}}
        self.assertEqual(len(self.pinned_warns(cand)), 1)

    def test_old_settings_still_checked(self):
        cand = result()
        cand["config"]["runs"] = 5
        self.assertFalse(compare_vet.compare(result(), cand)["comparable"])

    def test_regression_exit_code_is_still_1(self):
        cand = result()
        cand["scores"] = dict(cand["scores"], overall=60.0)
        code, text = run_cli(result(), cand)
        self.assertEqual(code, 1)
        self.assertIn("REGRESSION", text)
        self.assertIn("FAIL  overall score fell", text)

    def test_json_output_has_info(self):
        code, text = run_cli(result(), result(skillSha256=H["e"]), "--json")
        self.assertEqual(code, 0)
        self.assertIn("info", json.loads(text))

    def test_inputs_not_changed(self):
        a, b = result(), result()
        a0, b0 = copy.deepcopy(a), copy.deepcopy(b)
        compare_vet.compare(a, b)
        self.assertEqual((a, b), (a0, b0))


if __name__ == "__main__":
    unittest.main()
