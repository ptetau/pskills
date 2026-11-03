"""Tests for the red classifier in pdlclib and for `pdlc.py red`.
Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).parent.parent
BIN = PLUGIN / "skills/init/references/bin"
GIT_ENV = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "commit.gpgsign", "GIT_CONFIG_VALUE_0": "false"}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lib = load("pdlclib_red", BIN / "pdlclib.py")

ENTRIES = [
    ("Store::new(path: impl Into<PathBuf>) -> Store", False),
    ("Store::mark_done(&self, id: u64) -> io::Result<bool>", True),
    ("Item { id: u64, text: String, done: bool }", True),
]
REQS = ["CAP-store.R8", "CAP-store.R9"]
FILES = ["tests/store.rs", "tests/page.rs (only the `Item` literals)"]


def classify(output, exit_code=1, entries=ENTRIES, reqs=REQS, files=FILES, **kw):
    return lib.classify_red(entries, reqs, files, output, exit_code, **kw)


RUST_FIELD = """   Compiling todo v0.1.0 (/x)
error[E0560]: struct `Item` has no field named `done`
  --> tests/page.rs:13:60
   |
13 |     let html = render(&[Item { id: 1, text: "milk".into(), done: false }]);
   |                                                            ^^^^ `Item` does not have this field

For more information about this error, try `rustc --explain E0560`.
error: could not compile `todo` (test "page") due to 1 previous error
"""
RUST_METHOD = """error[E0599]: no method named `mark_done` found for struct `Store` in the current scope
  --> tests/store.rs:20:11
error: aborting due to 1 previous error
"""
RUST_IMPORT = """error[E0432]: unresolved import `todo::store::Archive`
 --> tests/store.rs:1:5
"""
RUST_MISSING_FIELDS = """error[E0063]: missing fields `done` and `text` in initializer of `Item`
 --> tests/store.rs:9:5
"""
RUST_MISMATCH = """error[E0308]: mismatched types
 --> tests/store.rs:9:5
"""
RUST_OLD_METHOD = """error[E0599]: no method named `remove` found for struct `Store` in the current scope
 --> tests/store.rs:20:11
"""


def libtest(*lines, running="tests/store.rs"):
    return "     Running %s (target/debug/deps/x-1)\nrunning %d tests\n%s\ntest result: FAILED.\n" % (
        running, len(lines), "\n".join("test %s ... %s" % l for l in lines))


class RustCompile(unittest.TestCase):
    def test_a_missing_field_of_a_proposed_shape_is_red_compile(self):
        got = classify(RUST_FIELD)
        self.assertEqual(got["verdict"], "red-compile")
        self.assertEqual(got["missing"], ["done"])

    def test_a_missing_method_is_red_compile(self):
        got = classify(RUST_METHOD)
        self.assertEqual((got["verdict"], got["missing"]), ("red-compile", ["mark_done"]))

    def test_all_missing_fields_must_match(self):
        self.assertEqual(classify(RUST_MISSING_FIELDS)["verdict"], "red-compile")

    def test_an_import_that_nothing_proposed_is_broken(self):
        got = classify(RUST_IMPORT)
        self.assertEqual(got["verdict"], "broken")
        self.assertIn("Archive", " ".join(got["evidence"]))

    def test_a_method_of_an_existing_entry_is_broken(self):
        self.assertEqual(classify(RUST_OLD_METHOD)["verdict"], "broken")

    def test_an_error_with_no_missing_name_is_broken(self):
        self.assertEqual(classify(RUST_MISMATCH)["verdict"], "broken")

    def test_one_good_and_one_bad_error_is_broken(self):
        self.assertEqual(classify(RUST_METHOD + RUST_IMPORT)["verdict"], "broken")

    def test_colour_codes_are_ignored(self):
        coloured = RUST_METHOD.replace("error[E0599]: ", "\x1b[0m\x1b[1m\x1b[38;5;9merror[E0599]\x1b[0m\x1b[1m: ")
        self.assertEqual(classify(coloured)["verdict"], "red-compile")


class RustRun(unittest.TestCase):
    def test_new_checks_fail_and_old_checks_pass_is_red(self):
        out = libtest(("cap_store_r8_done", "FAILED"), ("cap_store_r9_mark", "FAILED"), ("old_load", "ok"))
        self.assertEqual(classify(out)["verdict"], "red")

    def test_a_new_check_that_passes_is_broken(self):
        out = libtest(("cap_store_r8_done", "FAILED"), ("cap_store_r9_mark", "ok"))
        got = classify(out)
        self.assertEqual(got["verdict"], "broken")
        self.assertIn("CAP-store.R9", " ".join(got["evidence"]))

    def test_a_requirement_with_no_failing_check_is_broken(self):
        self.assertEqual(classify(libtest(("cap_store_r8_done", "FAILED")))["verdict"], "broken")

    def test_allow_pass_lets_an_existing_behaviour_check_pass(self):
        out = libtest(("cap_store_r8_done", "ok"), ("cap_store_r9_mark", "FAILED"))
        self.assertEqual(classify(out, allow_pass=["CAP-store.R8"])["verdict"], "red")

    def test_r1_does_not_match_r10(self):
        out = libtest(("cap_store_r10_x", "FAILED"))
        self.assertEqual(classify(out, reqs=["CAP-store.R1"])["verdict"], "broken")

    def test_a_failing_existing_check_is_broken(self):
        out = libtest(("cap_store_r8_done", "FAILED"), ("cap_store_r9_mark", "FAILED"), ("old_load", "FAILED"))
        got = classify(out)
        self.assertEqual(got["verdict"], "broken")
        self.assertIn("old_load", " ".join(got["evidence"]))

    def test_a_failure_in_a_file_outside_check_files_is_broken(self):
        out = libtest(("cap_store_r8_done", "FAILED"), ("cap_store_r9_mark", "FAILED")) + \
            libtest(("cap_store_r8_other", "FAILED"), running="tests/app.rs")
        self.assertEqual(classify(out)["verdict"], "broken")

    def test_a_time_out_is_broken(self):
        got = classify("running 1 test\n", exit_code=None)
        self.assertEqual(got["verdict"], "broken")
        self.assertIn("time limit", " ".join(got["evidence"]))

    def test_all_passing_is_broken(self):
        out = libtest(("cap_store_r8_done", "ok"), ("cap_store_r9_mark", "ok"))
        self.assertEqual(classify(out, exit_code=0)["verdict"], "broken")


PYTEST_COLLECT = """============================= test session starts ==============================
collected 0 items / 1 error

==================================== ERRORS ====================================
_______________________ ERROR collecting tests/test_store.py _______________________
tests/test_store.py:3: in <module>
    from todo.store import mark_done
E   ImportError: cannot import name 'mark_done' from 'todo.store' (/x/todo/store.py)
=========================== short test summary info ============================
ERROR tests/test_store.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
"""
PYTEST_ATTR = PYTEST_COLLECT.replace("ImportError: cannot import name 'mark_done' from 'todo.store' (/x/todo/store.py)",
                                     "AttributeError: module 'todo.store' has no attribute 'mark_done'")
PYTEST_NAME = PYTEST_COLLECT.replace("ImportError: cannot import name 'mark_done' from 'todo.store' (/x/todo/store.py)",
                                     "NameError: name 'Item' is not defined")
PYTEST_SYNTAX = PYTEST_COLLECT.replace("ImportError: cannot import name 'mark_done' from 'todo.store' (/x/todo/store.py)",
                                       "SyntaxError: invalid syntax")
PYTEST_MODULE = PYTEST_COLLECT.replace("ImportError: cannot import name 'mark_done' from 'todo.store' (/x/todo/store.py)",
                                       "ModuleNotFoundError: No module named 'todo.archive'")
PYENTRIES = [("todo.store.mark_done(store, id) -> bool", True), ("Item(id, text, done)", True)]
PYFILES = ["tests/test_store.py"]


def py(output, **kw):
    kw.setdefault("entries", PYENTRIES)
    kw.setdefault("files", PYFILES)
    return classify(output, **kw)


class PythonOutput(unittest.TestCase):
    def test_import_error_of_a_proposed_name_is_red_compile(self):
        self.assertEqual(py(PYTEST_COLLECT)["verdict"], "red-compile")

    def test_attribute_and_name_errors_are_red_compile(self):
        self.assertEqual(py(PYTEST_ATTR)["verdict"], "red-compile")
        self.assertEqual(py(PYTEST_NAME)["verdict"], "red-compile")

    def test_a_syntax_error_is_broken(self):
        self.assertEqual(py(PYTEST_SYNTAX)["verdict"], "broken")

    def test_a_missing_module_that_nothing_proposed_is_broken(self):
        self.assertEqual(py(PYTEST_MODULE)["verdict"], "broken")

    def test_unittest_failed_import(self):
        out = ("ERROR: tests.test_store (unittest.loader._FailedTest.tests.test_store)\n"
               "----------------------------------------------------------------------\n"
               "ImportError: Failed to import test module: tests.test_store\nTraceback (most recent call last):\n"
               "ImportError: cannot import name 'mark_done' from 'todo.store'\n\n"
               "----------------------------------------------------------------------\nRan 1 test in 0.0s\n\nFAILED (errors=1)\n")
        self.assertEqual(py(out)["verdict"], "red-compile")

    def test_pytest_verbose_run(self):
        out = ("============ test session starts ============\ncollected 3 items\n"
               "tests/test_store.py::test_CAP_store_R8_done FAILED [ 33%]\n"
               "tests/test_store.py::test_CAP_store_R9_mark FAILED [ 66%]\n"
               "tests/test_store.py::test_old PASSED [100%]\n=== 2 failed, 1 passed ===\n")
        self.assertEqual(py(out)["verdict"], "red")
        self.assertEqual(py(out.replace("test_old PASSED", "test_old FAILED"))["verdict"], "broken")

    def test_unittest_verbose_run(self):
        out = ("test_cap_store_r8_done (tests.test_store.T.test_cap_store_r8_done) ... FAIL\n"
               "test_cap_store_r9_mark (tests.test_store.T.test_cap_store_r9_mark) ... ERROR\n"
               "test_old (tests.test_store.T.test_old) ... ok\n\nRan 3 tests in 0.0s\n\nFAILED (failures=1, errors=1)\n")
        self.assertEqual(py(out)["verdict"], "red")


CLJ_SYMBOL = """Syntax error compiling at (todo/store_test.clj:12:5).
Unable to resolve symbol: mark-done! in this context

Full report at:
/tmp/clojure-1.edn
"""
CLJ_NS = """Syntax error (FileNotFoundException) compiling at (todo/store_test.clj:1:1).
Could not locate todo/archive__init.class, todo/archive.clj or todo/archive.cljc on classpath.
"""
CLJ_VAR = "Syntax error compiling at (todo/store_test.clj:12:5).\nNo such var: store/mark-done!\n"
CLJ_ARITY = "Syntax error (ArityException) compiling at (todo/store_test.clj:12:5).\nWrong number of args (3) passed to: todo.store/add\n"
CLJ_RUN = ("Testing todo.store-test\n\nFAIL in (cap-store-r8-done) (store_test.clj:10)\nexpected: true\n  actual: false\n\n"
           "ERROR in (cap-store-r9-mark) (store_test.clj:20)\nActual: java.lang.NullPointerException\n\n"
           "Ran 4 tests containing 5 assertions.\n2 failures, 0 errors.\n")
CLJENTRIES = [("(store/mark-done! store id)", True), ("(store/add store text)", False)]
CLJFILES = ["test/todo/store_test.clj"]


def clj(output, **kw):
    kw.setdefault("entries", CLJENTRIES)
    kw.setdefault("files", CLJFILES)
    return classify(output, **kw)


class ClojureOutput(unittest.TestCase):
    def test_an_unresolved_symbol_of_a_proposed_entry_is_red_compile(self):
        got = clj(CLJ_SYMBOL)
        self.assertEqual((got["verdict"], got["missing"]), ("red-compile", ["mark-done!"]))

    def test_a_no_such_var_is_red_compile(self):
        self.assertEqual(clj(CLJ_VAR)["verdict"], "red-compile")

    def test_a_missing_namespace_that_nothing_proposed_is_broken(self):
        self.assertEqual(clj(CLJ_NS)["verdict"], "broken")

    def test_a_compile_error_with_no_missing_name_is_broken(self):
        self.assertEqual(clj(CLJ_ARITY)["verdict"], "broken")

    def test_failures_of_the_new_checks_are_red(self):
        self.assertEqual(clj(CLJ_RUN)["verdict"], "red")

    def test_a_failure_of_an_old_check_is_broken(self):
        self.assertEqual(clj(CLJ_RUN.replace("cap-store-r9-mark", "old-load"))["verdict"], "broken")


class Unknown(unittest.TestCase):
    def test_an_unrecognised_output_is_unknown(self):
        got = classify("hello\nworld\n")
        self.assertEqual(got["verdict"], "unknown")
        self.assertIn("not recognised", " ".join(got["evidence"]))

    def test_an_empty_output_is_unknown(self):
        self.assertEqual(classify("", exit_code=0)["verdict"], "unknown")

    def test_a_failing_run_with_no_check_results_is_unknown(self):
        self.assertEqual(classify("running 0 tests\ntest result: FAILED.\n")["verdict"], "unknown")


CHANGE = """# CH-0001 · Done

Intent: IN-0001 · Scope: CAP-store · Status: testing · Ticket: none · Branch: b · Base: main
Tests-Locked: none

## Requirements

### CAP-store.R8 · An item has a done state

- Given x, then y.

### CAP-store.R2 · Old (retire)

- Given x, then y.

### CAP-store.R9 · Mark done

- Given x, then y.

## Interface

- `Store::mark_done(&self, id: u64) -> io::Result<bool>` · call · `src/store.rs`
  - in: id
- `Store::new(path: impl Into<PathBuf>) -> Store` · call · `src/store.rs`
- `Item { id: u64, done: bool }` · shared shape · `src/store.rs` · proposed

## Check files

- tests/store.rs
- `tests/page.rs` (only the literals)

## Steps
"""
SCOPE = """# CAP-store

## Interface

- `Store::mark_done(&self, id: u64) -> io::Result<bool>` · call · `src/store.rs` · proposed
- `Store::new(path: impl Into<PathBuf>) -> Store` · call · `src/store.rs`
- `Item { id: u64, done: bool }` · shared shape · `src/store.rs` · proposed
"""


class Inputs(unittest.TestCase):
    def test_the_inputs_come_from_the_change_and_its_scope(self):
        got = lib.red_inputs(CHANGE, SCOPE)
        self.assertEqual(got["reqs"], ["CAP-store.R8", "CAP-store.R9"])
        self.assertEqual(got["check_files"], ["tests/store.rs", "tests/page.rs"])
        self.assertEqual([p for _, p in got["entries"]], [True, False, True])

    def test_the_scope_alone_can_mark_an_entry(self):
        got = lib.red_inputs(CHANGE.replace(" · proposed", ""), SCOPE)
        self.assertEqual([p for _, p in got["entries"]], [True, False, True])

    def test_no_scope_text_leaves_the_change_marks(self):
        self.assertEqual([p for _, p in lib.red_inputs(CHANGE, "")["entries"]], [False, False, True])

    def test_checks_command(self):
        text = "## Checks\n\n- all: `cargo test`\n- one requirement: `cargo test {req}`\n"
        self.assertEqual(lib.checks_command(text), "cargo test")
        self.assertIsNone(lib.checks_command("## Checks\n\n- all: `...`\n"))
        self.assertIsNone(lib.checks_command("nothing"))


def git(root, *args):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=str(root),
                          capture_output=True, text=True, check=True, env=env).stdout.strip()


class Command(unittest.TestCase):
    """`pdlc.py red`, with a checks command that prints a canned output."""

    def project(self, output, code=1):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        files = {
            "pdlc/config.md": "## Checks\n\n- all: `cat out.txt; exit %d`\n" % code,
            "pdlc/changes/CH-0001-done/change.md": CHANGE,
            "pdlc/specs/capabilities/CAP-store.md": SCOPE,
            "out.txt": output,
        }
        for path, text in files.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_text(text)
        git(root, "init", "-q", "-b", "main")
        git(root, "add", "-A")
        git(root, "commit", "-qm", "x")
        return root

    def red(self, root, *args):
        return subprocess.run([sys.executable, str(BIN / "pdlc.py"), "red", "CH-0001", *args], cwd=str(root),
                              capture_output=True, text=True)

    def test_red_compile_exits_0_and_prints_the_missing_names(self):
        done = self.red(self.project(RUST_METHOD))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("red-compile", done.stdout)
        self.assertIn("mark_done", done.stdout)

    def test_broken_exits_1(self):
        done = self.red(self.project(RUST_IMPORT))
        self.assertEqual(done.returncode, 1)
        self.assertIn("broken", done.stdout)
        self.assertIn("Archive", done.stdout)

    def test_unknown_exits_3(self):
        done = self.red(self.project("hello\n"))
        self.assertEqual(done.returncode, 3)
        self.assertIn("unknown", done.stdout)

    def test_without_record_the_spec_stays(self):
        root = self.project(RUST_METHOD)
        self.red(root)
        self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_record_writes_one_red_line_under_the_lock_line(self):
        root = self.project(RUST_METHOD)
        self.assertEqual(self.red(root, "--record").returncode, 0)
        self.assertEqual(self.red(root, "--record").returncode, 0)
        lines = (root / "pdlc/changes/CH-0001-done/change.md").read_text().splitlines()
        self.assertEqual(sum(l.startswith("Red:") for l in lines), 1)
        at = lines.index(next(l for l in lines if l.startswith("Red:")))
        self.assertTrue(lines[at - 1].startswith("Tests-Locked:"))
        self.assertIn("red-compile", lines[at])
        self.assertIn("mark_done", lines[at])

    def test_record_writes_nothing_for_broken(self):
        root = self.project(RUST_IMPORT)
        self.assertEqual(self.red(root, "--record").returncode, 1)
        self.assertEqual(git(root, "status", "--porcelain"), "")

    def test_allow_pass_is_recorded(self):
        out = libtest(("cap_store_r8_done", "ok"), ("cap_store_r9_mark", "FAILED"))
        root = self.project(out)
        done = self.red(root, "--record", "--allow-pass", "CAP-store.R8")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("CAP-store.R8", (root / "pdlc/changes/CH-0001-done/change.md").read_text().split("Red:")[1].split("\n")[0])

    def test_an_unknown_change_is_a_contract_problem(self):
        root = self.project("x")
        done = subprocess.run([sys.executable, str(BIN / "pdlc.py"), "red", "CH-0009"], cwd=str(root),
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)


if __name__ == "__main__":
    unittest.main()
