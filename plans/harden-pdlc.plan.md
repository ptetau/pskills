# Plan: harden pdlc

**Owner:** Patrick Te Tau · **Status:** Done (final round run; results in the progress log)
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
  --permission-mode auto --allowedTools "<tools>"
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
| reviewer | Sonnet 5.5 (Fable 5.1 in round 0) | judges one app from a clean copy, the brief, the rubric, and two script outputs (probe results and process facts); one per app; a consistency reviewer only in the final round | see build logs, the builder's summary, or other reports |
| improver | Opus 5.5 | reads the reports, may read build logs and app repos, changes `plugins/pdlc` only, runs the plugin's unit tests | names an app in the harness, sees the hold-out, touches the rubric or probes |
| the user | | reads each round's summary; decides at the end | |

Round 0 used three Fable reviewers per app plus a consistency reviewer. From round 1, to
cut cost, scripts do the mechanical work (`run_probes.py` runs every probe in the brief;
`process_facts.py` collects the git and gate facts) and one Sonnet reviewer per app does
the judging. Sonnet is neither the builder's model nor the improver's. Round 1 is scored
with the new method for all three apps, so later rounds compare like with like.

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
6. The rubric and probes are frozen after round 0. Fix only typos, and log the fix. (The
   reviewer prompts changed once, from round 1, when reviews moved to one cheaper reviewer
   per app at the user's request.)
7. Every round uses the same model, the same tools list and the same seeds. Record the git
   hash of `plugins/pdlc` used for each round.

## Rounds and the stop rule

- **Round 0**: build the three apps with the harness as it is. Review. The improver fixes.
- **Round 1 and round 2**: build the three apps again with the fixed harness. Review. Improve.
  (Cut from three fix rounds to two, to save cost.)
- **Stop fixing** as soon as a round has, for every app: no hard fail, every rubric item
  scored at least 2, and a total of at least 85% of the maximum. Or after round 2, whatever
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
[2026-10-09] Round 0 (baseline, harness at e51c540)
Setup: builds run in auto permission mode. In acceptEdits mode, init could not copy pdlc's
       files with the shell and hand-wrote the scripts instead; auto mode copies them
       byte-for-byte. Restarted twice before any data counted (stray processes from a
       killed run kept writing into the app folders).
Scores: pocket-cli 54% (H1, H7) · convert-web 55% (H1, H2, H6, H7) · polls-api 48%
        (H1, H2, H3, H4, H6, H7) · consistency 3 / 6.
What went wrong: almost nothing merged. Ship stopped with questions despite "defaults";
        a newer intent's words were treated as a contradiction; verify kept finding new
        scope and never converged; a stuck change held back verify for finished ones;
        stages left files uncommitted; half a stack merged and crashed the app.
Fixes (Opus, 8): newest words win; reviewers fail only on spec, design or unsafe code and
        list follow-ups; every change runs every stage; every stage ends committed and
        clean; intake reads change state from branches; checks must not hang; one
        (assumed) marker with its own acceptance line; the merge check needs a tests
        review of the current lock (3 new failing-first tests). 50 unit tests pass.
        Word check: no app words in the diff.
Left: half a stack merging alone; status-line conflicts across intents; commit subject
      shapes; init copying with cp -r; guard blocks the test writer's root Glob.

[2026-10-10] Round 1 (harness at 05d64f4)
Setup: a usage limit cut off one ship; it was resumed once. Reviews switched to one
       Sonnet reviewer per app plus scripts (probe runner, process facts), at the user's
       request, and round 1 was scored that way for all three apps.
Scores: pocket-cli 79% (no hard fail) · convert-web 67% (H1: a shown number lacked the
        asked-for decimal) · polls-api 62% on main (H1, H2, H3). Round 0 was 54/55/48%.
What improved: two apps merged every change (6 of 6 each); every must probe passed in
        those two; ship took recommended answers instead of stopping; stopped changes
        were taken up first and finished.
What went wrong: one app's finished stack (all three branches pass the merge check,
        20/20 probes on its tip) never reached main: a later intent's spec edits on main
        conflicted with the first branch. Fix rounds added behaviour with no requirement
        or check; removed features stayed in the README; a page format was guessed.
Fixes (Opus, 5): while work is unmerged, intent stages commit on the intent's own branch
        on top of the stack; the merge check fails a branch that conflicts with main
        (new failing-first test); the intent's own words and examples bind; checks drive
        what the user does, with stand-ins and clock seams; bad input is specified up
        front; the README stays true. 52 unit tests pass. No app words in the diff.

[2026-10-10] Round 2 (harness at 5ac3983)
Setup: no interruptions. The probe script was loosened to find an error code under any
       key (the briefs don't name one); it had shown four false fails, which the
       reviewer had already checked by hand.
Scores: pocket-cli 40% (H1, H7) · convert-web 74% (no hard fail) · polls-api 68%
        (H1, H2, H7). Round 1 was 79/67/62%; the mean fell from 69% to 61%, so the
        regression rule applies before any new fix.
What improved: the first intent of the app that had a merge conflict now reached main
        (3 of 3 changes); one app merged all six changes with no hard fail.
What went wrong: one app's first change failed the quality review three times over
        something no requirement asked for, and nothing merged; ship asked which branch a
        later change should start from (intent branches added in round 1); one intent was
        split into about seven changes and stopped when the file guard blocked the test
        writer; specs were edited after ready "as an exception".
Regression cause (found by the improver): a round 1 rule sent a review problem that no
        check caught to tests first; a remit-rule problem has no acceptance line to tag a
        check with, and a branch may not add one, so verify handed it to the user and
        ship stopped. Intent branches could also miss a change built after them.
Fixes (Opus, 5): verify sends every failed review to tests or build, never to the user,
        and a stop never recommends merging over the gate; the guard finds the project
        from the file, not the agent's folder (it had blocked a test writer and let a
        builder edit checks; 4 new tests); no early stops, one retry for a blocked agent;
        an intent's first change merges its base in by rule; terminal GIF frames show
        the newest lines and errors (2 new tests). 58 unit tests pass (2 need the GIF
        tools). No app words in the diff.

[2026-10-10] Final round (harness at b1dd8e3, no fixes after)
Setup: five builds: the three apps, the hold-out (a Node library) and a second build of
       the greenfield CLI. Reviewed by one Sonnet reviewer each, plus one consistency
       reviewer. The merge stand-in was corrected to treat a branch merged before as
       merged (pdlc's catch-up had committed to an already-merged branch, and the
       stand-in had retried it and stopped); it was re-run on all five builds, which
       merged four more changes in one app.
Scores: pocket-cli 83% (no hard fail) · its second build 76% (no hard fail) ·
        convert-web 70% (H1, H2, H7: the second intent stopped at its first change) ·
        polls-api 56% (H1, H2, H3, H7: half a stack merged again) · hold-out 83% (no
        hard fail) · consistency 2 / 6.
Verdicts:
- Stop rule (every app at least 85%, every item at least 2, no hard fail): not met.
- Fixes generalise: yes. The hold-out had no hard fail and scored 83%, 13 points above
  the mean of the three apps (70%).
- Same brief, two builds: consistent. Both had no hard fail; no rubric item differed by
  more than 1 (totals 83% and 76%).
- Across apps: not yet consistent. Styles still differ, and scores spread 27 points.
Still open (from the final reviews):
- Half a stack can merge: a capability change that raises a new error merges before
  the change that handles it, and main breaks. The gate judges one change at a time.
- Verify fixes add behaviour that no requirement or check covers.
- After the last merge, statuses, bases and handoffs on main stay stale; pdlc's catch-up
  commits to branches that already merged.
- Checks that can't tell right from wrong: sample values that pass either way, limits
  tested near the edge, class-wide rules tested with a few examples.
- Date rules without a clock seam at the command line.
- Brownfield job and capability boundaries: one app put all route code in a capability,
  so its job changes couldn't be planned.
- Stale spec and README text after a behaviour changes; blank GIF frames accepted.
Scoreboard (percent of the rubric; hard fails in brackets):
| App | Round 0 | Round 1 | Round 2 | Final |
|---|---|---|---|---|
| pocket-cli | 54 (2) | 79 | 40 (2) | 83 |
| pocket-cli, second build | | | | 76 |
| convert-web | 55 (4) | 67 (1) | 74 | 70 (3) |
| polls-api | 48 (6) | 62 (3) | 68 (3) | 56 (4) |
| hold-out | | | | 83 |
| consistency (of 6) | 3 | | | 2 |
Round 0 was reviewed by three Fable reviewers per app; later rounds by one Sonnet
reviewer per app with scripts, so round 0 is not exactly comparable.

[2026-10-10] After the final round: the user's decisions on four open problems
Decided (with the user): an intent's changes merge together or not at all; a script
        keeps records on main and pdlc never writes to a merged branch; the tests review
        names a wrong version of the code for each check; new behaviour from a review
        waits for the user's approval, and ready settles implied behaviour first.
Fixes (Opus): check_merge fails a change while another change of its intent isn't ready,
        fails new commits on a merged change's branch, and fails a tests review with no
        "Wrong versions" lines or one that says "passes"; new bin/record_merges.py does
        the bookkeeping on main only; verify files review-only behaviour as an intent
        that awaits approval, and no skill takes it up on its own; ready walks a short
        checklist of implied behaviour (bad input, limits, order, old data, unsafe input,
        open business rules). 77 unit tests pass (2 need the GIF tools). Not yet tried in
        a build.
```
