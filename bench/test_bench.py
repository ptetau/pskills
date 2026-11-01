"""Tests of the parts of run_bench.py that do not call a model."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402
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


class RepeatedStageTest(unittest.TestCase):
    """With two changes, each change stage runs twice. Its time is the sum of both visits."""

    def test_a_stage_that_runs_twice_gets_the_time_of_both_visits(self):
        events = [
            assistant(10, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:build"})]),
            assistant(20, "m2", usage(10, 0, 0, 5), [("s2", "Skill", {"skill": "pdlc:verify"})]),
            assistant(25, "m3", usage(10, 0, 0, 5), [("s3", "Skill", {"skill": "pdlc:build"})]),
            assistant(40, "m4", usage(10, 0, 0, 5), [("s4", "Skill", {"skill": "pdlc:verify"})]),
            assistant(42, "m5", usage(10, 0, 0, 5)),
            {"t": 43, "e": {"type": "result", "total_cost_usd": 1.0, "duration_ms": 43000, "num_turns": 5,
                            "is_error": False, "modelUsage": {"m": {"costUSD": 1.0}}, "subagent_stats": {}}},
        ]
        stages = run_bench.analyse(events)["stages"]
        self.assertEqual(stages["build"]["wall_s"], 25.0)
        self.assertEqual(stages["verify"]["wall_s"], 7.0)


class StageAgentTest(unittest.TestCase):
    """Ship can run each stage in a pdlc:stage agent. The agents of that stage run inside it."""

    def events(self):
        def stage_call(stage, work):
            return {"subagent_type": "pdlc:stage",
                    "prompt": "Project root: /app\nStage: %s\nSkill file: /p/skills/%s/SKILL.md\nWork: %s"
                              % (stage, stage, work)}
        return [
            assistant(1, "m1", usage(10, 0, 100, 5), [("g1", "Agent", stage_call("acceptance", "IN-0001"))]),
            assistant(2, "m2", usage(20, 0, 50, 5), [("a1", "Agent", {"subagent_type": "pdlc:test-writer",
                                                                      "prompt": "Write pdlc/acceptance/IN-0001"})],
                      parent="g1"),
            assistant(3, "m3", usage(20, 0, 50, 40), parent="a1"),
            tool_result(10, "a1"),
            tool_result(12, "g1"),
            assistant(13, "m4", usage(10, 0, 100, 5), [("g2", "Agent", stage_call("tests", "CH-0001"))]),
            assistant(14, "m5", usage(20, 0, 50, 5), [("a2", "Agent", {"subagent_type": "pdlc:test-writer",
                                                                       "prompt": "Write the checks of CH-0001"})],
                      parent="g2"),
            assistant(15, "m6", usage(20, 0, 50, 10), parent="a2"),
            tool_result(20, "a2"),
            tool_result(25, "g2"),
            assistant(26, "m7", usage(10, 0, 100, 5)),
            {"t": 27, "e": {"type": "result", "total_cost_usd": 1.0, "duration_ms": 27000, "num_turns": 7,
                            "is_error": False, "modelUsage": {"m": {"costUSD": 1.0}},
                            "subagent_stats": {"spawned": 4}}},
        ]

    def test_a_stage_agent_starts_the_stage_that_its_prompt_names(self):
        stages = run_bench.analyse(self.events())["stages"]
        self.assertEqual(stages["acceptance"]["agents"]["pdlc:stage"]["calls"], 1)
        self.assertEqual(stages["tests"]["agents"]["pdlc:stage"]["calls"], 1)

    def test_agents_that_a_stage_agent_starts_count_under_its_stage(self):
        stages = run_bench.analyse(self.events())["stages"]
        self.assertEqual(stages["acceptance"]["agents"]["pdlc:test-writer"]["tokens"]["output"], 40)
        self.assertEqual(stages["tests"]["agents"]["pdlc:test-writer"]["tokens"]["output"], 10)

    def test_stage_time_runs_from_one_stage_agent_to_the_next(self):
        stages = run_bench.analyse(self.events())["stages"]
        self.assertEqual(stages["acceptance"]["wall_s"], 12.0)

    def test_the_visual_reviewer_counts_toward_show(self):
        prompt = "/app/pdlc/changes/CH-0001-top/review/visual/packet.md"
        self.assertEqual(run_bench.agent_stage("pdlc:reviewer", prompt, "verify"), "show")
        self.assertEqual(run_bench.agent_stage("pdlc:reviewer", prompt.replace("visual", "quality"), "show"),
                         "verify")

    def test_a_stage_line_that_names_no_stage_keeps_the_current_stage(self):
        self.assertEqual(run_bench.agent_stage("pdlc:stage", "Stage: lunch", "build"), "build")

    def test_the_forward_flag_streams_the_messages_of_agents(self):
        command = run_bench.claude_command("x", "/p", ("--forward-subagent-text",))
        self.assertIn("--forward-subagent-text", command)
        self.assertNotIn("--forward-subagent-text", run_bench.claude_command("x", "/p"))


class AcceptanceStageTest(unittest.TestCase):
    """The acceptance stage starts the same agents as the tests stage, so its stage decides."""

    def events(self):
        return [
            assistant(1, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:acceptance"})]),
            assistant(2, "m2", usage(10, 0, 100, 5), [("a1", "Agent", {"subagent_type": "pdlc:test-writer"})]),
            assistant(3, "m3", usage(20, 0, 50, 40), parent="a1"),
            tool_result(10, "a1"),
            assistant(11, "m4", usage(10, 0, 100, 5), [
                ("a2", "Agent", {"subagent_type": "pdlc:reviewer",
                                 "prompt": "Review /app/pdlc/inbox/IN-0001-x/review/tests/packet.md"})]),
            assistant(12, "m5", usage(20, 0, 50, 30), parent="a2"),
            tool_result(20, "a2"),
            assistant(21, "m6", usage(10, 0, 100, 5), [("s2", "Skill", {"skill": "pdlc:tests"})]),
            assistant(22, "m7", usage(10, 0, 100, 5), [("a3", "Agent", {"subagent_type": "pdlc:test-writer"})]),
            assistant(23, "m8", usage(20, 0, 50, 10), parent="a3"),
            tool_result(30, "a3"),
            {"t": 31, "e": {"type": "result", "total_cost_usd": 1.0, "duration_ms": 31000, "num_turns": 8,
                            "is_error": False, "modelUsage": {"m": {"costUSD": 1.0}},
                            "subagent_stats": {"spawned": 3}}},
        ]

    def test_the_agents_of_acceptance_stay_in_acceptance(self):
        stages = run_bench.analyse(self.events())["stages"]
        self.assertEqual(sorted(stages["acceptance"]["agents"]),
                         ["pdlc:reviewer", "pdlc:reviewer/tests", "pdlc:test-writer"])
        self.assertEqual(stages["acceptance"]["wall_s"], 20.0)
        self.assertEqual(stages["tests"]["agents"]["pdlc:test-writer"]["tokens"]["output"], 10)

    def test_an_agent_with_no_stage_skill_starts_its_own_stage(self):
        events = [assistant(1, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:change"})]),
                  assistant(2, "m2", usage(10, 0, 0, 5), [("a1", "Agent", {"subagent_type": "pdlc:test-writer"})])]
        self.assertIn("tests", run_bench.analyse(events)["stages"])

    def test_the_prompt_names_the_stage_of_a_check_writer(self):
        self.assertEqual(run_bench.agent_stage(
            "pdlc:test-writer", "Write the acceptance checks of the intent /app/pdlc/inbox/IN-0001-x.md", "intake"),
            "acceptance")
        self.assertEqual(run_bench.agent_stage(
            "pdlc:test-writer", "Write the component checks of /app/pdlc/changes/CH-0001-x/change.md", "acceptance"),
            "tests")
        self.assertEqual(run_bench.agent_stage(
            "pdlc:reviewer", "Read /app/pdlc/acceptance/IN-0001-x/review/tests/packet.md", "init"), "acceptance")
        self.assertEqual(run_bench.agent_stage(
            "pdlc:reviewer", "Read /app/pdlc/changes/CH-0001-x/review/quality/packet.md", "acceptance"), "verify")

    def test_recon_in_init_stays_in_init(self):
        events = [assistant(1, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:init"})]),
                  assistant(2, "m2", usage(10, 0, 0, 5), [("a1", "Agent", {"subagent_type": "pdlc:recon"})]),
                  assistant(3, "m3", usage(20, 0, 0, 7), parent="a1")]
        self.assertIn("pdlc:recon", run_bench.analyse(events)["stages"]["init"]["agents"])


def reviewer_events():
    """A verify stage that starts two reviewers, security and privacy, in one message."""
    return [
        assistant(1, "m1", usage(10, 0, 0, 5), [("s1", "Skill", {"skill": "pdlc:verify"})]),
        assistant(2, "m2", usage(10, 0, 100, 5), [
            ("a1", "Agent", {"subagent_type": "pdlc:reviewer",
                             "prompt": "Review /app/pdlc/changes/CH-0001-x/review/security/packet.md"}),
            ("a2", "Agent", {"subagent_type": "pdlc:reviewer",
                             "prompt": "Review /app/pdlc/changes/CH-0001-x/review/privacy/packet.md"})]),
        assistant(3, "m3", usage(20, 0, 50, 40), parent="a1"),
        assistant(4, "m4", usage(20, 0, 50, 20), parent="a2"),
        tool_result(5, "a1"),
        tool_result(6, "a2"),
        {"t": 10, "e": {"type": "result", "total_cost_usd": 1.0, "duration_ms": 10000, "num_turns": 4,
                        "is_error": False, "modelUsage": {"m": {"costUSD": 1.0, "inputTokens": 60,
                        "outputTokens": 70, "cacheReadInputTokens": 200, "cacheCreationInputTokens": 0}},
                        "subagent_stats": {"spawned": 2}}},
    ]


class RemitSplitTest(unittest.TestCase):
    def test_a_reviewer_call_is_counted_under_its_remit_too(self):
        agents = run_bench.analyse(reviewer_events())["stages"]["verify"]["agents"]
        self.assertEqual(agents["pdlc:reviewer/security"]["calls"], 1)
        self.assertAlmostEqual(agents["pdlc:reviewer/security"]["cost_usd"], 0.5233, places=4)
        self.assertEqual(agents["pdlc:reviewer/privacy"]["calls"], 1)
        self.assertAlmostEqual(agents["pdlc:reviewer/privacy"]["cost_usd"], 0.2907, places=4)

    def test_the_aggregate_reviewer_entry_does_not_change(self):
        agents = run_bench.analyse(reviewer_events())["stages"]["verify"]["agents"]
        self.assertEqual(agents["pdlc:reviewer"]["calls"], 2)
        self.assertEqual(agents["pdlc:reviewer"]["messages"], 2)
        self.assertAlmostEqual(agents["pdlc:reviewer"]["cost_usd"], 0.8140, places=3)

    def test_agent_stats_reads_one_remit(self):
        result = {"runs": [run_bench.analyse(reviewer_events())]}
        stats = run_bench.agent_stats(result, "pdlc:reviewer/privacy")
        self.assertAlmostEqual(stats["per_call"], 0.2907, places=4)
        self.assertEqual(stats["calls"], 1)

    def test_a_reviewer_without_a_remit_in_its_prompt_gets_only_the_aggregate(self):
        events = reviewer_events()
        events[1]["e"]["message"]["content"][0]["input"]["prompt"] = "Review the packet"
        agents = run_bench.analyse(events)["stages"]["verify"]["agents"]
        self.assertNotIn("pdlc:reviewer/security", agents)
        self.assertEqual(agents["pdlc:reviewer"]["calls"], 2)


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


def agent_result(per_call, calls, totals, seeds=None, per_calls=None):
    """A result whose runs each hold `calls` reviewer calls at `per_call` dollars, or at per_calls[i] dollars."""
    runs = []
    for i, total in enumerate(totals):
        cost = per_calls[i] if per_calls else per_call
        runs.append({"totals": {"cost_usd": total, "duration_s": 100.0}, "wall_s": 100.0,
                     "stages": {"verify": {"agents": {"pdlc:reviewer": {"cost_usd": cost * calls, "calls": calls}}}},
                     "outcome": {"probes": {"passed": 8, "total": 8}, "unit": {"ok": True}}})
    return {"runs": runs, "seeds": {"caught": seeds} if seeds is not None else {}}


BASE_CALLS = [0.0595, 0.062, 0.0657, 0.0617, 0.0414, 0.0529]


class TargetGateTest(unittest.TestCase):
    def test_a_cheaper_agent_is_kept_even_when_whole_runs_vary_a_lot(self):
        baseline = agent_result(0.06, 7, [1.8, 2.5, 1.9, 2.0, 2.1])
        candidate = agent_result(0.005, 7, [1.6, 2.2, 1.7, 1.9, 2.0])
        plain = run_bench.gate(baseline, candidate)
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(plain["verdict"].startswith("NO GAIN"))
        self.assertTrue(aimed["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(aimed["target"]["expected_run_saving"], 0.385, places=3)
        self.assertLess(aimed["p"], 0.01)

    def test_a_whole_run_that_costs_much_more_is_a_regression(self):
        baseline = agent_result(0.06, 7, [1.8, 1.9, 2.0, 1.9, 1.8])
        candidate = agent_result(0.005, 7, [2.9, 3.1, 3.0, 2.8, 3.2])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_a_missed_defect_beats_a_cheaper_agent(self):
        baseline = agent_result(0.06, 7, [1.8, 1.9, 2.0, 1.9, 1.8], seeds=["a", "b"])
        candidate = agent_result(0.005, 7, [1.0, 1.1, 1.2, 1.0, 1.1], seeds=["a"])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_a_modest_fall_in_each_call_is_kept_when_runs_agree(self):
        baseline = agent_result(0.06, 7, [1.8] * 6, per_calls=BASE_CALLS)
        candidate = agent_result(0.06, 7, [1.8] * 6, per_calls=[c * 0.8 for c in BASE_CALLS])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(aimed["p"], 0.016, places=3)

    def test_a_cheaper_call_in_a_much_dearer_run_is_a_regression(self):
        baseline = agent_result(0.06, 7, BASE_TOTALS, per_calls=BASE_CALLS)
        candidate = agent_result(0.06, 7, [t * 1.4 for t in BASE_TOTALS], per_calls=[c * 0.8 for c in BASE_CALLS])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_the_same_cost_a_call_is_no_gain(self):
        baseline = agent_result(0.06, 7, BASE_TOTALS, per_calls=BASE_CALLS)
        candidate = agent_result(0.06, 7, BASE_TOTALS, per_calls=BASE_CALLS)
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("NO GAIN"))

    def test_a_cheaper_agent_in_three_runs_needs_more_runs(self):
        baseline = agent_result(0.06, 7, [1.8, 2.5, 1.9])
        candidate = agent_result(0.04, 7, [1.6, 2.2, 1.7])
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("NEED MORE RUNS"))

    def test_a_candidate_without_the_agent_is_no_gain(self):
        baseline = agent_result(0.06, 7, [1.8, 2.5, 1.9, 2.0, 2.1])
        candidate = agent_result(0.005, 7, [1.6, 2.2, 1.7, 1.9, 2.0])
        for run in candidate["runs"]:
            run["stages"]["verify"]["agents"] = {}
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("NO GAIN"))
        self.assertIn("no pdlc:reviewer call", aimed["reasons"][0])

    def test_a_missed_defect_beats_a_candidate_without_the_agent(self):
        baseline = agent_result(0.06, 7, [1.8, 2.5, 1.9, 2.0, 2.1], seeds=["a", "b"])
        candidate = agent_result(0.005, 7, [1.6, 2.2, 1.7, 1.9, 2.0], seeds=["a"])
        for run in candidate["runs"]:
            run["stages"]["verify"]["agents"] = {}
        aimed = run_bench.gate(baseline, candidate, target="pdlc:reviewer")
        self.assertTrue(aimed["verdict"].startswith("REGRESSION"))

    def test_the_cost_of_a_call_is_the_cost_over_the_calls(self):
        stats = run_bench.agent_stats(agent_result(0.06, 7, [1.8, 2.5]), "pdlc:reviewer")
        self.assertAlmostEqual(stats["per_call"], 0.06)
        self.assertEqual(stats["calls"], 14)


def waiting_result(waits, totals):
    """A result whose run i spent waits[i] dollars on waiting turns, and totals[i] in all."""
    data = result(totals)
    for run, wait in zip(data["runs"], waits):
        run["waiting"] = {"messages": 10 if wait else 0, "cost_usd": wait}
    return data


BASE_WAITS = [0.08, 0.03, 0.21, 0.19, 0.75, 0.02]
BASE_TOTALS = [1.78, 1.87, 2.49, 1.78, 1.99, 1.36]


class WaitingGateTest(unittest.TestCase):
    def test_no_waiting_against_a_waiting_baseline_is_kept(self):
        baseline = waiting_result(BASE_WAITS, BASE_TOTALS)
        candidate = waiting_result([0.0] * 6, [1.7, 1.8, 2.3, 1.6, 1.3, 1.3])
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))
        self.assertLess(verdict["p"], 0.01)
        self.assertAlmostEqual(verdict["target"]["expected_run_saving"], 0.213, places=3)

    def test_the_same_waiting_is_no_gain(self):
        baseline = waiting_result(BASE_WAITS, BASE_TOTALS)
        candidate = waiting_result(BASE_WAITS, BASE_TOTALS)
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

    def test_no_waiting_but_a_much_dearer_run_is_a_regression(self):
        baseline = waiting_result(BASE_WAITS, BASE_TOTALS)
        candidate = waiting_result([0.0] * 6, [t * 1.4 for t in BASE_TOTALS])
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("not luck", verdict["reasons"][0])

    def test_no_waiting_and_a_slightly_dearer_run_is_kept(self):
        baseline = waiting_result(BASE_WAITS, BASE_TOTALS)
        candidate = waiting_result([0.0] * 6, [t * 1.1 for t in BASE_TOTALS])
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))

    def test_no_waiting_in_three_runs_needs_more_runs(self):
        baseline = waiting_result(BASE_WAITS[:3], BASE_TOTALS[:3])
        candidate = waiting_result([0.0] * 3, [1.7, 1.8, 2.3])
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("NEED MORE RUNS"))

    def test_a_result_without_waiting_counts_as_zero(self):
        self.assertEqual(run_bench.summarise(result([2.0]))["waiting"], [0.0])

    def test_a_run_that_did_not_finish_beats_no_waiting(self):
        def finished(waits, totals, ok):
            data = waiting_result(waits, totals)
            for run in data["runs"]:
                run["outcome"]["merge_check"] = {"pdlc/CH-0001": ["ok   CH-0001" if ok else "FAIL CH-0001"]}
            return data
        baseline = finished(BASE_WAITS, BASE_TOTALS, True)
        candidate = finished([0.0] * 6, [1.0, 1.1, 1.2, 1.0, 1.1, 1.2], False)
        verdict = run_bench.gate(baseline, candidate, target="waiting")
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("did not finish", verdict["reasons"][0])


class WritingFindingsTest(unittest.TestCase):
    def project(self):
        """A git repository with the check script, one spec and a README, committed as base."""
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        (root / "pdlc" / "bin").mkdir(parents=True)
        (root / "pdlc" / "specs" / "jobs").mkdir(parents=True)
        shutil.copyfile(run_bench.DEFAULT_PLUGIN / "skills/init/references/bin/check_writing.py",
                        root / "pdlc" / "bin" / "check_writing.py")
        (root / "pdlc" / "specs" / "jobs" / "JOB-x.md").write_text("# JOB-x · Do a thing\n\nA short line.\n")
        (root / "README.md").write_text("# App\n\nA short line.\n")
        run_bench.git(root, "init", "-q", "-b", "main")
        self.commit(root, "base")
        return root

    def commit(self, root, subject):
        run_bench.git(root, "add", "-A")
        run_bench.git(root, "commit", "-q", "-m", subject)

    def head(self, root):
        return run_bench.git(root, "rev-parse", "HEAD").stdout.strip()

    def test_counts_the_findings_in_the_packet_text_written_since_a_commit(self):
        root = self.project()
        base = self.head(root)
        long_sentence = " ".join(["word"] * 30) + "."
        (root / "pdlc" / "changes" / "CH-0001-x").mkdir(parents=True)
        (root / "pdlc" / "changes" / "CH-0001-x" / "change.md").write_text(long_sentence + "\nThe R3 checks pass.\n")
        (root / "pdlc" / "changes" / "CH-0001-x" / "handoff.md").write_text("The R4 checks pass.\n")
        (root / "pdlc" / "inbox").mkdir()
        (root / "pdlc" / "inbox" / "IN-0001-x.md").write_text(long_sentence + "\n")
        (root / "README.md").write_text("# App\n\nA short line.\nIt picks a color.\n")
        (root / "pdlc" / "specs" / "jobs" / "JOB-x.md").write_text("# JOB-x · Do a thing\n\nA short line. See R2 for more.\n")
        self.commit(root, "Write text")
        result = run_bench.writing_findings(root, base)
        self.assertEqual(result["count"], 4)
        self.assertEqual(result["files"], ["README.md", "pdlc/changes/CH-0001-x/change.md", "pdlc/specs/jobs/JOB-x.md"])
        for finding in result["findings"]:
            self.assertNotIn("handoff.md", finding)
            self.assertNotIn("inbox", finding)

    def test_lines_from_before_the_commit_do_not_count(self):
        root = self.project()
        spec = root / "pdlc" / "specs" / "jobs" / "JOB-x.md"
        spec.write_text("# JOB-x · Do a thing\n\n" + " ".join(["word"] * 30) + ".\n")
        self.commit(root, "Write a long line")
        since = self.head(root)
        spec.write_text(spec.read_text() + "A new short line.\n")
        self.commit(root, "Add a short line")
        self.assertEqual(run_bench.writing_findings(root, since)["count"], 0)

    def test_no_text_file_gives_zero(self):
        root = self.project()
        base = self.head(root)
        (root / "app.py").write_text("print('hello')\n")
        self.commit(root, "Add the app")
        self.assertEqual(run_bench.writing_findings(root, base), {"count": 0, "files": [], "findings": []})

    def test_without_the_script_the_count_is_none(self):
        root = self.project()
        base = self.head(root)
        (root / "pdlc" / "bin" / "check_writing.py").unlink()
        (root / "README.md").write_text("# App\n\nA short line.\nIt picks a color.\n")
        self.commit(root, "Remove the script and write text")
        result = run_bench.writing_findings(root, base)
        self.assertIsNone(result["count"])
        self.assertIn("error", result)


WRITING_COSTS = [0.36, 0.39, 0.37, 0.39, 0.38, 0.38]
WRITING_FINDINGS = [4, 1, 2, 2, 6, 3]


def writing_result(costs, findings, completed=True):
    """A result whose run i costs costs[i] and leaves findings[i] writing findings (None: no count)."""
    runs = []
    for cost, count in zip(costs, findings):
        outcome = {"merge_check": {"stage": ["ok   tests" if completed else "FAIL tests"]},
                   "probes": {"passed": 8, "total": 8, "failed": []},
                   "unit": {"ok": True, "ran": 8}, "verify_rounds": None}
        if count is not None:
            outcome["writing"] = {"count": count, "files": [], "findings": []}
        runs.append({"totals": {"cost_usd": cost, "duration_s": 300}, "wall_s": 300, "stages": {},
                     "waiting": {"messages": 0, "cost_usd": 0.0}, "outcome": outcome})
    return {"runs": runs}


class CompletedTest(unittest.TestCase):
    def run_with(self, checks):
        return {"outcome": {"merge_check": checks}}

    def test_an_intent_branch_with_no_output_does_not_count(self):
        checks = {"pdlc/CH-0001-top-option": ["ok   CH-0001"], "pdlc/IN-0001-top-option": []}
        self.assertTrue(run_bench.completed(self.run_with(checks)))

    def test_a_failed_change_branch_is_not_complete(self):
        checks = {"pdlc/CH-0001-top-option": ["FAIL CH-0001", "  - R4 is built, not verified"],
                  "pdlc/IN-0001-top-option": []}
        self.assertFalse(run_bench.completed(self.run_with(checks)))

    def test_no_output_on_each_branch_is_not_complete(self):
        self.assertFalse(run_bench.completed(self.run_with({"pdlc/IN-0001-top-option": []})))


class WritingGateTest(unittest.TestCase):
    def test_fewer_findings_are_kept(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result(WRITING_COSTS, [0, 0, 1, 0, 0, 0])
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))

    def test_the_same_findings_are_no_gain(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

    def test_fewer_findings_in_a_slightly_dearer_stage_are_kept(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result([c * 1.04 for c in WRITING_COSTS], [0, 0, 1, 0, 0, 0])
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))

    def test_fewer_findings_in_a_clearly_dearer_stage_are_a_regression(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result([c * 1.15 for c in WRITING_COSTS], [0, 0, 1, 0, 0, 0])
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("costs 15% more", verdict["reasons"][0])

    def test_a_missing_count_cannot_be_judged(self):
        baseline = writing_result(WRITING_COSTS, [None] * 6)
        candidate = writing_result(WRITING_COSTS, [0, 0, 1, 0, 0, 0])
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))
        self.assertIn("no writing count", verdict["reasons"][0])

    def test_fewer_findings_in_three_runs_need_more_runs(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result(WRITING_COSTS[:3], [0, 0, 0])
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("NEED MORE RUNS"))

    def test_a_stage_that_did_not_finish_beats_fewer_findings(self):
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result(WRITING_COSTS, [0, 0, 1, 0, 0, 0], completed=False)
        verdict = run_bench.gate(baseline, candidate, target="writing")
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))

    def test_the_gate_prints_the_writing_line(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        baseline = writing_result(WRITING_COSTS, WRITING_FINDINGS)
        candidate = writing_result(WRITING_COSTS, [0, 0, 1, 0, 0, 0])
        (folder / "baseline.json").write_text(run_bench.json.dumps(baseline))
        (folder / "candidate.json").write_text(run_bench.json.dumps(candidate))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run_bench.command_gate(Namespace(baseline=str(folder / "baseline.json"),
                                             candidate=str(folder / "candidate.json"),
                                             min_gain=0.05, speed_limit=1.5, target="writing", min_runs=5))
        self.assertIn("writing    3.0 -> 0.2 findings a run", out.getvalue())


def calls_result(counts, per_call, totals, label="pdlc:reviewer/compliance"):
    """A result whose run i makes counts[i] calls of `label`, at per_call dollars each."""
    runs = []
    for count, total in zip(counts, totals):
        agents = {label: {"cost_usd": per_call * count, "calls": count}} if count else {}
        runs.append({"totals": {"cost_usd": total, "duration_s": 100.0}, "wall_s": 100.0,
                     "stages": {"verify": {"agents": agents}},
                     "outcome": {"probes": {"passed": 8, "total": 8}, "unit": {"ok": True}}})
    return {"runs": runs}


REF_TOTALS = [1.26, 1.41, 1.40, 1.62, 1.46, 1.68]
REF_COUNTS = [1, 1, 1, 2, 1, 1]
TARGET = "calls:pdlc:reviewer/compliance"


class CallsGateTest(unittest.TestCase):
    def test_agent_stats_counts_the_calls_of_each_run(self):
        stats = run_bench.agent_stats(calls_result([1, 0, 2], 0.025, [1.0, 1.0, 1.0]), "pdlc:reviewer/compliance")
        self.assertEqual(stats["counts"], [1, 0, 2])
        self.assertEqual(len(stats["per_run"]), 2)

    def test_removing_every_call_is_kept(self):
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result([0] * 6, 0.025, [1.23, 1.38, 1.37, 1.57, 1.43, 1.65])
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(verdict["p"], 0.00108, places=5)
        self.assertAlmostEqual(verdict["target"]["expected_run_saving"], 0.0292, places=4)
        self.assertEqual(verdict["target"]["calls_after"], 0)

    def test_one_run_that_still_calls_is_kept(self):
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result([0, 0, 0, 0, 0, 1], 0.025, [1.23, 1.38, 1.37, 1.57, 1.43, 1.65])
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(verdict["p"], 0.00649, places=5)

    def test_two_runs_that_still_call_are_kept(self):
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result([0, 0, 0, 0, 1, 1], 0.025, [1.23, 1.38, 1.37, 1.57, 1.43, 1.65])
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("SAME OR BETTER"))
        self.assertAlmostEqual(verdict["p"], 0.02273, places=5)

    def test_the_same_calls_is_no_gain(self):
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))
        self.assertIn("changed from 1.17 to 1.17", verdict["reasons"][0])

    def test_fewer_calls_in_a_much_dearer_run_is_a_regression(self):
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result([0] * 6, 0.025, [t * 1.4 for t in REF_TOTALS])
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("REGRESSION"))
        self.assertIn("not luck", verdict["reasons"][0])

    def test_fewer_calls_in_three_runs_needs_more_runs(self):
        baseline = calls_result([1, 1, 1], 0.025, [1.3, 1.4, 1.5])
        candidate = calls_result([0, 0, 0], 0.025, [1.2, 1.3, 1.4])
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("NEED MORE RUNS"))
        self.assertAlmostEqual(verdict["p"], 0.05)

    def test_a_baseline_without_the_calls_is_no_gain(self):
        baseline = calls_result([0] * 6, 0.025, REF_TOTALS)
        candidate = calls_result([0] * 6, 0.025, REF_TOTALS)
        verdict = run_bench.gate(baseline, candidate, target=TARGET)
        self.assertTrue(verdict["verdict"].startswith("NO GAIN"))

    def test_the_gate_prints_the_calls_line(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        baseline = calls_result(REF_COUNTS, 0.025, REF_TOTALS)
        candidate = calls_result([0] * 6, 0.025, [1.23, 1.38, 1.37, 1.57, 1.43, 1.65])
        (folder / "baseline.json").write_text(run_bench.json.dumps(baseline))
        (folder / "candidate.json").write_text(run_bench.json.dumps(candidate))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run_bench.command_gate(Namespace(baseline=str(folder / "baseline.json"),
                                             candidate=str(folder / "candidate.json"),
                                             min_gain=0.05, speed_limit=1.5, target=TARGET, min_runs=5))
        self.assertIn("1.17 -> 0.00 calls a run at $0.025 each", out.getvalue())


class WaitingTest(unittest.TestCase):
    def waiting(self, command):
        return run_bench.is_waiting([{"type": "tool_use", "name": "Bash", "input": {"command": command}}])

    def test_a_loop_that_greps_and_sleeps_is_waiting(self):
        self.assertTrue(self.waiting("f=/x/out; for i in $(seq 1 90); do grep -q done $f && break; sleep 3; done"))

    def test_a_loop_that_checks_git_and_then_sleeps_is_waiting(self):
        self.assertTrue(self.waiting("cd /app; for i in $(seq 1 90); do git diff --quiet -- a.py || break; "
                                     "sleep 3; done; sleep 40; git status --short"))

    def test_an_until_loop_is_waiting(self):
        self.assertTrue(self.waiting("until [ -f x ]; do sleep 3; done; echo result"))

    def test_a_sleep_before_a_commit_is_not_waiting(self):
        self.assertFalse(self.waiting("sleep 2; git add -A && git commit -qm x"))

    def test_a_sleep_after_the_tests_is_not_waiting(self):
        self.assertFalse(self.waiting("python3 -m unittest discover -s tests; sleep 1"))

    def test_a_status_check_is_not_waiting(self):
        self.assertFalse(self.waiting("git status --short"))

    def test_a_notification_read_is_waiting_and_a_file_read_is_not(self):
        self.assertTrue(run_bench.is_waiting([{"type": "tool_use", "name": "ReadNotifications", "input": {}}]))
        self.assertFalse(run_bench.is_waiting([{"type": "tool_use", "name": "Read", "input": {"file_path": "/x"}}]))


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

    def test_the_final_reply_is_the_text_of_the_result_event(self):
        items = [{"e": {"type": "assistant"}}, {"e": {"type": "result", "result": "Result: pass"}}]
        self.assertEqual(run_bench.final_reply(items), "Result: pass")
        self.assertEqual(run_bench.final_reply([]), "")

    def test_a_reviewer_that_answers_in_its_reply_is_still_scored(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        label = folder / "results" / "x"
        (label / "seeded").mkdir(parents=True)
        (label / "clean").mkdir()
        seeds = {"caught": [], "missed": ["privacy-log"], "false_fails": [],
                 "seeded": {"privacy": {"verdict": "none", "problems": ""}},
                 "clean": {"specification": {"verdict": "none", "problems": ""}}}
        (label / "seeds.json").write_text(run_bench.json.dumps(seeds))
        privacy = {"t": 1, "e": {"type": "result", "result": (
            "Result: fail\n\nRemit: privacy\n\nProblems:\n"
            "- cli.py:42 · writes the text of the file to a log in /tmp · remit rule\n\n"
            "Follow-ups: none\n")}}
        clean = {"t": 1, "e": {"type": "result", "result": "Result: pass\n\nRemit: specification\n\nProblems: none\n"}}
        (label / "seeded" / "privacy.stream.jsonl").write_text(run_bench.json.dumps(privacy) + "\n")
        (label / "clean" / "specification.stream.jsonl").write_text(run_bench.json.dumps(clean) + "\n")
        original = run_bench.HERE
        self.addCleanup(setattr, run_bench, "HERE", original)
        run_bench.HERE = folder
        run_bench.command_rescore_seeds(Namespace(label="x"))
        data = run_bench.json.loads((label / "seeds.json").read_text())
        self.assertEqual(data["seeded"]["privacy"]["verdict"], "fail")
        self.assertIn("privacy-log", data["caught"])
        self.assertEqual(data["clean"]["specification"]["verdict"], "pass")
        self.assertEqual(data["false_fails"], [])


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


    def test_a_stage_spec_names_its_snapshot_and_a_baseline_of_another_snapshot_is_refused(self):
        spec = run_experiment.load_spec(self.write(stage="verify"))
        self.assertEqual(spec["snapshot"], run_bench.DEFAULT_SNAPSHOT)
        self.assertIsNone(run_experiment.snapshot_mismatch(spec, {"snapshot": "wordfreq"}))
        self.assertIn("r5", run_experiment.snapshot_mismatch(spec, {"label": "old"}))
        spec = run_experiment.load_spec(self.write(stage="verify", snapshot="r5"))
        self.assertIsNone(run_experiment.snapshot_mismatch(spec, {"label": "old"}))
        self.assertIsNone(run_experiment.snapshot_mismatch(run_experiment.load_spec(self.write()), {"label": "old"}))
        with self.assertRaises(run_experiment.SpecError):
            run_experiment.load_spec(self.write(snapshot="nope"))

    def test_a_good_spec_gets_its_defaults(self):
        spec = run_experiment.load_spec(self.write())
        self.assertEqual((spec["runs"], spec["seeds"], spec["target"]), (6, False, None))
        self.assertEqual(spec["baseline"], "bench/baseline.json")

    def test_a_stage_spec_compares_with_its_stage_baseline(self):
        spec = run_experiment.load_spec(self.write(stage="verify"))
        self.assertEqual(spec["baseline"], "bench/sections/verify.json")
        self.assertTrue((run_experiment.REPO / spec["baseline"]).exists())

    def test_an_unknown_stage_is_refused(self):
        with self.assertRaises(run_experiment.SpecError) as caught:
            run_experiment.load_spec(self.write(stage="ship"))
        self.assertIn('"stage"', str(caught.exception))

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

    def test_apply_writes_the_edits_once_and_then_refuses(self):
        plugin = Path(tempfile.mkdtemp()) / "pdlc"
        self.addCleanup(shutil.rmtree, plugin.parent, True)
        shutil.copytree(run_experiment.PLUGIN / "agents", plugin / "agents")
        spec_path = self.write()
        real = run_experiment.PLUGIN
        run_experiment.PLUGIN = plugin
        self.addCleanup(setattr, run_experiment, "PLUGIN", real)
        run_experiment.command_apply(Namespace(spec=str(spec_path)))
        self.assertIn("tools: Read, Write, Glob", (plugin / "agents" / "reviewer.md").read_text())
        with self.assertRaises(run_experiment.SpecError):
            run_experiment.command_apply(Namespace(spec=str(spec_path)))

    def test_the_background_command_uses_an_absolute_spec_path(self):
        command = run_experiment.runner_command("bench/experiments/round3/x.json")
        self.assertTrue(Path(command[-1]).is_absolute())
        self.assertTrue(command[-1].endswith("bench/experiments/round3/x.json"))

    def test_status_updates_keep_the_process_id(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        run_experiment.write_status(folder, state="starting", pid=123)
        run_experiment.write_status(folder, state="running")
        status = run_bench.json.loads((folder / "status.json").read_text())
        self.assertEqual((status["state"], status["pid"]), ("running", 123))

    def test_a_dead_process_is_not_alive(self):
        self.assertTrue(run_experiment.process_alive(os.getpid()))
        self.assertFalse(run_experiment.process_alive(2 ** 22 + 12345))

    def test_check_reports_new_writing_findings(self):
        long_sentence = " ".join(["word"] * 40) + "."
        edits = [{"file": "skills/verify/SKILL.md", "find": "# pdlc verify\n", "replace": "# pdlc verify\n\n" + long_sentence + "\n"}]
        spec = run_experiment.load_spec(self.write(edits=edits))
        scratch, report, diff = run_experiment.check(spec, run_tests=False)
        self.addCleanup(shutil.rmtree, scratch.parent, True)
        self.assertIn("NEW FINDINGS", report)
        self.assertIn("+" + long_sentence, diff)


class TodoProbes:
    """The probes of the to-do intent fail on the base app, and pass on the reference solution."""
    fixture = None

    def copy(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        app = folder / "app"
        shutil.copytree(run_bench.FIXTURES[self.fixture]["app"], app,
                        ignore=shutil.ignore_patterns("target", "pdlc"))
        run_bench.git(app, "init", "-q")
        return app

    def test_the_base_app_passes_only_the_probe_of_the_old_behaviour(self):
        result = run_bench.todo_probes(self.copy(), self.fixture)
        self.assertEqual(result["passed"], 1, result)
        self.assertNotIn("adding and the empty-text error still work", result["failed"])

    def test_the_reference_solution_passes_each_probe(self):
        app = self.copy()
        patch = run_bench.HERE / "fixtures" / "solutions" / (self.fixture + ".patch")
        run_bench.git(app, "apply", str(patch))
        self.assertEqual(run_bench.todo_probes(app, self.fixture), {"passed": 8, "total": 8, "failed": []})
        self.assertTrue(run_bench.unit_checks(app, self.fixture)["ok"])


@unittest.skipUnless(shutil.which("clojure"), "needs clojure")
class TodoClojureProbeTest(TodoProbes, unittest.TestCase):
    fixture = "todo-clojure"


@unittest.skipUnless(shutil.which("cargo"), "needs cargo")
class TodoProbeTest(TodoProbes, unittest.TestCase):
    fixture = "todo-rust"

    def test_the_bash_commands_of_the_fixture_are_allowed(self):
        command = run_bench.claude_command("x", "/p", tools=run_bench.FIXTURES["todo-rust"]["tools"])
        self.assertIn("Bash(cargo:*)", command[command.index("--allowedTools") + 1])

    def test_the_visible_text_of_a_page_has_no_tags(self):
        self.assertEqual(run_bench.visible_text("<li>milk <b>(done)</b></li>\n<li>a &amp; b</li>"),
                         "milk (done) a & b")
        self.assertFalse(run_bench.has_word("almilky", "milk"))


class MetricsTest(unittest.TestCase):
    """The measures of the stream: loops, failures and time, by stage."""

    def bash(self, t, tool_id, command, parent=None):
        return assistant(t, "b" + tool_id, usage(10, 0, 100, 5), [(tool_id, "Bash", {"command": command})],
                         parent=parent)

    def result(self, t, tool_id, text, error=False, parent=None):
        return {"t": t, "e": {"type": "user", "parent_tool_use_id": parent, "message": {"content": [
            {"type": "tool_result", "tool_use_id": tool_id, "content": text, "is_error": error}]}}}

    def events(self):
        return [
            assistant(1, "m1", usage(10, 0, 1000, 5), [("s1", "Skill", {"skill": "pdlc:build"})]),
            assistant(2, "m2", usage(10, 0, 2000, 5), [("a1", "Agent", {"subagent_type": "pdlc:builder"})]),
            self.bash(3, "c1", "cargo test 2>&1 | tail -3", parent="a1"),
            self.result(4, "c1", "test result: FAILED. 1 passed; 2 failed", parent="a1"),
            self.bash(5, "c2", "cargo test", parent="a1"),
            self.result(6, "c2", "test result: ok. 3 passed", parent="a1"),
            self.result(7, "a1", "done"),
            self.bash(8, "c3", "cargo build --release"),
            self.result(9, "c3", "error[E0425]: cannot find value", error=True),
            {"t": 10, "e": {"type": "system", "subtype": "hook_response", "hook_name": "PostToolUse:Bash",
                            "exit_code": "2", "stderr": "pdlc: commit x has 2 writing findings\n  - a\n  - b"}},
            {"t": 11, "e": {"type": "result", "total_cost_usd": 1.0, "duration_api_ms": 9000,
                            "permission_denials": [{"tool_name": "Bash"}], "usage": {"output_tokens": 15}}},
        ]

    def test_a_failed_check_run_counts_also_when_a_pipe_hides_the_exit_code(self):
        loops = metrics.measure_stream(self.events(), "todo-rust")["loops"]["build"]
        self.assertEqual((loops["check runs"], loops["check failures"]), (2, 1))
        self.assertEqual((loops["builds"], loops["build failures"]), (1, 1))

    def test_a_builder_call_counts_its_check_runs_until_green(self):
        self.assertEqual(metrics.measure_stream(self.events(), "todo-rust")["builder_check_runs_until_green"], [2])

    def test_failures_count_hooks_tools_and_denials(self):
        failures = metrics.measure_stream(self.events(), "todo-rust")["failures"]
        self.assertEqual(failures["hook blocks"], {"commits: writing": 1})
        self.assertEqual(failures["hook findings"], {"commits: writing": 2})
        self.assertEqual(failures["tool errors"], {"Bash (main)": 1})
        self.assertEqual(failures["permission denials"], 1)

    def test_the_main_session_time_goes_to_the_model_or_the_work(self):
        time = metrics.measure_stream(self.events(), "todo-rust")["time"]
        self.assertEqual(time["main_session"]["agent"], 5.0)
        self.assertEqual(time["main_session"]["build"], 1.0)
        self.assertEqual(time["api_s"], 9.0)

    def test_the_time_of_checks_and_builds_counts_in_each_session(self):
        work = metrics.measure_stream(self.events(), "todo-rust")["time"]["work_by_session"]
        self.assertEqual(work["pdlc:builder"], {"checks": 2.0})
        self.assertEqual(work["main"], {"build": 1.0})

    def test_each_fault_changes_one_place_of_an_added_line(self):
        found = metrics.mutants([("src/a.rs", 3, '    if done == true { return "Done"; }'),
                                 ("src/a.rs", 4, "    item.done = true;")])
        names = [name for _, _, name, _ in found]
        self.assertEqual(names, ["true to false", "== to !=", "a letter of a text", "true to false",
                                 "remove the line"])
        self.assertEqual(found[0][3], '    if done == false { return "Done"; }')
        self.assertEqual(found[2][3], '    if done == true { return "Xone"; }')
        self.assertIsNone(found[4][3])
        self.assertEqual(metrics.mutants([("a.py", 1, "# a comment with true")]), [])

    def test_a_docstring_is_not_code(self):
        lines = ['(defn render [items]', '(defn page', '  "The page of the list."', '  [items]',
                 '  (str "<h1>To-do</h1>"))', '    """A python docstring."""']
        self.assertTrue(metrics.is_docstring(lines, 2))
        self.assertTrue(metrics.is_docstring(lines, 5))
        self.assertFalse(metrics.is_docstring(lines, 4))

    def test_the_spread_gives_the_range_of_each_measure(self):
        columns = [("a", {"cost $": "2.00", "probes": "8 of 8", "finished": True}),
                   ("b", {"cost $": "1.00", "probes": "6 of 8", "finished": True})]
        found = dict((row[0], row[1:]) for row in metrics.spread(columns))
        self.assertEqual(found["cost $"], ("1", "1.50", "2", "67%"))
        self.assertEqual(found["probes"], ("6", "7", "8", "29%"))
        self.assertEqual(found["finished"], ("", "", "", ""))

    def test_a_requirement_id_in_a_check_name_is_found_in_each_form(self):
        found = metrics.REQ.findall("fn test_CAP_store_R2_keeps_done() {} // JOB-view-list.R10")
        self.assertEqual(found, [("CAP_store", "R2"), ("JOB-view-list", "R10")])


class StageReplayTest(unittest.TestCase):
    def stage_project(self, stage, plugin=None):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        return run_bench.make_stage_project(folder / "app", stage, plugin or run_bench.DEFAULT_PLUGIN, "r5")

    def subject(self, project, rev="HEAD"):
        return run_bench.git(project, "log", "-1", "--format=%s", rev).stdout.strip()

    def test_each_stage_starts_at_its_entry_commit(self):
        for stage, (entry_subject, branch, _, _) in run_bench.LEGACY_STAGES.items():
            with self.subTest(stage=stage):
                project, _ = self.stage_project(stage)
                head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
                self.assertTrue(self.subject(project, head).startswith(entry_subject))
                self.assertEqual(run_bench.git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), branch)

    def test_main_ends_at_the_plan_for_a_change_branch_stage(self):
        project, _ = self.stage_project("build")
        self.assertTrue(self.subject(project, "main").startswith("Plan IN-0001"))

    def test_a_stage_project_has_no_remote(self):
        project, _ = self.stage_project("intake")
        self.assertEqual(run_bench.git(project, "remote").stdout.strip(), "")

    def test_a_stage_with_no_work_is_not_finished(self):
        project, entry = self.stage_project("show")
        result = run_bench.check_stage(project, "show", entry, "r5")
        self.assertFalse(result["finished"])
        self.assertFalse(result["ok"])

    def test_the_snapshot_passes_the_checks_of_earlier_stages(self):
        project, _ = self.stage_project("show")
        self.assertTrue(run_bench.check_stage(project, "show", run_bench.entry_commit(project, "Built CH-0001"), "r5")["ok"])
        self.assertTrue(run_bench.check_stage(project, "build", run_bench.entry_commit(project, "Tests reviewed CH-0001"), "r5")["ok"])
        project, _ = self.stage_project("build")
        result = run_bench.check_stage(project, "tests", run_bench.entry_commit(project, "Plan IN-0001"), "r5")
        self.assertTrue(result["ok"])

    def test_a_changed_plugin_file_gets_an_upgrade_commit(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        plugin = folder / "pdlc"
        shutil.copytree(run_bench.DEFAULT_PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
        readme = plugin / "skills" / "init" / "references" / "templates" / "README.md"
        readme.write_text(readme.read_text() + "\nA line that the test adds.\n")
        project, _ = self.stage_project("verify", plugin)
        self.assertEqual(self.subject(project), "Upgrade pdlc")
        self.assertIn("A line that the test adds.", (project / "pdlc" / "README.md").read_text())

    def prepare(self, state):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        with contextlib.redirect_stdout(io.StringIO()):
            run_bench.main(["prepare", "--state", state, "--snapshot", "r5", "--dest", str(folder / "app")])
        return folder / "app"

    def test_prepare_tags_the_start_of_each_state(self):
        for state in run_bench.prepare_states("r5"):
            with self.subTest(state=state):
                project = self.prepare(state)
                self.assertEqual(run_bench.git(project, "rev-parse", "start").stdout,
                                 run_bench.git(project, "rev-parse", "HEAD").stdout)

    def test_a_prepared_project_has_a_clean_working_tree(self):
        for state in run_bench.prepare_states("r5"):
            with self.subTest(state=state):
                project = self.prepare(state)
                self.assertEqual(run_bench.git(project, "status", "--porcelain").stdout.strip(), "")

    def test_prepare_init_has_no_pdlc_folder(self):
        self.assertFalse((self.prepare("init") / "pdlc").exists())

    def test_prepare_done_is_at_the_proposal(self):
        project = self.prepare("done")
        head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
        self.assertTrue(self.subject(project, head).startswith("Propose CH-0001"))
        self.assertEqual(run_bench.git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
                         run_bench.CHANGE_BRANCH)

    def test_prepare_board_sets_a_tracker_on_main_and_on_the_branch(self):
        project = self.prepare("board")
        for branch in ("main", run_bench.CHANGE_BRANCH):
            with self.subTest(branch=branch):
                config = run_bench.git(project, "show", branch + ":pdlc/config.md").stdout
                self.assertIn("- tracker: tracker-github-projects", config)
                self.assertIn("- status field: Status", config)
        self.assertEqual(run_bench.git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
                         run_bench.CHANGE_BRANCH)

    def test_check_stage_counts_the_writing_findings_of_the_stage(self):
        project, _ = self.stage_project("verify")
        entry = run_bench.entry_commit(project, "Tests reviewed CH-0001")
        writing = run_bench.check_stage(project, "build", entry, "r5")["extra"]["writing"]
        self.assertEqual(writing["count"], 0)
        # The upgrade commit refreshes the four default specs that the early snapshot lacks.
        self.assertEqual(writing["files"], ["README.md", "pdlc/changes/CH-0001-top-option/change.md",
                                            "pdlc/specs/design/DES-pdlc-check-tagging.md",
                                            "pdlc/specs/design/DES-pdlc-commit-trailers.md",
                                            "pdlc/specs/design/DES-pdlc-review-checklist.md",
                                            "pdlc/specs/design/DES-writing-style.md",
                                            "pdlc/specs/jobs/JOB-report-word-frequencies.md"])

    def test_a_stage_outcome_carries_the_writing_count_and_the_entry(self):
        project, _ = self.stage_project("verify")
        entry = run_bench.entry_commit(project, "Tests reviewed CH-0001")
        check = run_bench.check_stage(project, "build", entry, "r5")
        outcome = run_bench.stage_outcome("build", check, entry)
        self.assertEqual(outcome["writing"], check["extra"]["writing"])
        self.assertEqual(outcome["entry"], entry)
        self.assertEqual(outcome["merge_check"], {"stage": ["ok   build"]})

    def test_inspect_project_counts_the_findings_of_a_whole_run(self):
        project, _ = self.stage_project("verify")
        writing = run_bench.inspect_project(project)["writing"]
        self.assertEqual(writing["count"], 11)
        self.assertIn("README.md", writing["files"])
        self.assertIn("pdlc/specs/jobs/JOB-report-word-frequencies.md", writing["files"])

    def test_recheck_reads_a_stage_folder_again(self):
        project, _ = self.stage_project("show")
        shown = run_bench.entry_commit(project, "Built CH-0001")
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        run = {"totals": {"cost_usd": 0.2, "duration_s": 1.0}, "stages": {}, "waiting": {}, "wall_s": 1.0,
               "project": str(project), "outcome": {"stage": "show", "entry": shown}}
        summary = {"label": "x", "stage": "show", "plugin_commit": "x", "model": "m", "effort": "e", "runs": [run]}
        (folder / "e2e.json").write_text(run_bench.json.dumps(summary))
        (folder / "run1.json").write_text(run_bench.json.dumps(run))
        with contextlib.redirect_stdout(io.StringIO()):
            run_bench.command_recheck(Namespace(folder=str(folder)))
        saved = run_bench.json.loads((folder / "e2e.json").read_text())["runs"][0]["outcome"]
        self.assertTrue(saved["check"]["ok"])
        self.assertEqual(saved["writing"]["count"], 0)
        self.assertEqual(saved["entry"], shown)


def rebuild_project(test):
    """A project that an e2e run could leave: the fixture on main, and a change branch that adds
    a spec, a change, an acceptance file, a new check and a build file. Main stays checked out."""
    root = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, root, True)
    app = root / "app"
    shutil.copytree(run_bench.FIXTURE, app, ignore=shutil.ignore_patterns("__pycache__"))
    run_bench.git(app, "init", "-q", "-b", "main")
    run_bench.git(app, "add", "-A")
    run_bench.git(app, "commit", "-q", "-m", "Set up pdlc")
    run_bench.git(app, "checkout", "-q", "-b", "pdlc/CH-0001-x")
    files = {
        "pdlc/specs/jobs/JOB-branch-only.md": "# JOB-branch-only\n",
        "pdlc/changes/CH-0001-x/change.md": "# CH-0001\n",
        "pdlc/inbox/IN-0001-x.md": "# IN-0001\n",
        "pdlc/acceptance/IN-0001-x/brief.md": "# Brief\n",
        "pdlc/bin/check_merge.py": "print('ok')\n",
        "pdlc/README.md": "How to read a spec.\n",
        "tests/acceptance_IN-0001.py": "import unittest\n",
        "tests/acceptance_IN-9999.py": "import unittest\n",
        "tests/test_new.py": "import unittest\n",
        "Cargo.toml": "[package]\n",
    }
    for name, text in files.items():
        (app / name).parent.mkdir(parents=True, exist_ok=True)
        (app / name).write_text(text)
    (app / "wordfreq" / "cli.py").write_text(REFERENCE_CLI)
    with open(app / "tests" / "test_cli.py", "a") as handle:
        handle.write("\n# changed by pdlc\n")
    config = app / "pdlc" / "config.md"
    config.write_text(config.read_text().replace(
        "- check folders: `tests/`\n",
        "- check folders: `tests/`\n- acceptance file: `tests/acceptance_{intent}.py`\n"
        "- acceptance: `python3 -m unittest {files}`\n"))
    run_bench.git(app, "add", "-A")
    run_bench.git(app, "commit", "-q", "-m", "Tests reviewed CH-0001")
    run_bench.git(app, "checkout", "-q", "main")
    return app


class FixtureUpgradeTest(unittest.TestCase):
    """The fixtures and the plugin under test meet at the upgrade script."""

    def upgrade_module(self):
        return run_bench.load_upgrade(run_bench.DEFAULT_PLUGIN)

    def test_a_new_project_has_no_file_that_the_upgrade_would_change(self):
        for fixture in ("wordfreq", "todo-rust", "todo-clojure"):
            with self.subTest(fixture=fixture):
                folder = Path(tempfile.mkdtemp())
                self.addCleanup(shutil.rmtree, folder, True)
                project = run_bench.make_project(folder / "app", run_bench.DEFAULT_PLUGIN, fixture=fixture)
                module = self.upgrade_module()
                plan = module.build_plan(str(project), str(run_bench.DEFAULT_PLUGIN), set())
                self.assertEqual(plan["files"], [])
                self.assertEqual(run_bench.git(project, "log", "--format=%s").stdout.split("\n")[:-1],
                                 ["Set up pdlc"])

    def test_each_fixture_lists_the_acceptance_lock_in_its_trailer_spec(self):
        for path in (run_bench.FIXTURE, run_bench.HERE / "fixtures" / "todo-rust", run_bench.HERE / "fixtures" / "todo-clojure"):
            with self.subTest(fixture=path.name):
                text = (path / "pdlc" / "specs" / "design" / "DES-pdlc-commit-trailers.md").read_text()
                self.assertIn("Lock acceptance", text)

    def test_each_fixture_has_a_marker_of_the_current_plugin(self):
        version = json.loads((run_bench.DEFAULT_PLUGIN / ".claude-plugin" / "plugin.json").read_text())["version"]
        for path in (run_bench.FIXTURE, run_bench.HERE / "fixtures" / "todo-rust", run_bench.HERE / "fixtures" / "todo-clojure"):
            with self.subTest(fixture=path.name):
                marker = json.loads((path / "pdlc" / "version.json").read_text())
                self.assertEqual(marker["pdlc"], version)
                self.assertIn("specs/design/DES-errors.md", marker["files"])

    def test_a_changed_plugin_file_reaches_a_new_project(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        plugin = folder / "pdlc"
        shutil.copytree(run_bench.DEFAULT_PLUGIN, plugin, ignore=shutil.ignore_patterns("__pycache__"))
        port = plugin / "skills" / "init" / "references" / "ports" / "checks.md"
        port.write_text(port.read_text() + "\nA line that the test adds.\n")
        project = run_bench.make_project(folder / "app", plugin)
        self.assertIn("A line that the test adds.", (project / "pdlc" / "ports" / "checks.md").read_text())


def synthetic_snapshot(test):
    """A bundle with the commits of a finished run in the form of the new snapshots.

    main:               Set up pdlc, Specify IN-0001
    pdlc/IN-0001-x:     Ready, Plan, Acceptance reviewed
    pdlc/CH-0001-x:     Tests reviewed, Built, Verified, Visual review, Propose
    """
    folder = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, folder, True)
    repo = run_bench.make_project(folder / "src", run_bench.DEFAULT_PLUGIN)
    tools = repo / "pdlc" / ".tools"
    if tools.is_symlink():
        tools.unlink()
        run_bench.git(repo, "rm", "-q", "--cached", "pdlc/.tools")

    def commit(subject, files=None):
        for name, text in (files or {}).items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text)
        run_bench.git(repo, "add", "-A")
        run_bench.git(repo, "commit", "-q", "--allow-empty", "-m", subject)

    commit("Specify IN-0001", {"pdlc/inbox/IN-0001-x.md": "# IN-0001 · x\n\nStatus: ready · Branch: pdlc/IN-0001-x\n"})
    run_bench.git(repo, "checkout", "-q", "-b", "pdlc/IN-0001-x")
    commit("Ready IN-0001")
    commit("Plan IN-0001", {"pdlc/changes/CH-0001-x/change.md":
                            "# CH-0001 · x\n\nIntent: IN-0001 · Status: planned · Branch: pdlc/CH-0001-x\n"})
    commit("Acceptance reviewed IN-0001", {"pdlc/inbox/IN-0001-x.md":
                                           "# IN-0001 · x\n\nStatus: ready · Branch: pdlc/IN-0001-x\n\nAcceptance-Locked: abc123\n"})
    run_bench.git(repo, "checkout", "-q", "-b", "pdlc/CH-0001-x")
    for subject in ("Tests reviewed CH-0001", "Built CH-0001", "Verified CH-0001", "Visual review CH-0001", "Propose CH-0001"):
        commit(subject)
    run_bench.git(repo, "checkout", "-q", "main")
    bundle = folder / "synthetic.bundle"
    run_bench.git(repo, "bundle", "create", str(bundle), "--all")
    return bundle


def realistic_snapshot(test):
    """A bundle laid out as a finished run: intake, ready and plan on main with Branch none,
    the acceptance stage starts the intent branch, a stacked second change, HEAD on the last branch."""
    folder = Path(tempfile.mkdtemp())
    test.addCleanup(shutil.rmtree, folder, True)
    repo = run_bench.make_project(folder / "src", run_bench.DEFAULT_PLUGIN)
    tools = repo / "pdlc" / ".tools"
    tools.unlink()
    run_bench.git(repo, "rm", "-q", "--cached", "pdlc/.tools")

    def commit(subject, files=None):
        for name, text in (files or {}).items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text)
        run_bench.git(repo, "add", "-A")
        run_bench.git(repo, "commit", "-q", "--allow-empty", "-m", subject)

    def change(number, scope, status, branch, base):
        return {"pdlc/changes/CH-000%d-x/change.md" % number:
                "# CH-000%d · x\n\nIntent: IN-0001 · Scope: %s · Status: %s · Ticket: none · Branch: %s · Base: %s\n"
                % (number, scope, status, branch, base)}

    intent = "pdlc/inbox/IN-0001-x.md"
    head = "# IN-0001 · x\n\nStatus: %s · Ticket: none · Branch: %s · Added: 2026\n"
    commit("Specify IN-0001: x", {intent: head % ("proposed", "none")})
    commit("Ready IN-0001: x")
    commit("Plan IN-0001: a, b", {**change(1, "CAP-a", "planned", "none", "main"),
                                  **change(2, "JOB-b", "planned", "none", "main")})
    run_bench.git(repo, "checkout", "-q", "-b", "pdlc/IN-0001-x")
    commit("Acceptance IN-0001", {intent: head % ("building", "pdlc/IN-0001-x")})
    commit("Lock acceptance IN-0001")
    commit("Acceptance reviewed IN-0001")
    run_bench.git(repo, "checkout", "-q", "-b", "pdlc/CH-0001-x")
    commit("Start CH-0001", change(1, "CAP-a", "building", "pdlc/CH-0001-x", "main"))
    for subject in ("Tests reviewed CH-0001", "Built CH-0001", "Verified CH-0001", "Visual review CH-0001",
                    "Propose CH-0001"):
        commit(subject)
    run_bench.git(repo, "checkout", "-q", "-b", "pdlc/CH-0002-x")
    commit("Start CH-0002", change(2, "JOB-b", "building", "pdlc/CH-0002-x", "pdlc/CH-0001-x"))
    for subject in ("Tests reviewed CH-0002", "Built CH-0002", "Verified CH-0002", "Propose CH-0002"):
        commit(subject)
    bundle = folder / "real.bundle"
    run_bench.git(repo, "bundle", "create", str(bundle), "--all")
    return bundle


class SnapshotTest(unittest.TestCase):
    def synthetic(self):
        bundle = synthetic_snapshot(self)
        patcher = mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"], "bundle": bundle}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def prepare(self, state, snapshot):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        with contextlib.redirect_stdout(io.StringIO()):
            run_bench.main(["prepare", "--state", state, "--snapshot", snapshot, "--dest", str(folder / "app")])
        return folder / "app"

    def real(self, name):
        if not run_bench.SNAPSHOTS[name]["bundle"].exists():
            self.skipTest("the snapshot %s is not recorded yet" % name)

    def subject(self, project, rev="HEAD"):
        return run_bench.git(project, "log", "-1", "--format=%s", rev).stdout.strip()

    def branch(self, project):
        return run_bench.git(project, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def test_the_default_snapshot_is_wordfreq_and_r5_is_the_old_one(self):
        self.assertEqual(run_bench.DEFAULT_SNAPSHOT, "wordfreq")
        self.assertEqual(sorted(run_bench.SNAPSHOTS), ["r5", "todo-rust", "wordfreq"])
        self.assertEqual(run_bench.SNAPSHOTS["r5"]["bundle"], run_bench.SECTIONS / "project.bundle")
        self.assertEqual(run_bench.SNAPSHOTS["todo-rust"]["fixture"], "todo-rust")

    def test_the_new_stages_add_acceptance_and_end_the_run_with_the_proposal(self):
        self.assertEqual(list(run_bench.REPLAY_STAGES),
                         ["intake", "ready", "change", "acceptance", "tests", "build", "verify", "show"])
        self.assertEqual(run_bench.REPLAY_STAGES["acceptance"][0], "Plan IN-0001")
        self.assertEqual(run_bench.REPLAY_STAGES["tests"][0], "Acceptance reviewed IN-0001")
        self.assertEqual(run_bench.REPLAY_STAGES["show"][2], "Propose CH-")
        self.assertNotIn("acceptance", run_bench.LEGACY_STAGES)

    def test_the_legacy_table_is_unchanged(self):
        self.assertEqual(run_bench.LEGACY_STAGES["show"][3], "Visual review CH-")
        self.assertEqual(run_bench.LEGACY_STAGES["tests"][0], "Plan IN-0001")

    def test_prepare_states_follow_the_snapshot(self):
        self.assertIn("acceptance", run_bench.prepare_states("wordfreq"))
        self.assertNotIn("acceptance", run_bench.prepare_states("r5"))
        self.assertEqual(run_bench.prepare_states("r5")[0], "init")
        self.assertEqual(run_bench.prepare_states("r5")[-2:], ["done", "board"])

    def test_prepare_refuses_a_state_that_the_snapshot_lacks(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                self.prepare("acceptance", "r5")

    def test_prepare_says_so_when_the_bundle_is_missing(self):
        with mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"],
                                                                "bundle": Path("/nonexistent/x.bundle")}}):
            with self.assertRaises(SystemExit) as caught:
                self.prepare("ready", "wordfreq")
        self.assertIn("x.bundle", str(caught.exception))

    def test_prepare_r5_ready_keeps_the_bundle_and_adds_only_the_upgrade(self):
        project = self.prepare("ready", "r5")
        head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
        self.assertTrue(self.subject(project, head).startswith("Specify IN-0001"))
        self.assertEqual(self.branch(project), "main")
        bundle = run_bench.SNAPSHOTS["r5"]["bundle"]
        clone = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, clone, True)
        subprocess.run(["git", "clone", "-q", str(bundle), str(clone / "x")], check=True)
        entry = run_bench.entry_commit(clone / "x", "Specify IN-0001")
        self.assertEqual(run_bench.git(project, "rev-parse", head + "^{tree}").stdout,
                         run_bench.git(clone / "x", "rev-parse", entry + "^{tree}").stdout)
        # What differs from the bundle is the upgrade: pdlc/ and the .gitignore line.
        changed = run_bench.git(project, "diff", "--name-only", entry, "HEAD").stdout.split()
        self.assertTrue(changed and all(name.startswith("pdlc/") or name == ".gitignore" for name in changed), changed)
        self.assertIn("pdlc/version.json", changed)
        for name in ("check-tagging", "commit-trailers", "review-checklist"):
            self.assertIn("pdlc/specs/design/DES-pdlc-%s.md" % name, changed)
        self.assertEqual(run_bench.git(project, "branch", "--format=%(refname:short)").stdout.split(), ["main"])

    def test_each_state_of_a_new_snapshot_starts_on_the_right_branch(self):
        self.synthetic()
        expected = {
            "intake": ("Set up pdlc", "main"),
            "ready": ("Specify IN-0001", "pdlc/IN-0001-x"),
            "change": ("Ready IN-0001", "pdlc/IN-0001-x"),
            "acceptance": ("Plan IN-0001", "pdlc/IN-0001-x"),
            "tests": ("Acceptance reviewed IN-0001", "pdlc/IN-0001-x"),
            "build": ("Tests reviewed CH-0001", "pdlc/CH-0001-x"),
            "verify": ("Built CH-0001", "pdlc/CH-0001-x"),
            "show": ("Verified CH-0001", "pdlc/CH-0001-x"),
            "done": ("Propose CH-0001", "pdlc/CH-0001-x"),
        }
        for state, (subject, branch) in expected.items():
            with self.subTest(state=state):
                project = self.prepare(state, "wordfreq")
                head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
                self.assertTrue(self.subject(project, head).startswith(subject), self.subject(project, head))
                self.assertEqual(self.branch(project), branch)
                self.assertEqual(run_bench.git(project, "rev-parse", "start").stdout,
                                 run_bench.git(project, "rev-parse", "HEAD").stdout)
                self.assertEqual(run_bench.git(project, "remote").stdout.strip(), "")

    def test_main_is_the_last_commit_of_main_before_the_entry_commit(self):
        self.synthetic()
        project = self.prepare("verify", "wordfreq")
        self.assertEqual(self.subject(project, "main"), "Specify IN-0001")
        project = self.prepare("intake", "wordfreq")
        self.assertEqual(self.subject(project, "main"), "Set up pdlc")

    def test_the_acceptance_stage_is_finished_when_the_intent_is_locked(self):
        self.synthetic()
        project, entry = run_bench.make_stage_project(Path(tempfile.mkdtemp()) / "app", "acceptance",
                                                      run_bench.DEFAULT_PLUGIN, "wordfreq")
        self.addCleanup(shutil.rmtree, project.parent, True)
        result = run_bench.check_stage(project, "acceptance", entry, "wordfreq")
        self.assertFalse(result["finished"])
        self.assertFalse(result["ok"])
        # the commit after the entry commit, here made by hand
        run_bench.git(project, "checkout", "-q", "pdlc/IN-0001-x")
        intent = next((project / "pdlc" / "inbox").glob("IN-0001-*.md"))
        intent.write_text(intent.read_text() + "\nAcceptance-Locked: abc123\n")
        run_bench.git(project, "add", "-A")
        run_bench.git(project, "commit", "-q", "-m", "Acceptance reviewed IN-0001")
        run_bench.git(project, "checkout", "-q", "main")
        result = run_bench.check_stage(project, "acceptance", entry, "wordfreq")
        self.assertTrue(result["finished"])
        self.assertTrue(result["extra"]["locked"])
        self.assertTrue(result["ok"])

    def test_the_recorded_snapshots_start_each_state(self):
        for name in ("wordfreq", "todo-rust"):
            for state in run_bench.prepare_states(name):
                if state in ("init", "board"):
                    continue
                with self.subTest(snapshot=name, state=state):
                    self.real(name)
                    project = self.prepare(state, name)
                    head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
                    if state == "done":
                        self.assertTrue(self.subject(project, head).startswith("Propose CH-"))
                    else:
                        self.assertTrue(self.subject(project, head).startswith(run_bench.REPLAY_STAGES[state][0]))
                    self.assertEqual(run_bench.git(project, "rev-parse", "start").stdout,
                                     run_bench.git(project, "rev-parse", "HEAD").stdout)


    def heads(self, project):
        return sorted(run_bench.git(project, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split())

    def test_a_realistic_layout_gives_the_right_branches_and_no_leaked_branch(self):
        bundle = realistic_snapshot(self)
        IN, C1, C2 = "pdlc/IN-0001-x", "pdlc/CH-0001-x", "pdlc/CH-0002-x"
        expected = {
            "intake": ("Set up pdlc", "main", ["main"]),
            "ready": ("Specify IN-0001", "main", ["main"]),
            "change": ("Ready IN-0001", "main", ["main"]),
            "acceptance": ("Plan IN-0001", "main", ["main"]),
            "tests": ("Acceptance reviewed IN-0001", IN, sorted(["main", IN])),
            "build": ("Tests reviewed CH-0001", C1, sorted(["main", C1])),
            "verify": ("Built CH-0001", C1, sorted(["main", C1])),
            "show": ("Verified CH-0001", C1, sorted(["main", C1])),
            "done": ("Propose CH-0002", C2, sorted(["main", C1, C2])),
        }
        with mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"], "bundle": bundle}}):
            for state, (subject, branch, heads) in expected.items():
                with self.subTest(state=state):
                    project = self.prepare(state, "wordfreq")
                    head = "HEAD~1" if self.subject(project) == "Upgrade pdlc" else "HEAD"
                    self.assertTrue(self.subject(project, head).startswith(subject), self.subject(project, head))
                    self.assertEqual(self.branch(project), branch)
                    self.assertEqual(self.heads(project), heads)

    def test_the_done_state_puts_the_base_branch_at_its_last_commit_before_the_tip(self):
        bundle = realistic_snapshot(self)
        with mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"], "bundle": bundle}}):
            project = self.prepare("done", "wordfreq")
        self.assertTrue(self.subject(project, "pdlc/CH-0001-x").startswith("Propose CH-0001"))
        self.assertTrue(self.subject(project, "main").startswith("Plan IN-0001"))

    def test_a_replay_on_todo_rust_checks_with_its_own_unit_checks_and_no_wordfreq_probes(self):
        self.synthetic()
        with mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"], "fixture": "todo-rust"}}):
            project, entry = run_bench.make_stage_project(Path(tempfile.mkdtemp()) / "app", "build",
                                                          run_bench.DEFAULT_PLUGIN, "wordfreq")
            self.addCleanup(shutil.rmtree, project.parent, True)
            with mock.patch.object(run_bench, "unit_checks", return_value={"ok": True, "ran": 3}) as unit, \
                    mock.patch.object(run_bench, "run_probes") as probes:
                result = run_bench.check_stage(project, "build", entry, "wordfreq")
            probes.assert_not_called()
            unit.assert_called_with(mock.ANY, "todo-rust")
            self.assertTrue(result["extra"]["probes"]["not_run"])
            outcome = run_bench.stage_outcome("build", result, entry)
            self.assertEqual(outcome["probes"]["failed"], [])

    def test_a_replay_gives_the_agent_the_tools_of_the_fixture(self):
        self.synthetic()
        calls = []

        def fake(prompt, cwd, plugin, log, **kw):
            calls.append(kw)
            return [], 0.0, ""

        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out, True)
        args = Namespace(plugin=str(run_bench.DEFAULT_PLUGIN), out=str(out), label="x", stage="intake", runs=1,
                         timeout=10, budget=1.0, snapshot="wordfreq")
        with mock.patch.dict(run_bench.SNAPSHOTS, {"wordfreq": {**run_bench.SNAPSHOTS["wordfreq"], "fixture": "todo-rust"}}), \
                mock.patch.object(run_bench, "run_claude", side_effect=fake), \
                mock.patch.object(run_bench, "analyse", return_value={"totals": {"cost_usd": 0.0}}):
            run_bench.command_stage(args)
        self.assertEqual(calls[0]["tools"], run_bench.FIXTURES["todo-rust"]["tools"])
        self.assertTrue(calls[0]["tools"])

    def test_the_freeze_of_a_stage_result_keeps_the_snapshot_name(self):
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        (folder / "e2e.json").write_text(json.dumps({"plugin_commit": "abc", "snapshot": "wordfreq", "runs": []}))
        with contextlib.redirect_stdout(io.StringIO()):
            run_bench.command_freeze(Namespace(results=[str(folder / "e2e.json")], out=str(folder / "b.json"),
                                               seeds=None, label="x"))
        self.assertEqual(json.loads((folder / "b.json").read_text())["snapshot"], "wordfreq")

    def test_e2e_takes_an_intent_that_replaces_the_one_of_the_fixture(self):
        args = run_bench.build_parser().parse_args(["e2e", "--label", "x", "--intent", "Do a thing."])
        self.assertEqual(args.intent, "Do a thing.")
        args = run_bench.build_parser().parse_args(["e2e", "--label", "x"])
        self.assertIsNone(args.intent)


class ShipLogCopyTest(unittest.TestCase):
    ENTRY = {"t": "2031-01-01T00:00:01+00:00", "run": "ship-x", "session": "s", "event": "run_start",
             "branch": "main", "head": "abc", "plugin": "0.6.0"}

    def setUp(self):
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.project, self.out = self.work / "app", self.work / "out"
        (self.project / "pdlc/.logs").mkdir(parents=True)
        self.out.mkdir()

    def test_the_log_is_copied_and_summarised(self):
        (self.project / "pdlc/.logs/ship-20310101T000001Z.jsonl").write_text(json.dumps(self.ENTRY) + "\n")
        summary = run_bench.collect_shiplog(self.project, self.out, 2, run_bench.HERE.parent / "plugins/pdlc")
        copied = self.out / "run2.shiplog.jsonl"
        self.assertEqual(json.loads(copied.read_text().splitlines()[0])["event"], "run_start")
        self.assertIn("the log ends with no turn_end", summary)

    def test_the_newest_log_by_modified_time_is_copied(self):
        old, new = (self.project / ("pdlc/.logs/ship-%s.jsonl" % n) for n in ("20310101T000009Z", "20300101T000001Z"))
        old.write_text(json.dumps({**self.ENTRY, "run": "old"}) + "\n")
        new.write_text(json.dumps({**self.ENTRY, "run": "new"}) + "\n")
        os.utime(old, (1000, 1000))
        os.utime(new, (2000, 2000))
        run_bench.collect_shiplog(self.project, self.out, 1, run_bench.HERE.parent / "plugins/pdlc")
        self.assertIn('"new"', (self.out / "run1.shiplog.jsonl").read_text())

    def test_no_log_gives_none(self):
        self.assertIsNone(run_bench.collect_shiplog(self.project, self.out, 1, run_bench.HERE.parent / "plugins/pdlc"))
        self.assertFalse((self.out / "run1.shiplog.jsonl").exists())

    def test_e2e_stores_the_summary_under_shiplog(self):
        (self.project / "pdlc/.logs/ship-20310101T000001Z.jsonl").write_text(json.dumps(self.ENTRY) + "\n")
        args = Namespace(plugin=str(run_bench.HERE.parent / "plugins/pdlc"), out=str(self.out), label="x", runs=1,
                         fixture="wordfreq", intent=None, timeout=1, budget=1, forward=False)
        project = self.project
        with mock.patch.object(run_bench, "make_project", return_value=project), \
                mock.patch.object(run_bench, "run_claude", return_value=([], 1, "")), \
                mock.patch.object(run_bench, "analyse", return_value={"totals": {"cost_usd": 0.0}}), \
                mock.patch.object(run_bench, "inspect_project",
                                  return_value={"probes": {"passed": 0, "total": 0, "failed": []}}), \
                contextlib.redirect_stdout(io.StringIO()):
            run_bench.command_e2e(args)
        saved = json.loads((self.out / "x/run1.json").read_text())
        self.assertIn("run_start", (self.out / "x/run1.shiplog.jsonl").read_text())
        self.assertIn("end", saved["shiplog"])


class RebuildCopyTest(unittest.TestCase):
    branch = "pdlc/CH-0001-x"

    def setUp(self):
        self.app = rebuild_project(self)
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.tree = run_bench.export_tree(self.app, self.branch, self.work / "tree")

    def files_of(self, folder):
        return sorted(p.relative_to(folder).as_posix() for p in Path(folder).rglob("*")
                      if p.is_file() and ".git" not in p.relative_to(folder).parts)

    def spec_files(self):
        return [f for f in self.files_of(self.tree) if f.startswith("pdlc/specs/")]

    def test_the_clean_copy_has_the_specs_the_config_and_the_readme_only(self):
        kept = run_bench.clean_copy(self.tree, self.work / "copy")
        expected = sorted(self.spec_files() + ["pdlc/config.md", "pdlc/README.md"])
        self.assertEqual(kept, expected)
        self.assertEqual(self.files_of(self.work / "copy"), expected)
        self.assertIn("pdlc/specs/jobs/JOB-branch-only.md", kept)

    def test_the_clean_copy_has_no_code_no_checks_and_one_commit(self):
        run_bench.clean_copy(self.tree, self.work / "copy")
        found = self.files_of(self.work / "copy")
        self.assertEqual([f for f in found if f.endswith(".py")], [])
        self.assertEqual([f for f in found if f.startswith("tests/")], [])
        copy = self.work / "copy"
        self.assertEqual(run_bench.git(copy, "rev-list", "--count", "HEAD").stdout.strip(), "1")
        self.assertEqual(run_bench.git(copy, "log", "-1", "--format=%s").stdout.strip(), "Specs only")
        self.assertEqual(run_bench.git(copy, "status", "--porcelain").stdout, "")

    def test_the_export_reads_the_branch_and_not_the_checked_out_main(self):
        main = run_bench.export_tree(self.app, "main", self.work / "main")
        self.assertFalse((main / "pdlc" / "specs" / "jobs" / "JOB-branch-only.md").exists())
        self.assertTrue((self.tree / "pdlc" / "specs" / "jobs" / "JOB-branch-only.md").exists())
        self.assertFalse((self.tree / ".git").exists())

    def test_keep_adds_only_the_named_file(self):
        base = run_bench.clean_copy(self.tree, self.work / "plain")
        kept = run_bench.clean_copy(self.tree, self.work / "extra", keep=["Cargo.toml"])
        self.assertEqual(kept, sorted(base + ["Cargo.toml"]))
        self.assertEqual(self.files_of(self.work / "extra"), kept)

    def test_config_checks_reads_the_rust_config(self):
        text = (run_bench.HERE / "fixtures" / "todo-rust" / "pdlc" / "config.md").read_text()
        config = run_bench.config_checks(text)
        self.assertEqual(config["check_folders"], ["tests/", "acceptance/"])
        self.assertEqual(config["acceptance_file"], "acceptance/{intent}.rs")
        self.assertEqual(config["all"], "cargo test")
        self.assertTrue(config["acceptance"].startswith("cargo build -q && for f in {files}"))
        self.assertEqual(config["id_form"], "underscored")

    def test_config_checks_gives_none_for_a_missing_line(self):
        text = (run_bench.FIXTURE / "pdlc" / "config.md").read_text()
        config = run_bench.config_checks(text)
        self.assertEqual(config["all"], "python3 -m unittest discover -s tests")
        self.assertEqual(config["check_folders"], ["tests/"])
        self.assertIsNone(config["acceptance"])
        self.assertIsNone(config["acceptance_file"])

    def test_config_checks_gives_none_for_the_value_none(self):
        config = run_bench.config_checks("## Checks\n\n- all: `make test`\n- acceptance: none\n"
                                         "- check folders: none\n\n## Reviews\n\n- acceptance: `x`\n")
        self.assertIsNone(config["acceptance"])
        self.assertIsNone(config["check_folders"])
        self.assertEqual(config["all"], "make test")

    def config(self):
        return run_bench.config_checks((self.tree / "pdlc" / "config.md").read_text())

    def test_acceptance_files_leave_out_the_file_of_init(self):
        self.assertEqual(run_bench.acceptance_files(self.tree, self.config()), ["tests/acceptance_IN-0001.py"])

    def test_acceptance_files_are_empty_without_an_acceptance_line(self):
        config = run_bench.config_checks("## Checks\n\n- all: `make test`\n")
        self.assertEqual(run_bench.acceptance_files(self.tree, config), [])

    def test_check_files_are_the_component_checks(self):
        found = run_bench.check_files(self.tree, self.config())
        self.assertEqual(found, ["tests/test_cli.py", "tests/test_counter.py", "tests/test_new.py"])

    def test_check_origin_tells_where_each_check_came_from(self):
        found = run_bench.check_files(self.tree, self.config())
        origin = run_bench.check_origin(self.app, self.branch, found)
        self.assertEqual(origin, {"tests/test_cli.py": "changed by pdlc",
                                  "tests/test_counter.py": "pre-pdlc",
                                  "tests/test_new.py": "added by pdlc"})

    def test_rebuild_source_reads_a_result_folder(self):
        folder = self.work / "results"
        folder.mkdir()
        (folder / "run2.json").write_text(run_bench.json.dumps(
            {"project": str(self.app), "outcome": {"tip": "main"}}))
        (folder / "e2e.json").write_text(run_bench.json.dumps({"fixture": "todo-rust"}))
        self.assertEqual(run_bench.rebuild_source(folder, run=2), (self.app, "main", "todo-rust"))
        self.assertEqual(run_bench.rebuild_source(folder, run=2, ref=self.branch)[1], self.branch)

    def test_rebuild_source_gives_a_clear_error_for_each_failure(self):
        folder = self.work / "empty"
        folder.mkdir()
        with self.assertRaisesRegex(RuntimeError, "no run1.json in"):
            run_bench.rebuild_source(folder)
        with self.assertRaisesRegex(RuntimeError, "does not exist"):
            run_bench.rebuild_source(self.work / "nowhere")
        (folder / "run1.json").write_text(run_bench.json.dumps({"project": str(folder), "outcome": {}}))
        with self.assertRaisesRegex(RuntimeError, "is not a git repository"):
            run_bench.rebuild_source(folder)

    def test_a_symlink_in_the_specs_is_not_followed(self):
        os.symlink(self.tree / "wordfreq" / "cli.py", self.tree / "pdlc" / "specs" / "link.md")
        kept = run_bench.clean_copy(self.tree, self.work / "copy")
        self.assertNotIn("pdlc/specs/link.md", kept)
        self.assertFalse((self.work / "copy" / "pdlc" / "specs" / "link.md").exists())

    def test_a_backup_file_next_to_the_config_is_not_kept(self):
        for name in ("pdlc/config.md.orig", "pdlc/README.md~"):
            (self.tree / name).write_text("old\n")
        kept = run_bench.clean_copy(self.tree, self.work / "copy")
        self.assertNotIn("pdlc/config.md.orig", kept)
        self.assertNotIn("pdlc/README.md~", kept)

    def test_a_file_that_only_looks_like_an_acceptance_file_does_not_match(self):
        (self.tree / "tests" / "acceptance_notes.py").write_text("x\n")
        self.assertEqual(run_bench.acceptance_files(self.tree, self.config()), ["tests/acceptance_IN-0001.py"])
        config = {"acceptance_file": "tests/test_{intent}.py"}
        self.assertEqual(run_bench.acceptance_files(self.tree, config), [])

    def test_a_backticked_none_is_none(self):
        config = run_bench.config_checks("## Checks\n\n- acceptance: `none`\n- check folders: `None`\n")
        self.assertIsNone(config["acceptance"])
        self.assertIsNone(config["check_folders"])

    def test_a_tree_with_nothing_to_keep_is_an_error(self):
        empty = self.work / "nothing"
        empty.mkdir()
        (empty / "a.py").write_text("x\n")
        with self.assertRaises(RuntimeError):
            run_bench.clean_copy(empty, self.work / "copy")

    def test_rebuild_source_reads_a_project_folder(self):
        run_bench.git(self.app, "checkout", "-q", self.branch)
        run_bench.git(self.app, "commit", "-q", "--allow-empty", "-m", "Later")
        run_bench.git(self.app, "checkout", "-q", "main")
        project, ref, fixture = run_bench.rebuild_source(self.app)
        self.assertEqual((project, ref, fixture), (self.app, self.branch, "wordfreq"))

    def test_rebuild_source_names_a_project_that_is_gone(self):
        folder = self.work / "results"
        folder.mkdir()
        (folder / "run1.json").write_text(run_bench.json.dumps(
            {"project": str(self.work / "gone"), "outcome": {"tip": "main"}}))
        with self.assertRaises(RuntimeError) as caught:
            run_bench.rebuild_source(folder)
        self.assertIn("gone", str(caught.exception))


UNITTEST_OUTPUT = """\
.F
======================================================================
FAIL: test_b (tests.test_a.ATest.test_b)
----------------------------------------------------------------------
AssertionError: 1 != 2

======================================================================
ERROR: test_c (tests.test_a.ATest.test_c)
----------------------------------------------------------------------
Ran 3 tests in 0.002s

FAILED (failures=1, errors=1)
"""
CARGO_OUTPUT = """\
running 3 tests
test store::tests::adds ... ok
test store::tests::removes ... FAILED
test page::tests::escapes ... ok

failures:

---- store::tests::removes stdout ----
panicked at src/store.rs:9

failures:
    store::tests::removes

test result: FAILED. 2 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out

running 1 test
test src_lib_doc ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out
"""
CLOJURE_OUTPUT = """\
Testing todo.store-test

FAIL in (adds-an-item) (store_test.clj:9)
expected: (= 1 2)

ERROR in (removes-an-item) (store_test.clj:14)

Ran 4 tests containing 6 assertions.
1 failures, 1 errors.
"""

ACCEPTANCE_FILE = """\
import io
import unittest

from wordfreq.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    return main(argv, stdout=out, stderr=err), out.getvalue(), err.getvalue()


class JOB_top_option_R1(unittest.TestCase):
    def test_JOB_top_option_R1_keeps_the_most_common(self):
        import os, tempfile
        handle, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(handle, "w") as file:
            file.write("the the cat")
        self.addCleanup(os.remove, path)
        self.assertEqual(run(["--top", "1", path]), (0, "the 2\\n", ""))


class JOB_top_option_R2(unittest.TestCase):
    def test_JOB_top_option_R2_zero_is_an_error(self):
        code, out, err = run(["--top", "0", "x.txt"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: --top needs a whole number greater than zero\\n")
"""
SPEC_TEXT = "# JOB-top-option · Keep the top words\\n\\nR1. The command can run `main` with --top.\\n"


class RebuildScoreTest(unittest.TestCase):
    branch = "pdlc/CH-0001-x"
    acceptance_names = ["test_JOB_top_option_R1_keeps_the_most_common", "test_JOB_top_option_R2_zero_is_an_error"]

    def setUp(self):
        self.app = rebuild_project(self)
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.tree = run_bench.export_tree(self.app, self.branch, self.work / "tree")
        (self.tree / "tests" / "acceptance_IN-0001.py").write_text(ACCEPTANCE_FILE)
        (self.tree / "pdlc" / "specs" / "jobs" / "JOB-top-option.md").write_text(SPEC_TEXT)
        # The usage line changes with the option, so pdlc changed this check too.
        cli_check = self.tree / "tests" / "test_cli.py"
        cli_check.write_text(cli_check.read_text().replace("usage: wordfreq FILE", "usage: wordfreq [--top N] FILE"))
        self.config = run_bench.config_checks((self.tree / "pdlc" / "config.md").read_text())
        self.count = 0

    def rebuilt(self, oracle=False):
        self.count += 1
        dest = self.work / ("rebuilt%d" % self.count)
        run_bench.clean_copy(self.tree, dest)
        if oracle:
            shutil.copytree(self.tree / "wordfreq", dest / "wordfreq", ignore=shutil.ignore_patterns("__pycache__"))
        return dest

    def score(self, rebuilt):
        return run_bench.score_rebuild(self.tree, rebuilt, self.config, "wordfreq")

    def basic(self, text):
        found = run_bench.parse_check_output(text)
        return {"ran": found["ran"], "failed": found["failed"]}

    def test_parse_unittest_output(self):
        found = self.basic(UNITTEST_OUTPUT)
        self.assertEqual(found, {"ran": 3, "failed": ["test_b (tests.test_a.ATest.test_b)",
                                                      "test_c (tests.test_a.ATest.test_c)"]})

    def test_parse_unittest_output_of_one_test(self):
        self.assertEqual(self.basic("Ran 1 test in 0.001s\n\nOK\n"), {"ran": 1, "failed": []})

    def test_parse_rust_output_sums_each_harness(self):
        found = self.basic(CARGO_OUTPUT)
        self.assertEqual(found, {"ran": 4, "failed": ["store::tests::removes"]})

    def test_parse_clojure_output(self):
        found = self.basic(CLOJURE_OUTPUT)
        self.assertEqual(found, {"ran": 4, "failed": ["adds-an-item store_test.clj", "removes-an-item store_test.clj"]})

    def test_parse_output_with_no_runner_gives_nothing(self):
        self.assertEqual(self.basic("Traceback: boom\n"), {"ran": 0, "failed": []})

    def test_run_checks_fills_in_the_files_and_reports_the_exit_code(self):
        done = run_bench.run_checks(self.work, "echo {files}; exit 3", ["a.py", "b.py"])
        self.assertFalse(done["ok"])
        self.assertIn("a.py b.py", done["output"])
        self.assertTrue(run_bench.run_checks(self.work, "true")["ok"])

    def test_run_checks_runs_in_the_project_and_keeps_the_last_2000_characters(self):
        done = run_bench.run_checks(self.work, "pwd; python3 -c \"print('x' * 3000 + 'END')\"")
        self.assertEqual(len(done["output"]), 2000)
        self.assertTrue(done["output"].endswith("END\n"))
        self.assertEqual(run_bench.run_checks(self.work, "pwd")["output"].strip(), str(self.work.resolve()))

    def test_run_checks_stops_at_the_timeout(self):
        done = run_bench.run_checks(self.work, "sleep 5", timeout=1)
        self.assertFalse(done["ok"])
        self.assertEqual(done["ran"], 0)

    def test_score_counts_every_original_check_when_the_run_crashed(self):
        names = ["test_a", "test_b", "test_c"]
        crashed = {"ran": 1, "failed": ["tests.test_a (unittest.loader._FailedTest)"]}
        self.assertEqual(run_bench.score(3, crashed, names), {"total": 3, "passed": 0, "failed": names})
        nothing = {"ran": 0, "failed": []}
        self.assertEqual(run_bench.score(3, nothing, names), {"total": 3, "passed": 0, "failed": names})

    def test_score_counts_the_checks_that_did_not_run_as_not_passed(self):
        partial = {"ran": 4, "failed": ["load error"]}
        found = run_bench.score(8, partial, ["a", "b"])
        self.assertEqual(found, {"total": 8, "passed": 3, "failed": ["load error"]})

    def test_score_with_a_full_run_uses_the_failures_only(self):
        found = run_bench.score(5, {"ran": 5, "failed": ["x", "y"]}, ["a"])
        self.assertEqual(found, {"total": 5, "passed": 3, "failed": ["x", "y"]})

    def test_score_never_goes_below_zero_or_above_the_total(self):
        self.assertEqual(run_bench.score(2, {"ran": 9, "failed": ["x"]}, [])["passed"], 1)
        self.assertEqual(run_bench.score(2, {"ran": 1, "failed": ["x", "y", "z"]}, [])["passed"], 0)
        self.assertEqual(run_bench.score(0, {"ran": 3, "failed": []}, [])["passed"], 0)

    def test_an_oracle_rebuild_scores_every_check_as_passed(self):
        got = self.score(self.rebuilt(oracle=True))
        self.assertEqual(got["acceptance"]["total"], 2)
        self.assertEqual(got["acceptance"]["passed"], 2)
        self.assertEqual(got["acceptance"]["failed"], [])
        self.assertGreaterEqual(got["component"]["total"], 8)
        self.assertEqual(got["component"]["passed"], got["component"]["total"])
        self.assertEqual(got["component"]["failed"], [])
        self.assertEqual(got["probes"]["passed"], got["probes"]["total"])
        self.assertEqual(got["probes"]["total"], len(run_bench.PROBES))
        self.assertEqual(got["gaps"], [])
        self.assertTrue(got["original"]["acceptance"]["ok"])
        self.assertTrue(got["original"]["component"]["ok"])

    def test_the_totals_come_from_the_original_run(self):
        oracle = self.score(self.rebuilt(oracle=True))
        empty = self.score(self.rebuilt())
        self.assertEqual(empty["component"]["total"], oracle["component"]["total"])
        self.assertEqual(empty["acceptance"]["total"], 2)

    def test_an_empty_rebuild_fails_each_acceptance_check_by_name(self):
        got = self.score(self.rebuilt())
        self.assertEqual(got["acceptance"]["passed"], 0)
        self.assertEqual(got["acceptance"]["total"], 2)
        self.assertEqual(sorted(got["acceptance"]["failed"]), sorted(self.acceptance_names))
        self.assertEqual(got["component"]["passed"], 0)
        self.assertEqual(got["probes"]["passed"], 0)

    def test_an_empty_rebuild_names_the_requirement_and_spec_of_each_gap(self):
        got = self.score(self.rebuilt())
        gaps = {gap["check"]: gap for gap in got["gaps"]}
        gap = gaps[self.acceptance_names[0]]
        self.assertEqual(gap["requirement"], "JOB-top-option.R1")
        self.assertEqual(gap["spec"], "pdlc/specs/jobs/JOB-top-option.md")
        self.assertEqual(gaps[self.acceptance_names[1]]["requirement"], "JOB-top-option.R2")
        # The spec gives `main`, so only the names that the spec leaves out are gaps.
        self.assertNotIn("main", gap["missing_names"])
        self.assertIn("main", run_bench.missing_names("main(argv)", "def main(argv): pass", "no names"))

    def test_a_renamed_function_fails_its_check_and_is_a_gap(self):
        rebuilt = self.rebuilt(oracle=True)
        counter = rebuilt / "wordfreq" / "counter.py"
        counter.write_text(counter.read_text().replace("def count_words", "def tally"))
        cli = rebuilt / "wordfreq" / "cli.py"
        cli.write_text(cli.read_text().replace("import count_words", "import tally as count_words"))
        got = self.score(rebuilt)
        self.assertTrue(any("test_counter" in name for name in got["component"]["failed"]))
        self.assertLess(got["component"]["passed"], got["component"]["total"])
        self.assertEqual(got["acceptance"]["passed"], 2)
        self.assertEqual(got["component"]["failed_files"], {got["component"]["failed"][0]: "tests/test_counter.py"})
        gap = next(g for g in got["gaps"] if "test_counter" in g["check"])
        self.assertIn("count_words", gap["missing_names"])
        self.assertNotIn("assertEqual", gap["missing_names"])
        self.assertNotIn("tally", gap["missing_names"])

    def test_a_check_that_the_builder_wrote_is_removed_before_the_originals_are_copied(self):
        rebuilt = self.rebuilt(oracle=True)
        (rebuilt / "tests").mkdir(exist_ok=True)
        (rebuilt / "tests" / "test_builder.py").write_text(
            "import unittest\n\nclass B(unittest.TestCase):\n    def test_fails(self):\n        self.fail('x')\n")
        (rebuilt / "tests" / "test_counter.py").write_text("import unittest\n")
        (rebuilt / "tests" / "acceptance_IN-0001.py").write_text("import unittest\n")
        original = self.score(self.rebuilt(oracle=True))
        got = self.score(rebuilt)
        self.assertFalse((rebuilt / "tests" / "test_builder.py").exists())
        self.assertEqual((rebuilt / "tests" / "test_counter.py").read_text(),
                         (self.tree / "tests" / "test_counter.py").read_text())
        for key in ("total", "passed", "failed"):
            self.assertEqual(got["component"][key], original["component"][key])
        self.assertEqual(got["acceptance"]["passed"], 2)
        self.assertEqual(got["component"]["passed"], got["component"]["total"])

    def test_install_checks_keeps_files_outside_the_check_folders(self):
        rebuilt = self.rebuilt(oracle=True)
        (rebuilt / "tests").mkdir(exist_ok=True)
        (rebuilt / "tests" / "extra.txt").write_text("x\n")
        run_bench.install_checks(self.tree, rebuilt, self.config)
        self.assertFalse((rebuilt / "tests" / "extra.txt").exists())
        self.assertTrue((rebuilt / "wordfreq" / "cli.py").exists())
        self.assertTrue((rebuilt / "pdlc" / "config.md").exists())

    def test_the_origin_of_each_check_file_goes_in_the_result(self):
        origin = {"tests/test_counter.py": "pre-pdlc"}
        got = run_bench.score_rebuild(self.tree, self.rebuilt(oracle=True), self.config, "wordfreq", origin)
        self.assertEqual(got["component"]["origin"], origin)

    def test_no_acceptance_command_means_acceptance_is_not_measured(self):
        config = dict(self.config, acceptance=None)
        got = run_bench.score_rebuild(self.tree, self.rebuilt(oracle=True), config, "wordfreq")
        self.assertEqual(got["acceptance"], {"measured": False})
        self.assertEqual(got["component"]["passed"], got["component"]["total"])

    def test_missing_names_keeps_only_names_in_the_check_and_the_code_but_not_the_spec(self):
        check = "from app import load_items, SPEC_NAME, ab\nself.assertEqual(load_items(x), None)\nlocal_only(1)"
        code = "def load_items(): pass\nSPEC_NAME = 1\nab = 2\nself.x = unused_name\nimport os"
        spec = "The function SPEC_NAME is described here."
        self.assertEqual(run_bench.missing_names(check, code, spec), ["load_items"])

    def test_missing_names_matches_whole_words_in_the_spec(self):
        check = "load_items()"
        self.assertEqual(run_bench.missing_names(check, "def load_items(): pass", "load_items_all"), ["load_items"])
        self.assertEqual(run_bench.missing_names(check, "def load_items(): pass", "Call `load_items()`"), [])

    def test_missing_names_leaves_out_keywords_and_builtins(self):
        check = "import unittest\nself.assertEqual(len(x), 1)\nfor item in range(3): print(item, None, True)"
        code = "import unittest\nself.x = 1\nfor item in range(3): print(item, None, True)\nlen(x)"
        self.assertEqual(run_bench.missing_names(check, code, ""), ["item", "unittest"])

    def test_checks_that_never_ran_are_not_counted_as_passed(self):
        # Six unit tests in src/ pass. The first failing binary stops cargo, so two checks never run.
        text = ("running 6 tests\n" + "".join("test tests::u%d ... ok\n" % n for n in range(6)) +
                "\ntest result: ok. 6 passed; 0 failed; 0 ignored\n\nrunning 2 tests\n"
                "test adds ... ok\ntest removes ... FAILED\n\nfailures:\n    removes\n\n"
                "test result: FAILED. 1 passed; 1 failed; 0 ignored\n")
        found = run_bench.parse_check_output(text)
        names = ["adds", "removes", "lists", "pages"]
        got = run_bench.score(len(names), found, names)
        self.assertEqual(got["total"], 4)
        self.assertEqual(got["passed"], 1)
        self.assertEqual(sorted(got["failed"]), ["lists", "pages", "removes"])

    def test_a_rust_unit_test_with_the_name_of_no_original_check_does_not_pass_one(self):
        found = run_bench.parse_check_output("running 1 test\ntest tests::adds ... ok\n\n"
                                             "test result: ok. 1 passed; 0 failed; 0 ignored\n")
        self.assertEqual(run_bench.score(2, found, ["adds", "lists"])["passed"], 1)
        self.assertEqual(run_bench.score(2, found, ["lists", "pages"])["passed"], 0)

    def test_a_unit_test_with_the_leaf_name_of_an_original_check_does_not_pass_it(self):
        text = ("     Running unittests src/lib.rs (target/debug/deps/todo-1)\n\nrunning 1 test\n"
                "test leaf::x ... ok\n\ntest result: ok. 1 passed; 0 failed; 0 ignored\n\n"
                "     Running tests/app.rs (target/debug/deps/app-2)\n\nrunning 1 test\n"
                "test x ... FAILED\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n\n"
                "   Doc-tests todo\n\nrunning 1 test\ntest src/lib.rs - x (line 1) ... ok\n")
        found = run_bench.parse_check_output(text)
        self.assertEqual(found["passed_names"], [("src/lib.rs", "leaf::x"), ("doc", "src/lib.rs - x (line 1)")])
        got = run_bench.score(1, found, ["x"], files=["tests/app.rs"])
        self.assertEqual(got, {"total": 1, "passed": 0, "failed": ["x"]})
        ok = run_bench.parse_check_output(text.replace("x ... FAILED", "x ... ok"))
        self.assertEqual(run_bench.score(1, ok, ["x"], files=["tests/app.rs"])["passed"], 1)

    def test_a_name_before_any_binary_header_counts(self):
        found = run_bench.parse_check_output("running 1 test\ntest x ... ok\n")
        self.assertEqual(found["passed_names"], [(None, "x")])
        self.assertEqual(run_bench.score(1, found, ["x"], files=["acceptance/IN-1.rs"])["passed"], 1)

    def test_same_named_rust_failures_in_two_binaries_both_count(self):
        text = ("test adds ... FAILED\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n\n"
                "test adds ... FAILED\n\ntest result: FAILED. 0 passed; 1 failed; 0 ignored\n")
        found = run_bench.parse_check_output(text)
        self.assertEqual(found["failed"], ["adds", "adds"])
        self.assertEqual(run_bench.score(2, found, ["adds", "adds"])["passed"], 0)

    def test_same_named_clojure_failures_in_two_files_both_count(self):
        text = ("FAIL in (adds) (a_test.clj:3)\nFAIL in (adds) (b_test.clj:5)\n"
                "Ran 4 tests containing 4 assertions.\n2 failures, 0 errors.\n")
        found = run_bench.parse_check_output(text)
        self.assertEqual(len(found["failed"]), 2)
        self.assertEqual(run_bench.score(4, found)["passed"], 2)

    def test_a_rust_doc_test_name_has_spaces(self):
        found = run_bench.parse_check_output("test src/lib.rs - add (line 3) ... FAILED\n")
        self.assertEqual(found["failed"], ["src/lib.rs - add (line 3)"])

    def test_the_failure_count_of_the_summary_counts_when_no_name_is_found(self):
        text = "Ran 3 tests in 0.1s\n\nFAILED (failures=2, errors=1)\n"
        found = run_bench.parse_check_output(text)
        self.assertEqual(found["failed"], [])
        self.assertEqual(run_bench.score(3, found)["passed"], 0)
        self.assertEqual(run_bench.score(5, run_bench.parse_check_output(
            "Ran 5 tests in 0.1s\n\nFAILED (failures=2)\n"))["passed"], 3)

    def test_skipped_checks_do_not_count_as_passed(self):
        found = run_bench.parse_check_output("Ran 5 tests in 0.1s\n\nOK (skipped=2)\n")
        self.assertEqual(found["skipped"], 2)
        self.assertEqual(run_bench.score(5, found)["passed"], 3)
        self.assertEqual(run_bench.score(5, found, skipped_original=2)["passed"], 5)
        both = run_bench.parse_check_output("Ran 5 tests in 0.1s\n\nOK (skipped=1, expected failures=1)\n")
        self.assertEqual(run_bench.score(5, both)["passed"], 3)

    def test_a_check_that_fails_in_the_original_run_makes_the_section_not_measured(self):
        (self.tree / "tests" / "test_bad.py").write_text(
            "import unittest\n\nclass B(unittest.TestCase):\n    def test_bad(self):\n        self.fail('x')\n")
        got = self.score(self.rebuilt(oracle=True))
        self.assertEqual(got["component"], {"measured": False, "reason": "the original checks did not pass"})
        self.assertTrue(got["acceptance"]["measured"])
        self.assertEqual(got["acceptance"]["passed"], 2)

    def test_an_original_run_with_no_checks_is_not_measured(self):
        config = dict(self.config, all="true")
        got = run_bench.score_rebuild(self.tree, self.rebuilt(oracle=True), config, "wordfreq")
        self.assertEqual(got["component"]["measured"], False)
        self.assertIn("reason", got["component"])

    def test_the_code_is_read_before_the_checks_run(self):
        with open(self.tree / "tests" / "test_counter.py", "a") as handle:
            handle.write("# leaked_name\n")
        command = ("python3 -m unittest discover -s tests && mkdir -p gen && "
                   "echo 'def leaked_name(): pass' > gen/out.py")
        config = dict(self.config, all=command)
        got = run_bench.score_rebuild(self.tree, self.rebuilt(), config, "wordfreq")
        gap = next(g for g in got["gaps"] if g["file"] == "tests/test_counter.py")
        self.assertNotIn("leaked_name", gap["missing_names"])
        self.assertIn("count_words", gap["missing_names"])

    def test_code_text_leaves_out_build_folders(self):
        for name in ("target/debug/x.rs", ".cpcache/y.clj", "wordfreq/__pycache__/z.py"):
            (self.tree / name).parent.mkdir(parents=True, exist_ok=True)
            (self.tree / name).write_text("def build_only(): pass\n")
        text = run_bench.code_text_of(self.tree, self.config)
        self.assertNotIn("build_only", text)
        self.assertIn("count_words", text)

    def test_a_symlinked_check_folder_is_replaced_and_not_followed(self):
        rebuilt = self.rebuilt(oracle=True)
        outside = self.work / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep\n")
        (rebuilt / "tests").symlink_to(outside)
        run_bench.install_checks(self.tree, rebuilt, self.config)
        self.assertTrue((outside / "keep.txt").exists())
        self.assertEqual(list(outside.iterdir()), [outside / "keep.txt"])
        self.assertFalse((rebuilt / "tests").is_symlink())
        self.assertTrue((rebuilt / "tests" / "test_counter.py").is_file())

    def test_a_symlinked_check_file_is_replaced_and_not_written_through(self):
        rebuilt = self.rebuilt(oracle=True)
        outside = self.work / "target.py"
        outside.write_text("untouched\n")
        (rebuilt / "tests").mkdir(exist_ok=True)
        (rebuilt / "tests" / "test_counter.py").symlink_to(outside)
        run_bench.install_checks(self.tree, rebuilt, self.config)
        self.assertEqual(outside.read_text(), "untouched\n")
        self.assertFalse((rebuilt / "tests" / "test_counter.py").is_symlink())

    def test_a_timeout_stops_the_children_and_keeps_the_partial_output(self):
        started = run_bench.time.time()
        done = run_bench.run_checks(self.work, "echo started; (sleep 20 &); sleep 20", timeout=1)
        self.assertLess(run_bench.time.time() - started, 10)
        self.assertFalse(done["ok"])
        self.assertIn("started", done["output"])
        self.assertIn("timeout", done["output"])

    @unittest.skipUnless(shutil.which("cargo"), "cargo is not installed")
    def test_parse_check_output_reads_the_real_output_of_cargo_test(self):
        copy = self.work / "todo-rust"
        shutil.copytree(run_bench.HERE / "fixtures" / "todo-rust", copy, ignore=shutil.ignore_patterns("target"))
        proc = subprocess.run(["cargo", "test"], cwd=copy, capture_output=True, text=True, timeout=900)
        found = run_bench.parse_check_output(proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(found["failed"], [])
        self.assertEqual(found["ran"], run_bench.unit_checks(copy, "todo-rust")["ran"])
        self.assertGreater(found["ran"], 0)


def scored_project(test):
    """The project of rebuild_project, with the spec and the acceptance file that the score tests use,
    committed on the change branch. Main stays checked out."""
    app = rebuild_project(test)
    run_bench.git(app, "checkout", "-q", "pdlc/CH-0001-x")
    (app / "tests" / "acceptance_IN-0001.py").write_text(ACCEPTANCE_FILE)
    (app / "pdlc" / "specs" / "jobs" / "JOB-top-option.md").write_text(SPEC_TEXT)
    cli_check = app / "tests" / "test_cli.py"
    cli_check.write_text(cli_check.read_text().replace("usage: wordfreq FILE", "usage: wordfreq [--top N] FILE"))
    run_bench.git(app, "add", "-A")
    run_bench.git(app, "commit", "-q", "-m", "Acceptance reviewed")
    run_bench.git(app, "checkout", "-q", "main")
    return app


def init_event(plugins):
    return {"t": 0.1, "e": {"type": "system", "subtype": "init", "plugins": plugins}}


class RebuildCommandTest(unittest.TestCase):
    branch = "pdlc/CH-0001-x"

    def setUp(self):
        self.app = scored_project(self)
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, True)
        self.tree = run_bench.export_tree(self.app, self.branch, self.work / "tree")
        self.seen = []

    def args(self, **more):
        values = dict(source=str(self.app), run=1, ref=self.branch, fixture="wordfreq", keep=[], label="rb",
                      out=str(self.work / "out"), budget=5.0, timeout=60, plugin=str(run_bench.DEFAULT_PLUGIN))
        values.update(more)
        return Namespace(**values)

    def oracle(self, dest):
        """A builder that writes the original code back."""
        self.seen.append(Path(dest))
        shutil.copytree(self.tree / "wordfreq", Path(dest) / "wordfreq", ignore=shutil.ignore_patterns("__pycache__"))
        return [], 1.5, ""

    def idle(self, dest):
        self.seen.append(Path(dest))
        return [], 0.5, ""

    def peeking(self, path):
        def builder(dest):
            self.oracle(dest)
            return [assistant(1.0, "m1", usage(), [("t1", "Read", {"file_path": path})])], 2.0, ""
        return builder

    def run_command(self, builder, **more):
        try:
            with contextlib.redirect_stdout(io.StringIO()) as printed:
                found = run_bench.command_rebuild(self.args(**more), builder=builder)
        finally:
            for folder in self.seen:
                self.addCleanup(shutil.rmtree, folder.parent, True)
        self.printed = printed.getvalue()
        return found

    def test_claude_command_leaves_out_the_plugin_when_there_is_none(self):
        self.assertNotIn("--plugin-dir", run_bench.claude_command("x", None))
        command = run_bench.claude_command("x", "/p")
        self.assertEqual(command[command.index("--plugin-dir") + 1], "/p")

    def test_loaded_plugins_reads_the_init_event(self):
        plugins = [{"name": "pdlc", "path": "/p", "source": "pdlc@inline"}]
        events = [{"t": 0, "e": {"type": "system", "subtype": "hook"}}, init_event(plugins), init_event([])]
        self.assertEqual(run_bench.loaded_plugins(events), plugins)
        self.assertEqual(run_bench.loaded_plugins([]), [])

    def test_peeked_finds_a_read_of_the_repository_and_a_command_on_a_bench_folder(self):
        forbidden = ["/tmp/pdlc-bench-src/app", str(run_bench.REPO), "pdlc-bench-"]
        events = [assistant(1, "m1", usage(), [("a", "Read", {"file_path": str(run_bench.FIXTURE / "wordfreq" / "cli.py")}),
                                              ("b", "Bash", {"command": "cat /tmp/pdlc-bench-x/app/wordfreq/cli.py"}),
                                              ("c", "Grep", {"pattern": "main", "path": "/tmp/pdlc-bench-src/app"}),
                                              ("d", "Read", {"file_path": "pdlc/specs/jobs/JOB-x.md"})])]
        found = run_bench.peeked(events, forbidden)
        self.assertEqual(len(found), 3)
        self.assertIn("cat /tmp/pdlc-bench-x/app/wordfreq/cli.py", found)
        self.assertEqual(run_bench.peeked(events[:0], forbidden), [])

    def test_peeked_ignores_a_call_in_its_own_folder(self):
        events = [assistant(1, "m1", usage(), [("a", "Read", {"file_path": "pdlc/specs/jobs/JOB-x.md"}),
                                              ("b", "Bash", {"command": "cd /tmp/pdlc-rebuild-q/app && ls"})])]
        self.assertEqual(run_bench.peeked(events, ["/tmp/pdlc-bench-src/app", str(run_bench.REPO), "pdlc-bench-"]), [])

    def test_verdict_holds_only_for_a_measured_pass_without_peeking(self):
        good = {"acceptance": {"measured": True, "total": 2, "passed": 2, "failed": [], "ok": True},
                "component": {"measured": True, "total": 3, "passed": 2, "failed": ["x"]},
                "probes": {"passed": 8, "total": 8, "failed": []}, "peeked": []}
        self.assertEqual(run_bench.rebuild_verdict(good), "holds")
        self.assertEqual(run_bench.rebuild_verdict({**good, "peeked": ["cat x"]}), "invalid")
        self.assertEqual(run_bench.rebuild_verdict({**good, "acceptance": {"measured": False}}), "broken")
        self.assertEqual(run_bench.rebuild_verdict({**good, "acceptance": {"measured": True, "total": 0, "passed": 0, "failed": []}}), "broken")
        self.assertEqual(run_bench.rebuild_verdict({**good, "acceptance": {"measured": True, "total": 2, "passed": 1, "failed": ["a"]}}), "broken")
        self.assertEqual(run_bench.rebuild_verdict({**good, "probes": {"passed": 7, "total": 8, "failed": ["p"]}}), "broken")

    def test_verdict_is_invalid_when_the_original_checks_did_not_pass(self):
        base = {"probes": {"passed": 8, "total": 8, "failed": []}, "peeked": []}
        bad = {"measured": False, "reason": "the original checks did not pass"}
        passed = {"measured": True, "total": 2, "passed": 2, "failed": []}
        self.assertEqual(run_bench.rebuild_verdict({**base, "acceptance": bad, "component": passed}), "invalid")
        self.assertEqual(run_bench.rebuild_verdict({**base, "acceptance": passed, "component": bad}), "invalid")

    def test_verdict_is_not_holds_when_the_acceptance_command_failed_with_no_failing_check(self):
        result = {"acceptance": {"measured": True, "total": 2, "passed": 2, "failed": [], "ok": False},
                  "component": {"measured": True, "total": 3, "passed": 3, "failed": []},
                  "probes": {"passed": 8, "total": 8, "failed": []}, "peeked": []}
        self.assertEqual(run_bench.rebuild_verdict(result), "broken")

    def test_peeked_finds_a_forbidden_path_in_the_output_of_a_tool(self):
        forbidden = ["/tmp/pdlc-bench-src/app"]
        text = {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "a", "content": "OLDPWD=/tmp/pdlc-bench-src/app\n"},
            {"type": "tool_result", "tool_use_id": "b", "content": [{"type": "text", "text": "in /tmp/pdlc-bench-src/app/x"}]},
            {"type": "tool_result", "tool_use_id": "c", "content": "fine"}]}}
        self.assertEqual(len(run_bench.peeked([{"t": 1, "e": text}], forbidden)), 2)

    def test_the_session_of_the_builder_starts_in_its_own_folder(self):
        env = run_bench.session_env("/tmp/pdlc-rebuild-q/app")
        self.assertEqual((env["PWD"], env["OLDPWD"]), ("/tmp/pdlc-rebuild-q/app",) * 2)
        fake = self.work / "bin"
        fake.mkdir()
        (fake / "claude").write_text("#!/bin/sh\necho \"{\\\"type\\\": \\\"system\\\", \\\"pwd\\\": \\\"$PWD $OLDPWD\\\"}\"\n")
        (fake / "claude").chmod(0o755)
        folder = self.work / "cwd"
        folder.mkdir()
        old = os.environ["PATH"]
        os.environ["PATH"] = "%s:%s" % (fake, old)
        try:
            events, _, _ = run_bench.run_claude("x", folder, None, self.work / "log", env=run_bench.session_env(folder))
            plain, _, _ = run_bench.run_claude("x", folder, None, self.work / "log")
        finally:
            os.environ["PATH"] = old
        self.assertEqual(events[0]["e"]["pwd"], "%s %s" % (folder, folder))
        self.assertNotEqual(plain[0]["e"]["pwd"], "%s %s" % (folder, folder))

    def test_the_original_tree_is_not_beside_the_app_while_the_builder_runs(self):
        seen = {}

        def builder(dest):
            seen["beside"] = (Path(dest).parent / "original").exists()
            return self.oracle(dest)
        found = self.run_command(builder)
        self.assertFalse(seen["beside"])
        self.assertEqual(found["verdict"], "holds")

    def test_kept_extra_lists_only_a_file_that_the_copy_has(self):
        found = self.run_command(self.oracle, keep=["Cargo.toml", "nothing.txt"])
        self.assertEqual(found["kept_extra"], ["Cargo.toml"])

    def test_the_report_says_what_the_peek_check_cannot_see(self):
        self.run_command(self.oracle)
        report = (Path(self.args().out) / "rb" / "rebuild.md").read_text()
        self.assertIn("Peek check: tool inputs and outputs only. A relative path, a glob or a command "
                      "substitution can get past it.", report)

    def test_the_original_tree_is_gone_when_the_command_returns(self):
        self.run_command(self.oracle)
        self.assertTrue(self.seen[0].parent.is_dir())
        self.assertFalse((self.seen[0].parent / "original").exists())

    def test_the_original_tree_is_gone_when_scoring_fails(self):
        real = run_bench.score_rebuild

        def boom(*a, **k):
            raise ValueError("boom")
        run_bench.score_rebuild = boom
        try:
            with self.assertRaises(ValueError):
                self.run_command(self.oracle)
        finally:
            run_bench.score_rebuild = real
        self.assertFalse((self.seen[0].parent / "original").exists())

    def test_a_branch_that_moves_during_the_build_does_not_change_what_is_scored(self):
        def builder(dest):
            events = self.oracle(dest)
            run_bench.git(self.app, "branch", "-f", self.branch, "main")  # main has no acceptance file
            return events
        found = self.run_command(builder)
        self.assertEqual(found["verdict"], "holds")
        self.assertEqual(found["acceptance"]["total"], 2)
        self.assertNotEqual(found["source"]["commit"], run_bench.git(self.app, "rev-parse", self.branch).stdout.strip())

    def test_a_builder_that_writes_the_original_code_holds(self):
        found = self.run_command(self.oracle)
        self.assertEqual(found["verdict"], "holds")
        self.assertEqual(found["acceptance"]["passed"], 2)
        self.assertEqual(found["acceptance"]["total"], 2)
        self.assertEqual(found["probes"]["passed"], found["probes"]["total"])
        self.assertEqual(found["peeked"], [])
        out = Path(self.args().out) / "rb"
        saved = json.loads((out / "rebuild.json").read_text())
        self.assertEqual(saved["verdict"], "holds")
        self.assertTrue((out / "rebuild.md").read_text().startswith("#"))
        self.assertIn("holds", (out / "rebuild.md").read_text())
        self.assertIn("acceptance 2/2", self.printed)
        self.assertIn("probes 8/8", self.printed)

    def test_the_result_names_the_source_the_cost_and_the_builder_files(self):
        events = [{"t": 3.0, "e": {"type": "result", "total_cost_usd": 1.25, "duration_ms": 3000}}]
        found = self.run_command(lambda dest: (self.oracle(dest)[0] + events, 3.0, ""))
        self.assertEqual(found["cost_usd"], 1.25)
        self.assertEqual(found["wall_s"], 3.0)
        self.assertEqual(found["source"]["ref"], self.branch)
        self.assertEqual(found["source"]["project"], str(self.app))
        self.assertEqual(found["source"]["fixture"], "wordfreq")
        self.assertEqual(found["source"]["commit"], run_bench.git(self.app, "rev-parse", self.branch).stdout.strip())
        self.assertIn("plugin_commit", found["source"])
        self.assertIn("plugin_status", found["source"])
        self.assertIn("wordfreq/cli.py", found["builder_files"])
        self.assertTrue(all("__pycache__" not in name for name in found["builder_files"]))
        self.assertIn("pdlc/specs/jobs/JOB-branch-only.md", found["kept"])
        self.assertEqual(found["kept_extra"], [])

    def test_keep_adds_a_file_and_the_result_records_it(self):
        found = self.run_command(self.oracle, keep=["Cargo.toml"])
        self.assertEqual(found["kept_extra"], ["Cargo.toml"])
        self.assertTrue((self.seen[0] / "Cargo.toml").exists())

    def test_the_builder_folder_is_a_clean_copy_without_the_name_of_a_bench_folder(self):
        looked = {}

        def builder(dest):
            looked.update(name=str(dest), tests=(Path(dest) / "tests").exists(),
                          changes=(Path(dest) / "pdlc" / "changes").exists(),
                          commits=run_bench.git(dest, "rev-list", "--count", "HEAD").stdout.strip())
            return self.idle(dest)
        self.run_command(builder)
        self.assertNotIn("pdlc-bench-", looked["name"])
        self.assertEqual((looked["tests"], looked["changes"], looked["commits"]), (False, False, "1"))

    def test_a_builder_that_does_nothing_is_broken_and_the_report_names_each_acceptance_check(self):
        found = self.run_command(self.idle)
        self.assertEqual(found["verdict"], "broken")
        self.assertEqual(found["acceptance"]["passed"], 0)
        report = (Path(self.args().out) / "rb" / "rebuild.md").read_text()
        self.assertIn("broken", report)
        for name in RebuildScoreTest.acceptance_names:
            self.assertIn(name, report)
        self.assertIn("JOB-top-option", report)

    def test_a_builder_that_reads_the_source_project_is_invalid(self):
        found = self.run_command(self.peeking(str(self.app / "wordfreq" / "cli.py")))
        self.assertEqual(found["verdict"], "invalid")
        self.assertEqual(len(found["peeked"]), 1)
        self.assertEqual(found["acceptance"]["passed"], 2)
        report = (Path(self.args().out) / "rb" / "rebuild.md").read_text()
        self.assertIn("invalid", report)
        self.assertIn(str(self.app / "wordfreq" / "cli.py"), report)

    def test_a_builder_that_reads_the_repository_is_invalid(self):
        found = self.run_command(self.peeking(str(run_bench.FIXTURE / "wordfreq" / "cli.py")))
        self.assertEqual(found["verdict"], "invalid")

    def test_the_verdict_is_invalid_when_the_original_acceptance_checks_fail(self):
        def breaker(dest):
            return self.oracle(dest)
        run_bench.git(self.app, "checkout", "-q", self.branch)
        (self.app / "wordfreq" / "cli.py").write_text("import sys\n\ndef main(argv=None, stdout=None, stderr=None):\n    return 1\n")
        run_bench.git(self.app, "commit", "-qam", "Break the original")
        run_bench.git(self.app, "checkout", "-q", "main")
        found = self.run_command(breaker)
        self.assertEqual(found["verdict"], "invalid")
        self.assertFalse(found["acceptance"]["measured"])

    def test_the_stream_of_the_e2e_run_gives_the_loaded_plugins_and_a_warning(self):
        results = self.work / "results"
        results.mkdir()
        (results / "run1.json").write_text(json.dumps({"project": str(self.app), "outcome": {"tip": self.branch}}))
        other = [{"name": "pdlc", "path": "/elsewhere/pdlc", "source": "pdlc@pskills"}]
        (results / "run1.stream.jsonl").write_text(json.dumps(init_event(other)) + "\n")
        found = self.run_command(self.oracle, source=str(results), ref=None, fixture=None)
        self.assertEqual(found["source"]["plugins"], other)
        self.assertIn("plugin_warning", found)
        self.assertEqual(found["source"]["fixture"], "wordfreq")
        self.assertEqual(found["source"]["ref"], self.branch)

    def test_no_warning_when_the_plugin_path_matches(self):
        results = self.work / "results"
        results.mkdir()
        (results / "run1.json").write_text(json.dumps({"project": str(self.app), "outcome": {"tip": self.branch}}))
        mine = [{"name": "pdlc", "path": str(run_bench.DEFAULT_PLUGIN.resolve()), "source": "pdlc@inline"}]
        (results / "run1.stream.jsonl").write_text(json.dumps(init_event(mine)) + "\n")
        found = self.run_command(self.oracle, source=str(results), ref=None)
        self.assertNotIn("plugin_warning", found)

    def test_a_missing_project_stops_with_a_clear_error(self):
        results = self.work / "results"
        results.mkdir()
        (results / "run1.json").write_text(json.dumps({"project": "/nonexistent/app", "outcome": {"tip": "x"}}))
        with self.assertRaises(RuntimeError):
            self.run_command(self.oracle, source=str(results))

    def test_the_command_takes_the_options(self):
        with contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(SystemExit):
            run_bench.main(["rebuild", "--help"])
        for option in ("--run", "--ref", "--fixture", "--keep", "--label", "--out", "--budget", "--timeout", "--plugin"):
            self.assertIn(option, printed.getvalue())


if __name__ == "__main__":
    unittest.main()
