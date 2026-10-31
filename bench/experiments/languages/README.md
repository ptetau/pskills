# pdlc on the to-do web app in three languages

This experiment runs pdlc on the same to-do web app in Rust, Clojure, and Lean 4. Each
language gets the same intent and the same 8 HTTP probes. `bench/fixtures/README.md` gives
the app and the intent. Each language has 1 run first.

| Language | Status |
|---|---|
| Rust | 3 runs: `rust.json`, `rust-2.json` and `rust-3.json`, each with its `rust-N.metrics.json` |
| Clojure | 1 run: `clojure-1.json`, `clojure-1.metrics.json` |
| Lean 4 | Waits for Lean 4. The session blocks its installer, and Ubuntu has no package of it. |

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

## Rust, run 2: after the fixes of the test writer

Between the two runs, pdlc got three fixes of the test writer:

- A Glob counts as a read of the folders that its pattern can list.
- A stored-data line gets a component check, and no acceptance check.
- The test writer gets one brief with each input.

| Measure | Run 1 | Run 2 |
|---|---|---|
| Cost | $6.18 | $4.93 (-20%) |
| Time | 1,433 s | 1,257 s (-12%) |
| Tool calls of the test writer (reads) | 65 (33) | 46 (16) |
| Guard blocks | 9 | 0 |
| Tool errors | 13 | 1 |
| Acceptance locks | 3 | 2 |
| Acceptance stage | $1.18, 394 s | $0.73, 200 s |
| Failed tests reviews (problems) | 3 (9) | 2 (2) |
| `verify` rounds | 5 | 3 |
| Recordings (failed visual reviews) | 9 (3) | 4 (1) |
| Probes | 8 of 8 | 8 of 8 |

Each fix shows in the run:

- The skill made the brief 10 times, and each prompt of the test writer was only the path
  of a brief.
- The acceptance file starts with the list of its stored-data lines, each with its change.
- The tests reviewer failed one entry of that list. The entry named a data path that is a
  folder, and the interface can make that state. Thus, the guard against a wrong entry
  works.
- The other failed tests review found a real fault. A check of a write error returned
  early when the process could still write, so it proved nothing.

Each column is one run, and one run varies a lot. The guard blocks, the tool errors, the
reads of the test writer and the acceptance stage follow from the fixes. The `verify`
rounds and the recordings can also vary by chance. The tests stage took longer (342 s
against 222 s), with 4 locks in each run.

## Rust, run 3: status codes in a terminal frame

Before this run, a web recording got `run` steps in a terminal tab. Show uses them for what
a page cannot show, such as a status code. The bench also got four new measures: check
strength, code quality, the time of checks and builds in each session, and the spread.

| Measure | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Cost | $6.18 | $4.93 | $4.99 |
| Time | 1,433 s | 1,257 s | 1,251 s |
| Failed reviews | 8 | 3 | 0 |
| Recordings | 9 | 4 | 3 |
| `verify` rounds | 5 | 3 | 3 |
| Acceptance locks | 3 | 2 | 1 |
| Faults that the checks catch | 19 of 20 | 20 of 20 | 20 of 20 |
| Faults that a user sees and the checks miss | 0 | 0 | 0 |
| New clippy findings: app code, checks | 0, 0 | 0, 0 | 0, 7 |
| Check time in all sessions | 36 s | 22 s | 21 s |
| Probes | 8 of 8 | 8 of 8 | 8 of 8 |

- Each change got one recording, and each visual review passed at the first try. The
  recordings show status codes, redirects and 404 answers with `curl -si`.
- But show used the terminal too much. One web recording had 12 terminal steps of 17, and
  some of them searched the HTML of a page with `grep`. Now show and the visual remit say
  that what a user sees shows on the page. A terminal frame that shows the HTML of a page
  is a `script` problem. No run measured this rule yet.
- The 7 clippy findings are all one style warning in a check file: `assert_eq!` with a
  literal `true` or `false`.
- The guard blocked 3 calls. The test writer tried to write a temporary file outside the
  project, and to search a file of app code. A reviewer tried to read a folder.

The three runs had different versions of pdlc, so their spread is not the noise of one
version.

## Clojure, run 1

The Clojure app runs on Clojure 1.11 from the Ubuntu package. This run had the same version
of pdlc as Rust run 3, and the rule that keeps what a user sees on the page.

| Measure | Rust, run 3 | Clojure, run 1 |
|---|---|---|
| Cost | $4.99 | $6.28 |
| Time | 1,251 s | 1,754 s |
| Main turns | 92 | 115 |
| Check runs (failed) | 16 (7) | 21 (4) |
| Check time in all sessions | 21 s | 71 s |
| `verify` rounds | 3 | 4 |
| Recordings | 3 | 10 |
| Failed reviews | 0 | 4 |
| Faults that the checks catch | 20 of 20 | 17 of 20 |
| Faults that a user sees and the checks miss | 0 | 0 |
| Probes | 8 of 8 | 8 of 8 |

The run finished, with 3 changes, and passed 8 of 8 probes.

- **Show cost the most: $1.98, 471 s, and 10 recordings.** The visual review failed 2
  times, with 8 problems. Most problems were a frame that showed a setup step under the
  caption of the result. Show sets the caption at the first step of a line, and a caption
  stays until the next one. Thus, each setup frame carried the claim of the line. Now a
  setup step gets its own `setup:` caption, and the last frame of a caption shows its
  claim.
- **The checks miss the heading.** A change of the title, a change of the heading, and the
  removal of the heading all pass the checks. The probes do not read the heading either.
- **Each check run starts a JVM.** The check runs took 71 s in all sessions, against 21 s in
  Rust.
- **No linter.** The session has no Clojure linter, so the run has no code-quality measure.

### Faults in the measures

- The check strength changed a docstring as if it were code. Now it skips docstrings.
- The fault that changes a text changed a letter of an HTML tag, such as `<h1>` to `<X1>`.
  A user does not see that. Now it changes the first letter that a reader sees.
- The probe of the "Show all" link read only its target. Now it also reads its text.

The Rust runs got the same new faults and the same probe again. Their results stay the
same, except one fault in run 1 that the checks miss: a letter of a text in the storage.
