"""Tests of the parts of run_bench.py that do not call a model."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_bench  # noqa: E402

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
        verdict = run_bench.gate(result([2.0, 2.1]), result([1.2, 1.3]))
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))

    def test_a_saving_inside_the_noise_is_no_gain(self):
        verdict = run_bench.gate(result([2.0, 2.6]), result([2.1, 2.2]))
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

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


if __name__ == "__main__":
    unittest.main()
