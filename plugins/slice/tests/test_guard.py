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


class Base(unittest.TestCase):
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


class Guard(Base):

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
        for agent in ("slice:reviewer", "pdlc:builder", "", None):
            self.assertTrue(self.ok(agent, "Read", file_path="src/a.py"), agent)
            self.assertTrue(self.ok(agent, "Write", file_path="src/a.py"), agent)

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

    def test_blocks_every_known_runner_and_python_spelling(self):
        for command in ("pytest", "pytest -q", "python3 -m pytest -q", "python -m unittest discover -v",
                        "python3.12 -m unittest", "/usr/bin/python3 -m pytest", "python3 -m nose2",
                        "python3 -m tox", "tox", "make test", "npm test", "npm run test", "yarn test",
                        "pnpm test", "pnpm run test", "npx jest", "jest", "vitest run", "go test ./...",
                        "cargo test", "cd src && pytest", "FOO=1 python3 -m pytest", "uv run pytest",
                        "poetry run pytest", "bash -c 'pytest -q'", "py.test", "nose2"):
            self.assertFalse(self.bash(command), command)

    def test_allows_commands_that_only_look_like_runners(self):
        for command in ("npm install", "make build", "go build ./...", "cargo build", "cat src/pytest_helpers.py",
                        "python3 -m json.tool src/a.json", "grep pytest src/a.py", "echo test",
                        "python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py test S1"):
            self.assertTrue(self.bash(command), command)

    def test_the_implementer_writes_only_in_the_source_folders(self):
        for path in ("slice/001-x/slices.md", "slice/001-x/review/S1.md", "conftest.py", "slice/config.md",
                     "setup.cfg"):
            for tool in ("Write", "Edit", "MultiEdit"):
                self.assertFalse(self.ok(IMPL, tool, file_path=path), "%s %s" % (tool, path))
        self.assertTrue(self.ok(IMPL, "Edit", file_path="src/a.py"))
        self.assertTrue(self.ok(IMPL, "Write", file_path=str(self.root / "src/sub/a.py")))
        self.assertFalse(self.ok(IMPL, "Write", file_path="src/../conftest.py"))
        self.assertTrue(self.ok(IMPL, "Read", file_path="slice/001-x/review/S1.md"))

    def test_the_implementer_runs_only_the_test_subcommand_of_slice_py(self):
        slice_py = "python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py"
        for sub in ("commit S1", "commit interface", "set S1 done", "round S1 test", "next", "status",
                    "resume S1", "scan"):
            self.assertFalse(self.bash("%s %s" % (slice_py, sub)), sub)
        self.assertFalse(self.bash("%s --root . set S1 done" % slice_py))
        self.assertFalse(self.bash("cd src && %s --spec 001 commit S1" % slice_py))
        self.assertTrue(self.bash("%s test S1" % slice_py))
        self.assertTrue(self.bash("%s --spec 001 test S1" % slice_py))
        self.assertTrue(self.bash("%s commit S1" % slice_py, agent="slice:test-writer"))

    def test_the_implementer_may_not_print_the_withheld_messages(self):
        slice_py = "python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py"
        for flags in ("S1 --full", "--full S1", "S1 --red", "--spec 001 test S1 --full"):
            self.assertFalse(self.bash("%s test %s" % (slice_py, flags)) if not flags.startswith("--spec")
                             else self.bash("%s %s" % (slice_py, flags)), flags)
        self.assertTrue(self.bash("%s test S1 --full" % slice_py, agent="slice:test-writer"))
        self.assertTrue(self.bash("%s test S1 --full" % slice_py, agent="slice:reviewer"))

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

    def test_blocks_a_bare_star_that_lists_the_tests(self):
        (self.root / "tests/test_a.py").write_text("x")
        os.symlink(self.root / "tests", self.root / "src/tl")
        for command in ("cat */*", "cat ./*/test_a.py", "cat src/tl/*", "cat src/tl/t*", "ls *", "cat src/*/*"):
            self.assertFalse(self.bash(command), command)
        self.assertTrue(self.bash("ls src/*.py"))
        self.assertTrue(self.ok(IMPL, "Bash", cwd=self.root / "src", command="ls *.py"))

    def test_a_bare_star_in_a_folder_with_no_tests_is_allowed(self):
        (self.root / "src/pkg").mkdir()
        for command in ("cat src/*", "cat src/pkg/*", "ls src/*/"):
            self.assertTrue(self.bash(command), command)

    def test_blocks_a_quoted_or_escaped_folder_name(self):
        for command in ("cat 'tes''ts/test_a.py'", 'base64 tes"ts"/test_a.py', "cat te\\sts/test_a.py",
                        'cat "tests"/test_a.py', "cat t''ests/a.py"):
            self.assertFalse(self.bash(command), command)

    def test_blocks_a_symlink_into_the_tests_from_bash(self):
        (self.root / "tests/test_a.py").write_text("x")
        os.symlink(self.root / "tests", self.root / "src/tl")
        os.symlink(self.root / "tests", self.root / "lnk")
        os.symlink(self.root / "tests/test_a.py", self.root / "flink")
        for command in ("cat src/tl/test_a.py", "cat lnk/test_a.py", "cat flink", "head -1 ./lnk/test_a.py",
                        "cd lnk && cat test_a.py", "cat < lnk/test_a.py", "python3 lnk/test_a.py"):
            self.assertFalse(self.bash(command), command)
        self.assertFalse(self.ok(IMPL, "Bash", cwd=self.root / "src", command="cat tl/test_a.py"))
        self.assertTrue(self.bash("cat src/a.py"))

    def test_tar_and_rsync_are_always_recursive(self):
        for command in ("tar cf - . | cat", "tar -cf x.tar .", "rsync -a . /tmp/x", "zip -r x.zip ."):
            self.assertFalse(self.bash(command), command)
        for command in ("tar cf - src | cat", "rsync -a src/ /tmp/x", "tar tf x.tar"):
            self.assertTrue(self.bash(command), command)

    def test_blocks_the_runner_with_a_joined_flag(self):
        for command in ("python3 -munittest discover", "PYTHONPATH=src python3 -munittest -v",
                        "python3  -m  unittest", "python3 -m 'unittest'"):
            self.assertFalse(self.bash(command), command)
        self.assertTrue(self.bash("python3 -mjson.tool src/a.json"))


class TestWriter(Base):
    """The test writer never sees the app code: the source folders are hidden from it."""
    AGENT = "slice:test-writer"

    def setUp(self):
        super().setUp()
        (self.root / "slice/001-x").mkdir()

    def w(self, tool, **tool_input):
        return self.ok(self.AGENT, tool, **tool_input)

    def wb(self, command, cwd=None):
        return self.ok(self.AGENT, "Bash", cwd=cwd, command=command)

    def test_blocks_every_file_tool_on_a_source_path(self):
        for tool in ("Read", "Write", "Edit", "MultiEdit"):
            self.assertFalse(self.w(tool, file_path="src/wordfreq.py"), tool)
        self.assertFalse(self.w("NotebookEdit", notebook_path="src/a.ipynb"))
        self.assertFalse(self.w("Read", file_path="tests/../src/a.py"))
        self.assertFalse(self.w("Grep", pattern="x", path="src"))
        self.assertFalse(self.w("Grep", pattern="x"))
        self.assertFalse(self.w("Glob", pattern="**/*.py"))
        self.assertFalse(self.w("Glob", pattern="src/*.py"))

    def test_blocks_a_symlink_into_the_source(self):
        os.symlink(self.root / "src", self.root / "tests/lnk")
        self.assertFalse(self.w("Read", file_path="tests/lnk/a.py"))

    def test_allows_the_spec_folder_and_the_tests(self):
        self.assertTrue(self.w("Read", file_path="slice/001-x/interface.md"))
        self.assertTrue(self.w("Read", file_path="slice/config.md"))
        self.assertTrue(self.w("Read", file_path="tests/test_a.py"))
        self.assertTrue(self.w("Write", file_path="tests/test_a.py"))
        self.assertTrue(self.w("Grep", pattern="x", path="tests"))
        self.assertTrue(self.w("Glob", pattern="tests/*.py"))

    def test_writes_only_in_the_tests_folder(self):
        self.assertFalse(self.w("Write", file_path="slice/001-x/interface.md"))
        self.assertFalse(self.w("Edit", file_path="notes.md"))

    def test_blocks_bash_that_names_the_source(self):
        for command in ("cat src/wordfreq.py", "grep -rn x ./src", "cat s*/a.py", "cat 'sr''c'/a.py",
                        "cat */a.py", "ls -R", "git diff", "cat " + str(self.root) + "/src/a.py"):
            self.assertFalse(self.wb(command), command)
        os.symlink(self.root / "src", self.root / "tests/lnk")
        self.assertFalse(self.wb("cat tests/lnk/a.py"))

    def test_allows_bash_in_the_spec_and_tests(self):
        for command in ("cat slice/001-x/interface.md", "ls tests", "grep -rn x tests", "cat tests/test_a.py"):
            self.assertTrue(self.wb(command), command)

    def test_the_test_command_is_not_blocked_for_the_test_writer(self):
        self.assertTrue(self.wb("python3 -m unittest discover -s tests"))

    def test_the_source_folders_come_from_the_config(self):
        (self.root / "slice/config.md").write_text(fixture.CONFIG.replace("`src`", "`app`, `lib`"))
        self.assertFalse(self.w("Read", file_path="app/a.py"))
        self.assertFalse(self.w("Read", file_path="lib/a.py"))
        self.assertTrue(self.w("Read", file_path="src/a.py"))

    def test_without_a_config_the_default_source_folders_apply(self):
        (self.root / "slice/config.md").unlink()
        self.assertFalse(self.w("Read", file_path="src/a.py"))
        self.assertFalse(self.w("Read", file_path="lib/a.py"))
        self.assertTrue(self.w("Read", file_path="tests/a.py"))

    def test_the_implementer_still_reads_the_source(self):
        self.assertTrue(self.ok(IMPL, "Read", file_path="src/a.py"))
        self.assertTrue(self.ok(IMPL, "Write", file_path="src/a.py"))


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


class SmokeLog(unittest.TestCase):
    """The log of the smoke run: the implementer never read a test file, and the test writer
    never read the app code."""
    rows = [json.loads(l) for l in (Path(fixture.PLUGIN) / "tests/smoke/guard-log.jsonl").read_text().splitlines()]

    def calls(self, agent):
        return [r for r in self.rows if r["agent"] == agent]

    def test_the_log_has_each_agent(self):
        for agent in (IMPL, "slice:test-writer", "slice:reviewer"):
            self.assertTrue(self.calls(agent), agent)

    def test_no_implementer_call_names_the_tests(self):
        for r in self.calls(IMPL):
            text = " ".join(str(v) for k, v in (r["input"] or {}).items() if k in ("command", "file_path", "path"))
            text = text.replace("slice.py test ", "slice.py RUN ")
            self.assertNotRegex(text, r"(^|[^\w.-])tests?(/|\b)|test_\w+\.py", text[:80])
            self.assertTrue(r["allowed"])

    def test_the_test_writer_read_only_the_spec_folder_and_wrote_only_tests(self):
        for r in self.calls("slice:test-writer"):
            path = (r["input"] or {}).get("file_path", "")
            if r["tool"] == "Write":
                self.assertIn("<project>/tests/", path)
            if r["tool"] == "Read":
                self.assertIn("<project>/slice/", path)
            self.assertNotIn("<project>/src", json.dumps(r["input"]))


class SourceFiles(Base):
    """The `source files:` config line: paths outside the source folders that the implementer may write."""

    TEST_WRITER = "slice:test-writer"

    def config(self, line):
        (self.root / "slice/config.md").write_text(fixture.CONFIG + "- source files: %s\n" % line)

    def test_the_implementer_writes_the_listed_files_and_globs(self):
        self.config("`package.json`, `migrations/**`, `*.toml`")
        for path in ("package.json", "migrations/001_init.sql", "migrations/sub/002.sql", "pyproject.toml"):
            self.assertTrue(self.ok(IMPL, "Write", file_path=path), path)
            self.assertTrue(self.ok(IMPL, "Edit", file_path=str(self.root / path)), path)

    def test_the_implementer_still_may_not_write_other_files(self):
        self.config("`package.json`, `migrations/**`")
        for path in ("setup.cfg", "migrations_old/a.sql", "sub/package.json", "package.json.bak", "conftest.py"):
            self.assertFalse(self.ok(IMPL, "Write", file_path=path), path)

    def test_none_means_no_source_files(self):
        self.config("none")
        self.assertFalse(self.ok(IMPL, "Write", file_path="none"))
        self.assertTrue(self.ok(self.TEST_WRITER, "Read", file_path="none"))

    def test_without_the_line_only_the_source_folders_are_writable(self):
        self.assertFalse(self.ok(IMPL, "Write", file_path="package.json"))

    def test_a_pattern_never_opens_the_tests_folder_or_slice(self):
        self.config("`**/*.json`, `**`")
        self.assertTrue(self.ok(IMPL, "Write", file_path="package.json"))
        for path in ("tests/a.json", "tests/sub/a.json", "slice/001-x/a.json", "slice/config.md", "slice/x"):
            self.assertFalse(self.ok(IMPL, "Write", file_path=path), path)

    def test_a_symlink_does_not_lead_a_write_into_the_tests(self):
        self.config("`links/**`")
        (self.root / "links").mkdir()
        os.symlink(self.root / "tests", self.root / "links/t")
        self.assertFalse(self.ok(IMPL, "Write", file_path="links/t/a.py"))

    def test_the_test_writer_does_not_see_the_source_files(self):
        self.config("`package.json`, `migrations/**`, `*.toml`")
        for path in ("package.json", "migrations/001_init.sql", "migrations/sub/a.sql", "pyproject.toml"):
            self.assertFalse(self.ok(self.TEST_WRITER, "Read", file_path=path), path)
        for command in ("cat package.json", "cat migrations/001_init.sql", "cat pyproject.toml", "ls migrations"):
            self.assertFalse(self.bash(command, agent=self.TEST_WRITER), command)

    def test_the_test_writer_still_reads_the_records_and_writes_the_tests(self):
        self.config("`**/*.json`, `package.json`")
        self.assertTrue(self.ok(self.TEST_WRITER, "Read", file_path="slice/001-x/interface.md"))
        self.assertTrue(self.ok(self.TEST_WRITER, "Read", file_path="slice/001-x/data.json"))
        self.assertTrue(self.ok(self.TEST_WRITER, "Read", file_path="tests/data.json"))
        self.assertTrue(self.ok(self.TEST_WRITER, "Write", file_path="tests/test_a.py"))
        self.assertFalse(self.ok(self.TEST_WRITER, "Write", file_path="package.json"))

    def test_the_implementer_still_reads_the_source_files(self):
        self.config("`package.json`")
        self.assertTrue(self.ok(IMPL, "Read", file_path="package.json"))
        self.assertTrue(self.bash("cat package.json"))


if __name__ == "__main__":
    unittest.main()
