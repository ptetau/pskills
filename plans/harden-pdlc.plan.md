# Plan: harden pdlc

**Owner:** Patrick Te Tau · **Status:** Draft
**Plan location:** `plans/harden-pdlc.plan.md`

## Goal

We want consistent good software from our harness.

pdlc (`plugins/pdlc`) turns an idea into specs, specs into small changes, and changes into
verified code. This plan tests it the hard way: use it to build small sample apps, judge the
results independently, fix the harness, and build again. Repeat until the apps come out
good, and stay good.

Three things must be true at the end:

- Every sample app does what its brief asked, with real checks and honest records.
- The fixes are general. An app the harness has never seen comes out just as good.
- Two builds of the same brief come out about as good as each other.

The harness never learns the names of the apps. The builder never learns it is being judged.

## How one build runs

A headless Claude Code session, in a fresh git repo that holds the app's seed:

```
claude -p "/pdlc:init defaults" --plugin-dir <plugin> --model claude-haiku-5-5 \
  --permission-mode acceptEdits --allowedTools "<tools>"
claude -p "/pdlc:ship defaults <intent 1>" ...   (same flags)
claude -p "/pdlc:ship defaults <intent 2>" ...
```

- `<tools>` is the fixed list in `harden/bin/run_app.sh`: the file tools, Agent, Skill, and
  `Bash` for git, node, npm, npx, python3, curl and common shell commands. Don't change it
  between rounds.
- `defaults` means pdlc never asks. It takes its recommended answer and marks it
  *(assumed)*. It still stops on a contradiction between requirements.
- `harden/bin/run_app.sh <round> <app-id>` does all of this for one app: makes the repo
  from the seed, runs init, then runs each intent in order with the merge stand-in after
  each. It saves the full transcript of every session (`stream-json`), the last message,
  and a `run.txt` with times and outcomes. The improver needs the transcripts to find root
  causes.
- Budgets: init up to 25 minutes, each ship up to 90 minutes. The script doesn't resume a
  ship that runs out of time. A cut-off is recorded and counts as a stop. If the
  orchestrator adds one resume within the budget, it records it and does it the same way
  every round.
- Apps in one round run in parallel, each in its own folder.

**The merge stand-in.** There is no git remote, so delivery stops at "here is the branch and
the PR body". A small script plays the human. After each ship, for each change branch of that
intent in stack order (follow `Base:` out from main), it switches to the branch, runs
`python3 pdlc/bin/check_merge.py`, and merges the branch into main only if the script
prints `ok`. On a `FAIL` it records the reasons and merges nothing further for that intent.
It never fixes anything. If a ship left the working tree dirty, it stashes the leftovers and
records that; a dirty tree is itself a finding. The next ship starts from whatever main is
then.

**Rules for every app.** Standard library only: Python 3 with `unittest`, or Node 22 with
`node:test` and `node:http`. No packages. (pdlc's GIF recorder installs its own tools into
`pdlc/.tools/`; that is pdlc's business.)

## The sample apps

Three apps, small and different from each other: two languages, three kinds of interface,
three starting points. Each gets two or three intents, run in order, so the app grows. Later
intents change or remove earlier behaviour, not just add, so changed and retiring
requirements get exercised. Every round builds every app again from the same seed and the
same intents, from scratch.

**pocket-cli** · Python 3 · command line · greenfield. A pocket-money ledger. The repo
starts with a README and nothing else, so init has no code to map and no check runner to
find. Intent 1 creates the whole thing: `add` and `list`, saved to a JSON file. Intent 2 adds
categories, changes the list layout, and adds amount validation with an exact message and
exit code. Intent 3 replaces `list` with a `report` that defaults to this month (so the
harness needs a clock seam and a date it never stored), and adds `undo`. Three intents,
because greenfield can only add on the first one.

**convert-web** · Node 22 · web page over a JSON API · brownfield with tests. A unit
converter: a pure conversion module, an `http` server with two routes, a page, and a small
test file. The seed has quirks: converting between kinds (km to kg) gives a number, and an
unknown unit gives null. Intent 1 makes both into proper 400 errors with codes, and a plain
message on the page. Intent 2 adds temperature (which doesn't fit the seed's "one factor per
unit" shape), changes rounding everywhere (which breaks the seed's own tests), and removes a
button. Two intents.

**polls-api** · Python 3 · HTTP JSON API · brownfield with no tests. Quick polls in memory:
create, read, vote, delete. The seed has a bug (voting for an option that isn't on the poll
adds it) that recon may write down as a requirement. Intent 1 fixes that, adds validation on
create, and changes the shape of every error reply. Intent 2 adds closing a poll (409 on
later votes), adds percentages to results, and removes the delete route. Two intents.

**A hold-out app exists.** It is a different kind of app again. Its brief is hidden until
the final round and is never shown to the improver, so we can tell whether fixes generalise
or only fit the three apps above.

The briefs, seed files and acceptance probes live outside this repo, in the orchestrator's
hidden folder. They are never copied into an app repo or shown to the builder or improver.

## Who does what

| Who | Model | Does | Never |
|---|---|---|---|
| orchestrator | this session | makes seed repos, runs builds, runs the merge stand-in, makes clean copies, starts reviewers and the improver, keeps the scoreboard | fixes an app or the harness itself |
| builder | Haiku 5.5, through pdlc | runs init and ship exactly as above | sees the rubric, the probes, the reviews, or any hint it is judged |
| reviewers | Fable 5.1 | judge one app each from a clean copy, the brief and the rubric; three per app plus one consistency reviewer per round | see build logs, the builder's summary, or each other's reports |
| improver | Opus 5.5 | reads the reports, may read build logs and app repos, changes `plugins/pdlc` only, runs the plugin's unit tests | names an app in the harness, sees the hold-out, touches the rubric or probes |
| the user | | reads each round's summary; decides at the end | |

Reviewers run on Fable because it runs and probes apps well, and it is neither the builder's
model nor the improver's, so the three don't share blind spots.

## Separation rules

These keep the data honest. Break one and the round doesn't count.

1. The builder's prompt is only `/pdlc:init defaults` and `/pdlc:ship defaults <intent>`.
   No system prompt, no extra files, no mention of evaluation.
2. Build logs and transcripts go to a logs folder that reviewers never see.
3. Reviewers get a fresh `git clone` of the build repo, with every branch and nothing
   untracked, plus the brief (with probes) and the rubric. Nothing else.
4. Reviewers of one app work in separate sessions. They don't read each other's reports.
5. The improver reads the reports and may read logs and repos. It edits only
   `plugins/pdlc`. It may not read the hidden folder. Before it hands back, the orchestrator
   greps its diff for app names and domain words (the hidden folder lists them). A hit is a
   failed round for the improver.
6. The rubric, probes and prompts are frozen after round 0. Fix only typos, and log the fix.
7. Every round uses the same model, the same tools list and the same seeds. Record the git
   hash of `plugins/pdlc` used for each round.

## Rounds and the stop rule

- **Round 0**: build the three apps with the harness as it is. Review. The improver fixes.
- **Rounds 1 to 3**: build the three apps again with the fixed harness. Review. Improve.
- **Stop fixing** as soon as a round has, for every app: no hard fail, every rubric item
  scored at least 2, and a total of at least 85% of the maximum. Or after round 3, whatever
  the scores.
- **Final round**: no fixes afterwards. Build the three apps, the hold-out, and
  `pocket-cli` a second time from the same seed and intents in a separate folder
  (`run_app.sh <round> pocket-cli -twin`). Review all five as normal. The twin builds are
  reviewed by different sessions that don't know they are twins.
- **Verdicts from the final round.** Fixes generalise if the hold-out has no hard fail and
  its total is within 10 percentage points of the mean of the three. The harness is
  consistent if the two `pocket-cli` builds agree on hard fails and differ by at most 1 on
  every rubric item.
- **Regression rule.** If a round's mean total drops more than 5 points against the round
  before, the improver first finds which of its last changes caused it, and may revert it,
  before doing anything new.

## What gets recorded each round

In the orchestrator's working folder, under `r<N>/`:

- the seed repo state and the `plugins/pdlc` git hash used;
- per app: `init.log`, `ship-<n>.log` and full transcripts; wall time per session; resumes;
  the merge stand-in's output per branch (`ok` or `FAIL` with reasons);
- per app: the number of changes per intent, how many merged, how many checks ran, how many
  manual checks were declared, and why ship stopped if it did;
- per app: three reviewer reports and their score sheets; per round: one consistency report;
- the improver's round note: each finding, its root cause, the harness change, the general
  rule it rests on, and what should look different next round; its diff; the unit test
  result (`python3 -m unittest discover -s plugins/pdlc/tests`); the grep result;
- one line per app in `scoreboard.md`: round, app, total, percent, hard fails, per-item
  scores. This is what rounds are compared on.

## Folders

```
<orchestrator folder>/harden/
  bin/               run_app.sh (build one app), review_copy.sh (clean clone for reviewers)
  hidden/            never given to the builder or the improver
    apps/<app>.md      brief: kind, seed, intents, probes
    seeds/<app>/       the seed files; run_app.sh copies them into a fresh repo
    intents/<app>.txt  one intent per line, in order; run_app.sh reads it
    rubric.md, prompts.md
  r<N>/
    build/<app>/       the build repos
    logs/<app>/        init and ship transcripts, run.txt, approvals.txt
    review/<app>/      repo/ (the clean clone) and a scratch folder per reviewer
    reports/<app>/     software.md, specs-and-checks.md, process.md
    reports/consistency.md
    improver.md        the round note
  scoreboard.md
```

## Progress log

One entry per round, appended when the round ends. Newest last.

```
(none yet)
```
