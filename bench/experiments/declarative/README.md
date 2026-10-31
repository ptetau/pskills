# Declarative skills: pdlc 0.3.0 against 0.4.0

In pdlc 0.4.0, each skill states only its goal, constraints, inputs and outputs. This folder holds
6 full runs of `/pdlc:ship` for each version, on the same fixture app and the same intent.

- `v030.json`: pdlc 0.3.0, commit da9f30c, the skills with numbered steps.
- `v040.json`: pdlc 0.4.0, commit 79fd355, the declarative skills with the fixes from `/vet`.

## Result

| Measure | 0.3.0 | 0.4.0 |
|---|---|---|
| Runs that proposed the merge, with a passing merge check | 5 of 6 | 6 of 6 |
| Acceptance probes that pass | 8 of 8 in each run | 8 of 8 in each run |
| Cost of a run (mean) | $1.75 | $1.96 (+12%) |
| Time of a run (mean) | 494 s | 628 s (+27%) |
| `verify` rounds | 1, 2, 1, 2, 1, 2 | 1, 2, 1, 1, 1, 1 |
| Writing findings that a run leaves (mean) | 0.2 | 0.2 |

Run 2 of 0.3.0 stopped with the line "Stop CH-0001: third failed verify round, wording fixed". Each
run of 0.4.0 reached the merge proposal.

The cost rise is probably real. The one-sided test that 0.4.0 costs more gives a chance of 6% that
the rise is luck. Most of the rise is in the main session, not in the agents:

| Stage | 0.3.0 | 0.4.0 | Change |
|---|---|---|---|
| acceptance | $0.278 | $0.404 | +$0.126 |
| intake | $0.168 | $0.253 | +$0.085 |
| tests | $0.211 | $0.271 | +$0.060 |
| verify | $0.541 | $0.574 | +$0.032 |
| build | $0.179 | $0.143 | -$0.036 |
| ready | $0.061 | $0.039 | -$0.023 |

- The main session of acceptance costs about $0.10 more a run.
- Intake also starts the recon agent more often: 12 times in 6 runs, against 5 times.
- The `verify` stage has fewer reviewer calls, because it has fewer `verify` rounds.

A first version of this note gave about $0.11 more for the tests stage. That number came from a
fault in the bench. It counted the test writer and the reviewer of the acceptance stage under the
tests stage. The bench now counts each agent call under the stage that made it, and the result
files hold the corrected split.

Run 6 of 0.4.0 lost about 430 s to one command. The command `cat > $TMPDIR/ed.sh` waited for
input. The Bash tool moved it to the background after 120 s, and the session then waited for it
after its work was done. Without this loss, a run of 0.4.0 takes about 556 s on average.

The plain gate gives "NO GAIN", because the edit does not aim at cost. The gate with
`--target writing` gives "REGRESSION", because a run costs 12% more.

## Commands

```
python3 bench/run_bench.py e2e --plugin <checkout at da9f30c>/plugins/pdlc --label v030-N --runs 1 --out <results>
python3 bench/run_bench.py e2e --plugin <checkout at 79fd355>/plugins/pdlc --label v040-N --runs 1 --out <results>
python3 bench/run_bench.py freeze <results>/v030-{1..6}/e2e.json --label v030 --out v030.json
python3 bench/run_bench.py freeze <results>/v040-{1..6}/e2e.json --label v040 --out v040.json
python3 bench/run_bench.py gate v030.json v040.json
python3 bench/run_bench.py gate v030.json v040.json --target writing
```

Each run used its own checkout of the plugin, so that a later commit could not change a run.
