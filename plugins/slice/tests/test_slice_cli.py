"""Tests for bin/slice.py. Run: (cd plugins/slice && python3 -m unittest discover -s tests)"""
import unittest

import fixture
from fixture import Project, git


class Base(unittest.TestCase):
    def setUp(self):
        self.p = Project()
        self.addCleanup(self.p.close)


class Status(Base):
    def test_shows_each_slice_and_the_next_stage(self):
        r = self.p.slice("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("spec: ratified", r.stdout)
        self.assertIn("S1 red", r.stdout)
        self.assertIn("S2 red", r.stdout)
        self.assertIn("next: build S1", r.stdout)

    def test_draft_spec_comes_first(self):
        self.p.write("slice/spec.md", "# Spec\n\nStatus: draft\n")
        self.assertIn("next: spec", self.p.slice("status").stdout)

    def test_planned_slices_need_the_interface_stage(self):
        self.p.slice("set", "S2", "planned")
        self.assertIn("next: interface", self.p.slice("status").stdout)

    def test_no_slice_folder(self):
        import tempfile, subprocess, sys
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(fixture.SLICE), "status"], cwd=d, capture_output=True,
                               text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("next: spec", r.stdout)

    def test_stopped_slice_is_reported_for_the_user(self):
        self.p.slice("set", "S1", "stopped", "--reason", "tests still fail")
        out = self.p.slice("status").stdout
        self.assertIn("stopped", out)
        self.assertIn("tests still fail", out)
        self.assertIn("next: ask the user about S1", out)

    def test_all_done(self):
        self.p.slice("set", "S1", "done")
        self.p.slice("set", "S2", "done")
        self.assertIn("next: all slices done", self.p.slice("status").stdout)


class Set(Base):
    def test_writes_status_and_reason(self):
        r = self.p.slice("set", "S2", "building")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- Status: building\n", self.p.read("slice/slices.md").split("## S2")[1])
        self.assertIn("- Status: red\n", self.p.read("slice/slices.md").split("## S2")[0])
        self.p.slice("set", "S2", "stopped", "--reason", "limit")
        self.assertIn("- Status: stopped (limit)\n", self.p.read("slice/slices.md"))

    def test_rejects_unknown_status_and_slice(self):
        self.assertEqual(self.p.slice("set", "S1", "nope").returncode, 2)
        self.assertEqual(self.p.slice("set", "S9", "done").returncode, 2)


class Rounds(Base):
    def test_test_rounds_stop_at_five(self):
        for n in range(1, 6):
            r = self.p.slice("round", "S1", "test")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("round %d of 5" % n, r.stdout)
        r = self.p.slice("round", "S1", "test")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no test rounds left", r.stderr)
        self.assertIn("- Test rounds: 5\n", self.p.read("slice/slices.md"))
        self.assertIn("- Status: stopped (", self.p.read("slice/slices.md"))

    def test_review_rounds_stop_at_three(self):
        for n in range(1, 4):
            self.assertEqual(self.p.slice("round", "S1", "review").returncode, 0)
        r = self.p.slice("round", "S1", "review")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no review rounds left", r.stderr)

    def test_the_two_counts_are_separate_and_per_slice(self):
        for _ in range(3):
            self.p.slice("round", "S1", "review")
        self.assertEqual(self.p.slice("round", "S1", "test").returncode, 0)
        self.assertEqual(self.p.slice("round", "S2", "review").returncode, 0)

    def test_bad_kind(self):
        self.assertEqual(self.p.slice("round", "S1", "lunch").returncode, 2)


class TestCommand(Base):
    def test_prints_names_and_messages_and_no_source(self):
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_S1_counts_words", r.stdout)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("AssertionError", r.stdout)
        self.assertNotIn("test_S2_top_word", r.stdout)
        out = r.stdout + r.stderr
        self.assertNotIn('wordfreq.count("a b a")', out)
        self.assertNotIn("self.assertEqual", out)
        self.assertNotIn("def test_", out)
        self.assertNotIn("File \"", out)

    def test_passes_when_the_code_is_right(self):
        self.p.write("src/wordfreq.py", fixture.GOOD)
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PASS test_S1_counts_words", r.stdout)
        self.assertIn("2 passed", r.stdout)

    def test_import_error_in_the_code_is_reported_by_message(self):
        self.p.write("src/wordfreq.py", "def count(:\n")
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("SyntaxError", r.stdout)
        self.assertNotIn("def count(:", r.stdout)

    def test_no_tests_for_the_slice(self):
        self.p.write("tests/test_wordfreq.py", "import unittest\n")
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no tests found for S1", r.stdout)

    def test_s1_does_not_match_s10(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace("test_S2_top_word", "test_S10_top_word"))
        self.p.write("src/wordfreq.py", fixture.GOOD)
        r = self.p.slice("test", "S1")
        self.assertIn("2 passed", r.stdout)
        self.assertNotIn("S10", r.stdout)

    def test_junit_format(self):
        runner = (
            "import sys\n"
            "open(sys.argv[1], 'w').write('''<testsuites><testsuite>"
            "<testcase classname=\"t\" name=\"test_S1_a\"/>"
            "<testcase classname=\"t\" name=\"test_S1_b\"><failure message=\"expected 2, got 0\">"
            "assert f(x) == 2</failure></testcase>"
            "<testcase classname=\"t\" name=\"test_S2_c\"><error message=\"boom\" type=\"RuntimeError\"/>"
            "</testcase></testsuite></testsuites>''')\n")
        self.p.write("fake.py", runner)
        cfg = fixture.CONFIG.replace("PYTHONPATH=src python3 -m unittest discover -s tests -v",
                                     "python3 fake.py {junit}").replace("unittest\n- tests", "junit\n- tests")
        self.p.write("slice/config.md", cfg)
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("PASS t::test_S1_a", r.stdout)
        self.assertIn("FAIL t::test_S1_b", r.stdout)
        self.assertIn("expected 2, got 0", r.stdout)
        self.assertNotIn("assert f(x)", r.stdout)
        self.assertNotIn("test_S2_c", r.stdout)


class Red(Base):
    def test_red_when_each_test_fails_for_missing_behaviour(self):
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1 red: 2 tests fail", r.stdout)

    def test_not_implemented_stub_counts_as_red(self):
        self.p.write("src/wordfreq.py", "def count(text):\n    raise NotImplementedError\n\n\n"
                                        "def top(text, n):\n    raise NotImplementedError\n")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_a_passing_test_is_not_red(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace('{"a": 2, "b": 1})', "None)"))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("passes already", r.stdout)

    def test_import_error_is_broken(self):
        self.p.write("tests/test_wordfreq.py", "import unittest\nimport nothere\n\n\nclass W(unittest.TestCase):\n"
                                               "    def test_S1_x(self):\n        pass\n")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken", r.stdout)
        self.assertIn("ModuleNotFoundError", r.stdout)

    def test_syntax_error_in_a_test_is_broken(self):
        self.p.write("tests/test_wordfreq.py", "def test_S1_x(:\n")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken", r.stdout)
        self.assertNotIn("def test_S1_x(:", r.stdout)

    def test_error_inside_the_test_is_broken(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace('self.assertEqual(wordfreq.count(""), {})',
                                                                     "self.assertEqual(missing_fixture, {})"))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken: test_S1_empty_text", r.stdout)
        self.assertIn("NameError", r.stdout)

    def test_no_tests_is_not_red(self):
        self.p.write("tests/test_wordfreq.py", "import unittest\n")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no tests found for S1", r.stdout)


class Commit(Base):
    def make_ready(self):
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.slice("set", "S1", "review")

    def test_commits_with_subject_and_trailer(self):
        self.make_ready()
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "Slice S1: Count words")
        body = git(self.p.root, "log", "-1", "--format=%b").strip()
        self.assertEqual(body.splitlines()[-1], "Slice: S1")
        self.assertIn("- Status: done\n", self.p.read("slice/slices.md").split("## S2")[0])
        self.assertEqual(git(self.p.root, "status", "--porcelain").strip(), "")

    def test_refuses_failing_tests(self):
        self.p.slice("set", "S1", "review")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tests fail", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")
        self.assertIn("- Status: review\n", self.p.read("slice/slices.md"))

    def test_refuses_an_open_major_finding(self):
        self.make_ready()
        self.p.write("slice/review/S1.md", "# Review S1\n\n- minor: rename x\n- major: count ignores case\n")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("major finding", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")

    def test_minor_findings_do_not_block(self):
        self.make_ready()
        self.p.write("slice/review/S1.md", "# Review S1\n\n- minor: rename x\n")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)

    def test_refuses_a_slice_with_no_tests(self):
        self.p.write("tests/test_wordfreq.py", "import unittest\n")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)

    def test_refuses_a_stopped_or_done_slice(self):
        self.make_ready()
        self.p.slice("set", "S1", "stopped", "--reason", "x")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 1)

    def test_commits_only_named_paths(self):
        self.make_ready()
        self.p.write("notes.txt", "keep me out\n")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)
        self.assertIn("notes.txt", git(self.p.root, "status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
