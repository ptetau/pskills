"""Tests for pdlc.py, the command that writes the structured outputs of pdlc.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "skills/init/references/bin/pdlc.py"
SUBCOMMANDS = ["commit", "message", "handoff", "stop", "set", "intent", "change"]


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class EntryPoint(unittest.TestCase):
    def test_each_subcommand_is_registered_and_not_implemented(self):
        for name in SUBCOMMANDS:
            done = run(name)
            self.assertEqual(done.returncode, 2, name)
            self.assertIn("not implemented", done.stdout + done.stderr, name)

    def test_extra_arguments_are_accepted_by_a_stub(self):
        done = run("commit", "build", "CH-0001", "--text", "x", "--req", "JOB-a.1")
        self.assertEqual(done.returncode, 2)
        self.assertIn("not implemented", done.stdout + done.stderr)

    def test_no_subcommand_is_a_usage_error(self):
        self.assertEqual(run().returncode, 2)

    def test_unknown_subcommand_is_a_usage_error(self):
        self.assertEqual(run("nope").returncode, 2)

    def test_help_lists_each_subcommand(self):
        done = run("--help")
        self.assertEqual(done.returncode, 0)
        for name in SUBCOMMANDS:
            self.assertIn(name, done.stdout)


class Imports(unittest.TestCase):
    def test_no_bytecode_left_in_the_bin_folder(self):
        shutil.rmtree(SCRIPT.parent / "__pycache__", ignore_errors=True)
        run("commit")
        self.assertFalse((SCRIPT.parent / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
