"""Tests of the parts of run_bench.py that do not call a model."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_bench  # noqa: E402
import run_experiment  # noqa: E402

REFERENCE_CLI = '''
import sys
from wordfreq.counter import count_words

ERROR = "error: --top needs a whole number greater than zero"


def main(argv=None, stdout=None, stderr=None):
    args = list(sys.argv[1:] if argv is None else argv)
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    top = None
    if "--top" in args:
        at = args.index("--top")
        value = args[at + 1] if at + 1 < len(args) else ""
        del args[at:at + 2]
        if not value.isdigit() or int(value) < 1:
            print(ERROR, file=stderr)
            return 2
        top = int(value)
    if len(args) != 1:
        print("usage: wordfreq [--top N] FILE", file=stderr)
        return 2
    try:
        with open(args[0], encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        print("error: cannot read " + args[0], file=stderr)
        return 2
    for word, count in count_words(text)[:top]:
        print(word + " " + str(count), file=stdout)
    return 0
'''


def usage(inp=0, write=0, read=0, out=0):
    return {"input_tokens": inp, "cache_creation_input_tokens": write,
            "cache_creation": {"ephemeral_5m_input_tokens": write, "ephemeral_1h_input_tokens": 0},
            "cache_read_input_tokens": read, "output_tokens": out}


def assistant(t, mid, use, blocks=(), parent=None, model="m"):
    content = [{"type": "tool_use", "id": b[0], "name": b[1], "input": b[2]} for b in blocks]
    return {"t": t, "e": {"type": "assistant", "parent_tool_use_id": parent,
                          "message": {"id": mid, "model": model, "usage": use, "content": content}}}


def tool_result(t, tool_id):
    return {"t": t, "e": {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id}]}}}


class AnalyseTest(unittest.TestCase):
    def events(self):
        return [
            assistant(1, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:intake"})]),
            assistant(5, "m2", usage(10, 0, 100, 5)),
            assistant(10, "m3", usage(10, 0, 200, 5), [("s2", "Skill", {"skill": "pdlc:tests"})]),
            assistant(11, "m4", usage(10, 0, 300, 5), [("a1", "Agent", {"subagent_type": "pdlc:test-writer"})]),
            assistant(15, "m5", usage(20, 0, 50, 40), parent="a1"),
            tool_result(20, "a1"),
            {"t": 30, "e": {"type": "result", "total_cost_usd": 1.0, "duration_ms": 30000, "num_turns": 6,
                            "is_error": False, "modelUsage": {"m": {"costUSD": 1.0, "inputTokens": 60,
                            "outputTokens": 60, "cacheReadInputTokens": 650, "cacheCreationInputTokens": 0}},
                            "subagent_stats": {"spawned": 1}}},
        ]

    def test_messages_go_to_the_stage_that_was_active(self):
        result = run_bench.analyse(self.events())
        self.assertEqual(result["stages"]["intake"]["tokens"]["cache_read"], 100)
        self.assertEqual(result["stages"]["tests"]["tokens"]["cache_read"], 550)

    def test_an_agent_is_counted_under_its_stage_and_name(self):
        agent = run_bench.analyse(self.events())["stages"]["tests"]["agents"]["pdlc:test-writer"]
        self.assertEqual(agent["calls"], 1)
        self.assertEqual(agent["wall_s"], 9.0)
        self.assertEqual(agent["tokens"]["output"], 40)

    def test_stage_costs_add_up_to_the_total(self):
        result = run_bench.analyse(self.events())
        total = sum(stage["cost_usd"] for stage in result["stages"].values())
        self.assertAlmostEqual(total, 1.0, places=2)
        self.assertEqual(result["totals"]["cost_usd"], 1.0)

    def test_a_message_that_repeats_counts_once(self):
        events = self.events()
        events.insert(2, assistant(5, "m2", usage(10, 0, 100, 5)))
        self.assertEqual(run_bench.analyse(events)["stages"]["intake"]["messages"], 2)

    def test_stage_time_runs_to_the_next_stage(self):
        result = run_bench.analyse(self.events())
        self.assertEqual(result["stages"]["intake"]["wall_s"], 9.0)


def result(costs, probes=True, units=True, seeds=None, wall=100.0):
    return {"runs": [{"totals": {"cost_usd": c, "duration_s": wall}, "wall_s": wall,
                      "outcome": {"probes": {"passed": 8 if probes else 7, "total": 8}, "unit": {"ok": units}}}
                     for c in costs], "seeds": {"caught": seeds} if seeds is not None else {}}


class GateTest(unittest.TestCase):
    def test_a_clear_saving_with_the_same_results_is_kept(self):
        verdict = run_bench.gate(result([2.0, 2.1, 2.2, 2.0, 2.1]), result([1.2, 1.3, 1.1, 1.2, 1.3]))
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))
        self.assertLess(verdict["p"], 0.01)

    def test_a_saving_in_few_runs_is_not_kept_yet(self):
        verdict = run_bench.gate(result([2.0, 2.1, 2.2]), result([1.2, 1.3, 1.1]))
        self.assertTrue(verdict["verdict"].startswith("NEED MORE RUNS"))
        self.assertAlmostEqual(verdict["p"], 0.05)

    def test_a_saving_inside_the_noise_is_no_gain(self):
        verdict = run_bench.gate(result([2.0, 2.6, 1.8, 2.2, 2.0]), result([2.1, 2.2, 1.9, 2.4, 2.0]))
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

    def test_two_runs_each_are_too_few_to_show_a_saving(self):
        verdict = run_bench.gate(result([2.0, 2.1]), result([1.2, 1.3]))
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

    def test_the_chance_of_luck_is_exact(self):
        self.assertAlmostEqual(run_bench.permutation_p([3, 3, 3], [1, 1, 1]), 1 / 20)
        self.assertGreater(run_bench.permutation_p([1, 2, 3], [1, 2, 3]), 0.5)

    def test_a_run_that_did_not_finish_is_a_regression_even_when_cheaper(self):
        def finished(costs, ok):
            data = result(costs)
            for run in data["runs"]:
                run["outcome"]["merge_check"] = {"pdlc/CH-0001": ["ok   CH-0001" if ok else "FAIL CH-0001"]}
            return data
        verdict = run_bench.gate(finished([2.0, 2.1, 2.2], True), finished([1.0, 1.1, 1.2], False))
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("did not finish", verdict["reasons"][0])

    def test_a_failed_probe_is_a_regression_even_when_cost_falls(self):
        verdict = run_bench.gate(result([2.0]), result([1.0], probes=False))
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))

    def test_a_planted_defect_that_is_missed_is_a_regression(self):
        verdict = run_bench.gate(result([2.0], seeds=["a", "b"]), result([1.0], seeds=["a"]))
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("b", verdict["reasons"][0])

    def test_a_much_slower_run_is_a_regression(self):
        verdict = run_bench.gate(result([2.0], wall=100), result([1.0], wall=200))
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))

    def test_noise_is_zero_for_one_run(self):
        self.assertEqual(run_bench.noise([3.0]), 0.0)

    def test_noise_is_the_spread_over_the_mean(self):
        self.assertAlmostEqual(run_bench.noise([1.0, 3.0]), 1.0)


def agent_result(per_call, calls, totals, seeds=None):
    """A result whose runs each hold `calls` reviewer calls at `per_call` dollars."""
    runs = []
    for total in totals:
        runs.append({"totals": {"cost_usd": total, "duration_s": 100.0}, "wall_s": 100.0,
                     "stages": {"verify": {"agents": {"pdlc:reviewer": {"cost_usd": per_call * calls, "calls": calls}}}},
                     "outcome": {"probes": {"passed": 8, "total": 8}, "unit": {"ok": True}}})
    return {"runs": runs, "seeds": {"caught": seeds} if seeds is not None else {}}


class TargetGateTest(unittest.TestCase):
    def test_a_cheaper_agent_is_kept_even_when_whole_runs_vary_a_lot(self):
        baseline = agent_result(0.06, 7, [1.8, 2.5, 1.9])
        candidate = agent_result(0.005, 7, [1.6, 2.2])
        plain = run_bench.gate(baseline, candidate)
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(plain["verdict"].startswith("NO GAIN"))
        self.assertTrue(aimed["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(aimed["target"]["expected_run_saving"], 0.385, places=3)

    def test_a_whole_run_that_costs_much_more_is_a_regression(self):
        baseline = agent_result(0.06, 7, [1.8, 1.9])
        candidate = agent_result(0.005, 7, [2.9, 3.1])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_a_missed_defect_beats_a_cheaper_agent(self):
        baseline = agent_result(0.06, 7, [1.8, 1.9], seeds=["a", "b"])
        candidate = agent_result(0.005, 7, [1.0, 1.1], seeds=["a"])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_the_cost_of_a_call_is_the_cost_over_the_calls(self):
        stats = run_bench.agent_stats(agent_result(0.06, 7, [1.8, 2.5]), "pdlc:reviewer")
        self.assertAlmostEqual(stats["per_call"], 0.06)
        self.assertEqual(stats["calls"], 14)


class ProbeTest(unittest.TestCase):
    def copy_fixture(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        app = folder / "app"
        shutil.copytree(run_bench.FIXTURE, app, ignore=shutil.ignore_patterns("__pycache__", "pdlc"))
        return app

    def test_the_fixture_before_the_change_fails_the_new_probes(self):
        outcome = run_bench.run_probes(self.copy_fixture())
        self.assertEqual(outcome["passed"], 1)
        self.assertEqual(outcome["total"], len(run_bench.PROBES))

    def test_a_correct_change_passes_every_probe(self):
        app = self.copy_fixture()
        (app / "wordfreq" / "cli.py").write_text(REFERENCE_CLI)
        outcome = run_bench.run_probes(app)
        self.assertEqual(outcome["failed"], [])

    def test_an_option_that_only_works_before_the_file_still_passes(self):
        app = self.copy_fixture()
        source = REFERENCE_CLI.replace('        at = args.index("--top")\n', '        at = args.index("--top")\n        if at != 0:\n            print("usage: wordfreq [--top N] FILE", file=stderr)\n            return 2\n')
        (app / "wordfreq" / "cli.py").write_text(source)
        outcome = run_bench.run_probes(app)
        self.assertEqual(outcome["failed"], [])
        self.assertEqual(len(outcome["option_after_file_failed"]), 7)

    def test_the_project_checks_pass_on_the_fixture(self):
        self.assertTrue(run_bench.run_unit_checks(self.copy_fixture())["ok"])


class SeedTest(unittest.TestCase):
    spec = run_bench.json.loads((run_bench.SEEDS / "seeds.json").read_text())

    def test_a_result_with_problems_is_read(self):
        text = "Result: fail\n\nRemit: security\n\nProblems:\n- cli.py:9 · eval of user input · rule\n\nFollow-ups: none\n"
        parsed = run_bench.parse_result(text)
        self.assertEqual(parsed["verdict"], "fail")
        self.assertIn("eval", parsed["problems"])
        self.assertNotIn("Follow-ups", parsed["problems"])

    def test_a_result_with_no_problems_is_a_pass(self):
        parsed = run_bench.parse_result("Result: pass\n\nRemit: x\n\nProblems: none\n\nFollow-ups:\n- more\n")
        self.assertEqual(parsed, {"verdict": "pass", "problems": ""})

    def test_a_defect_is_caught_only_when_the_reviewer_fails_and_names_it(self):
        results = {
            "security": {"verdict": "fail", "problems": "- cli.py · eval of the value · rule"},
            "privacy": {"verdict": "pass", "problems": ""},
            "quality": {"verdict": "fail", "problems": "- cli.py · a name is unclear · rule"},
        }
        caught, missed = run_bench.score_seeds(self.spec, results)
        self.assertEqual(caught, ["security-eval"])
        self.assertIn("privacy-log", missed)
        self.assertIn("quality-dead-code", missed)
        self.assertIn("tests-weak-check", missed)

    def build(self, seeded):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        return run_bench.build_seed_project(folder / "app", run_bench.DEFAULT_PLUGIN, seeded)

    def test_the_clean_copy_passes_the_probes_and_its_own_checks(self):
        project = self.build(False)
        self.assertEqual(run_bench.run_probes(project)["failed"], [])
        self.assertTrue(run_bench.run_unit_checks(project)["ok"])

    def test_each_planted_defect_is_in_the_packet_of_its_reviewer(self):
        project = self.build(True)
        remits = sorted({seed["remit"] for seed in self.spec["seeds"]})
        run_bench.make_seed_packets(project, remits)
        marks = {"security": "eval(top)", "privacy": "wordfreq-usage", "quality": "_parse_top_old",
                 "specification": "return 1", "tests": 'self.assertEqual(out, "", argv)\n\n'}
        folder = project / "pdlc" / "changes" / "CH-0001-top-option" / "review"
        for remit, mark in marks.items():
            self.assertIn(mark, (folder / remit / "packet.md").read_text(), remit)


class ExperimentSpecTest(unittest.TestCase):
    def write(self, **fields):
        spec = {"id": "r3-test", "hypothesis": "a hypothesis", "lever": "a lever",
                "edits": [{"file": "agents/reviewer.md", "find": "tools: Read, Write", "replace": "tools: Read, Write, Glob"}]}
        spec.update(fields)
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        path = folder / "spec.json"
        path.write_text(run_bench.json.dumps(spec))
        return path

    def test_a_good_spec_gets_its_defaults(self):
        spec = run_experiment.load_spec(self.write())
        self.assertEqual((spec["runs"], spec["seeds"], spec["target"]), (6, False, None))
        self.assertEqual(spec["baseline"], "bench/baseline.json")

    def test_a_bad_spec_names_each_problem(self):
        with self.assertRaises(run_experiment.SpecError) as caught:
            run_experiment.load_spec(self.write(id="Bad Id", edits=[]))
        self.assertIn('"id"', str(caught.exception))
        self.assertIn('"edits"', str(caught.exception))

    def test_an_edit_that_changes_nothing_is_refused(self):
        edits = [{"file": "agents/reviewer.md", "find": "x", "replace": "x"}]
        with self.assertRaises(run_experiment.SpecError):
            run_experiment.load_spec(self.write(edits=edits))

    def test_edits_apply_to_a_copy_and_not_to_the_plugin(self):
        spec = run_experiment.load_spec(self.write())
        scratch = run_experiment.apply_edits(spec)
        self.addCleanup(shutil.rmtree, scratch.parent, True)
        self.assertIn("tools: Read, Write, Glob", (scratch / "agents" / "reviewer.md").read_text())
        self.assertNotIn("Glob", (run_experiment.PLUGIN / "agents" / "reviewer.md").read_text().split("---")[1])

    def test_a_find_text_that_is_not_there_is_refused(self):
        edits = [{"file": "agents/reviewer.md", "find": "no such text anywhere", "replace": "y"}]
        spec = run_experiment.load_spec(self.write(edits=edits))
        with self.assertRaises(run_experiment.SpecError) as caught:
            run_experiment.apply_edits(spec)
        self.assertIn("0 times", str(caught.exception))

    def test_a_find_text_that_occurs_twice_is_refused(self):
        edits = [{"file": "agents/reviewer.md", "find": "the", "replace": "y"}]
        spec = run_experiment.load_spec(self.write(edits=edits))
        with self.assertRaises(run_experiment.SpecError):
            run_experiment.apply_edits(spec)

    def test_check_reports_new_writing_findings(self):
        long_sentence = " ".join(["word"] * 40) + "."
        edits = [{"file": "skills/verify/SKILL.md", "find": "# pdlc verify\n", "replace": "# pdlc verify\n\n" + long_sentence + "\n"}]
        spec = run_experiment.load_spec(self.write(edits=edits))
        scratch, report, diff = run_experiment.check(spec, run_tests=False)
        self.addCleanup(shutil.rmtree, scratch.parent, True)
        self.assertIn("NEW FINDINGS", report)
        self.assertIn("+" + long_sentence, diff)


if __name__ == "__main__":
    unittest.main()
