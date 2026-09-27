"""Tests for the dashboard-builder guard. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).parent.parent / "skills/dashboard/references/dashboard-builder-guard.py"
spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, tool_input):
        return guard.allowed({"cwd": self.cwd, "tool_input": tool_input})[1]

    def test_allows_the_dashboard_folder(self):
        self.assertTrue(self.ok({"file_path": ".dashboard/index.html"}))
        self.assertTrue(self.ok({"file_path": os.path.join(self.cwd, ".dashboard/state.json")}))

    def test_allows_its_own_memory(self):
        self.assertTrue(self.ok({"file_path": "~/.claude/agent-memory/dashboard-builder/style.md"}))

    def test_blocks_project_files(self):
        self.assertFalse(self.ok({"file_path": "src/app.py"}))
        self.assertFalse(self.ok({"file_path": ".dashboard-other/x"}))

    def test_blocks_escaping_the_folder(self):
        self.assertFalse(self.ok({"file_path": ".dashboard/../secrets.env"}))
        self.assertFalse(self.ok({"file_path": "~/.claude/agent-memory/other-agent/x.md"}))

    def test_glob_without_a_path_means_the_project_root_and_is_blocked(self):
        self.assertFalse(self.ok({"pattern": "**/*.py"}))
        self.assertTrue(self.ok({"pattern": "*", "path": ".dashboard"}))

    def test_glob_pattern_cannot_escape_the_folder(self):
        self.assertFalse(self.ok({"path": ".dashboard", "pattern": "../**/*"}))
        self.assertFalse(self.ok({"path": ".dashboard", "pattern": "/home/**/*.env"}))
        self.assertTrue(self.ok({"path": ".dashboard", "pattern": "**/*.json"}))

    def test_exit_code_2_blocks_and_explains(self):
        run = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True,
                             input=json.dumps({"cwd": self.cwd, "tool_input": {"file_path": "x"}}))
        self.assertEqual(run.returncode, 2)
        self.assertIn("may only use .dashboard/", run.stderr)


if __name__ == "__main__":
    unittest.main()
