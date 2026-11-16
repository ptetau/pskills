"""Tests for hooks/guard.py: the implementer never reads or edits the tests."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture

spec = importlib.util.spec_from_file_location("slice_guard", fixture.GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

IMPL = "slice:implementer"


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / "slice").mkdir()
        (self.root / "slice/config.md").write_text(fixture.CONFIG)
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()

    def ok(self, agent, tool, cwd=None, **tool_input):
        return guard.decide({"agent_type": agent, "tool_name": tool, "cwd": str(cwd or self.root),
                             "tool_input": tool_input})[0]

    def bash(self, command, agent=IMPL):
        return self.ok(agent, "Bash", command=command)

    # file tools

    def test_blocks_every_file_tool_on_a_test_path(self):
        for tool in ("Read", "Write", "Edit", "MultiEdit"):
            self.assertFalse(self.ok(IMPL, tool, file_path="tests/test_a.py"), tool)
        self.assertFalse(self.ok(IMPL, "NotebookEdit", notebook_path="tests/a.ipynb"))
        self.assertFalse(self.ok(IMPL, "Read", file_path=str(self.root / "tests/sub/test_a.py")))
        self.assertFalse(self.ok(IMPL, "Read", file_path="src/../tests/test_a.py"))
        self.assertFalse(self.ok(IMPL, "Read", file_path="test_a.py", cwd=self.root / "tests"))

    def test_blocks_a_symlink_into_the_tests(self):
        os.symlink(self.root / "tests", self.root / "src/link")
        self.assertFalse(self.ok(IMPL, "Read", file_path="src/link/test_a.py"))

    def test_allows_other_paths(self):
        self.assertTrue(self.ok(IMPL, "Read", file_path="src/a.py"))
        self.assertTrue(self.ok(IMPL, "Write", file_path="src/a.py"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="slice/spec.md"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="tests_notes.md"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="src/tests.py"))

    def test_grep_and_glob_cannot_reach_the_tests(self):
        self.assertFalse(self.ok(IMPL, "Grep", pattern="x", path="tests"))
        self.assertFalse(self.ok(IMPL, "Grep", pattern="x"))
        self.assertFalse(self.ok(IMPL, "Grep", pattern="x", path="."))
        self.assertFalse(self.ok(IMPL, "Glob", pattern="**/*.py"))
        self.assertFalse(self.ok(IMPL, "Glob", pattern="tests/*.py"))
        self.assertFalse(self.ok(IMPL, "Glob", pattern="{src,tests}/*.py"))
        self.assertTrue(self.ok(IMPL, "Grep", pattern="x", path="src"))
        self.assertTrue(self.ok(IMPL, "Grep", pattern="x", glob="src/**/*.py"))
        self.assertFalse(self.ok(IMPL, "Grep", pattern="x", glob="*.py"))
        self.assertTrue(self.ok(IMPL, "Glob", pattern="src/**/*.py"))
        self.assertTrue(self.ok(IMPL, "Glob", pattern="*.py", path="src"))

    def test_other_agents_and_the_main_session_are_free(self):
        for agent in ("slice:test-writer", "slice:reviewer", "pdlc:builder", "", None):
            self.assertTrue(self.ok(agent, "Read", file_path="tests/test_a.py"), agent)
            self.assertTrue(self.ok(agent, "Write", file_path="tests/test_a.py"), agent)
            self.assertTrue(self.bash("cat tests/test_a.py", agent), agent)

    def test_config_names_the_folder(self):
        (self.root / "slice/config.md").write_text(fixture.CONFIG.replace("`tests`", "`spec/acceptance`"))
        self.assertFalse(self.ok(IMPL, "Read", file_path="spec/acceptance/a.py"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="tests/a.py"))
        self.assertFalse(self.bash("cat spec/acceptance/a.py"))

    def test_project_found_from_the_file_when_cwd_is_elsewhere(self):
        elsewhere = Path(self.tmp.name).parent
        self.assertFalse(self.ok(IMPL, "Read", cwd=elsewhere, file_path=str(self.root / "tests/a.py")))

    # Bash

    def test_blocks_commands_that_name_the_folder(self):
        for command in ("cat tests/test_a.py", "grep -rn foo ./tests", "find tests -name '*.py'",
                        "sed -n 1,20p tests/test_a.py", "head -5 tests/test_a.py", "tail tests/test_a.py",
                        "less tests/test_a.py", 'python3 -c "print(open(\'tests/test_a.py\').read())"',
                        "cat " + str(self.root) + "/tests/test_a.py", "cd tests && cat test_a.py",
                        "cat 'tests/test_a.py'", "ls tests", "cat te*/test_a.py", "cat t[e]sts/a.py",
                        "git show HEAD:tests/test_a.py", "cp tests/test_a.py /tmp/x"):
            self.assertFalse(self.bash(command), command)

    def test_blocks_a_search_from_the_root(self):
        for command in ("grep -r foo .", "rg foo", "find . -name '*.py'", "tree", "ls -R",
                        "grep -rn foo " + str(self.root), "git grep foo", "git diff", "git show HEAD",
                        "git log -p"):
            self.assertFalse(self.bash(command), command)

    def test_allows_commands_that_stay_in_the_source(self):
        for command in ("cat src/a.py", "grep -rn foo src", "find src -name '*.py'", "ls", "python3 src/a.py",
                        "git status", "git diff -- src", "python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py test S1",
                        "mytests=1 ls src", "cat src/tests.py", "echo hi"):
            self.assertTrue(self.bash(command), command)

    def test_blocks_the_test_runner(self):
        for command in ("PYTHONPATH=src python3 -m unittest discover -s x", "python3 -m unittest",
                        "cd src && PYTHONPATH=. python3 -m unittest -v"):
            self.assertFalse(self.bash(command), command)
        (self.root / "slice/config.md").write_text(fixture.CONFIG.replace(
            "PYTHONPATH=src python3 -m unittest discover -s tests -v", "npm test --silent"))
        self.assertFalse(self.bash("npm test"))
        self.assertTrue(self.bash("npm install"))

    def test_bash_runs_from_a_subfolder_resolve_against_the_cwd(self):
        self.assertFalse(self.ok(IMPL, "Bash", cwd=self.root / "src", command="cat ../tests/a.py"))
        self.assertTrue(self.ok(IMPL, "Bash", cwd=self.root / "src", command="cat a.py"))
        self.assertFalse(self.ok(IMPL, "Bash", cwd=self.root / "src", command="grep -r x .."))
        self.assertTrue(self.ok(IMPL, "Bash", cwd=self.root / "src", command="grep -r x ."))

    def test_without_a_slice_config_the_default_folders_apply(self):
        (self.root / "slice/config.md").unlink()
        self.assertFalse(self.ok(IMPL, "Read", file_path="tests/a.py"))
        self.assertFalse(self.ok(IMPL, "Read", file_path="test/a.py"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="src/a.py"))


class Cli(unittest.TestCase):
    def run_hook(self, call, **env):
        return subprocess.run([sys.executable, str(fixture.GUARD)], input=json.dumps(call), text=True,
                              capture_output=True, env={**os.environ, **env})

    def test_exit_2_blocks_with_a_reason_on_stderr(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "slice"))
            Path(d, "slice/config.md").write_text(fixture.CONFIG)
            call = {"agent_type": IMPL, "tool_name": "Read", "cwd": d,
                    "tool_input": {"file_path": "tests/a.py"}}
            r = self.run_hook(call)
            self.assertEqual(r.returncode, 2)
            self.assertIn("slice guard", r.stderr)
            self.assertIn("slice.py test", r.stderr)
            call["agent_type"] = "slice:reviewer"
            self.assertEqual(self.run_hook(call).returncode, 0)

    def test_bad_input_does_not_block(self):
        r = subprocess.run([sys.executable, str(fixture.GUARD)], input="not json", text=True,
                           capture_output=True)
        self.assertEqual(r.returncode, 0)

    def test_log(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "log.jsonl")
            call = {"agent_type": IMPL, "tool_name": "Read", "cwd": d, "tool_input": {"file_path": "tests/a.py"}}
            self.run_hook(call, SLICE_GUARD_LOG=log)
            self.assertFalse(json.loads(open(log).readline())["allowed"])


if __name__ == "__main__":
    unittest.main()
