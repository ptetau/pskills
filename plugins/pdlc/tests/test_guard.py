"""Tests for pdlc's role guard. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).parent.parent / "hooks/guard.py"
spec = importlib.util.spec_from_file_location("guard", GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

CONFIG = """# pdlc config

## Checks

- all: `npm test`
- check folders: `test/`, `e2e/`
"""


class Guard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cwd = Path(self.tmp.name)
        (self.cwd / "pdlc").mkdir()
        (self.cwd / "pdlc/config.md").write_text(CONFIG)

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, agent, tool, **tool_input):
        return guard.decide({"agent_type": agent, "tool_name": tool, "cwd": str(self.cwd),
                             "tool_input": tool_input})[0]

    # test-writer: never sees app code, writes only checks

    def test_test_writer_reads_specs_and_checks(self):
        self.assertTrue(self.ok("pdlc:test-writer", "Read", file_path="pdlc/changes/CH-0001-x/change.md"))
        self.assertTrue(self.ok("pdlc:test-writer", "Read", file_path="test/greet.test.js"))
        self.assertTrue(self.ok("pdlc:test-writer", "Glob", pattern="**/*.js", path="e2e"))

    def test_test_writer_cannot_read_app_code(self):
        self.assertFalse(self.ok("pdlc:test-writer", "Read", file_path="src/greet.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Grep", pattern="greet"))
        self.assertFalse(self.ok("pdlc:test-writer", "Glob", pattern="src/**/*.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Read", file_path="test/../src/greet.js"))

    def test_test_writer_globs_from_the_root_when_the_pattern_lists_only_its_folders(self):
        root = str(self.cwd)
        self.assertTrue(self.ok("pdlc:test-writer", "Glob", pattern=root + "/test/**"))
        self.assertTrue(self.ok("pdlc:test-writer", "Glob",
                                pattern=root + "/{pdlc/changes/*/change.md,pdlc/specs/**/*.md,pdlc/config.md}"))
        self.assertTrue(self.ok("pdlc:test-writer", "Glob", pattern="pdlc/specs/design/DES-pdlc-ids.md"))

    def test_test_writer_cannot_glob_a_pattern_that_lists_app_code(self):
        self.assertFalse(self.ok("pdlc:test-writer", "Glob", pattern="*"))
        self.assertFalse(self.ok("pdlc:test-writer", "Glob", pattern="{test,src}/*.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Glob", pattern=str(self.cwd) + "/**/*.js"))

    def test_test_writer_cannot_read_reviews(self):
        self.assertFalse(self.ok("pdlc:test-writer", "Read",
                                 file_path="pdlc/changes/CH-0001-x/review/security/packet.md"))

    def test_test_writer_writes_only_checks(self):
        self.assertTrue(self.ok("pdlc:test-writer", "Write", file_path="test/cli.test.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Write", file_path="src/cli.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Edit", file_path="pdlc/specs/jobs/JOB-x.md"))

    # builder: never edits checks or pdlc files

    def test_builder_writes_app_code_but_not_checks(self):
        self.assertTrue(self.ok("pdlc:builder", "Edit", file_path="src/cli.js"))
        self.assertTrue(self.ok("pdlc:builder", "Read", file_path="test/cli.test.js"))
        self.assertFalse(self.ok("pdlc:builder", "Edit", file_path="test/cli.test.js"))
        self.assertFalse(self.ok("pdlc:builder", "Write", file_path="e2e/flow.spec.js"))
        self.assertFalse(self.ok("pdlc:builder", "Edit", file_path="pdlc/specs/jobs/JOB-x.md"))

    # reviewer: reads only its packet, writes only its result

    def test_reviewer_reads_only_packets_and_frames(self):
        base = "pdlc/changes/CH-0001-x/"
        self.assertTrue(self.ok("pdlc:reviewer", "Read", file_path=base + "review/security/packet.md"))
        self.assertTrue(self.ok("pdlc:reviewer", "Read", file_path=base + "frames/01.png"))
        self.assertFalse(self.ok("pdlc:reviewer", "Read", file_path=base + "review/quality/result.md"))
        self.assertFalse(self.ok("pdlc:reviewer", "Read", file_path="src/cli.js"))
        self.assertFalse(self.ok("pdlc:reviewer", "Grep", pattern="x", path="src"))

    def test_reviewer_writes_only_a_result(self):
        base = "pdlc/changes/CH-0001-x/review/security/"
        self.assertTrue(self.ok("pdlc:reviewer", "Write", file_path=base + "result.md"))
        self.assertFalse(self.ok("pdlc:reviewer", "Write", file_path=base + "packet.md"))
        self.assertFalse(self.ok("pdlc:reviewer", "Edit", file_path="src/cli.js"))

    # the project is found from the files, not only from the agent's working folder

    def ok_from(self, cwd, agent, tool, **tool_input):
        return guard.decide({"agent_type": agent, "tool_name": tool, "cwd": str(cwd),
                             "tool_input": tool_input})[0]

    def test_lanes_hold_when_the_agent_starts_inside_pdlc(self):
        inner = self.cwd / "pdlc"
        spec = str(self.cwd / "pdlc/changes/CH-0001-x/change.md")
        self.assertTrue(self.ok_from(inner, "pdlc:test-writer", "Read", file_path=spec))
        self.assertTrue(self.ok_from(inner, "pdlc:test-writer", "Read", file_path="config.md"))
        self.assertFalse(self.ok_from(inner, "pdlc:test-writer", "Read",
                                      file_path=str(self.cwd / "src/greet.js")))
        self.assertFalse(self.ok_from(inner, "pdlc:builder", "Edit",
                                      file_path=str(self.cwd / "test/greet.test.js")))
        self.assertFalse(self.ok_from(inner, "pdlc:builder", "Edit", file_path="specs/jobs/JOB-x.md"))

    def test_lanes_hold_when_the_agent_starts_outside_the_project(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            spec = str(self.cwd / "pdlc/changes/CH-0001-x/change.md")
            packet = str(self.cwd / "pdlc/changes/CH-0001-x/review/security/packet.md")
            self.assertTrue(self.ok_from(elsewhere, "pdlc:test-writer", "Read", file_path=spec))
            self.assertTrue(self.ok_from(elsewhere, "pdlc:reviewer", "Read", file_path=packet))
            self.assertFalse(self.ok_from(elsewhere, "pdlc:builder", "Write",
                                          file_path=str(self.cwd / "e2e/flow.spec.js")))

    def test_a_path_outside_the_project_says_so(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            allowed, reason = guard.decide({
                "agent_type": "pdlc:test-writer", "tool_name": "Read", "cwd": str(self.cwd),
                "tool_input": {"file_path": str(Path(elsewhere) / "pdlc/changes/CH-0001-x/change.md")}})
        self.assertFalse(allowed)
        self.assertIn("outside the project", reason)

    def test_builder_and_recon_keep_their_lanes_outside_the_project(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            scratch = str(Path(elsewhere) / "scratch.txt")
            self.assertTrue(self.ok("pdlc:builder", "Write", file_path=scratch))
            self.assertTrue(self.ok("pdlc:recon", "Read", file_path=scratch))

    # acceptance files are checks: the test writer writes them, the builder cannot

    def with_acceptance_line(self):
        (self.cwd / "pdlc/config.md").write_text(
            CONFIG + "- acceptance file: `acceptance/{intent}.acceptance.js` (the acceptance checks "
                     "of one intent)\n")

    def test_the_test_writer_reads_and_writes_the_acceptance_file_of_the_config(self):
        self.with_acceptance_line()
        self.assertTrue(self.ok("pdlc:test-writer", "Write", file_path="acceptance/IN-0001.acceptance.js"))
        self.assertTrue(self.ok("pdlc:test-writer", "Read", file_path="acceptance/IN-0002.acceptance.js"))
        self.assertFalse(self.ok("pdlc:test-writer", "Write", file_path="acceptance/helpers.js"))

    def test_the_builder_cannot_change_the_acceptance_file_of_the_config(self):
        self.with_acceptance_line()
        self.assertFalse(self.ok("pdlc:builder", "Edit", file_path="acceptance/IN-0001.acceptance.js"))
        self.assertTrue(self.ok("pdlc:builder", "Read", file_path="acceptance/IN-0001.acceptance.js"))
        self.assertTrue(self.ok("pdlc:builder", "Edit", file_path="acceptance/helpers.js"))

    def test_a_file_named_for_the_acceptance_of_an_intent_is_a_check_without_the_config_line(self):
        self.assertFalse(self.ok("pdlc:builder", "Write", file_path="acceptance_IN_0001.py"))
        self.assertFalse(self.ok("pdlc:builder", "Write", file_path="e2e2/IN-0003.acceptance.js"))
        self.assertTrue(self.ok("pdlc:test-writer", "Write", file_path="acceptance_IN_0001.py"))
        self.assertTrue(self.ok("pdlc:builder", "Write", file_path="src/acceptance.py"))

    def test_reviewer_reads_the_acceptance_packet_and_writes_its_result(self):
        base = "pdlc/acceptance/IN-0001-reset/review/tests/"
        self.assertTrue(self.ok("pdlc:reviewer", "Read", file_path=base + "packet.md"))
        self.assertTrue(self.ok("pdlc:reviewer", "Write", file_path=base + "result.md"))
        self.assertFalse(self.ok("pdlc:reviewer", "Write", file_path=base + "packet.md"))

    def test_test_writer_cannot_read_the_acceptance_review(self):
        self.assertFalse(self.ok("pdlc:test-writer", "Read",
                                 file_path="pdlc/acceptance/IN-0001-reset/review/tests/result.md"))

    # recon: read only

    def test_recon_never_writes(self):
        self.assertTrue(self.ok("pdlc:recon", "Read", file_path="src/cli.js"))
        self.assertFalse(self.ok("pdlc:recon", "Write", file_path="notes.md"))

    # everyone else is untouched

    def test_other_agents_and_the_main_session_are_allowed(self):
        self.assertTrue(self.ok(None, "Edit", file_path="test/cli.test.js"))
        self.assertTrue(self.ok("general-purpose", "Read", file_path="src/cli.js"))

    def test_default_check_folders_without_config(self):
        (self.cwd / "pdlc/config.md").unlink()
        self.assertTrue(self.ok("pdlc:test-writer", "Write", file_path="tests/test_x.py"))
        self.assertFalse(self.ok("pdlc:builder", "Write", file_path="tests/test_x.py"))

    def test_reads_the_check_folder_line_as_the_template_writes_it(self):
        (self.cwd / "pdlc/config.md").write_text(
            "## Checks\n\n- check folders: `test/` (where checks live; only the test writer may change them)\n")
        self.assertFalse(self.ok("pdlc:builder", "Edit", file_path="test/a.test.js"))
        self.assertTrue(self.ok("pdlc:test-writer", "Write", file_path="test/a.test.js"))

    def test_an_unwritable_log_still_blocks(self):
        env = dict(__import__("os").environ, PDLC_GUARD_LOG="/nonexistent-dir/guard.log")
        run = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True, env=env,
                             input=json.dumps({"agent_type": "pdlc:builder", "tool_name": "Edit",
                                               "cwd": str(self.cwd),
                                               "tool_input": {"file_path": "test/a.js"}}))
        self.assertEqual(run.returncode, 2)

    def test_blocking_exits_2_with_a_reason(self):
        run = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True,
                             input=json.dumps({"agent_type": "pdlc:builder", "tool_name": "Edit",
                                               "cwd": str(self.cwd),
                                               "tool_input": {"file_path": "test/a.js"}}))
        self.assertEqual(run.returncode, 2)
        self.assertIn("builder", run.stderr)


if __name__ == "__main__":
    unittest.main()
