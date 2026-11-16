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
        self.p.write("slice/001-wordfreq/spec.md", "# Spec\n\nStatus: draft\n")
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
        self.assertIn("next: stop S1: tests still fail", out)

    def test_all_done(self):
        self.p.slice("set", "S1", "done")
        self.p.slice("set", "S2", "done")
        self.assertIn("next: done", self.p.slice("status").stdout)


class Next(Base):
    def next(self, *args):
        r = self.p.slice(*args, "next") if args else self.p.slice("next")
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def test_prints_the_first_open_slice(self):
        self.assertEqual(self.next(), "build S1")

    def test_skips_a_done_slice(self):
        self.p.slice("set", "S1", "done")
        self.assertEqual(self.next(), "build S2")

    def test_prints_done_when_all_are_done(self):
        self.p.slice("set", "S1", "done")
        self.p.slice("set", "S2", "done")
        self.assertEqual(self.next(), "done")

    def test_prints_the_stop_with_its_reason(self):
        self.p.slice("set", "S2", "stopped", "--reason", "no review rounds left: 3 used")
        self.assertEqual(self.next(), "stop S2: no review rounds left: 3 used")

    def test_a_stop_comes_before_the_next_build(self):
        self.p.slice("set", "S2", "stopped", "--reason", "x")
        self.assertEqual(self.next(), "stop S2: x")

    def test_prints_the_stage_before_the_slices(self):
        self.p.write("slice/001-wordfreq/spec.md", "# Spec\n\nStatus: draft\n")
        self.assertEqual(self.next(), "spec")

    def test_planned_slices_need_the_interface_stage(self):
        self.p.slice("set", "S2", "planned")
        self.assertEqual(self.next(), "interface")

    def test_red_slices_with_uncommitted_tests_need_the_interface_commit(self):
        self.p.write("tests/test_more.py", "x = 1\n")
        self.assertEqual(self.next(), "interface")
        self.p.slice("commit", "interface")
        self.assertEqual(self.next(), "build S1")

    def test_a_missing_domain_comes_first(self):
        (self.p.root / "slice/001-wordfreq/domain.md").unlink()
        self.assertEqual(self.next(), "domain")

    def test_no_slice_folder(self):
        import tempfile, subprocess, sys
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(fixture.SLICE), "next"], cwd=d, capture_output=True,
                               text=True)
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "spec"))

    def test_status_ends_with_the_same_line(self):
        out = self.p.slice("status").stdout.strip().splitlines()[-1]
        self.assertEqual(out, "next: " + self.next())

    def test_prints_one_line_and_changes_nothing(self):
        before = self.p.read("slice/001-wordfreq/slices.md")
        r = self.p.slice("next")
        self.assertEqual(len(r.stdout.strip().splitlines()), 1)
        self.assertEqual(self.p.read("slice/001-wordfreq/slices.md"), before)


class SpecFolders(Base):
    def test_the_highest_number_is_the_current_spec(self):
        self.p.write("slice/002-other/spec.md", "# Spec\n\nStatus: draft\n")
        r = self.p.slice("status")
        self.assertIn("spec folder: 002-other", r.stdout)
        self.assertIn("next: spec", r.stdout)

    def test_the_spec_option_picks_a_folder_by_number_or_name(self):
        self.p.write("slice/002-other/spec.md", "# Spec\n\nStatus: draft\n")
        for ref in ("001", "001-wordfreq"):
            r = self.p.slice("--spec", ref, "status")
            self.assertIn("spec folder: 001-wordfreq", r.stdout, ref)
            self.assertIn("next: build S1", r.stdout)
        self.assertEqual(self.p.slice("--spec", "009", "status").returncode, 2)

    def test_set_writes_in_the_spec_folder(self):
        self.p.write("slice/002-other/spec.md", "# Spec\n")
        self.p.write("slice/002-other/slices.md", fixture.SLICES)
        self.p.slice("set", "S1", "building")
        self.assertIn("- Status: building\n", self.p.read("slice/002-other/slices.md"))
        self.assertIn("- Status: red\n", self.p.read("slice/001-wordfreq/slices.md"))

    def test_a_folder_that_is_not_numbered_is_not_a_spec(self):
        self.p.write("slice/notes/spec.md", "x")
        self.assertIn("spec folder: 001-wordfreq", self.p.slice("status").stdout)

    def test_no_spec_folder_asks_for_the_spec_stage(self):
        import shutil
        shutil.rmtree(self.p.root / "slice/001-wordfreq")
        r = self.p.slice("status")
        self.assertIn("next: spec", r.stdout)
        self.assertEqual(self.p.slice("set", "S1", "done").returncode, 2)


class Requirements(Base):
    def test_status_lists_the_requirements_no_slice_covers(self):
        self.p.write("slice/001-wordfreq/slices.md",
                     fixture.SLICES.replace("- Requirements: R2\n", ""))
        out = self.p.slice("status").stdout
        self.assertIn("uncovered by a slice: R2", out)
        self.assertIn("next: plan", out)

    def test_every_requirement_covered(self):
        out = self.p.slice("status").stdout
        self.assertIn("requirements: 2, uncovered by a slice: none", out)


class Domain(Base):
    def test_a_missing_domain_comes_before_the_interface(self):
        (self.p.root / "slice/001-wordfreq/domain.md").unlink()
        out = self.p.slice("status").stdout
        self.assertIn("domain: missing", out)
        self.assertIn("next: domain", out)

    def test_a_requirement_with_no_mapping_is_a_gap(self):
        self.p.write("slice/001-wordfreq/domain.md", "# Domain\n\n- R1: Text, WordCount\n- R2: GAP\n")
        out = self.p.slice("status").stdout
        self.assertIn("domain: gaps R2", out)
        self.assertIn("next: domain", out)

    def test_an_unfilled_mapping_is_a_gap(self):
        self.p.write("slice/001-wordfreq/domain.md", "# Domain\n\n- R1: <entities>\n")
        self.assertIn("domain: gaps R1, R2", self.p.slice("status").stdout)

    def test_a_mapped_domain_lets_the_run_go_on(self):
        out = self.p.slice("status").stdout
        self.assertIn("domain: mapped", out)
        self.assertIn("next: build S1", out)


class Set(Base):
    def test_writes_status_and_reason(self):
        r = self.p.slice("set", "S2", "building")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- Status: building\n", self.p.read("slice/001-wordfreq/slices.md").split("## S2")[1])
        self.assertIn("- Status: red\n", self.p.read("slice/001-wordfreq/slices.md").split("## S2")[0])
        self.p.slice("set", "S2", "stopped", "--reason", "limit")
        self.assertIn("- Status: stopped (limit)\n", self.p.read("slice/001-wordfreq/slices.md"))

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
        self.assertIn("- Test rounds: 5\n", self.p.read("slice/001-wordfreq/slices.md"))
        self.assertIn("- Status: stopped (", self.p.read("slice/001-wordfreq/slices.md"))

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
        self.assertIn("ERROR", r.stdout)
        self.assertIn("NotImplementedError", r.stdout)
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
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace(
            'self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})', "self.assertEqual(1, 1)"))
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


DOC_TESTS = '''import unittest

import wordfreq


class Words(unittest.TestCase):
    def test_S1_counts_words(self):
        """Given a b a, the count of a is 2."""
        self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})

    def test_S1_empty_text(self):
        """An empty text has no words."""
        self.assertEqual(wordfreq.count(""), {})

    def test_S2_top_word(self):
        """The top word of a b a is a."""
        self.assertEqual(wordfreq.top("a b a", 1), ["a"])
'''


class Docstrings(Base):
    def test_a_passing_docstring_test_is_counted(self):
        self.p.write("tests/test_wordfreq.py", DOC_TESTS)
        self.p.write("src/wordfreq.py", fixture.GOOD)
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1: 2 tests, 2 passed", r.stdout)
        self.assertIn("PASS test_S1_empty_text", r.stdout)
        self.assertNotIn("An empty text", r.stdout)

    def test_a_docstring_test_with_the_not_implemented_error_is_red(self):
        self.p.write("tests/test_wordfreq.py", DOC_TESTS)
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1 red: 2 tests", r.stdout)

    def test_a_failure_block_with_a_docstring_gives_its_message(self):
        self.p.write("tests/test_wordfreq.py", DOC_TESTS)
        self.p.write("src/wordfreq.py", "def count(text):\n    return {'a': 1}\n\n\ndef top(text, n):\n    return []\n")
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL test_S1_counts_words", r.stdout)
        self.assertIn("AssertionError", r.stdout)
        self.assertNotIn("Given a b a", r.stdout)

    def test_the_parser_reads_a_header_with_a_docstring(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("slice_cli", fixture.SLICE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = ("test_S1_a (m.W.test_S1_a)\nDoc one. ... ok\ntest_S1_b (m.W.test_S1_b)\nDoc two. ... ERROR\n\n"
               + "=" * 70 + "\nERROR: test_S1_b (m.W.test_S1_b)\nDoc two.\n" + "-" * 70
               + "\nTraceback (most recent call last):\n  File \"x.py\", line 1, in f\n    boom()\n"
               "NotImplementedError: not implemented\n\n" + "-" * 70 + "\nRan 2 tests\n")
        got = {r["name"]: r for r in mod.parse_unittest(out)}
        self.assertEqual(got["test_S1_a (m.W.test_S1_a)"]["status"], "pass")
        self.assertEqual(got["test_S1_b (m.W.test_S1_b)"]["message"], "NotImplementedError: not implemented")


class RedNeedsTheSurface(Base):
    def test_a_stub_that_returns_none_makes_a_broken_test(self):
        self.p.write("src/wordfreq.py", "def count(text):\n    return None\n\n\ndef top(text, n):\n    return None\n")
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace(
            'self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})',
            'self.assertEqual(list(wordfreq.count("a b a").items()), [("a", 2), ("b", 1)])'))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken: test_S1_counts_words", r.stdout)
        self.assertIn("AttributeError", r.stdout)

    def test_a_test_that_never_calls_the_surface_does_not_reach_it(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS.replace(
            'self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})', "self.assertEqual(1, 2)"))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not reach the surface: test_S1_counts_words", r.stdout)
        self.assertNotIn("S1 red:", r.stdout)

    def test_a_stub_that_returns_wrong_data_is_not_red(self):
        self.p.write("src/wordfreq.py", "def count(text):\n    return {}\n\n\ndef top(text, n):\n    return []\n")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not reach the surface", r.stdout)


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
        self.assertIn("- Status: done\n", self.p.read("slice/001-wordfreq/slices.md").split("## S2")[0])
        self.assertEqual(git(self.p.root, "status", "--porcelain").strip(), "")

    def test_refuses_failing_tests(self):
        self.p.slice("set", "S1", "review")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tests fail", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")
        self.assertIn("- Status: review\n", self.p.read("slice/001-wordfreq/slices.md"))

    def test_refuses_an_open_major_finding(self):
        self.make_ready()
        self.p.write("slice/001-wordfreq/review/S1.md", "# Review S1\n\n- minor: rename x\n- major: count ignores case\n")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("major finding", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")

    def test_minor_findings_do_not_block(self):
        self.make_ready()
        self.p.write("slice/001-wordfreq/review/S1.md", "# Review S1\n\n- minor: rename x\n")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)

    def test_refuses_a_slice_with_no_tests(self):
        self.p.write("tests/test_wordfreq.py", "import unittest\n")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)

    def test_refuses_a_stopped_or_done_slice(self):
        self.make_ready()
        self.p.slice("set", "S1", "stopped", "--reason", "x")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 1)

    def test_a_slice_commit_holds_no_tests_of_other_slices(self):
        self.make_ready()
        self.p.write("tests/test_wordfreq.py", fixture.TESTS + "\n# S2 more\n")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("commit interface", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")

    def test_the_interface_commit_holds_the_records_tests_and_stubs(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS + "\n# more\n")
        self.p.write("src/wordfreq.py", fixture.STUB + "\n# stub\n")
        r = self.p.slice("commit", "interface")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "Interface: 001-wordfreq")
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%b").strip().splitlines()[-1], "Slice: interface")
        files = git(self.p.root, "show", "--name-only", "--format=").split()
        self.assertIn("tests/test_wordfreq.py", files)
        self.assertIn("src/wordfreq.py", files)
        self.assertEqual(self.p.slice("commit", "interface").stdout.strip(), "interface: nothing to commit")

    def test_the_interface_commit_waits_for_red_slices(self):
        self.p.slice("set", "S2", "planned")
        r = self.p.slice("commit", "interface")
        self.assertEqual(r.returncode, 1)
        self.assertIn("S2", r.stderr)

    def test_the_slice_commit_after_the_interface_commit_holds_only_that_slice(self):
        self.p.write("tests/test_wordfreq.py", fixture.TESTS + "\n# more\n")
        self.assertEqual(self.p.slice("commit", "interface").returncode, 0)
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.slice("set", "S1", "review")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)
        files = git(self.p.root, "show", "--name-only", "--format=").split()
        self.assertEqual(sorted(f for f in files if not f.startswith("slice/")), ["src/wordfreq.py"])
        self.assertEqual(git(self.p.root, "status", "--porcelain").strip(), "")

    def test_commits_only_named_paths(self):
        self.make_ready()
        self.p.write("notes.txt", "keep me out\n")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)
        self.assertIn("notes.txt", git(self.p.root, "status", "--porcelain"))


NUMBERED = fixture.TESTS.replace("test_S1_", "test_001_S1_R1_").replace("test_S2_", "test_001_S2_R2_")

STUB_SHOUT = fixture.GOOD + '''

def shout(text):
    raise NotImplementedError("not implemented")
'''

SPEC2 = "# Spec: extra\n\nStatus: ratified\n\n## Requirements\n\n- R1 (shout): the program shouts a text.\n"
SLICES2 = ("# Slices\n\n## S1: Shout\n\n- Story: As a user, I shout.\n- Requirements: R1\n- Layers: core\n"
           "- Status: red\n- Test rounds: 0\n- Review rounds: 0\n")
TESTS2 = ("import unittest\n\nimport wordfreq\n\n\nclass Extra(unittest.TestCase):\n"
          "    def test_002_S1_R1_shouts(self):\n        self.assertEqual(wordfreq.shout(\"a\"), \"A\")\n")


class TwoSpecs(Base):
    """A second spec folder numbers its slices from S1 again: the test name holds the spec number."""

    def setUp(self):
        super().setUp()
        p = self.p
        p.write("tests/test_wordfreq.py", NUMBERED)
        p.write("src/wordfreq.py", STUB_SHOUT)
        p.write("tests/test_extra.py", TESTS2)
        p.write("slice/002-extra/spec.md", SPEC2)
        p.write("slice/002-extra/domain.md", "# Domain\n\n## Requirement map\n\n- R1: Text; boundary: caller\n")
        p.write("slice/002-extra/slices.md", SLICES2)
        p.write("slice/002-extra/interface.md", "# Interface\n\nStatus: approved\n\n## S1\n\n- shout(text)\n")
        p.slice("--spec", "001", "set", "S1", "done")
        p.slice("--spec", "001", "set", "S2", "done")
        git(p.root, "add", "-A")
        git(p.root, "commit", "-q", "-m", "second spec")

    def test_belongs_matches_the_spec_number_and_the_slice(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("slice_cli", fixture.SLICE)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        self.assertTrue(cli.belongs("test_002_S1_R2_counts_words", "S1", "002"))
        self.assertFalse(cli.belongs("test_001_S1_R2_counts_words", "S1", "002"))
        self.assertFalse(cli.belongs("test_002_S10_R2_x", "S1", "002"))
        self.assertFalse(cli.belongs("test_S1_R2_x", "S1", "002"))
        self.assertTrue(cli.belongs("test_S1_R2_x", "S1", "001", single=True))
        self.assertFalse(cli.belongs("test_002_S1_R2_x", "S1", "001", single=True))

    def test_the_tests_of_the_other_spec_are_not_mine(self):
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1 red: 1 tests", r.stdout)
        self.assertNotIn("001", r.stdout)

    def test_a_test_with_no_number_belongs_to_no_spec_when_there_are_two(self):
        self.p.write("tests/test_extra.py", TESTS2.replace("test_002_S1_R1", "test_S1_R1"))
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no tests found for S1", r.stdout)

    def test_the_spec_option_scopes_the_tests_to_that_spec(self):
        r = self.p.slice("--spec", "001", "test", "S1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1: 2 tests, 2 passed", r.stdout)


class Regressions(Base):
    def make_ready(self):
        self.p.write("src/wordfreq.py", fixture.GOOD.replace("return [w for w, _ in Counter(text.split()).most_common(n)]",
                                                             "return []"))
        self.p.slice("set", "S1", "review")

    def other_test(self, body):
        self.p.write("tests/test_other.py", "import unittest\n\n\nclass Old(unittest.TestCase):\n"
                                            "    def test_old_thing(self):\n        %s\n" % body)
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "old test")

    def test_a_failing_test_of_a_done_slice_blocks_the_commit(self):
        self.make_ready()
        self.p.slice("set", "S2", "done")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_S2_top_word", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")
        self.assertIn("- Status: review\n", self.p.read("slice/001-wordfreq/slices.md").split("## S2")[0])

    def test_a_failing_test_that_no_slice_owns_blocks_the_commit(self):
        self.make_ready()
        self.other_test("self.assertEqual(1, 2)")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("test_old_thing", r.stderr)

    def test_a_passing_test_that_no_slice_owns_is_fine(self):
        self.make_ready()
        self.other_test("self.assertEqual(1, 1)")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)

    def test_the_tests_of_a_slice_that_is_not_done_may_fail(self):
        self.make_ready()
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)

    def test_the_test_command_reports_the_regressions_after_its_own_results(self):
        self.make_ready()
        self.p.slice("set", "S2", "done")
        self.other_test("self.assertEqual(1, 2)")
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 1)
        own = r.stdout.index("PASS test_S1_counts_words")
        reg = r.stdout.index("regressions")
        self.assertLess(own, reg)
        self.assertIn("test_S2_top_word", r.stdout[reg:])
        self.assertIn("test_old_thing", r.stdout[reg:])
        self.assertNotIn("def test_", r.stdout)

    def test_no_regression_no_extra_output(self):
        self.make_ready()
        r = self.p.slice("test", "S1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("regressions", r.stdout)


class Resume(Base):
    def stop(self):
        for _ in range(5):
            self.p.slice("round", "S1", "test")
        self.p.slice("round", "S1", "review")
        r = self.p.slice("round", "S1", "test")
        self.assertEqual(r.returncode, 1)

    def test_a_stopped_slice_goes_back_to_building_with_no_rounds_used(self):
        self.stop()
        self.assertIn("stopped", self.p.slice("status").stdout)
        r = self.p.slice("resume", "S1")
        self.assertEqual(r.returncode, 0, r.stderr)
        block = self.p.read("slice/001-wordfreq/slices.md").split("## S2")[0]
        self.assertIn("- Status: building\n", block)
        self.assertIn("- Test rounds: 0\n", block)
        self.assertIn("- Review rounds: 0\n", block)
        self.assertEqual(self.p.slice("next").stdout.strip(), "build S1")
        self.assertEqual(self.p.slice("round", "S1", "test").returncode, 0)

    def test_only_a_stopped_slice_can_resume(self):
        for status in ("planned", "red", "building", "review", "done"):
            self.p.slice("set", "S1", status)
            r = self.p.slice("resume", "S1")
            self.assertEqual(r.returncode, 1, status)
            self.assertIn("not stopped", r.stderr)

    def test_an_unknown_slice_is_a_record_error(self):
        self.assertEqual(self.p.slice("resume", "S9").returncode, 2)


class InterfaceApproval(Base):
    def set_status(self, word):
        self.p.write("slice/001-wordfreq/interface.md",
                     fixture.INTERFACE.replace("Status: approved", "Status: %s" % word))

    def test_a_draft_interface_is_the_next_stage(self):
        self.set_status("draft")
        self.assertEqual(self.p.slice("next").stdout.strip(), "interface")
        self.assertIn("interface: draft", self.p.slice("status").stdout)

    def test_an_interface_with_no_status_is_a_draft(self):
        self.p.write("slice/001-wordfreq/interface.md", "# Interface\n\n## S1\n\n- x\n")
        self.assertEqual(self.p.slice("next").stdout.strip(), "interface")

    def test_a_missing_interface_is_the_next_stage(self):
        (self.p.root / "slice/001-wordfreq/interface.md").unlink()
        self.assertEqual(self.p.slice("next").stdout.strip(), "interface")
        self.assertIn("interface: missing", self.p.slice("status").stdout)

    def test_an_approved_interface_lets_the_build_start(self):
        self.assertEqual(self.p.slice("next").stdout.strip(), "build S1")
        self.assertIn("interface: approved", self.p.slice("status").stdout)

    def test_commit_interface_refuses_an_interface_that_is_not_approved(self):
        self.set_status("draft")
        self.p.write("tests/test_wordfreq.py", fixture.TESTS + "\n# more\n")
        r = self.p.slice("commit", "interface")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not approved", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "base")


CHANGED_TESTS = '''import unittest

import wordfreq


class Words(unittest.TestCase):
    def test_S1_R1_counts_words(self):
        self.assertEqual(wordfreq.count("a b a"), {"a": 2, "b": 1})

    def test_S2_R2_top_word(self):
        self.assertEqual(wordfreq.top("a b a", 1), ["a"])
'''
OLD_COUNT = ('def count(text):\n    return {}\n\n\ndef top(text, n):\n'
             '    raise NotImplementedError("not implemented")\n')


class Changed(Base):
    def setUp(self):
        super().setUp()
        self.p.write("src/wordfreq.py", OLD_COUNT)
        self.p.write("tests/test_wordfreq.py", CHANGED_TESTS)

    def mark(self, line):
        text = fixture.INTERFACE.replace("- count(text) -> dict\n- Changed: none", "- count(text) -> dict\n" + line)
        self.p.write("slice/001-wordfreq/interface.md", text)

    def test_a_plain_failure_is_not_red_for_an_unmarked_requirement(self):
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not reach the surface", r.stdout)

    def test_a_plain_failure_is_red_for_a_changed_requirement(self):
        self.mark("- Changed: R1")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("S1 red", r.stdout)

    def test_a_changed_requirement_may_be_in_a_list(self):
        self.mark("- Changed: R3, R1")
        self.assertEqual(self.p.slice("test", "S1", "--red").returncode, 0)

    def test_the_marker_covers_only_the_requirements_it_lists(self):
        self.mark("- Changed: R2")
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not reach the surface", r.stdout)

    def test_the_marker_of_another_slice_does_not_count(self):
        text = fixture.INTERFACE.replace("- top(text, n) -> list\n- Changed: none", "- top(text, n) -> list\n- Changed: R1")
        self.p.write("slice/001-wordfreq/interface.md", text)
        self.assertEqual(self.p.slice("test", "S1", "--red").returncode, 1)

    def test_a_pass_is_still_not_red(self):
        self.mark("- Changed: R1")
        self.p.write("src/wordfreq.py", fixture.GOOD)
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("passes already", r.stdout)

    def test_an_error_that_is_not_the_stub_error_is_still_broken(self):
        self.mark("- Changed: R1")
        self.p.write("tests/test_wordfreq.py", CHANGED_TESTS.replace("wordfreq.count(", "missing.count("))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("broken: ", r.stdout)

    def test_a_skip_is_still_not_red(self):
        self.mark("- Changed: R1")
        self.p.write("tests/test_wordfreq.py", CHANGED_TESTS.replace(
            "    def test_S1_R1_", "    @unittest.skip('later')\n    def test_S1_R1_"))
        r = self.p.slice("test", "S1", "--red")
        self.assertEqual(r.returncode, 1)
        self.assertIn("skipped", r.stdout)


class SourceFiles(Base):
    def setUp(self):
        super().setUp()
        self.p.write("slice/config.md", fixture.CONFIG + "- source files: `package.json`, `migrations/**`\n")
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "config")

    def test_commit_stages_the_source_files(self):
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.write("package.json", "{}\n")
        self.p.write("migrations/001_init.sql", "create table t(a);\n")
        self.p.write("notes.txt", "keep me out\n")
        self.p.slice("set", "S1", "review")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        files = git(self.p.root, "show", "--name-only", "--format=").split()
        self.assertIn("package.json", files)
        self.assertIn("migrations/001_init.sql", files)
        self.assertNotIn("notes.txt", files)

    def test_commit_interface_stages_the_source_files(self):
        self.p.write("package.json", "{}\n")
        self.p.write("migrations/001_init.sql", "create table t(a);\n")
        self.assertEqual(self.p.slice("commit", "interface").returncode, 0)
        files = git(self.p.root, "show", "--name-only", "--format=").split()
        self.assertIn("package.json", files)
        self.assertIn("migrations/001_init.sql", files)

    def test_a_source_file_pattern_never_stages_the_tests_folder(self):
        self.p.write("slice/config.md", fixture.CONFIG + "- source files: `**/*.py`\n")
        git(self.p.root, "add", "-A")
        git(self.p.root, "commit", "-q", "-m", "config")
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.write("tests/test_new.py", "x = 1\n")
        self.p.slice("set", "S1", "review")
        r = self.p.slice("commit", "S1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("commit interface", r.stderr)
        self.assertEqual(git(self.p.root, "log", "-1", "--format=%s").strip(), "config")
        self.assertIn("tests/test_new.py", git(self.p.root, "status", "--porcelain"))

    def test_none_means_no_source_files(self):
        self.p.write("slice/config.md", fixture.CONFIG + "- source files: none\n")
        self.p.write("none", "x\n")
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.slice("set", "S1", "review")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)
        self.assertNotIn("none", git(self.p.root, "show", "--name-only", "--format=").split())

    def test_the_config_without_the_line_works_as_before(self):
        self.p.write("slice/config.md", fixture.CONFIG)
        self.p.write("src/wordfreq.py", fixture.GOOD)
        self.p.write("package.json", "{}\n")
        self.p.slice("set", "S1", "review")
        self.assertEqual(self.p.slice("commit", "S1").returncode, 0)
        self.assertNotIn("package.json", git(self.p.root, "show", "--name-only", "--format=").split())


if __name__ == "__main__":
    unittest.main()
