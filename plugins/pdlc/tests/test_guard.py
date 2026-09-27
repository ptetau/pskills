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

    def test_blocking_exits_2_with_a_reason(self):
        run = subprocess.run([sys.executable, str(GUARD)], capture_output=True, text=True,
                             input=json.dumps({"agent_type": "pdlc:builder", "tool_name": "Edit",
                                               "cwd": str(self.cwd),
                                               "tool_input": {"file_path": "test/a.js"}}))
        self.assertEqual(run.returncode, 2)
        self.assertIn("builder", run.stderr)


if __name__ == "__main__":
    unittest.main()
