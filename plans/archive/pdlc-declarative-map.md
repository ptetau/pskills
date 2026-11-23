# Rule map: pdlc skills in the declarative form

This map lists each rule of the old pdlc text (version 0.3.0) and the place of the rule in
the new text (version 0.4.0). A row that says "removed" gives the reason. The old text is
in commit da9f30c, and the new text is in `plugins/pdlc/`.

Words used here:

- README: `plugins/pdlc/skills/init/references/templates/README.md`. Init copies it to
  `pdlc/README.md`.
- README "X": the section "X" of the README.
- Goal, Constraints, Inputs, Outputs: the four sections of a new `SKILL.md`.
- "Procedure": an order of steps that a Sonnet class model can find from the goal,
  the constraints, and the outputs.

## Rules that each skill had

| Old rule | New place |
|---|---|
| Read `pdlc/README.md` first, and obey it | README intro ("Each skill reads this file first"). Each skill: Constraints, line 1 ("The rules of `pdlc/README.md` hold"), and Inputs |
| Start with the "Before any work" step | README "Bookkeeping on main". Each writing skill: Constraints, line 1 ("Bookkeeping on main" runs first) |
| Read the latest handoff of the intent or change | README "Stages and handoffs" (each stage starts from the latest handoff). Each skill: Inputs |
| Tell the tracker port about each changed status | README "Stages and handoffs" (end of each stage) and README "Ports" |
| Start each agent with `run_in_background: false` | README "Who does what" |
| Give each ID a short description, 25 words in each sentence | README "Writing" |
| Numbered steps ("1.", "2.", "Step 3") | removed: procedure. The order now comes from the constraints and the outputs |

## README template

| Old rule | New place |
|---|---|
| Each pdlc skill reads this file first | README intro |
| (new) pdlc runs only on a Sonnet 5.5 class model or above | README "Core rules" 1 |
| Core 1: all work enters through the inbox | "Core rules" 2 |
| Core 2: specs before code, an intent is `ready` before a change is planned | "Core rules" 3 |
| Core 3: one job, one capability, or one design spec for each change | "Core rules" 4 |
| Core 4: a job owns its entry points (routes, handlers, commands, page scripts) | "Code maps" (job owns entry points) |
| Core 4: a capability holds only the shared logic | "Code maps" (capability owns shared logic) |
| Core 4: a job change uses capabilities, but does not edit them; a missing capability gets an earlier change | "Core rules" 5 |
| Core 5: the test writer writes checks first, from the spec only; acceptance first, then component; locked; app writer does not change checks | "Core rules" 6 |
| Core 6: reviews are independent, one fresh reviewer for each remit, only its packet | "Core rules" 7 |
| Core 7: the six merge conditions, checked by `bin/check_merge.py` | "Core rules" 8 |
| Core 7: the changes of an intent merge together, bottom first | "Stacked changes" |
| Core 8: these files are the truth, boards only show them | "Core rules" 9 |
| Core 9: subject and trace trailers, blank line, one on each line | "Commits" |
| Core 9: `Intent` first, `Change` on a change branch, `Req` for code, checks, or README | "Commits" |
| Core 9: the skill of each stage gives the subject | "Commits" |
| Core 9: a hook examines each new commit on a pdlc branch, fix at once with `git commit --amend` | "Commits" |
| Core 10: all text obeys `DES-writing-style.md`, with the list of text types | "Writing" |
| Core 10: the short form of the rules (25 and 20 words, active voice, one topic, "must"/"can", no semicolon, described IDs) | "Writing" |
| Core 10: read the full rules before a spec or an intent; short form enough for a handoff, proposal, commit, reply | "Writing" |
| Core 10: `bin/check_writing.py` finds the breaks that a script can find | "Writing" |
| Layout: each item of `pdlc/` | "Layout" |
| Layout: replace each `<placeholder>` and guide sentence of a template | "Layout" (`templates/`) |
| Layout: `.tools/` is not committed | "Layout" |
| Code maps: all five rules (job, capability, shared file by parts, change lists own parts, README in no map) | "Code maps" |
| Who does what: the table | "Who does what" |
| A guard keeps the roles in their lanes | "Who does what" |
| Starting an agent: absolute paths | "Who does what" |
| Starting an agent: Agent tool, `run_in_background: false`, the call returns the reply | "Who does what" |
| No wait with a sleep, a loop, a monitor, or a notification | "Who does what" |
| Side-by-side agents (reviewers) start in one message | "Who does what" |
| Do not stop a slow agent | "Who does what" |
| A blocked agent: fix the path, run once more from the project root; a second failure is one failure of the stage; not a reason to stop | "Who does what" |
| Stages: the intent stages and the change stages; ship runs all | "Stages and handoffs" |
| Each stage reads the latest handoff, and writes a new one | "Stages and handoffs" |
| Intent handoff in the "Handoff" section with `###` headings | "Stages and handoffs" |
| Thus, the full handoff stays inside that one section | removed: reason. The `###` rule stays |
| Change handoff in `changes/CH-xxxx-name/handoff.md` | "Stages and handoffs" |
| Use `templates/handoff.md`, the title from its list, every section, "none" under an empty one | "Stages and handoffs" |
| Time from the real clock (`date -Iseconds`) | "Stages and handoffs" |
| Replace the old handoff, git keeps the history | "Stages and handoffs" |
| Each stage sets the statuses that it owns (tests: `testing` then `building`; `verify`: `in review`; `record_merges.py`: `merged`, `done`) | "Stages and handoffs" |
| Commit everything, `git status --porcelain` shows nothing | "Stages and handoffs" |
| Delete check leftovers, do not commit them; init lists their folders in `.gitignore` | "Stages and handoffs" |
| The handoff says only what the files show; real counts, no estimates | "Stages and handoffs" |
| Acceptance checks: one file for each intent, at the "acceptance file" path | "Acceptance checks" |
| Acceptance checks: through what a user uses, any feature of the intent or existing | "Acceptance checks" |
| Acceptance stage writes, locks, and reviews before the first change; `Acceptance-File:`, `Acceptance-Locked:` | "Acceptance checks" |
| Component checks use only the interface of their change and earlier changes | "Acceptance checks" |
| The "all" command does not run an acceptance file; main stays green | "Acceptance checks" |
| Build and `verify` run all checks and **run earlier acceptance** | "Acceptance checks" |
| `verify` of the last change runs **run acceptance**, and writes `Acceptance-Passed:` | "Acceptance checks" (also covers build, which ran it for the last change too) |
| After the intent merges, the checks stay green | "Acceptance checks" |
| Where pdlc commits: init on main; intent stages on main when no pdlc branch is unmerged; by design, also where the usual rule is to branch first | "Where pdlc commits" |
| Acceptance stage commits on the intent branch, and starts it | "Where pdlc commits" |
| A change commits on its own branch; an unmerged change is `planned` on main | "Where pdlc commits" |
| While a pdlc branch is unmerged, only `record_merges.py` commits on main; intent stages use the intent branch | "Where pdlc commits" |
| The intent branch starts from the newest unmerged branch (the `git branch --no-merged` command, the `DES-pdlc-branches` pattern), named in `Branch:` | "Where pdlc commits" |
| So the patches come after the work, and every branch merges in order | "Where pdlc commits" |
| Do not commit on a merged branch, not even a status or `Base:`; later work is a new change; the merge check refuses new commits | "Where pdlc commits" |
| Work only in the project checkout, not a worktree | "Where pdlc commits" |
| ... because work in a worktree goes to the wrong place | "Where pdlc commits", in short form ("use the paths of the checkout") |
| Commit before `git switch`; when it refuses, commit or delete what `git status` shows (`__pycache__/`) | "Where pdlc commits" |
| Before a selection by status: list the unmerged branches, read each `change.md` from its branch (`git show`), read each intent from the newest branch | "Where pdlc commits" (as a constraint, not as steps) |
| A change with no branch is `planned` | "Where pdlc commits" |
| Stacked changes: built on the branch of the change before it; `Base:` names it; the pull request targets it | "Stacked changes" |
| First change: on the newest unmerged change of an earlier intent, or main | "Stacked changes" |
| An intent `Branch:` is the start of the first change, which carries the spec patches | "Stacked changes" |
| If that branch lacks the base, the tests skill merges the base into it first | "Stacked changes" |
| The merge check fails each change of the intent until all are `in review` | "Stacked changes" |
| A base that merged into main: `Base:` becomes main on the change branch, propose against main | "Stacked changes" |
| Do not rewrite `Base:` on a merged branch | "Stacked changes" ("A merged branch keeps its `Base:`") |
| Statuses of intent, requirement, change, spec file | "Statuses" |
| Asking questions: one short question at a time, two or three answers, the recommended one marked with one line on why, `skip` | "Questions" |
| A decision without an instruction gets `(assumed)` where it is written, and goes in the handoff | "Questions" |
| The mark is plain, reason outside the brackets; the merge check rejects `(limit assumed)` and `*(assumed)*` | "Questions" |
| With `defaults`: no question, the recommended answer, recorded in "Decided on defaults" and in "Notes" | "Questions" |
| Before any work: main, pull, `record_merges.py`, its effects, no bookkeeping by hand or on another branch | "Bookkeeping on main". Its scope is now exact: each skill that names the section. `trace` and `dashboard` never ran it |
| New behaviour needs approval (definition, not on a change branch, `verify` files a `new` intent with `Awaits approval:`, no skill takes it up, also with `defaults`, the user names it, the line goes) | "New behaviour needs approval" |
| pdlc's own files (which files, upgrade on main in an own commit, not on a change branch, `Default: yes` refresh, `Default: no` belongs to the project) | "pdlc's own files" |
| Using a port: read the port, find the adapter in `config.md`, follow the adapter; do not call a covered tool directly | "Ports" (as a constraint, not as steps) |
| After any status change, tell the tracker; skip with `none` | "Ports" |

## ship

| Old rule | New place |
|---|---|
| Ship runs each stage with its skill until each change is proposed | Goal |
| (new) Stop on a model below the Sonnet 5.5 class | Constraints, line 1 |
| An earlier stop on an unmerged change: continue it first | Constraints (the work to take, first item) |
| With `defaults`, take the recommended answer of the stop handoff | Constraints (first item) |
| Give the change two new rounds | Constraints (first item) |
| A contradiction still waits for the user | Constraints (first item) |
| New words: start at intake with them | Constraints (second item) |
| A named intent or change: start from its status | Constraints (third item) |
| Else the oldest intent not `in review`, `done`, `paused`, `cancelled`, with no `Awaits approval:` | Constraints (fourth item) |
| An intent `in review` has each change proposed, and waits for the user | Constraints (fourth item) |
| Do not take an `Awaits approval:` intent unless the user names it | Constraints (fourth item) and README "New behaviour needs approval" |
| Read intents and changes where they live | Constraints ("Where pdlc commits") |
| Read the latest handoff; ship can continue after a stop, a crash, or a new session | Constraints |
| Follow each stage skill, always with `defaults` | Constraints |
| Only handoffs and files carry details between stages | Constraints |
| The stage order (intent stages, change stages, propose) | Constraints (README "Stages and handoffs") |
| The acceptance stage locks the checks before the first change; they pass only at the last change | README "Acceptance checks" |
| Each change runs each stage; do not hold or skip show or `verify` | Constraints |
| Changes stack; start the tests of the next change at once; no wait for merges | Constraints |
| Update the dashboard and the tracker after each stage | Constraints |
| A one-line note for each stage, for the summary | Outputs |
| A failed `verify` goes to the stage that its handoff names; then build, show, `verify` | Constraints |
| Do not ask the user about a failed review | Constraints |
| A failed tests review: back to tests, then build, show, `verify` | Constraints |
| A failed acceptance review: back to acceptance | Constraints |
| Two rounds for each change and each acceptance stage; stop on the third failure | Constraints and README "Rounds" |
| What a round is | README "Rounds" |
| The four stops (contradiction, file outside "Files", three failures, the end) | Constraints |
| A missing "Interface" entry is not a stop | Constraints |
| Ready takes no default for a contradiction | Constraints |
| Each other case: the recommended answer, in the handoff and the "Notes" | Constraints |
| Not stops: missing remote, a choice (default: the stand-in seam), the base | Constraints |
| Do not stop for long work, a slow agent, or a failed tool; run a blocked agent once more | Constraints and README "Who does what" |
| At a stop: the reason under "Open", what the user must decide, the recommended answer | Outputs |
| The answer obeys the rules of pdlc (not "merge over a failed gate", not "accept a failed review") | Constraints |
| Commit "Stop CH-xxxx: <why>" or "Stop IN-xxxx: <why>"; `git status --porcelain` empty; tell the user | Outputs |
| The final summary (changes and pull requests with GIFs, default answers, new behaviour with intents, what waits for the user) | Outputs |
| Continue to the end of the stack or a stop; a new run continues from the handoffs | Outputs |

## intake

| Old rule | New place |
|---|---|
| Intake makes spec patches, and does not write code | Goal |
| (new) Stop on a model below the Sonnet 5.5 class | Constraints, line 1 |
| With an unmerged pdlc branch, switch to the newest one | Constraints |
| ... so that the inbox and the specs are current | removed: reason |
| New words: add through the inbox port, the words as "What and why", tell the ID | Constraints (sources) |
| A named intent: remove `Awaits approval:`, the name is the approval | Constraints (sources) |
| A `.blueprint.md`: the words of the intent; scope gives "What and why"; other sections give requirements, codes, signatures; keep `(assumed)`; the pdlc specs lead; nobody changes the blueprint | Constraints (sources) |
| Else the oldest `new` intent with no `Awaits approval:` | Constraints (sources) |
| With an unmerged branch, start the intent branch from it through the delivery port, before any commit, in `Branch:` | Constraints |
| With no unmerged branch, commit on main, keep `Branch: none` | Constraints |
| Set the intent to `specifying` | Outputs |
| Where a thing belongs (job, capability, design, output look, shared behaviour, the unsubscribe example) | README "Spec patches" |
| Prefer an existing spec; a capability boundary around a likely change, its name (`CAP-payments`) | README "Spec patches" |
| Two meanings: ask first; with `defaults`, the likely meaning and a note | Constraints |
| A stub spec: recon with three items only (root, spec path, `deep look`) | Constraints |
| Recon knows the format of its reply | removed: reason. `agents/recon.md` holds the reply format |
| Do not ask recon for a summary, the template, or extra detail | Constraints |
| Write the recon requirements as `built`, `Source: recon`; spec becomes `Status: active` | Constraints |
| List the change branches first; statuses on main can be out of date | Constraints |
| Do not edit a change spec; an unmerged change keeps what it copied | README "Spec patches" |
| A changed requirement of an unmerged change: say so in the handoff; this change stacks after | Constraints |
| Write directly into the specs; a new spec from the templates | Constraints |
| New requirement: next number, `proposed`, `Intents:`, one or two sentences, Given/when/then | Constraints |
| `(assumed)` on each detail that the intent does not give (message, limit, order, format) | Constraints |
| 25 words also in an acceptance line; a second short sentence | README "Writing" |
| Described IDs, as in `R5 (usage line)` | README "Writing" |
| The words of the intent bind (examples exactly, plain reading, edge values, no narrow `(assumed)` reading) | README "Spec patches" |
| Changed requirement: in place, `proposed`, add the intent | Constraints |
| Removed requirement: `retiring`, add the intent | Constraints |
| New job: list its capabilities and design specs | Constraints |
| The newest words win; a changed requirement, not a contradiction | README "Spec patches" |
| Find every requirement of this type (a new format changes every example) | Constraints |
| Note `<ID>: was "<old>", now "<new>"` | README "Spec patches" |
| A question for ready only for two possible meanings | Constraints |
| Leave no old wording (the search, the places, the cross-references) | README "Spec patches" |
| The summary shows each added requirement ("Who and why", "What it is for", the new option example); the specification review fails it | Constraints |
| Do not edit the README; `README: "<old line>" → <requirement>` in "Notes"; the change fixes it | README "Spec patches" |
| A requirement still `proposed` for another open intent: ask; with `defaults` this intent wins, its changes come after | Constraints |
| "Requirements" section: each touched requirement with one word | Outputs |
| Handoff for ready: what was written, assumed, unclear | Outputs |
| Commit "Specify IN-xxxx: <name>" with `Intent`; also when stopping early | Outputs |
| Tell the user what was written, and that `/pdlc:ready` is next | Outputs |

## ready

| Old rule | New place |
|---|---|
| Each requirement clear, testable, consistent | Goal |
| No intent named: the oldest `specifying` intent | Constraints |
| Read the intent and its "Handoff" | Inputs |
| Switch to `Branch:`, commit there | Constraints |
| Collect `proposed` and `retiring` requirements and their specs | Inputs |
| List the implied behaviour before anything is `ready`; the six kinds of item; skip what does not apply | Constraints |
| Settle each as lines on its requirement, or a new `proposed` requirement listed as added | Constraints |
| 25 words, two lines for a long line, described IDs | README "Writing" |
| The right spec, as in intake; shared behaviour one time in the capability | README "Spec patches" |
| Ask about each item; with `defaults`, `(assumed)`; the list in the handoff; do not build an omitted item without approval | Constraints |
| The 13 conditions of a clear requirement | Constraints (the list) |
| Each example of the intent is a line, exactly | README "Spec patches", named in the list |
| Ask as "Asking questions" says; with `defaults`, no question | README "Questions" |
| Recommend the plain reading; not a reading that keeps old behaviour or changes an example | README "Spec patches" ("No `(assumed)` reading or recommendation narrows ...") |
| Write each answer into the requirement; a default answer `(assumed)` with its "Notes" line | Outputs |
| A missing design spec: `pdlc:conventions`, then continue | Constraints |
| Compare requirements with each other, their specs, the relied-on specs; the 50 ms example | Constraints |
| Newest words win: change the older one, list it as `changed`, a "Notes" line | Constraints |
| A guess gives way: keep its mark, update its "Notes" line | Constraints |
| Other contradictions: show both, ask, no selection also with `defaults`, both stay `proposed`, tell the user | Constraints and Outputs |
| Leave no old wording; README lines in "Notes" | README "Spec patches" |
| Clear requirements to `ready`; `retiring` stays | Outputs |
| The intent `ready` when all are `ready` or `retiring` | Outputs |
| Handoff for change: decisions and what helps the plan | Outputs |
| Commit "Ready IN-xxxx: <name>" with `Intent`, also at a contradiction stop | Outputs |
| Tell the user what changed, and that `/pdlc:change` is next | Outputs |

## change

| Old rule | New place |
|---|---|
| Divide a ready intent into changes, one change spec each | Goal |
| Read the "Handoff" of the intent | Inputs |
| No intent named: the oldest `ready`; not `ready`: tell the user, stop | Constraints |
| Switch to `Branch:`, commit there | Constraints |
| Read every requirement, their specs, relied-on specs, the code of their maps | Inputs |
| Group by spec, one change for each group, no change across two specs | Constraints |
| Order by need (the `JOB-pay-invoice` and `invoices` example) | Constraints |
| Otherwise design, then capabilities, then jobs; a relied-on capability first | Constraints |
| Next free number, the folder, `change.md` from the template | Constraints |
| Header fields; the tests stage sets the real base | Constraints |
| Requirements: heading and lines, number order, nothing else, ` (retire)` | Constraints |
| Relies on: "used, not changed"; the design specs, with the three named ones | Constraints |
| Interface: what checks can call, sufficient without code; the kinds of item | Constraints |
| Each entry: file, in and out with types, errors by `DES-errors` code | Constraints |
| A user action in "when": list that surface; checks drive it, not only a helper | Constraints |
| New names here, in the style of the code, `(assumed)` | Constraints |
| Only items of this, earlier, and existing code; not a later change; component checks call only these; acceptance checks read every Interface | Constraints |
| Test seams: clock, randomness, vendors and stores | Constraints |
| The seam at the outermost interface, so that a check of the surface reaches it; for a command an environment variable or flag that the README names; not only deep in the code | Constraints |
| The stand-in seam (the three steps: stub page, network only, act as the user) | Constraints (as one statement) |
| "none" only when no line needs a seam | Constraints |
| Files: only what the change needs, from the code map; shared file by parts; a job change lists no capability files or parts | Constraints |
| A job entry point in a capability map moves to the job map, a note, no stop | Constraints and Outputs |
| A job change lists the README; another change when it alters what the README tells; `.gitignore` when it lacks check folders | Constraints |
| Check files: in the check folders of `config.md`, named after the spec | Constraints |
| Steps: one for each requirement, its check (ID in the name), "Done when"; a `(retire)` step removes code and checks, with no check | Constraints |
| The README step and its four "Done when" conditions | Constraints |
| Manual checks: only what no check can see, one line in template form, `manual check` | Constraints |
| A missing runner or tool is not a reason for a manual check or a stop; use a stand-in | Constraints |
| The "Changes" section of the intent, in order | Outputs |
| Handoff for acceptance: changes, order, interface help | Outputs |
| Commit "Plan IN-xxxx: <names of changes>" with `Intent` | Outputs |
| Tell the tracker about each new change | Outputs |
| Tell the user the changes and that `/pdlc:acceptance` is next | Outputs |

## acceptance

| Old rule | New place |
|---|---|
| The checks prove all of the intent, one line each, as a user meets it; any feature; they fail until the last change | Goal and README "Acceptance checks" |
| Read the "Handoff" of the intent | Inputs |
| The named intent, or the oldest `ready` intent with changes and `Acceptance-Locked: none` | Constraints |
| After a send-back, read the reason in that `handoff.md`; app code exists | Constraints and Inputs |
| Work at the top of the stack of the intent (its definition) | Constraints |
| `Branch: none`: start the intent branch from the newest unmerged pdlc branch or main, in `Branch:` | Constraints |
| Set the intent to `building` | Outputs |
| All requirements `retiring`: nothing to prove, keep both lines `none`, finish | Constraints and Outputs |
| Missing config lines: write them as init does, commit them with the file | Constraints and Outputs |
| `Acceptance-File:` path with the intent ID in the ID form of the project | Constraints |
| The test writer gets only the absolute path of the intent | Constraints |
| A missing Interface item: add it yourself, start the test writer again | README "Checks before code" |
| The test writer can move an earlier check of a changed or retired requirement | Constraints |
| Red through **run acceptance**, time limit, broken check back before the lock | Constraints and README "Checks before code" |
| New behaviour fails; a pass goes back; an existing behaviour pass is recorded in "Notes"; a missing interface counts; not a check mistake; after a send-back a pass is correct | README "Checks before code" |
| On a change branch, each commit also has `Change` | Constraints and README "Commits" |
| Commit "Acceptance IN-xxxx" with `Intent` and `Req` | Outputs |
| Lock hash on `Acceptance-Locked:`, replaced on a new lock | Outputs and README "Checks before code" |
| Commit "Lock acceptance IN-xxxx" with `Intent` | Outputs |
| After the lock only the test writer, only through this skill; each edit a new lock and a new review | README "Checks before code" |
| A new lock makes `Acceptance-Passed:` out of date; the merge check finds both | Constraints |
| `make_packets.py IN-xxxx`; a fresh reviewer with only the packet path | Outputs and README "Checks before code" |
| Commit "Review acceptance IN-xxxx" with `Intent` | Outputs |
| A fail goes to the test writer; red, lock, review again; a third fail stops and asks | README "Checks before code", README "Rounds", and Outputs |
| Handoff for tests (checks, lock, what each change must give); after a send-back, the change `handoff.md` for build | Outputs |
| Commit "Acceptance reviewed IN-xxxx" with `Intent` | Outputs |
| Tell the user the next step (tests, or build after a send-back) | Outputs |

## tests

| Old rule | New place |
|---|---|
| Checks first, from the spec, by a writer that does not see the code; acceptance checks come earlier | Goal |
| The named change, or the first `planned` change in intent order | Constraints |
| The first change needs a complete acceptance stage (`acceptance → tests` handoff), else acceptance first | Constraints |
| A change with a branch was sent back: same branch, keep `Base:`, start from the reason, no status change until the finish | Constraints and Outputs ("A send-back has no new start") |
| The base (previous change, earlier intent, or main) | README "Stacked changes" |
| No merge of the previous change first; but it is `in review` or `merged`, else its show and `verify` first | Constraints |
| Start the branch through the delivery port; the intent `Branch:` for the first change, which carries the specs and acceptance checks | Constraints and README "Stacked changes" |
| Make sure that the intent branch holds the base; else merge it, with `Intent` | README "Stacked changes" |
| The conflict rule for that merge | README "Stacked changes" |
| `Branch:` and `Base:` in the header; change `testing`, intent `building`; commit "Start CH-xxxx" with `Intent`, `Change` | Outputs |
| Read the change `handoff.md`, or else the intent "Handoff" | Inputs |
| The test writer gets only the change spec path, and writes the "Check files" | Constraints |
| The test writer cannot delete; `git rm` a file of a `(retire)` requirement before the lock | Constraints |
| A missing Interface item: add it yourself, start again | README "Checks before code" |
| Red: time limit, broken check, new behaviour fails, pass back, existing pass recorded in the progress log, missing interface counts, after a send-back a pass is correct | README "Checks before code" |
| Commit "Tests CH-xxxx" with `Intent`, `Change`, `Req` | Outputs |
| `Tests-Locked: <hash>` right under the header; replaced on a new lock | Outputs and README "Checks before code" |
| Commit "Lock tests CH-xxxx" with `Intent`, `Change` | Outputs |
| After the lock only the test writer, only through this skill; each change a new lock | README "Checks before code" |
| Each lock gets its own review; the merge check refuses an older lock; re-review packet content; the reviewer judges only these | README "Checks before code" |
| `make_packets.py CH-xxxx tests`; a fresh reviewer with only the packet path | Outputs and README "Checks before code" |
| Commit "Review tests CH-xxxx" with `Intent`, `Change` | Outputs |
| A fail goes to the test writer; red, lock, review again; a third fail stops and asks | README "Checks before code", README "Rounds", and Outputs |
| Set the change to `building` | Outputs |
| Handoff for build: checks and what each proves, the lock, what the builder must know | Outputs |
| Commit "Tests reviewed CH-xxxx" with `Intent`, `Change` | Outputs |
| Tell the user that `/pdlc:build` is next | Outputs |

## build

| Old rule | New place |
|---|---|
| Make the locked checks pass, without a change to them | Goal |
| Read the `handoff.md` of the change | Inputs |
| The named change, or the first `building` change in intent order | Constraints |
| No hash on `Tests-Locked:`: tell the user to run tests first, stop | Constraints |
| Switch to the change branch | Constraints |
| Base with new commits: merge it first, with `Intent` and `Change` | Constraints |
| The builder gets the change spec path and each acceptance file that must pass (two kinds) | Constraints |
| The builder changes only the "Files", runs the checks, reports | Constraints |
| A check that looks incorrect: do not change it; to tests (which relocks), then build again; an acceptance check to acceptance | Constraints |
| A file outside "Files": ask the user; on a yes add it, start the builder again | Constraints |
| The same problem a third time: stop and ask | Constraints and README "Rounds" |
| All checks pass; `git diff --name-only <Tests-Locked hash> -- <check files>` shows nothing | Constraints |
| **Run earlier acceptance** passes; the last change also **run acceptance**; an earlier failure is expected, not reported | Constraints and README "Acceptance checks" |
| Commit "Build CH-xxxx: <what changed>" with `Intent`, `Change`, `Req`, and `Ticket` when there is one | Outputs |
| Tick the steps, a progress-log line, requirements `built`; a `(retire)` requirement leaves its spec with its code; the test writer removed its checks | Outputs |
| Handoff for show: what was built, how to run it, surprises | Outputs |
| Commit "Built CH-xxxx" with `Intent`, `Change` | Outputs |
| Tell the user that `/pdlc:show` is next | Outputs |

## show

| Old rule | New place |
|---|---|
| A short GIF that shows the change do what its spec says | Goal |
| Read the `handoff.md` of the change | Inputs |
| The named change, or the first `building` change with all requirements `built`; its branch | Constraints |
| Every change gets its show; a capability in a terminal, also in a web app; do not hold show for later changes | Constraints |
| The recorder and its four needs | Constraints |
| `missing <name>`: the `npm install` command; no browser: the `playwright install` command | Constraints |
| `pdlc/.tools/` in `.gitignore` | Constraints |
| Obey the visual port and its adapter; write `visual.json` | Constraints |
| Steps for each line, in order; the caption form; each line a step; compare the count | Constraints |
| As a user meets it (web, CLI, library) | Constraints |
| Helper scripts in the change folder; paths from the project root, so anyone can record again | Constraints |
| A terminal script ends with a run of all checks; a web script does not | Constraints |
| A terminal frame scrolls, shows the newest lines with errors; output under one screen | Constraints |
| The record command | Constraints |
| A frame shows what its caption claims; the two failure cases of the recorder | Constraints |
| On a failure, correct the script (selector, step, silent command); record again | Constraints |
| `"unchanged": true` only when the line says that nothing changes | Constraints |
| Read the last frame of each line; correct the script and record again; do not correct the app | Constraints |
| Handoff for verify: frame by frame, lines shown out of how many | Outputs |
| One commit "Visual review CH-xxxx" with `Intent`, `Change`, `Review: …/review.gif` | Outputs |
| Tell the user that `/pdlc:verify` is next | Outputs |

## verify

| Old rule | New place |
|---|---|
| Decide if the change is good enough, ask the user to approve; do not merge | Goal |
| Read the `handoff.md` of the change | Inputs |
| The named change, or the first `building` change with a `review.gif`; its branch | Constraints |
| Each requirement has a check that passes; "No checks found" fails, except `(retire)` | Constraints |
| All checks pass; no check file changed since `Tests-Locked` | Constraints |
| **Run earlier acceptance** passes | Constraints |
| The last change: **run acceptance** passes, note `git rev-parse HEAD`; an earlier failure is expected | Constraints |
| `make_packets.py CH-xxxx --verify`; do not list remits; all remits except `tests`, whose result stays | Constraints |
| A remit that does not apply: the script writes `result.md`, no reviewer | Constraints |
| ... and the script says so | removed: a fact about the script, which the script does by itself |
| A later round: re-review packets; the reviewer judges only the earlier problems and the diff | Constraints |
| One fresh reviewer for each packet, in one message, `run_in_background: false`, only its own path, no other findings | Constraints and README "Who does what" |
| The tool calls return when all reviewers are done; each writes `result.md` | removed: a fact about the Agent tool (README "Who does what" says the call returns the reply) and about the reviewer (`agents/reviewer.md` writes `result.md`) |
| New behaviour (definition, examples, "Follow-ups", a problem that only new behaviour fixes) | Constraints and README "New behaviour needs approval" |
| Do not build it on this branch | README "New behaviour needs approval" |
| File it through the inbox, `new`, in the words of the reviewer, `Awaits approval: found reviewing CH-xxxx (<remit>)`; not when an intent asks already | Constraints |
| Its ID in the progress log, for the proposal | Outputs |
| With `defaults`, do not approve such an intent | Constraints |
| Commit "Verify CH-xxxx: round <n>" with `Intent`, `Change`, pass or fail; findings stay in git | Outputs |
| The problems in the `handoff.md`, each to its stage (the six routes) | Constraints and Outputs |
| Old wording: fix it now, on this branch, only those words, no acceptance line | Constraints |
| A remit failed only for new behaviour or old wording: nothing to build; `verify` again, a round | Constraints |
| A progress-log line | Outputs |
| Commit "Send back CH-xxxx: <stage>" with `Intent`, `Change` | Outputs |
| Tell the user the next stage, stop | Outputs |
| Every problem to tests, acceptance, or build, none to the user | Constraints |
| Build only meets an existing line, design spec, or remit rule, inside "Files", plainest fix; no new requirement, line, or code on a change branch | Constraints |
| Requirements `verified`, change `in review`, the pass commit on `Acceptance-Passed:` | Outputs |
| Commit "Verified CH-xxxx" with `Intent`, `Change` | Outputs |
| The gate passes, except `not ready` lines until the last change; the last change has no exception | Constraints |
| Correct each other gate problem; commit "Update CH-xxxx: <what>" | Constraints and Outputs |
| A conflict with main: merge main, `Intent` and `Change`, text of main, statuses of this branch | Constraints and Outputs |
| A mark: `(assumed)`, reason outside, same meaning | Constraints |
| App files changed after the acceptance pass: run again, new commit on `Acceptance-Passed:` | Constraints |
| Propose through the delivery port against the base; the description from `proposal.md`, each section filled | Constraints |
| The eight items of the description | Constraints (the list) |
| The intent `in review` when each change is `in review` or `merged`, on the change branch | Outputs |
| Handoff with the link and what the user must confirm; commit "Propose CH-xxxx" with `Intent`, `Change`, with the intent | Outputs |
| Each commit on a change branch carries `Change` | README "Commits" |
| Tell the tracker; give the user the link | README "Ports" and Outputs |
| Do not merge the change | Goal |

## init

| Old rule | New place |
|---|---|
| Prepare any project; after init all work enters through the inbox | Goal |
| (new) Stop on a model below the Sonnet 5.5 class | Constraints, line 1 |
| The files to copy are in `references/` | Constraints |
| Not a git repository: stop and say so | Constraints |
| `pdlc/` exists: stop, tell the user | Constraints |
| `defaults`: no questions, accept the map, the more common pattern, each recommended answer, list each decision at the end | Constraints and Outputs |
| The contents of `pdlc/`, and `.gitkeep` in each empty folder | Constraints |
| No code: recommend `/decompose`, `/blueprint`, then `/pdlc:intake <name>.blueprint.md`; do not run or wait for them | Constraints |
| ... "Continue with the next step" | removed: procedure |
| Recon thin map; two short lists with code maps; merge, split, rename; boundaries matter | Constraints |
| Map as "Code maps": entry points to jobs; capabilities only shared logic | Constraints |
| A shared file by parts; `: the rest`; each file or part in one map at most; README in no map | Constraints |
| "Unsure" items: not in a spec, in the final summary | Constraints and Outputs |
| Each kept item: a stub spec with summary, code map, "None written yet." | Constraints |
| Two patterns: ask which is the convention; a design spec | Constraints |
| Defaults with `Ask at init: yes`: one question at a time, options, recommendation, `skip` | Constraints |
| A different answer rewrites the rule, `Default: no`; copy without `## Question` | Constraints |
| The six check items in `config.md`, confirmed by the user; examples; a folder outside the check folders; no placeholder left | Constraints |
| The `IN-9999` test that the "all" command skips acceptance files; delete it; retry with a different path | Constraints |
| The visual adapter (`visual-web` with `start` and `url`, or `visual-terminal`) | Constraints |
| `.gitignore`: `pdlc/.tools/` and the check output folders; with no code, the first change adds them | Constraints |
| No way to run checks: tell the user, recommend a first intent | Constraints |
| Show the adapters, ask if the defaults are correct; the defaults; the two tracker adapters; a tracker needs an adapter first, an intent can add it | Constraints |
| Offer the dashboard; yes: `pdlc:dashboard`; `defaults`: no install, tell the user about `/pdlc:dashboard` | Constraints |
| Commit "Set up pdlc" on `main` with only `pdlc/`; no branch; the records live on main | Outputs |
| Tell the user how to start (`/pdlc:ship`, or one stage from `/pdlc:intake`) | Outputs |

## board

| Old rule | New place |
|---|---|
| Make all of the board agree with pdlc in one pass; when to use it | Goal |
| Tracker `none`: tell the user, stop | Constraints |
| A missing setting: name it, stop | Constraints |
| A missing column: list each, stop | Constraints |
| `dry-run` without access: no column check, current column "unknown" | Constraints |
| For each non-cancelled intent and change: ID, name, status, column, `Ticket`, links | Constraints |
| `dry-run`: no change, a table with card key and two columns, stop | Constraints and Outputs |
| Else **show intent**, then **show change** for each change; write new card keys in `Ticket` | Constraints and Outputs |
| A written `Ticket`: commit "Board: record card keys" on main | Outputs |
| Tell the user the counts of made, moved, and unchanged cards | Outputs |
| Only write to the board; do not act on moves of persons | Constraints |
| Do not delete a card | Constraints |
| A cancelled intent: to a `cancelled` column if there is one, else no move | Constraints |

## conventions

| Old rule | New place |
|---|---|
| Keep the software consistent; agree each convention; no change before asking | Goal and Constraints |
| Tell the user the subject and why now, in one or two sentences (the table example) | Constraints |
| Two or three options from the current code, real examples, a recommendation with one line; "Asking questions"; `defaults` takes it | Constraints |
| New: `DES-<name>.md` from the template; changed: edit, `Default: no` | Constraints |
| A checkable convention: `proposed` requirements and an intent for the check | Constraints |
| Find the code that does not obey (two causes), through the code maps | Constraints |
| One intent for each, "Migrate <spec> to <convention>", what changed and a link | Constraints |
| Do not start them; tell the user how many; the user selects when | Constraints and Outputs |
| Commit "Convention DES-<name>", with the `Intent` of a calling skill | Outputs |
| Go back to the calling skill | Outputs |

## dashboard

| Old rule | New place |
|---|---|
| Install the dashboard for this user; files outside the project; ask first | Goal |
| The files are in `references/` | Constraints |
| The three facts, in a short text, in the words of the skill | Constraints |
| "Install the live dashboard?", default no, no install without a clear yes, also with `defaults` | Constraints |
| Make `~/.claude/agents/`; copy the two files; show a difference and ask first | Constraints |
| `~/.claude/CLAUDE.md`: make it; leave a "## Live dashboard" section and say so; else append the rule after a blank line | Constraints |
| `.dashboard/` in `.git/info/exclude` | Constraints |
| Tell what and where; the rule works next session; the style question; a design skill can go | Outputs |
| How to remove it; the saved style folder | Outputs |

## trace

| Old rule | New place |
|---|---|
| Answer in plain words with paths and links | Goal |
| Read the README; change no file | Constraints |
| From code: `git blame`, `git log --follow`, the trailers, each `Req`, the `Intent`, the `Ticket` | Constraints |
| From an intent: requirements and changes with statuses, commits by `Change:`, checks by **find** | Constraints |
| From a requirement: status, intents, checks, commits by `Req:`, their files | Constraints |
| Change folders, and links when they help | Constraints |
| Tell the user each missing link (three examples); a useful finding | Constraints and Outputs |

## Agents, other documents, and version

| Old rule or request | New place |
|---|---|
| Agent bodies | unchanged |
| (new) `model: inherit` | front matter of `builder.md`, `recon.md`, `reviewer.md`, `test-writer.md` |
| (new) No work below the Sonnet 5.5 class, and a reply that says so | first paragraph of each agent body |
| (new) The model requirement | `INSTALL.md` "What you need", `OUTLINE.md` core rule 9 and section 12, root `README.md` pdlc section |
| (new) The declarative skill format | `OUTLINE.md` section 12, root `README.md` pdlc section |
| Version | `plugin.json` 0.3.0 → 0.4.0 |
