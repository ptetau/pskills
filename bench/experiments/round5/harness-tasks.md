# Harness tasks for round 5

Two small changes to `bench/run_bench.py`, each with tests in `bench/test_bench.py`. H4
(reviewer calls split by remit) lets the gate aim at one remit. H5 (a gate mode that
counts calls) gives experiment 2 its verdict. Experiment 1 needs neither; do them while
experiment 1 runs. Do H4 first. After each task, run `python3 bench/test_bench.py` and the
other repository tests from `AGENTS.md`. Do not change `bench/run_experiment.py`. Name the
functions, not line numbers: the code may have moved since this was written.

## H4: reviewer calls split by remit

Behaviour: `analyse(items)` counts each `pdlc:reviewer` call twice in the `agents` of its
stage: once under `pdlc:reviewer`, as today, and once under `pdlc:reviewer/<remit>`. The
remit comes from the path in the prompt of the Agent call (`/review/<remit>/`). A reviewer
call whose prompt names no remit gets only the aggregate entry. Nothing else changes: the
stage costs, the totals, and `agent_stats(result, "pdlc:reviewer")` stay as they are.

1. In `analyse(...)`, next to `agent_of = {}`, add `agent_remit = {}`.
2. In the block that handles `name in ("Agent", "Task")`, after the line
   `agent_of[block["id"]] = (owner or stage, label)`, add:

   ```python
                    remit = re.search(r"/review/([a-z]+)/", args.get("prompt") or "")
                    if label == "pdlc:reviewer" and remit:
                        agent_remit[block["id"]] = label + "/" + remit.group(1)
   ```

3. In the loop over `order` that shares the cost, inside `if label != "session":`, after
   the three lines that update `agent` (tokens, cost, messages), add:

   ```python
            sub = agent_remit.get(entry["parent"])
            if sub:
                part = data["agents"].setdefault(sub, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
                add_tokens(part["tokens"], tokens_of(entry["usage"]))
                part["cost_usd"] += share
                part["messages"] += 1
   ```

4. In the loop `for tool_id, (owner, label) in agent_of.items():`, after the line that
   sets `agent["wall_s"]`, add:

   ```python
        sub = agent_remit.get(tool_id)
        if sub:
            part = data["agents"].setdefault(sub, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
            part["calls"] += 1
            part["wall_s"] = round(part.get("wall_s", 0) + (end - start), 1)
   ```

   The rounding loop that follows (`for data in stages.values(): ... agent["cost_usd"] =
   round(...)`) already covers the new entries, because they are in the same dict.
5. Read the six runs behind `bench/reference.json` again, then freeze the reference again.
   Today these are `r3-lean-packets-1` to `-6` (label `r4`). After a kept experiment 1 they
   are `r5-terminal-transcript-1` to `-6` (label `r5`); use the matching seeds file.

   ```
   for n in 1 2 3 4 5 6; do python3 bench/run_bench.py reanalyse bench/results/r3-lean-packets-$n; done
   python3 bench/run_bench.py freeze bench/results/r3-lean-packets-{1,2,3,4,5,6}/e2e.json --out bench/reference.json --seeds bench/results/r3-lean-packets-seeds/seeds.json --label r4
   ```

   Check that the six whole-run costs in `bench/reference.json` did not change. For the
   `r3-lean-packets` runs they are 1.2608, 1.4138, 1.4024, 1.6238, 1.4632, 1.6802. Check that
   `python3 bench/run_bench.py gate bench/reference.json bench/reference.json --target pdlc:reviewer`
   prints the same calls a run as before the change (7.5 for the `r3-lean-packets` runs).
   Check that the same command with `--target pdlc:reviewer/compliance` prints between 1.0
   and 1.4 calls a run (1.2 for the `r3-lean-packets` runs).

Tests to add to `bench/test_bench.py`, in a new class `RemitSplitTest`. Write a helper
`reviewer_events()` next to the class, with the `usage`, `assistant` and `tool_result`
helpers that the file already has:

```python
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
```

The weights are 35, 45, 225 and 125 (total 430), so the security call gets 225/430 of the
dollar and the privacy call 125/430.

- `test_a_reviewer_call_is_counted_under_its_remit_too`: `agents =
  run_bench.analyse(reviewer_events())["stages"]["verify"]["agents"]`. Then
  `agents["pdlc:reviewer/security"]["calls"]` is 1 and its `cost_usd` is about 0.5233
  (4 places); `agents["pdlc:reviewer/privacy"]["calls"]` is 1 and its `cost_usd` is about
  0.2907 (4 places).
- `test_the_aggregate_reviewer_entry_does_not_change`: on the same `agents`,
  `agents["pdlc:reviewer"]["calls"]` is 2, its `messages` is 2, and its `cost_usd` is
  about 0.8140 (3 places).
- `test_agent_stats_reads_one_remit`: `run_bench.agent_stats(run_bench.analyse(reviewer_events())
  and {"runs": [...]}, ...)`: build `result = {"runs": [run_bench.analyse(reviewer_events())]}`
  and check that `run_bench.agent_stats(result, "pdlc:reviewer/privacy")["per_call"]` is
  about 0.2907 (4 places) and `["calls"]` is 1.
- `test_a_reviewer_without_a_remit_in_its_prompt_gets_only_the_aggregate`: change the
  prompt of `a1` to `"Review the packet"` (no path). Then `"pdlc:reviewer/security"` is not
  in `agents`, and `agents["pdlc:reviewer"]["calls"]` is still 2.

## H5: a gate mode that counts the calls of an agent

Behaviour: `gate(baseline, candidate, target="calls:<agent>")` judges the number of calls
of `<agent>` a run, with the permutation test. It is for an edit that removes calls, for
example a remit that no longer needs a reviewer. The saving is the mean cost of one call
in the baseline times the calls removed. Effectiveness checks stay as they are.

1. In `agent_stats(result, label)`, add a list `counts` next to `per_run`. In the loop over
   the runs, after the per-run sums, add `counts.append(run_calls)` (also when `run_calls`
   is 0). Return it as `"counts": counts`.
2. In `gate(...)`, add a branch **before** `elif target:`, with these steps. Use
   `statistics.mean`.
   - `elif target and target.startswith("calls:"):`
   - `name = target[len("calls:"):]`; `before, after = agent_stats(baseline, name),
     agent_stats(candidate, name)`.
   - `counts_before, counts_after = before["counts"], after["counts"]`;
     `mean_before, mean_after = statistics.mean(counts_before), statistics.mean(counts_after)`.
   - `change = (mean_after - mean_before) / mean_before if mean_before else 0.0`.
   - `chance = permutation_p(counts_before, counts_after)`; `p_value = chance`.
   - `needed = min_gain`; `few = min(len(counts_before), len(counts_after)) < min_runs`.
   - `saved = before["per_call"] * (mean_before - mean_after)`.
   - `detail = {"target": target, "calls_before": mean_before, "calls_after": mean_after,
     "per_call_before": before["per_call"], "expected_run_saving": saved,
     "expected_run_saving_share": saved / base["cost_usd"] if base["cost_usd"] else 0.0}`.
   - The same guard against a dearer run as the other target modes: if `run_change > 0`
     and either `run_change > max(base["noise"], 0.25)` or
     `permutation_p(cand["costs"], base["costs"]) <= alpha`, append
     `"a whole run costs %.0f%% more, and that is not luck"` to `worse`.
   - `gain_text = "%s calls fell from %.2f to %.2f a run (%.0f%% fewer), and the chance that
     this is luck is %.0f%%" % (name, mean_before, mean_after, -change * 100, chance * 100)`.
   - `none_text = "%s calls changed from %.2f to %.2f a run (%+.0f%%), and the chance that
     this is luck is %.0f%% (it must be %.0f%% or less)" % (name, mean_before, mean_after,
     change * 100, chance * 100, alpha * 100)`.
   - `if chance > alpha: change = 0.0`.
   - The verdict rules at the end of `gate` then apply as they are. REGRESSION if `worse`.
     NEED MORE RUNS if `few` and `change <= -needed`. SAME OR BETTER if
     `change <= -needed`. NO GAIN otherwise.
3. In `command_gate`, add a branch **before** the generic `elif detail:` branch:
   `elif detail and detail["target"].startswith("calls:"):` prints one line:
   `"%s  %.2f -> %.2f calls a run at $%.3f each, so about $%.2f (%.0f%%) less in a run" %
   (detail["target"], detail["calls_before"], detail["calls_after"],
   detail["per_call_before"], detail["expected_run_saving"],
   detail["expected_run_saving_share"] * 100)`.

Tests to add to `bench/test_bench.py`, in a new class `CallsGateTest`. Write a helper:

```python
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
```

- `test_agent_stats_counts_the_calls_of_each_run`:
  `run_bench.agent_stats(calls_result([1, 0, 2], 0.025, [1.0, 1.0, 1.0]), "pdlc:reviewer/compliance")["counts"]`
  is `[1, 0, 2]`, and `["per_run"]` has 2 entries.
- `test_removing_every_call_is_kept`: baseline `calls_result(REF_COUNTS, 0.025,
  REF_TOTALS)`; candidate `calls_result([0] * 6, 0.025, [1.23, 1.38, 1.37, 1.57, 1.43, 1.65])`;
  `gate(..., target=TARGET)`. Verdict starts with `SAME OR BETTER`. `verdict["p"]` is
  about 0.00108 (5 places; it is 1/924). `verdict["target"]["expected_run_saving"]` is
  about 0.0292 (4 places; it is 0.025 times 7/6). `verdict["target"]["calls_after"]` is 0.
- `test_one_run_that_still_calls_is_kept`: the same baseline; candidate counts
  `[0, 0, 0, 0, 0, 1]`, totals as above. Verdict `SAME OR BETTER`; `verdict["p"]` is about
  0.00649 (5 places; it is 6/924).
- `test_two_runs_that_still_call_are_kept`: candidate counts `[0, 0, 0, 0, 1, 1]`. Verdict
  `SAME OR BETTER`; `verdict["p"]` is about 0.02273 (5 places; it is 21/924).
- `test_the_same_calls_is_no_gain`: the same `calls_result(REF_COUNTS, 0.025, REF_TOTALS)`
  on both sides. Verdict `NO GAIN`, and the reason contains "changed from 1.17 to 1.17".
- `test_fewer_calls_in_a_much_dearer_run_is_a_regression`: candidate counts all 0, totals
  each 1.4 times `REF_TOTALS`. Verdict `REGRESSION`, and the reason says "not luck".
- `test_fewer_calls_in_three_runs_needs_more_runs`: baseline `calls_result([1, 1, 1],
  0.025, [1.3, 1.4, 1.5])`, candidate `calls_result([0, 0, 0], 0.025, [1.2, 1.3, 1.4])`.
  Verdict `NEED MORE RUNS` (the chance of luck is exactly 0.05, which passes the 10%
  limit, but three runs are too few).
- `test_a_baseline_without_the_calls_is_no_gain`: both sides counts all 0. Verdict
  `NO GAIN`, and no exception (the mean before is 0).
- `test_the_gate_prints_the_calls_line`: write the baseline and candidate of
  `test_removing_every_call_is_kept` to two JSON files in a temporary folder (use
  `run_bench.json.dumps`). Call `run_bench.command_gate(Namespace(baseline=...,
  candidate=..., min_gain=0.05, speed_limit=1.5, target=TARGET, min_runs=5))` inside
  `contextlib.redirect_stdout(io.StringIO())`. Check that the output contains
  `1.17 -> 0.00 calls a run at $0.025 each`. Add `import contextlib` and `import io` at
  the top of `bench/test_bench.py`.

Rule for the gate in calls mode. A candidate is kept when all of these are true:

- Every effectiveness check passes.
- The whole run is not clearly dearer (the guard above).
- The calls a run fell by at least `min_gain` (5%).
- The chance of luck is at most `alpha` (10%).
- Both sides have at least `min_runs` (5) runs.
