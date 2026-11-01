"""Tests for pdlc's change order check. Run: python3 -m unittest discover plugins/pdlc/tests"""
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

BIN = Path(__file__).parent.parent / "skills/init/references/bin"
spec = importlib.util.spec_from_file_location("check_order", BIN / "check_order.py")
check_order = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_order)

KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}

# The first lines of Interface entries, without the leading "- ".
MARK_DONE_KEY = "Store::mark_done(&self, id: u64) -> io::Result<bool>"
STORE = "`%s` · function · `src/store.rs` · proposed" % MARK_DONE_KEY
POST = "`POST /items/<id>/done` · route · `src/lib.rs` · proposed"
GET_ROOT = "`GET /` · route · `src/lib.rs`"
GET_ALL = "`GET /?show=all` · route · `src/lib.rs` · proposed"
BUTTON = "`Done button` · page element · `src/page.rs` · proposed"

STORE_LINE = "Given items 1 and 2, when mark_done(2) is called, then item 2 is done."
POST_LINE = "Given an open item 2, when a user sends `POST /items/2/done`, then the reply is 303 to `/`."
SHOW_LINE = 'Given that item is done, when the app restarts, then `GET /?show=all` shows "(done)" after its text.'
VIEW_LINE = 'Given a done item "a", when a user requests `GET /?show=all`, then the page shows "a (done)".'
PLAIN_LINE = "Given a thing, when a user acts, then it works."


def entry(first):
    """An Interface entry: the first line, then the in, out, and errors lines."""
    return "- %s\n  - in: nothing\n  - out: nothing\n  - errors: none" % first


def spec_file(root, spec_id, firsts):
    """Write a spec that has an Interface with these first lines."""
    path = root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(entry(first) for first in firsts)
    path.write_text("# %s · A spec\n\nStatus: active\n\n## Interface\n\n%s\n" % (spec_id, body))


def change_file(root, number, scope, lines, req="X.R1", relies=(), interface=(),
                status="planned", intent="IN-0001"):
    """Write pdlc/changes/CH-000n-a-change/change.md. The lines go under one requirement."""
    folder = root / "pdlc" / "changes" / ("CH-%04d-a-change" % number)
    folder.mkdir(parents=True, exist_ok=True)
    reqs = "### %s · A requirement\n\n%s" % (req, "\n".join("- " + line for line in lines))
    text = ("# CH-%04d · A change\n\nIntent: %s · Scope: %s · Status: %s · Ticket: none · "
            "Branch: none · Base: main\n\n## Requirements\n\n%s\n\n## Relies on\n\n%s\n\n"
            "## Interface\n\n%s\n" % (
                number, intent, scope, status, reqs,
                "\n".join("- %s (used, not changed)" % r for r in relies) or "- none",
                "\n".join(entry(first) for first in interface) or "- none"))
    (folder / "change.md").write_text(text)


class Base(unittest.TestCase):
    """An empty project in a temp folder, and helpers."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def listing(self, *numbers):
        lines = "\n".join("- CH-%04d · a change" % n for n in numbers)
        inbox = self.root / "pdlc" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / "IN-0001-mark-done.md").write_text(
            "# IN-0001 · Mark done\n\nStatus: planned\n\n## Changes\n\n%s\n\n## Notes\n\nnone\n"
            % lines)

    def run_check(self, *args):
        out = io.StringIO()
        argv = ["check_order.py", *(args or ("IN-0001",))]
        with redirect_stdout(out):
            code = check_order.main(argv, root=self.root)
        return code, out.getvalue()

    def as_command(self, with_merge=True):
        """Copy the scripts to <root>/pdlc/bin and run check_order.py there."""
        bin_dir = self.root / "pdlc" / "bin"
        bin_dir.mkdir(parents=True)
        for name in ("check_order.py", "check_merge.py")[: 2 if with_merge else 1]:
            shutil.copy(BIN / name, bin_dir / name)
        return subprocess.run([sys.executable, "pdlc/bin/check_order.py", "IN-0001"],
                              cwd=self.root, capture_output=True, text=True)


class Snapshot(Base):
    """A small copy of the todo-rust snapshot: CH-0001 store, CH-0002 mark done, CH-0003 view list."""

    def setUp(self):
        super().setUp()
        spec_file(self.root, "CAP-store", [STORE])
        spec_file(self.root, "JOB-mark-done", [POST])
        spec_file(self.root, "JOB-view-list", [GET_ROOT, GET_ALL, BUTTON])
        self.write_changes()
        self.listing(1, 2, 3)

    def write_changes(self, loop=False):
        change_file(self.root, 1, "CAP-store", [STORE_LINE], req="CAP-store.R1", interface=[STORE])
        change_file(self.root, 2, "JOB-mark-done", [POST_LINE, SHOW_LINE], req="JOB-mark-done.R1",
                    relies=["CAP-store"], interface=[POST, STORE])
        change_file(self.root, 3, "JOB-view-list", [VIEW_LINE], req="JOB-view-list.R1",
                    relies=["CAP-store"] + (["JOB-mark-done"] if loop else []),
                    interface=[GET_ROOT, GET_ALL] + ([POST] if loop else []))


class TheSnapshot(Snapshot):
    def test_a_change_before_the_change_that_builds_its_route_fails(self):
        code, out = self.run_check()
        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(len(lines), 2, out)
        self.assertTrue(lines[0].startswith("CH-0002 comes before CH-0003, but the line "), out)
        self.assertIn("JOB-mark-done.R1", lines[0])
        self.assertIn("`GET /?show=all`", lines[0])
        self.assertTrue(lines[0].endswith("which CH-0003 builds"), out)
        self.assertEqual(lines[1], "A good order: CH-0001, CH-0003, CH-0002")

    def test_the_good_order_passes_with_no_output(self):
        self.listing(1, 3, 2)
        self.assertEqual(self.run_check(), (0, ""))

    def test_two_changes_that_need_each_other_have_no_good_order(self):
        self.write_changes(loop=True)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("No order works, because these changes need each other: "
                      "CH-0002 → CH-0003 → CH-0002", out)
        self.assertNotIn("A good order", out)
        self.listing(1, 3, 2)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("CH-0003 comes before CH-0002, but its Interface lists "
                      "`POST /items/<id>/done`, which CH-0002 builds", out)
        self.assertIn("CH-0003 comes before CH-0002, but it relies on JOB-mark-done, "
                      "the scope of CH-0002", out)
        self.assertIn("No order works", out)
        self.assertNotIn("A good order", out)

    def test_the_relies_on_rule(self):
        change_file(self.root, 2, "JOB-mark-done", [POST_LINE], req="JOB-mark-done.R1",
                    relies=["CAP-store"], interface=[POST])
        self.listing(2, 1, 3)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertEqual(out.count("comes before"), 1, out)
        self.assertIn("CH-0002 comes before CH-0001, but it relies on CAP-store, "
                      "the scope of CH-0001", out)

    def test_the_interface_rule(self):
        change_file(self.root, 2, "JOB-mark-done", [POST_LINE], req="JOB-mark-done.R1",
                    relies=["CAP-store"], interface=[POST, GET_ALL])
        self.listing(1, 2, 3)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertEqual(out.count("comes before"), 1, out)
        self.assertIn("CH-0002 comes before CH-0003, but its Interface lists `GET /?show=all`, "
                      "which CH-0003 builds", out)

    def test_a_function_in_a_line(self):
        change_file(self.root, 2, "JOB-mark-done", ["Given item 2, when mark_done(2) is called, then it is done."],
                    req="JOB-mark-done.R1", interface=[POST])
        self.listing(2, 1, 3)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("CH-0002 comes before CH-0001, but the line", out)
        self.assertIn("uses `%s`, which CH-0001 builds" % MARK_DONE_KEY, out)

    def test_explain_prints_each_rule_and_the_exit_code_stays(self):
        code, out = self.run_check("IN-0001", "--explain")
        self.assertEqual(code, 1)
        self.assertIn("rule: CH-0002 needs CH-0003 (line rule: GET /?show=all)", out)
        self.assertIn("rule: CH-0002 needs CH-0001 (Relies on: CAP-store)", out)
        self.assertIn("rule: CH-0002 needs CH-0001 (Interface: %s)" % MARK_DONE_KEY, out)

    def test_explain_on_a_good_order_prints_only_rule_and_skip_lines(self):
        self.listing(1, 3, 2)
        code, out = self.run_check("IN-0001", "--explain")
        self.assertEqual(code, 0)
        for line in out.splitlines():
            self.assertTrue(line.startswith(("rule:", "skip:")), line)
        self.assertIn("rule:", out)
        self.assertIn("skip: Done button", out)

    def test_the_script_runs_as_a_command(self):
        result = self.as_command()
        self.assertEqual(result.returncode, 1)
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 2, result.stdout)
        self.assertTrue(lines[0].startswith("CH-0002 comes before CH-0003"))
        self.assertEqual(lines[1], "A good order: CH-0001, CH-0003, CH-0002")
        self.assertEqual(list((self.root / "pdlc" / "bin").glob("__pycache__")), [])

    def test_a_missing_check_merge_exits_with_2(self):
        result = self.as_command(with_merge=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn("pdlc/bin/check_merge.py is missing", result.stdout)

    def test_usage_errors(self):
        self.assertEqual(self.run_check("IN-0009"), (2, "IN-0009 is not in pdlc/inbox\n"))
        out = io.StringIO()
        with redirect_stdout(out):
            code = check_order.main(["check_order.py"], root=self.root)
        self.assertEqual(code, 2)
        self.assertEqual(out.getvalue().strip(),
                         "usage: python3 pdlc/bin/check_order.py IN-xxxx [--explain]")


class TheKinds(Base):
    """CH-0004 (scope JOB-builder) proposes an item. CH-0005 (scope JOB-user) is listed
    first and has one line. The check fails when the line uses the item."""

    def setUp(self):
        super().setUp()
        self.listing(5, 4)

    def build(self, *firsts):
        spec_file(self.root, "JOB-builder", list(firsts))
        change_file(self.root, 4, "JOB-builder", [PLAIN_LINE], req="JOB-builder.R1")

    def use(self, line, user_firsts=()):
        spec_file(self.root, "JOB-user", list(user_firsts))
        change_file(self.root, 5, "JOB-user", [line], req="JOB-user.R1")
        return self.run_check()[0]

    def uses(self, line, *firsts):
        """The exit code when CH-0004 proposes these entries and CH-0005 has this line."""
        self.build(*firsts)
        return self.use(line)

    def test_a_route_matches_each_style_of_placeholder(self):
        for key in ("`POST /items/<id>/done`", "`POST /items/{id}/done`", "`POST /items/:id/done`"):
            first = "%s · route · `src/lib.rs` · proposed" % key
            self.assertEqual(self.uses("When a user sends `POST /items/2/done`, then done.", first), 1, key)
            for line in ("When a user sends `POST /items/`, then done.",
                         "When a user sends `GET /items/2/done`, then done.",
                         "When a user sends `POST /items/2/done/more`, then done."):
                self.assertEqual(self.uses(line, first), 0, (key, line))

    def test_a_query_matches_its_own_key_and_the_key_without_a_query(self):
        root_key = "`GET /` · route · `src/lib.rs` · proposed"
        self.assertEqual(self.uses("Then `GET /?show=all` shows it.", GET_ALL), 1)
        self.assertEqual(self.uses("Then `GET /` shows it.", GET_ALL), 0)
        self.assertEqual(self.uses("Then `GET /?show=x` shows it.", root_key), 1)
        # A key with the same query wins over the key without a query.
        self.build(root_key)
        spec_file(self.root, "JOB-other", [GET_ALL])
        change_file(self.root, 6, "JOB-other", [PLAIN_LINE], req="JOB-other.R1")
        self.listing(5, 4, 6)
        self.use("Then `GET /?show=all` shows it.")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("which CH-0006 builds", out)
        self.assertNotIn("which CH-0004 builds", out)

    def test_a_function_needs_its_name_and_a_bracket_next_to_it(self):
        key = "`shown(x: u8) -> u8` · function · `src/a.rs` · proposed"
        self.assertEqual(self.uses("Then the page is shown (assumed) to the user.", key), 0)
        self.assertEqual(self.uses("When shown(2) is called, then it is 2.", key), 1)
        self.assertEqual(self.uses("When shown (2) is called, then it is 2.", key), 0)
        self.assertEqual(self.uses("When Page::shown(2) is called, then it is 2.", key), 1)

    def test_a_command_matches_a_flag_with_a_space_or_an_equals_sign(self):
        key = "`wordfreq --top N FILE` · command · `src/main.rs` · proposed"
        self.assertEqual(self.uses("When a user runs `wordfreq --top 3 a.txt`, then 3 words show.", key), 1)
        self.assertEqual(self.uses("When a user runs `wordfreq --top=3 a.txt`, then 3 words show.", key), 1)
        self.assertEqual(self.uses("When a user runs `wordfreq a.txt`, then all words show.", key), 0)
        self.assertEqual(self.uses("Then wordfreq --top 3 a.txt shows 3 words.", key), 0)

    def test_a_command_with_no_literal_word_matches_no_line(self):
        key = "`wordfreq FILE` · command · `src/main.rs` · proposed"
        self.assertEqual(self.uses("When a user runs `wordfreq --top 3 a.txt`, then it works.", key), 0)
        self.assertEqual(self.uses("When a user runs `wordfreq a.txt`, then it works.", key), 0)

    def test_the_command_with_the_most_literal_words_wins(self):
        self.build("`wordfreq --top N FILE` · command · `src/main.rs` · proposed")
        deeper = ["`wordfreq --top N --json FILE` · command · `src/main.rs`"]
        # The deeper key is existing code and wins, so the proposed key gives no rule.
        self.assertEqual(self.use("When a user runs `wordfreq --top 3 --json a.txt`, then it works.", deeper), 0)
        self.assertEqual(self.use("When a user runs `wordfreq --top 3 a.txt`, then it works.", deeper), 1)

    def test_a_seam_variable_matches_as_a_whole_word(self):
        key = "`WORDFREQ_NOW` · seam variable · `src/main.rs` · proposed"
        self.assertEqual(self.uses("Given WORDFREQ_NOW=2026-01-01, then it is 2026.", key), 1)
        self.assertEqual(self.uses("Given WORDFREQ_NOWX=2026-01-01, then it is 2026.", key), 0)
        self.assertEqual(self.uses("Given XWORDFREQ_NOW=2026-01-01, then it is 2026.", key), 0)

    def test_no_false_failure_when_the_key_has_no_proposed_mark(self):
        key = "`POST /items/<id>/done` · route · `src/lib.rs`"
        self.assertEqual(self.uses("When a user sends `POST /items/2/done`, then done.", key), 0)

    def test_no_false_failure_when_two_scope_specs_propose_the_key(self):
        self.build(POST)
        spec_file(self.root, "JOB-other", [POST])
        change_file(self.root, 6, "JOB-other", [PLAIN_LINE], req="JOB-other.R1")
        self.listing(5, 4, 6)
        self.assertEqual(self.use("When a user sends `POST /items/2/done`, then done."), 0)

    def test_no_false_failure_when_two_changes_propose_functions_with_one_name(self):
        self.build("`Store::mark_done(id: u64) -> bool` · function · `src/s.rs` · proposed")
        spec_file(self.root, "JOB-other", ["`Other::mark_done(id: u64) -> bool` · function · `src/o.rs` · proposed"])
        change_file(self.root, 6, "JOB-other", [PLAIN_LINE], req="JOB-other.R1")
        self.listing(5, 4, 6)
        self.assertEqual(self.use("When mark_done(2) is called, then it works."), 0)

    def test_no_false_failure_for_a_page_element_or_a_shape(self):
        self.assertEqual(self.uses("When a user clicks the Done button, then it is done.", BUTTON), 0)
        self.assertEqual(self.uses("Then the reply is Item { id: 2 }.",
                                   "`Item { id: u64 }` · type · `src/p.rs` · proposed"), 0)

    def test_no_false_failure_for_a_retire_requirement(self):
        self.build(POST)
        spec_file(self.root, "JOB-user", [])
        change_file(self.root, 5, "JOB-user", ["When a user sends `POST /items/2/done`, then done."],
                    req="JOB-user.R1 · Old (retire)")
        self.assertEqual(self.run_check()[0], 0)

    def test_no_false_failure_for_a_design_change(self):
        spec_file(self.root, "DES-errors", [POST])
        self.build(POST)
        change_file(self.root, 5, "DES-errors", ["When a user sends `POST /items/2/done`, then done."],
                    req="DES-errors.R1", relies=["JOB-builder"], interface=[POST])
        self.assertEqual(self.run_check()[0], 0)
        # A design change builds nothing: the proposed entry of its spec is not a builder.
        self.build()
        change_file(self.root, 5, "DES-errors", [PLAIN_LINE], req="DES-errors.R1")
        change_file(self.root, 4, "JOB-builder", ["When a user sends `POST /items/2/done`, then done."],
                    req="JOB-builder.R1")
        self.listing(4, 5)
        self.assertEqual(self.run_check()[0], 0)

    def test_five_lines_of_one_requirement_give_one_problem_line(self):
        self.build(GET_ALL)
        spec_file(self.root, "JOB-user", [])
        lines = ["Then `GET /?show=all` shows item %d." % n for n in range(5)]
        change_file(self.root, 5, "JOB-user", lines, req="JOB-user.R1")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertEqual(out.count("comes before"), 1, out)

    def test_one_use_that_matches_keys_of_two_changes_gives_no_rule(self):
        self.build("`POST /items/<id>/done` · route · `src/lib.rs` · proposed")
        spec_file(self.root, "JOB-other", ["`POST /items/{id}/done` · route · `src/lib.rs` · proposed"])
        change_file(self.root, 6, "JOB-other", [PLAIN_LINE], req="JOB-other.R1")
        self.listing(5, 4, 6)
        self.assertEqual(self.use("When a user sends `POST /items/2/done`, then done."), 0)

    def test_two_changes_with_one_scope_give_no_relies_on_rule(self):
        self.build()
        change_file(self.root, 6, "JOB-builder", [PLAIN_LINE], req="JOB-builder.R2")
        self.listing(5, 4, 6)
        spec_file(self.root, "JOB-user", [])
        change_file(self.root, 5, "JOB-user", [PLAIN_LINE], req="JOB-user.R1", relies=["JOB-builder"])
        self.assertEqual(self.run_check()[0], 0)

    def test_a_function_name_of_fewer_than_three_letters_is_not_matched(self):
        key = "`ab(x: u8) -> u8` · function · `src/a.rs` · proposed"
        self.assertEqual(self.uses("When ab(2) is called, then it is 2.", key), 0)
        key = "`abc(x: u8) -> u8` · function · `src/a.rs` · proposed"
        self.assertEqual(self.uses("When abc(2) is called, then it is 2.", key), 1)

    def test_a_placeholder_does_not_match_across_a_slash(self):
        key = "`POST /items/<id>/done` · route · `src/lib.rs` · proposed"
        self.assertEqual(self.uses("When a user sends `POST /items/a/b/done`, then done.", key), 0)

    def test_the_end_of_a_path_in_prose_loses_its_punctuation(self):
        key = "`POST /items/<id>/done` · route · `src/lib.rs` · proposed"
        for end in (".", ",", ";", ":"):
            self.assertEqual(self.uses("Then the app handles POST /items/2/done%s" % end, key), 1, end)

    def test_the_good_order_keeps_the_list_order(self):
        self.build("`POST /items/<id>/done` · route · `src/lib.rs` · proposed")
        spec_file(self.root, "JOB-user", [])
        spec_file(self.root, "JOB-free", [])
        change_file(self.root, 5, "JOB-user", ["When a user sends `POST /items/2/done`, then done."],
                    req="JOB-user.R1")
        change_file(self.root, 7, "JOB-free", [PLAIN_LINE], req="JOB-free.R1")
        change_file(self.root, 8, "JOB-free", [PLAIN_LINE], req="JOB-free.R2")
        self.listing(5, 7, 8, 4)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertTrue(out.endswith("A good order: CH-0007, CH-0008, CH-0004, CH-0005\n"), out)

    def test_explain_says_when_the_scope_spec_has_no_interface(self):
        spec = self.root / "pdlc" / "specs" / "jobs" / "JOB-builder.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("# JOB-builder · A spec\n\nStatus: active\n")
        change_file(self.root, 4, "JOB-builder", [PLAIN_LINE], req="JOB-builder.R1")
        spec_file(self.root, "JOB-user", [])
        change_file(self.root, 5, "JOB-user", [PLAIN_LINE], req="JOB-user.R1")
        code, out = self.run_check("IN-0001", "--explain")
        self.assertEqual(code, 0)
        self.assertIn("skip: CH-0004 has a scope spec with no Interface", out)

    def test_no_false_failure_when_the_scope_spec_has_no_interface(self):
        spec = self.root / "pdlc" / "specs" / "jobs" / "JOB-builder.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("# JOB-builder · A spec\n\nStatus: active\n")
        change_file(self.root, 4, "JOB-builder", [PLAIN_LINE], req="JOB-builder.R1")
        self.assertEqual(self.use("When a user sends `POST /items/2/done`, then done."), 0)


class TheList(Snapshot):
    def test_a_listed_change_with_no_spec(self):
        self.listing(1, 3, 2, 5)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('CH-0005 is in the "Changes" list of IN-0001, but pdlc/changes has no '
                      'change spec for it', out)

    def test_a_change_two_times_in_the_list(self):
        self.listing(1, 3, 2, 3)
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('CH-0003 is two times in the "Changes" list of IN-0001', out)

    def test_a_spec_that_the_list_leaves_out(self):
        self.listing(1, 3, 2)
        change_file(self.root, 4, "CAP-store", [PLAIN_LINE], req="CAP-store.R2")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn('CH-0004 has "Intent: IN-0001", but the "Changes" list of IN-0001 does '
                      'not name it', out)

    def test_a_spec_of_a_different_intent_is_no_problem(self):
        self.listing(1, 3, 2)
        change_file(self.root, 4, "CAP-store", [PLAIN_LINE], req="CAP-store.R2", intent="IN-0002")
        self.assertEqual(self.run_check(), (0, ""))

    def test_a_cancelled_change_gives_no_problem_and_no_rule(self):
        self.listing(1, 3, 2)
        change_file(self.root, 4, "CAP-store", [PLAIN_LINE], req="CAP-store.R2", status="cancelled")
        self.assertEqual(self.run_check(), (0, ""))
        self.listing(1, 3, 2, 4)
        self.assertEqual(self.run_check(), (0, ""))
        # A cancelled change builds nothing, and has no rule of its own.
        change_file(self.root, 3, "JOB-view-list", [VIEW_LINE], req="JOB-view-list.R1",
                    relies=["CAP-store"], interface=[GET_ROOT, GET_ALL], status="cancelled")
        self.listing(1, 2, 3)
        self.assertEqual(self.run_check(), (0, ""))


if __name__ == "__main__":
    unittest.main()
