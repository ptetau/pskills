# Plan: align decompose, blueprint, and pdlc

**Owner:** Patrick Te Tau · **Status:** Proposal. Nothing in this plan is built.
**Plan location:** `plans/align.plan.md`

## The answer first

| Pair | Verdict | How far |
|---|---|---|
| decompose with blueprint | Go. Already done | One maintenance task: a standalone design file, so that the `--design` check of the worked example runs. |
| blueprint with pdlc | Go, in two steps | Now: the same words, the same marker, the same fault words, and a written hand-off. Then a measured bridge script, if the test in section 5 shows a gain. |
| decompose with pdlc | Not yet. Keep apart | decompose reaches pdlc only through the blueprint. Keep `volatility.py` (git history) and recon (the code map) apart. Add one hint in each direction. |

Ranked options: B (words and a hand-off section, no code) first. Then the test of section 5. Then C (a bridge script), if the test shows a gain. A (change nothing) is a sound fallback while pdlc changes weekly. D (bundle the two skills into the plugin) is not yet. E (one merged skill) is a no-go.

Each claim below says where I read it, or says "inferred". Where two files disagree, the text says so. In the tables, a path such as `templates/job.md` or `defaults/DES-errors.md` is under `plugins/pdlc/skills/init/references/`. A path such as `skills/ready/SKILL.md` or `agents/recon.md` is under `plugins/pdlc/`.

## Words used here

- **Seam**: a place where the output of one tool becomes the input of the next tool.
- **Hand-off**: the act of passing that output, and the text that tells how.
- **Bridge**: a script that turns a blueprint into pdlc spec files, with no re-typing.
- **Invariant**: a rule that must always be true. A blueprint names each invariant, and gives the place that enforces it and its error code.
- **Scenario**: one Gherkin test in a blueprint, in Given, When, and Then steps.
- **Acceptance line**: one "Given …, when …, then …" line under a pdlc requirement.
- **Code map**: the files and parts of files that one pdlc spec owns.
- **Interface**: the section of a pdlc change spec that lists what the checks can call.
- **Remit**: one independent review in pdlc, for example security or quality.
- **Recon**: the read-only pdlc agent that maps an existing codebase.
- **Volatility**: how likely a thing is to change. The decompose skill puts a wall around each volatile thing.
- **Fixture**: a small app and a scripted request that the benchmark runs pdlc on.
- **Arm**: one side of a comparison in the benchmark.
- **Stack**: the change branches of one intent, each built on the one before.
- **Deterministic**: gives the same result each time for the same input.

## 1. The three tools in one table

| | decompose | blueprint | pdlc |
|---|---|---|---|
| Question | Where do the walls go, and what are the bricks? | What exactly gets built? | How does an idea become verified, traceable code? |
| Input | a feature list, or a request plus a host codebase | a `.design.md`, or any architecture text | an intent in the words of the user, plus the project |
| Output | `<name>.design.md`, ten sections | `<name>.blueprint.md`, six sections | `pdlc/specs/` (jobs, capabilities, design specs), intents, change specs, code, checks, a GIF, reviews |
| Units | Clients, Managers, Engines, ResourceAccess, Utilities, bricks, one shared contract | invariants, typed contracts, state machines, components with signatures, scenarios | jobs, capabilities, design specs, requirements with IDs, changes of one spec each |
| IDs | V1, F1, UC1, with the described-IDs rule | none, by design | IN-, CH-, JOB-, CAP-, DES-, and `.Rn` |
| Checker | `check_writing.py` (grade 7, glossary), `volatility.py` | `check_blueprint.py`, with `--design`, `--compile`, `--render` | `check_merge.py`, `make_packets.py`, two hooks, a four-rule writing check |
| Runs | once, at design time | once, after the design | for the life of the project |
| Install | copy to `~/.claude/skills/` | copy to `~/.claude/skills/` | plugin from the marketplace, version 0.2.0 |
| Read in | `decompose/SKILL.md`, `decompose/references/design-template.md` | `blueprint/SKILL.md`, `blueprint/references/blueprint-template.md` | `plugins/pdlc/OUTLINE.md`, `plugins/pdlc/skills/*/SKILL.md`, `plugins/pdlc/.claude-plugin/plugin.json` |

## 2. The seams

### 2.1 decompose to blueprint: already congruent

The two skills share one worked example, one `c4.md`, one writing check, and the same component names. I read this in `blueprint/SKILL.md`, "Inputs and how a design maps", and in `scripts/sync_shared.py`. `check_blueprint.py --design` makes sure that the blueprint keeps each component, verb, brick, contract, and state machine of the design (read in `blueprint/scripts/check_blueprint.py`, `check_design`).

I ran the checker on the worked example. Without `--design`, the result is PASS. With `--design decompose/references/examples.md`, the result is FAIL with three errors. That file holds two designs, and the promotions design has no section in the blueprint. The standalone `notifications.design.md` that `blueprint/SKILL.md` names (the "Example" section) is not in the repository. Thus, the claim that the example passes `--design` is true only against a file that nobody committed (inferred).

The pair needs no other change.

### 2.2 blueprint to pdlc: the main seam

| Blueprint element | pdlc element | Match | Read in |
|---|---|---|---|
| In scope: features in the words of the user | Intent "What and why". Job "Who and why" | Partial. A scope bullet is a feature. A job is one user goal, and holds several features | `blueprint-template.md` §1, `templates/intent.md`, `templates/job.md` |
| Out of scope (non-goals) | none. A line in the "Notes" of the intent at most | Missing | `templates/intent.md` |
| Decisions added by this spec, marked `(assumed)` inline | `(assumed)` inline, "Decided on defaults" in the handoff, "Notes" in the intent, "Assumed" in the proposal | Exact in idea. The form conflicts (conflict 1) | `blueprint/SKILL.md` "The core rule", `templates/handoff.md`, `templates/proposal.md`, `templates/README.md` "Asking questions" |
| Decisions carried from the design | "Notes" of the intent | Partial | `templates/intent.md` |
| `[NEEDS CLARIFICATION]`, three at most | The questions of `ready`, one at a time. With `defaults`, the recommended answer | Partial. pdlc stops only for a contradiction | `skills/ready/SKILL.md` steps 4 and 5, `skills/ship/SKILL.md` step 4 |
| Words used here | none | Missing. The pdlc writing check has no glossary rule | `bin/check_writing.py` of pdlc |
| Invariant: name, one rule, enforcement point, error code | A requirement on the capability that enforces the rule: title, one or two sentences, acceptance lines, a code from `DES-errors` | Partial. The invariant name becomes the requirement title. pdlc adds the `.Rn` number. The enforcement point names the capability | `blueprint-template.md` §2, `templates/capability.md`, `skills/ready/SKILL.md` step 3 |
| Error catalogue: Code, Meaning, Fault, HTTP, Retry helps? | `DES-errors`: Code, Meaning, Whose fault, Retry helps? | Exact shape, minus HTTP. The fault words differ (conflict 2). The blueprint has a row that is "not an error" (conflict 7) | `blueprint-template.md` §3, `defaults/DES-errors.md`, `blueprint/references/notifications.blueprint.md` |
| Typed data contracts | none. The "Interface" of a change gives types for each entry only | Missing. pdlc specs say what must be true, not how to build it | `skills/ready/SKILL.md` step 3, `templates/change.md` |
| State machines, with illegal moves and a code | Acceptance lines on the capability that stores the state | Partial. pdlc records behaviour, not structure | `agents/recon.md`, "A deep look" |
| Module map: one folder for each component | Code map of each job and capability spec | Near exact | `blueprint-template.md` §5, `templates/README.md` "Code maps" |
| C4 container and component diagrams | none | Missing. Keep apart | |
| Engine, ResourceAccess, Utility | Capability: "a store, an outside service, or plumbing that every job uses" | Exact in idea | `skills/intake/SKILL.md` step 2, `OUTLINE.md` §1 |
| Client: entry points | The entry points that each job owns. A shared file is mapped by parts | Partial. One Client serves several jobs | `templates/README.md` "Code maps", `skills/init/SKILL.md` step 2 |
| Manager: the flows of one family of use cases | No unit. Each Manager verb is the flow of one job | Partial (conflict 6) | `OUTLINE.md` rule 4 |
| Domain module: stable rules | Capability | Partial | `decompose/SKILL.md`, "The hybrid" |
| "May call" and the call rules | Rule 4: jobs use capabilities and do not edit them. Capabilities come before jobs | Partial. pdlc has one direction, decompose has four layers | `OUTLINE.md` §2, `skills/change/SKILL.md` step 2 |
| Signatures: typed methods, the codes each can return | "Interface": each entry, its file, in and out with types, each error by its code | Near exact. The blueprint gives no file, only a folder | `templates/change.md`, `blueprint-template.md` §5 |
| Flows: the calls of each Manager method | Steps of a change, one for each requirement | Partial. A step is a requirement, not a call | `templates/change.md` |
| Failure and retry rules | Acceptance lines on the capability | Partial | `skills/ready/SKILL.md` step 2 |
| Internals: the bricks | none | Missing. The builder decides | `agents/builder.md` |
| Scenario: 3 to 5 for the system, concrete values, Then is observable, Outline with Examples | Acceptance lines: one for each case, 25 words or fewer, concrete values, "then" is what a caller sees, edge values | Partial. The same grammar and the same three rules. A different grain: a system against a requirement. An Examples row becomes one line | `blueprint/SKILL.md` Phase 6, `skills/ready/SKILL.md` step 3 |
| Verify command | `config.md` "Checks: all" | Exact in kind. pdlc also needs the "one requirement" command, and the requirement ID in each check name. A scenario has no ID | `templates/config.md`, `defaults/DES-pdlc-check-tagging.md` |
| Done when: scenarios fail first, then pass, old tests still pass | tests stage: each new check must fail. build stage: all checks pass | Exact in idea | `skills/tests/SKILL.md` step 3, `skills/build/SKILL.md` step 3 |
| Writing: one master, grade 7, and a glossary | One master copied into `DES-writing-style`. A four-rule check | Partial (conflict 8) | `scripts/sync_shared.py`, both `check_writing.py` files |

### 2.3 decompose to pdlc, direct

| decompose element | pdlc element | Match | Read in |
|---|---|---|---|
| Core use case: "who does what, and what the system does in response" | Job: "what a user tries to do" | Exact in idea | `decompose/SKILL.md` Phase 1, `OUTLINE.md` §14 |
| Feature list F1, F2, … | The words of the intent | Partial | `templates/intent.md` |
| Volatility register. Name a component for the change that it hides, not for a feature | "Put its boundary around a thing that is likely to change (a vendor, a set of rules, a store). Name the capability for that thing, not for a feature" | Exact in idea, in different words. pdlc already uses the rule of decompose, and does not say so | `decompose/SKILL.md` "Rules", `skills/intake/SKILL.md` step 2 |
| `volatility.py`: hotspots and change coupling from git history | recon: entry points and shared logic, as stub specs with code maps | A different question. decompose asks where the walls must go. recon records where the boundaries are now | `decompose/references/brownfield.md`, `agents/recon.md` |
| Walkthroughs, change simulation, feature assembly | none | Missing. pdlc has no proof of a design | |
| `(assumed)` on proposed features | `(assumed)` | Exact in idea | `decompose/SKILL.md` Phase 0 step 2 |

## 3. Conflicts and gaps

Each item gives the smallest fix. "Owner" marks a decision that only the owner can make.

1. **Marker form.** The blueprint skill writes `*(assumed)*` with emphasis, and `*(assumed; owner: Legal)*` with a reason inside the brackets. The pdlc merge check rejects both forms, and accepts only the plain `(assumed)` with the reason outside. The counter of the blueprint checker also misses the second form, because it counts only the exact text `(assumed)`. I read these in `blueprint/SKILL.md`, in `blueprint-template.md` line 8, in `bin/check_merge.py`, in `templates/README.md`, and in `check_blueprint.py`. The fix: the blueprint skill writes the plain form, in three files.
2. **Fault words.** The blueprint writes "caller", "supplier", "vendor", and mixed values such as "caller data or vendor". `DES-errors` accepts `caller`, `system`, or `outside service` (read in `defaults/DES-errors.md`). The fix: blueprint adopts the three pdlc words, or the bridge maps them. Owner.
3. **The truth.** The blueprint says that a new verb is a design change, and that the design changes first (read in `blueprint/SKILL.md`, "Names stay the same"). The pdlc outline says that the pdlc files are the truth (rule 6). The intake skill says that the newest words win (read in `skills/intake/SKILL.md` step 4). After the hand-off, two truths exist. The fix: the design and the blueprint are frozen inputs that nobody regenerates, and pdlc specs lead after intake. A later design change runs decompose in subsystem mode on the real code, then a new blueprint, then intake again. Owner.
4. **IDs.** The blueprint skill removes the design IDs (read in `check_blueprint.py`, `CRYPTIC_ID`). The intake stage adds the pdlc IDs (read in `defaults/DES-pdlc-ids.md`). The two rules do not collide, because the blueprint comes first and its checker does not match pdlc IDs (inferred from the regex). The trace from a requirement back to its invariant is by name only.
5. **Granularity.** One blueprint of the worked example makes about nine components. In pdlc, that is about five capabilities, three jobs, and one `DES-errors` change. The result is nine changes, each with its four change stages (inferred from the example and from `skills/change/SKILL.md`). One intent holds the stack, and the changes of an intent merge together or not at all (read in `templates/README.md`, "Stacked changes"). With nine changes, nothing merges until the ninth is in review. Owner: one intent for the blueprint, or one intent for each capability group.
6. **Manager home.** A Manager holds the flows of several use cases. In pdlc, each use case is a job, and a job owns its entry handler, so each Manager verb maps to one job. The Manager file becomes a shared file, mapped by parts (read in `templates/README.md` "Code maps"). Owner: accept this rule, or make each Manager a capability.
7. **Non-error rows.** The example catalogue has `QUIET_HOURS_DEFERRED`, "not an error" (read in `notifications.blueprint.md` §3). `DES-errors` holds errors only. The fix: the bridge skips rows whose fault is "—", or the blueprint moves such rows out of the catalogue.
8. **Writing checks.** `scripts/sync_shared.py` keeps three copies of the master `check_writing.py` the same, but the pdlc copy in `skills/init/references/bin/` is not in that list. The pdlc copy is a different program of 419 lines, with four rules: sentence length, NZ spelling, ID alone, and conversation. The copy also has a `--since` option that the master lacks (read in both files, and in the diff that I ran). The master has sixteen rule tags, a reading grade, and a glossary rule, so a blueprint and a pdlc spec obey different checks. The fix: record the fork now. Later, the owner decides whether pdlc specs must meet grade 7 and a glossary, and I recommend no.
9. **Greenfield entry.** `pdlc:init` says: recommend `/decompose` for a new build, and start the first intent with the result (read in `skills/init/SKILL.md` step 2). But intake takes "the words of the user" for "What and why" (read in `skills/intake/SKILL.md` step 1). A design document is not an intent, and the blueprint, not the design, holds the types, codes, and signatures that the "Interface" needs. The fix: init and intake name the blueprint as the input, and intake gets one rule for a `.blueprint.md` path.
10. **Design file.** See section 2.1. The fix: commit the first example alone as `decompose/references/notifications.design.md`, or let the checker select a named design in a file of several. Owner.
11. **Other gaps.** Out of scope, typed contracts, C4 diagrams, and the glossary have no place in pdlc. Out of scope fits the "Notes" of the intent. The contracts go into the code of the first capability change, through the "Interface" and the handoff. The diagrams and the glossary stay in the blueprint.
12. **Brownfield boundaries.** In an existing codebase, decompose runs in subsystem mode, and recon maps the host at init. The two can draw different boundaries for the same code (inferred). The rule: the design decides the walls of the new subsystem, and recon decides the map of the host. Owner.

**Duplicated machinery.** `check_blueprint.py` and `check_merge.py` ask different questions: the shape and the congruence of one document, against the state of a change (read in both files). The pdlc review remits judge code and checks, and the blueprint has only a self-review step. Neither pair is duplicated. The two writing checks are duplicated and drift (conflict 8). `volatility.py` and recon are not duplicated (section 2.3).

## 4. Options

| Option | Value | Cost | Risk | A person with only decompose or blueprint | A person with only pdlc |
|---|---|---|---|---|---|
| A. Change nothing | none now. The three work alone | none | the conflicts stay. Each new pdlc round can widen them | no change | no change |
| B. The same words, a hand-off section, no code | the marker and the fault words agree. Each tool names its next step. A reader can map a blueprint to pdlc specs by hand | about three hours of text, plus a plugin version bump | low. A rule in a skill is often skipped by the model (read in `plans/pdlc-speed.plan.md`, round 3), so B helps people more than the model | one new paragraph in each skill | one new rule in `init` and `intake` |
| C. A bridge: `import_blueprint.py`, an intake rule for a `.blueprint.md`, and the reverse hints | a hand-off with no re-typing. A script is not skipped. The specs start with the names, codes, and signatures that the blueprint decided | one to two days for the script and its tests, plus the test in section 5 | the script decides structure (conflicts 5 and 6). A wrong split costs a round of intake. The stubs are `proposed`, so ready can still change them | no change | one more file in `pdlc/bin/`, used once or not at all |
| D. Bundle the two skills into the plugin as `pdlc:decompose` and `pdlc:blueprint`, and keep the standalone copies | one install, one namespace | about twenty more files for `sync_shared.py`, and a version bump for each skill change | a person with both installs gets two skills that answer "design a system". The plugin changes its identity from a lifecycle to a method | no change | the plugin grows, with skills that most intents do not use |
| E. One merged skill | one story | weeks. New evals, a new benchmark, and the loss of each separate use | high. The three have different rhythms: design once, build once, run for years | loses the skills as they are | loses pdlc as it is |

Why A can be right: pdlc changed in seven rounds in two days (read in `plans/pdlc-speed.plan.md`, the progress log). Nobody asked for the chain, and the value of the chain is unmeasured. Text that nobody tests is a cost too.

Why B first: B fixes the two conflicts that bite as soon as anyone pastes a blueprint into pdlc. These conflicts are the marker and the fault words, and B costs an afternoon.

Why C waits for a measurement: the last seven rounds teach two lessons (read in `plans/pdlc-speed.plan.md`). Measure a component, not a full run. Prefer a script to a rule. The test in section 5 says whether a blueprint makes better specs, before anyone writes the script.

Why not D and E: see the table. The standalone skills also feed `/quiz-plan`, and that path must stay.

## 5. How we would know that alignment helps

### 5.1 The second fixture

The current fixture is `wordfreq`: one job, one capability, a Python command, one change for each run (read in `bench/fixture-app/` and `bench/run_bench.py`). The two design skills have no real work there. The second fixture is a brief, not an app, because the chain starts from words. The brief must not be the notifications example, because both skills ship that example as their worked answer, and the model would copy it (inferred).

The `/vet` suites in `evals/decompose/` and `evals/blueprint/` judge each skill alone, with four prompts and twelve rubric items each (read in the two `suite.json` files). The suites cannot see the hand-off, so the chain needs the bench.

The shape of the brief, as a proposal for the owner:

- A help-desk ticket tool: open a ticket, assign it to a team, close it, and list the open tickets.
- A state machine: open, assigned, closed, with illegal moves that give an error code.
- A store: one JSON file, so that state outlives a run.
- An outside resource: a notifier that tells the team by "email". A stand-in vendor reads an environment variable, so the checks and the GIF need no network.
- Routing rules: which team gets which kind of ticket.
- Python 3 with the standard library and `unittest`, as the harden apps were (read in `plans/harden-pdlc.plan.md`, "Rules for every app"). Then `run_unit_checks` and the visual-terminal adapter work with small changes.

The decompose skill finds about five walls here: a Client, a Manager, a routing Engine, and two ResourceAccess parts (inferred). In pdlc, that is about three jobs and four capabilities, about eight changes, and one stack.

### 5.2 The arms

| Arm | Steps | What it tests |
|---|---|---|
| Alone | `/pdlc:init defaults` on the brief, then `/pdlc:ship defaults <brief>` | pdlc as it is |
| Chain | `/decompose <brief>`, then `/blueprint <name>.design.md`, then `/pdlc:init defaults`, then `/pdlc:ship defaults` with the blueprint as the intent | the full chain |
| Blueprint only (optional) | `/blueprint` from the brief text, then pdlc | what decompose adds |

The chain arm needs the two skills in the project. The bench copies `decompose/` and `blueprint/` into the `.claude/skills/` folder of the project for that arm (inferred from `--setting-sources project,local` in `run_bench.py`).

### 5.3 Two phases

Phase 1 measures the spec stages only. A replay of one stage varies by 10% to 14%, and a full run varies by 35% to 60% (read in `plans/pdlc-speed.plan.md`, "Sections"). Each arm runs intake, ready, and change six times, from the same `pdlc/` folder. Phase 2 runs the full chain and the full alone arm, six times each, only if phase 1 shows a gain.

### 5.4 What to measure

| Measure | How | Read from |
|---|---|---|
| Finish | the change is proposed, and `check_merge.py` prints `ok` on each branch | `inspect_project` in `run_bench.py` |
| Acceptance | a fixed probe set from the brief, about 25 probes, run on the tip | a new `probes.py` for the fixture |
| Rework between stages | the count of `Send back`, `Update CH-`, and `Stop` commits, and of `Lock tests` commits after the first. The highest `round <n>` in the `Verify` subjects | `git log --format=%s` |
| Guesses | the count of `(assumed)` in the specs and the change specs. The count of `(assumed)` entries in "Interface" | the spec files |
| Spec stability | requirements that change after `Ready`, and questions left open | `git log -p` on `pdlc/specs/` |
| Structure | the number of changes, capabilities before jobs, and a congruence score: blueprint components found as pdlc specs and code maps | a small deterministic script, like `check_design` in `check_blueprint.py` |
| Review rounds and cost | `verify_rounds`, `cost_usd`, `wall_s`, split by stage | the result file |
| Writing | the findings that a run leaves | `writing_findings` in `run_bench.py` |
| Defects caught | planted defects, three for this fixture: an illegal move that passes, a vendor error with no retry, a dropped notice | `bench/seeds/`, in phase 2 |

The gate of `run_bench.py` already judges finish, probes, checks, planted defects, cost, and writing (read in `run_bench.py`, `gate`). The rework and structure measures are new.

### 5.5 Runs and cost

| Phase | Runs | Cost for each run | Total | Wall time |
|---|---|---|---|---|
| 1. Spec stages | 6 decompose and blueprint runs, then 6 spec-stage runs for each arm | about $3 for a design and a blueprint (inferred, not measured). About $0.70 for the three spec stages (read in `plans/pdlc-speed.plan.md`, the stage table) | about $30 | half a day |
| 2. Full runs | 6 for each arm | about $10 for eight changes, from $0.85 to $1.55 for each change in the reference runs (inferred from `bench/reference.json`) | about $150, up to $200 with repeats | one to two days, with the runs in parallel |

The gate asks for five runs on each side, and six are better (read in `run_bench.py`, `min_runs`). The run budget in `run_experiment.py` is $8 a run (read in `load_spec`). Phase 2 must raise it to about $25.

### 5.6 What it takes to build

| Work | Files | Effort |
|---|---|---|
| Parametrise the harness: fixture folder, brief, probes, checks command, snapshot anchors | `bench/run_bench.py` (`FIXTURE`, `INTENT`, `PROBES`, `SAMPLE`, `CHANGE_BRANCH`, `STAGE_REPLAY`, `run_unit_checks`, `run_probes`), `bench/run_experiment.py`, `bench/test_bench.py` | one to two days. The fixture is hard-coded in about ten places (read in `run_bench.py`) |
| The brief, the probes, and the `pdlc/` folder from `init defaults` | `bench/fixtures/helpdesk/brief.md`, `probes.py`, `pdlc/` | half a day |
| The chain arm: copy the two skills into the project, then run decompose and blueprint first | `bench/run_bench.py` | half a day |
| The rework and structure measures | `bench/run_bench.py`, `bench/test_bench.py` | half a day |
| Planted defects | `bench/seeds/helpdesk/` | half a day, phase 2 only |

### 5.7 How the fixture widens the evidence for pdlc

The evidence for pdlc rests on one fixture with one change (read in `plans/pdlc-speed.plan.md`, "What we accept"). The second fixture exercises, inside the measured harness, the rules that the harden rounds found weak (read in `plans/harden-pdlc.plan.md`, "Still open"):

- A stack of changes that merge together.
- Capabilities before jobs.
- A shared file mapped by parts.
- A clock or vendor seam, and a stand-in for an outside service.
- A state machine with illegal moves.

The alone arm is also a second baseline for every later pdlc round, whatever the chain shows.

## 6. Recommendation

### 6.1 Verdict for each pair

| Pair | Verdict | Reason |
|---|---|---|
| decompose with blueprint | Go. Done, with one maintenance task | the same example, the same terms, one checker for congruence. Only the standalone design file is missing |
| blueprint with pdlc | Go, in two steps | the signatures match the "Interface" almost word for word. The error table matches `DES-errors`. The scenarios and the acceptance lines share their grammar and their three rules. The two conflicts of form are cheap |
| decompose with pdlc | Not yet. Keep apart | the ideas already agree (the naming rule). The outputs do not: a design has no types, codes, or signatures, and pdlc needs them. decompose reaches pdlc through the blueprint. `volatility.py` and recon answer different questions |

### 6.2 Steps, in order

| Step | What | Effort | Cost | Owner decision |
|---|---|---|---|---|
| 1 | Option B: the words, the marker, the fault words, the hand-off text, a version bump to 0.2.1 | three hours | none | decisions 1, 2, and 3 |
| 2 | The maintenance task of the first pair: the standalone design file | one hour | none | decision 6 |
| 3 | Parametrise the harness, and build the second fixture with the alone arm | two days | about $5 for one trial run | the brief |
| 4 | Phase 1: the spec-stage comparison | one day | about $30 | the gain that counts |
| 5 | Option C: the bridge script, if phase 1 shows a gain | one to two days | none | decision 7 |
| 6 | Phase 2: full runs, chain against alone | two days | about $150 to $200 | go or stop |
| 7 | Decide on D after phase 2 | | | |

### 6.3 Decisions for the owner

1. The truth after the first build: pdlc specs lead, and the design and the blueprint are frozen inputs. I recommend yes.
2. The fault words: blueprint adopts `caller`, `system`, and `outside service`. I recommend yes.
3. The Manager rule: each Manager verb is one job, and the code map names the parts of the Manager file. I recommend yes, and the test checks it.
4. One intent for a blueprint, or one intent for each capability group. I recommend one intent for the first test, and a measurement of the stack.
5. The fixture domain, and whether to spend about $200 on phase 2.
6. The standalone design file, or a checker option that selects one design in a file of several.
7. Where the bridge script lives: `pdlc/bin/`, which init copies into each project, or the plugin only.
8. Whether pdlc specs must meet grade 7 and a glossary. I recommend no.
9. Whether the marker change in blueprint needs a `/vet` run. The change is one token in three places. I recommend "not measured" in the pull request, as `AGENTS.md` asks.

### 6.4 The first three tasks

Each task is one pull request that an agent can do in this repository.

**Task 1. Write the hand-off text (option B).**

- Add a section "The chain: decompose, blueprint, pdlc" to `README.md`, with the table of section 2.2 in short form.
- In `decompose/SKILL.md`, Phase 6 step 4, and in `decompose/references/design-template.md` §10, add the pdlc step after the blueprint step.
- In `blueprint/SKILL.md`, Phase 7 step 4, add `/pdlc:intake <name>.blueprint.md` as a next step, when pdlc is installed.
- In `plugins/pdlc/skills/init/SKILL.md` step 2, name the blueprint, not the design, as the input of the first intent.
- In `plugins/pdlc/skills/intake/SKILL.md` step 1, add one rule: if the user names a `.blueprint.md`, read the file as the words of the intent.
- In `plugins/pdlc/OUTLINE.md`, add a short section "Before the first intent" with the mapping of section 2.2.
- Change the marker in `blueprint/SKILL.md`, `blueprint/references/blueprint-template.md`, and `blueprint/references/notifications.blueprint.md` to the plain `(assumed)`. Put any reason outside the brackets.
- Change the fault words in the same three files to `caller`, `system`, and `outside service`.
- Set the version in `plugins/pdlc/.claude-plugin/plugin.json` to 0.2.1.
- Run `python3 improve-writing/scripts/check_writing.py` on each changed file, and run `python3 blueprint/scripts/check_blueprint.py blueprint/references/notifications.blueprint.md`. Then run the five test commands in `AGENTS.md`.

**Task 2. Make the `--design` example reproducible.**

- Write `decompose/references/notifications.design.md` from the first example in `decompose/references/examples.md`, in the shape of `design-template.md`.
- Run `python3 blueprint/scripts/check_blueprint.py blueprint/references/notifications.blueprint.md --design decompose/references/notifications.design.md` until it prints PASS.
- Point the "Source design" line of the blueprint, and the "Example" section of `blueprint/SKILL.md`, at the new file.
- If the owner prefers one examples file, add a `--design-name` option to the checker instead.

**Task 3. Parametrise the harness for a second fixture.**

- Move `FIXTURE`, `INTENT`, `SAMPLE`, `PROBES`, `CHANGE_BRANCH`, `STAGE_REPLAY`, and the checks command out of `bench/run_bench.py`, into `bench/fixtures/wordfreq/fixture.json` and `bench/fixtures/wordfreq/probes.py`.
- Keep `wordfreq` as the default, so that each existing result file still gates.
- Add `--fixture <name>` to `e2e`, `init-fixture`, `stage`, `seeds`, and `recheck`, and a `fixture` field to the spec of `run_experiment.py`.
- Add the rework and structure measures to `inspect_project`, with tests in `bench/test_bench.py`.
- Run `python3 bench/test_bench.py`. Do not run `e2e`, `seeds`, or `stage` in this task.

## Progress log

Nothing is done yet. This file is the proposal.
