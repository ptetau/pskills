# pdlc on the to-do web app in three languages

This experiment runs pdlc on the same to-do web app in Rust, Clojure, and Lean 4. Each
language gets the same intent and the same 8 HTTP probes. `bench/fixtures/README.md` gives
the app and the intent. Each language has 1 run first.

| Language | Status |
|---|---|
| Rust | 1 run: `rust.json`, `rust-1.metrics.json` |
| Clojure | Waits for the Clojure CLI in the setup script of the environment |
| Lean 4 | Waits for Lean 4 (elan) in the setup script of the environment |

## Rust, run 1

The run finished, and passed 8 of 8 probes. pdlc planned 3 changes, not 2. The changes are
the storage of the done state, the page, and the route that marks an item done. The merge
check passed on each of the 3 branches, and the 54 checks of the app passed.

| Measure | Rust to-do app | wordfreq, 0.5.0 (run W-1) |
|---|---|---|
| Cost | $6.18 | $1.86 |
| Time | 1,438 s | 425 s |
| Changes | 3 | 1 |
| Main turns | 98 | 50 |
| Largest main context | 247,000 tokens | 137,000 tokens |
| Check runs (failed) | 24 (9) | 7 (1) |
| `verify` rounds | 5 | 2 |
| Recordings | 9 | 1 |
| Failed reviews | 8 | 1 |
| Lines of app code added | 87 | 21 |
| Lines of checks added | 1,269 | 153 |

The two apps differ in size, in kind, and in the count of changes. Thus, this table shows
the scale of the work, and not the effect of the language.

| Stage | Cost | Time |
|---|---|---|
| ship | $0.21 | 42 s |
| intake | $0.29 | 128 s |
| acceptance | $1.18 | 394 s |
| tests | $0.86 | 222 s |
| build | $0.71 | 156 s |
| `verify` | $1.21 | 147 s |
| show | $1.72 | 344 s |

Ship ran ready and change in its own conversation, with no Skill call. Thus, their cost is
part of intake.

### What cost the most

- **Show: $1.72 and 9 recordings.** The visual review failed 3 times, with 9 problems. Most
  problems were captions that claimed more than a browser frame can show. Examples are
  "answers 200", the `action` of a form, and a second app on the same data file. The
  acceptance lines of a web app talk about status codes and HTML, but a frame shows only
  the page.
- **Acceptance: $1.18 and 394 s.** The acceptance checks were locked 3 times.
- **9 guard blocks.** The test writer tried 7 times to read the project root, the README, or
  a review result. The reviewer tried once to read a review folder. Each block costs a
  turn. The CLI also counts each block as a permission denial, so the 9 denials are the
  same 9 blocks.
- **Check runs:** 9 of 24 failed. 4 failures were the red runs of the tests stage, which
  must fail. The builder needed 2 runs to get green in 1 of its calls, and 1 run in the
  others.

### Bench faults that this run found

- **Stage time with repeated stages.** Each change stage runs once for each change. The
  bench took the time from the first start of a stage to the first start of the next
  stage. Now the time of a stage is the sum of its visits, and the times add up to the
  wall time.
- **Change status.** The status is on one header line with other fields, and the bench
  read it as "?". Now it reads the field.
