# Harness tasks for round 3

Three small changes to `bench/run_bench.py`, each with tests in `bench/test_bench.py`. H1
(waiting target) gives experiment 1 its verdict. H2 (wider `is_waiting`) makes the baseline
honest. H3 (permutation test in agent target mode) gives experiment 2 its verdict. Do them
in this order. After each task, run `python3 bench/test_bench.py` and the other repository
tests from `AGENTS.md`. Do not change `bench/run_experiment.py`.

## H1: a `waiting` target for the gate

Behaviour: `gate(baseline, candidate, target="waiting")` judges the cost of the waiting
turns a run, with the same permutation test as the whole-run mode. Effectiveness checks
stay as they are.

1. In `summarise(result)`, add two keys:
   - `"waiting": [r.get("waiting", {}).get("cost_usd", 0.0) for r in runs]`
   - `"waiting_turns": [r.get("waiting", {}).get("messages", 0) for r in runs]`
   A run with no `waiting` key counts as zero.
2. In `gate(...)`, before `if target:`, add a branch `if target == "waiting":` with these
   steps. Use `statistics.mean` (`import statistics` is already there).
   - `before, after = base["waiting"], cand["waiting"]`.
   - `chance = permutation_p(before, after)`; `p_value = chance`.
   - `saved = mean(before) - mean(after)`; `share = saved / base["cost_usd"]` (0 if the
     base cost is 0).
   - `few = min(len(before), len(after)) < min_runs`.
   - `detail = {"target": "waiting", "per_run_before": mean(before), "per_run_after":
     mean(after), "turns_before": mean(base["waiting_turns"]), "turns_after":
     mean(cand["waiting_turns"]), "expected_run_saving": saved,
     "expected_run_saving_share": share}`.
   - Guard against a dearer run: if `run_change > 0` and either
     `run_change > max(base["noise"], 0.25)` or
     `permutation_p(cand["costs"], base["costs"]) <= alpha`, append
     `"a whole run costs %.0f%% more, and that is not luck"` to `worse`. The range rule
     alone is not enough: the baseline noise is 60%, so a run 40% dearer would pass it.
   - `change = -share`; `needed = min_gain`; if `chance > alpha`, set `change = 0.0`.
   - `gain_text = "waiting turns cost $%.2f -> $%.2f a run (%.1f -> %.1f turns), %.0f%% of
     a run less, and the chance that this is luck is %.0f%%"`.
   - `none_text = "waiting turns cost $%.2f -> $%.2f a run, %.0f%% of a run less, and the
     chance that this is luck is %.0f%% (it must be %.0f%% or less)"`.
   - The verdict rules are those of the whole-run mode. REGRESSION if `worse`. NEED MORE
     RUNS if `few` and `change <= -needed`. SAME OR BETTER if `change <= -needed`. NO GAIN
     otherwise. Make the `few` variable exist in this branch too.
3. In `command_gate`, when `detail["target"] == "waiting"`, print one line:
   `"waiting    $%.2f -> $%.2f a run, %.1f -> %.1f turns, so about $%.2f (%.0f%%) less in a
   run"`. Keep the existing agent line for other targets.

Tests to add to `bench/test_bench.py`. Write a helper `waiting_result(waits, totals)` that
returns a result like `result(...)` whose run `i` has `"waiting": {"messages": 10 if
waits[i] else 0, "cost_usd": waits[i]}`.

- `test_no_waiting_against_a_waiting_baseline_is_kept`: baseline waits
  `[0.08, 0.03, 0.21, 0.19, 0.75, 0.02]`, totals `[1.78, 1.87, 2.49, 1.78, 1.99, 1.36]`;
  candidate waits all `0.0`, totals `[1.7, 1.8, 2.3, 1.6, 1.3, 1.3]`. Verdict starts with
  `SAME OR BETTER`; `verdict["p"] < 0.01`; `verdict["target"]["expected_run_saving"]`
  is about `0.213` (3 places).
- `test_the_same_waiting_is_no_gain`: the same waits on both sides. Verdict `NO GAIN`.
- `test_no_waiting_but_a_much_dearer_run_is_a_regression`: the same baseline as the first
  test; candidate waits `0.0`, totals each 1.4 times the baseline total. Verdict
  `REGRESSION`, and the reason says "not luck".
- `test_no_waiting_and_a_slightly_dearer_run_is_kept`: the same baseline; candidate waits
  `0.0`, totals each 1.1 times the baseline total. Verdict `SAME OR BETTER`.
- `test_no_waiting_in_three_runs_needs_more_runs`: three runs a side, candidate waits
  `0.0`. Verdict `NEED MORE RUNS`.
- `test_a_result_without_waiting_counts_as_zero`: `summarise(result([2.0]))["waiting"]`
  is `[0.0]`.
- `test_a_run_that_did_not_finish_beats_no_waiting`: reuse the `finished` helper style of
  `test_a_run_that_did_not_finish_is_a_regression_even_when_cheaper`, with
  `target="waiting"`. Verdict `REGRESSION`.

## H2: count bash wait loops as waiting

Behaviour: `is_waiting(blocks)` treats a Bash command as a wait when it sleeps and does no
work. Today it only catches a command that starts with `sleep`, `until`, or `while`.

1. Add `WORK_WORDS = ("git commit", "git add", "unittest", "pytest", "npm ", "node ",
   "record_gif", "make_packets", "check_merge", "record_merges", "sed -i", "<<",
   "python3 -")` next to `WAITING_TOOLS`.
2. Add a function:

   ```python
   def waiting_command(command):
       """A Bash command that only waits: it sleeps, or loops, and does no work."""
       waits = re.match(r"\s*(sleep\b|until\b|while\b)", command) or re.search(r"\bsleep\s+\d", command)
       return bool(waits) and not any(word in command for word in WORK_WORDS)
   ```

3. In `is_waiting`, replace the `re.match(...)` test on Bash commands with
   `waiting_command(command)`.
4. Read the six baseline runs again, then freeze the baseline again:

   ```
   for n in 1 2 3 4 5 6; do python3 bench/run_bench.py reanalyse bench/results/baseline-$n; done
   python3 bench/run_bench.py freeze bench/results/baseline-{1,2,3,4,5,6}/e2e.json --out bench/baseline.json --seeds bench/results/baseline-seeds/seeds.json --label baseline
   ```

   Check that the six whole-run costs in `bench/baseline.json` did not change. Check that
   `waiting.messages` of baseline-6 rose from 1 to about 6.

Tests to add, in a class `WaitingTest`. Each builds one block
`{"type": "tool_use", "name": "Bash", "input": {"command": c}}` and calls
`run_bench.is_waiting([block])`.

- `f=/x/out; for i in $(seq 1 90); do grep -q done $f && break; sleep 3; done` is waiting.
- `cd /app; for i in $(seq 1 90); do git diff --quiet -- a.py || break; sleep 3; done;
  sleep 40; git status --short` is waiting.
- `until [ -f x ]; do sleep 3; done; echo result` is waiting.
- `sleep 2; git add -A && git commit -qm x` is not waiting.
- `python3 -m unittest discover -s tests; sleep 1` is not waiting.
- `git status --short` is not waiting.
- A `ReadNotifications` block is still waiting; a `Read` block is not.

## H3: a permutation test in agent target mode

Behaviour: with `target="pdlc:reviewer"` (or any agent), the gate judges the per-run cost
of one call of that agent. It uses the permutation test and `min_gain`, not the range of
the per-run values. Today the range rule needs a 42% fall on the baseline, so no edit
under 42% can pass.

1. In the `if target:` branch of `gate(...)`:
   - Replace `needed = max(min_gain, noise(before["per_run"]), noise(after["per_run"]))`
     with `needed = min_gain`.
   - Use the same guard against a dearer run as H1, in place of the range rule alone.
   - Add `chance = permutation_p(before["per_run"], after["per_run"])` and
     `p_value = chance`. If `chance > alpha`, set `change = 0.0` after `change` is computed.
   - Add `few = min(len(before["per_run"]), len(after["per_run"])) < min_runs`.
   - Put the chance in both texts: `gain_text = "each %s call costs %.0f%% less, and the
     chance that this is luck is %.0f%%"`; `none_text = "each %s call changed %+.0f%%, and
     the chance that this is luck is %.0f%% (it must be %.0f%% or less)"`.
   - Let the NEED MORE RUNS rule apply to this mode too: remove `not target and` from the
     `elif` that returns NEED MORE RUNS.
2. In `command_gate`, keep the agent line as it is.

Tests to change and add in `TargetGateTest`:

- Change `test_a_cheaper_agent_is_kept_even_when_whole_runs_vary_a_lot` to five runs a
  side: baseline `agent_result(0.06, 7, [1.8, 2.5, 1.9, 2.0, 2.1])`, candidate
  `agent_result(0.005, 7, [1.6, 2.2, 1.7, 1.9, 2.0])`. The assertions stay, and
  `aimed["p"] < 0.01`.
- Change `test_a_whole_run_that_costs_much_more_is_a_regression` and
  `test_a_missed_defect_beats_a_cheaper_agent` to five runs a side in the same way. Their
  verdicts stay `REGRESSION`.
- Add `test_a_modest_fall_in_each_call_is_kept_when_runs_agree`. Give `agent_result` an
  optional `per_calls` list that sets the per-call cost of run `i`. The baseline has
  per-call costs `[0.0595, 0.062, 0.0657, 0.0617, 0.0414, 0.0529]`, 7 calls a run, and
  totals of 1.8. The candidate has each value times 0.8. Verdict `SAME OR BETTER`, and
  `aimed["p"]` is about `0.016`.
- Add `test_a_cheaper_call_in_a_much_dearer_run_is_a_regression`: the same baseline with
  totals `[1.78, 1.87, 2.49, 1.78, 1.99, 1.36]`; the candidate has per-call costs times
  0.8 and totals times 1.4. Verdict `REGRESSION`.
- Add `test_the_same_cost_a_call_is_no_gain`: the same per-call list on both sides.
  Verdict `NO GAIN`.
- Add `test_a_cheaper_agent_in_three_runs_needs_more_runs`: `agent_result(0.06, 7,
  [1.8, 2.5, 1.9])` against `agent_result(0.04, 7, [1.6, 2.2, 1.7])`. Verdict
  `NEED MORE RUNS`.

Rule for the gate in agent target mode. A candidate is kept when all of these are true:

- Every effectiveness check passes.
- The whole run is not clearly dearer (the guard above).
- Each call costs at least `min_gain` less.
- The chance of luck is at most `alpha`.
- Both sides have at least `min_runs` runs.
