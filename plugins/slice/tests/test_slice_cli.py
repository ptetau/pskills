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


if __name__ == "__main__":
    unittest.main()
