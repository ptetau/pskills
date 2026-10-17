---
name: probe
description: >
  Autonomous exploratory tester for a running application. Reads the docs and specs, the
  commit history, and the code modules, and makes an app map. Then identifies the
  user-facing feature flows. Then uses a Workflow to start a flow × dimension matrix of
  read-only probe agents. Each probe agent examines the code statically, then drives the
  running app live in a non-destructive way. The agent records surprises and bugs with
  repro steps and evidence. An adversarial verify pass removes the false positives.
  Then the skill writes a Markdown report, ranked by severity, and a machine-readable
  JSON file of findings. Use when the user says "/probe", asks for an "exploratory
  test", wants to "hunt for bugs", or says "probe the app". Also use when the user wants
  an autonomous bug hunt against a running app instead of a manual code read.
---

# Probe: Exploratory Tester

## Purpose

`/probe` is an autonomous exploratory tester. At this time, to find bugs in an
unfamiliar app, a person reads the code by hand. Then the person clicks around and hopes
for luck. `probe` does these four steps instead:

1. `probe` reads the docs and specs, the commit history, and the code. From these
   sources, `probe` makes an app map and identifies the real user-facing feature flows.
2. `probe` starts a **flow × dimension** matrix of probe agents (a fan-out), with one
   agent for each (flow, dimension) cell. Each agent first examines the related code
   statically. Then the agent drives the running app live to show that a hypothesis is
   true or false. All the work is **read-only**.
3. `probe` examines each raw finding again, as an adversary, and drops the false
   positives.
4. `probe` writes a human report, ranked by severity, and a machine-readable file of
   findings.

`probe` uses the pattern of [[deep-research]]: fan-out, adversarial verify, and cited
synthesis. But `probe` applies the pattern to the behaviour of an application, not to web
sources. The pattern has these three parts:

- Many narrow probes, each with a forced schema, instead of one broad pass.
- An adversarial check of each result before the skill trusts the result.
- One cited artifact at the end. In `probe`, `repro` and `evidence` replace the
  citations.

## Writing

Write all text to `references/writing-guidelines.md`. This includes the replies to the
user, each question, and each file that this skill writes.

## When to Use This Skill

Use `/probe` in these conditions:

- The user says `/probe`, "exploratory test this", "hunt for bugs", or "probe the app".
- There is a running or runnable application: a web app, an API, or a CLI. There are
  also specs, docs, or a code history that tell the intended behaviour of the
  application.
- The user wants a breadth-first bug hunt across many feature flows and quality
  dimensions (functional, robustness, security, perf, a11y, ux). The user does not want
  to examine one known issue deeply.

Do **not** use `/probe` in these conditions:

- There is no way to run or drive the app (a pure static review). For a static review,
  read the code by hand, or use `/code-review`.
- The user wants only a security audit. Prefer `security-review`. You can then use
  `/probe` after `security-review` for broader coverage.
- To continue the work, the skill must do an action that is more than passive
  observation. `probe` does not do a destructive action to get more coverage, at any
  time. Read the guarantee below.

## The Read-Only Guarantee

**Each probe agent is read-only and non-destructive. There are no exceptions.**

A probe agent can do these actions:

- Read code and docs.
- Send safe `GET` requests and other read-only requests.
- Navigate the UI and read the UI state.
- Examine logs and responses.

A probe agent must **not** do these actions, at any time:

- Submit real transactions.
- Create, change, or delete real data.
- Send state-mutating requests (`POST`/`PUT`/`PATCH`/`DELETE`), except to one of these
  targets:
  - A designated sandbox or staging environment.
  - A scratch or test account made for this purpose.
- Do any action that a human reviewer is not comfortable to run unattended against
  production.

If only a mutating action can exercise a flow, and no safe sandbox exists, the probe
agent for that cell must stop before the action. The agent must record the flow as
**"untestable without write access"** in its finding. Then the agent goes to the next
cell. Even then, the agent must not do the mutating action.

This guarantee applies with no exceptions in each phase below, and especially in
Phase 2.

## Phase 1 — Understand

Goal: make an app map and a list of real user-facing feature flows before you probe the
app.

1. **Read docs/specs.** Read the README, CONTRIBUTING, `docs/`, ADRs, OpenAPI/GraphQL
   specs, and each `.plan.md` file. Also read any other text that gives the intended
   behaviour.
2. **Read commit history.** Read `git log --oneline -50` and the recent diffs. Find the
   parts that change actively (a higher bug risk), and the parts that are stable.
3. **Read code modules.** Read the entry points, routes/controllers, pages/components,
   and data models. Read sufficient code to know the structure of the app and the
   systems that the app connects to.
4. **Synthesise an app map.** Write a short summary of the structure: the architecture,
   the key modules, and the external dependencies. This summary becomes the App Summary
   of the report.
5. **Identify feature flows.** A feature flow is a named, end-to-end user journey, for
   example "sign up", "checkout", "reset password", or "export report". Try to make each
   flow something that a real user does, not an internal function. Flag the flows that
   have the highest risk: flows that changed recently, complex flows, and
   security-sensitive flows. Phase 2 uses these flags to scale the matrix to the budget.

Output of this phase: the text of the app summary, and an ordered `FLOWS` list. Each
flow in the list can have a tag with a risk level.

## Phase 2 — Fan-out

Goal: dispatch one read-only probe agent for each **(flow, dimension)** cell. Then
collect the findings of the agents into one structured array.

Write a `Workflow` script at runtime for this fan-out. **Do not** ship a prebuilt
`.workflow.js` file in the skill. Generate a new script for each app that you probe.

There are six quality dimensions: `functional`, `robustness`, `security`, `perf`,
`a11y`, and `ux`. These six values are the same as the `dimension` enum in
`references/findings.schema.json`.

This shape was proven directly (see the plan's step 1 fan-out proof). This skill uses
only this fan-out shape:

```js
export const meta = {
  name: 'probe-run',
  description: 'Fan out a flow x dimension matrix of read-only probe agents',
  phases: [{ title: 'Probe', detail: 'one agent per flow x dimension cell' }],
}

// FLOWS from Phase 1 (optionally risk-tagged); DIMENSIONS is the fixed six above
const CELLS = FLOWS.flatMap((flow) =>
  DIMENSIONS.map((dimension) => ({ flow, dimension })),
)

phase('Probe')
log(`fan-out: ${CELLS.length} cells (${FLOWS.length} flows x ${DIMENSIONS.length} dimensions)`)

const raw = await parallel(
  CELLS.map((cell) => () =>
    agent(probePrompt(cell), {
      label: `probe:${cell.flow}/${cell.dimension}`,
      phase: 'Probe',
      schema: FINDING_SCHEMA, // shape mirrors references/findings.schema.json's finding
    }),
  ),
)

const findings = raw.filter(Boolean) // merge the barrier's results into one array
return { findings }
```

Each `probePrompt(cell)` tells its agent to do these steps, in this order:

1. **Statically map** the code that relates to `cell.flow`. Use `cell.dimension` as the
   lens. Then make a concrete hypothesis about where the code of the flow could break.
2. **Live-drive the running app**, read-only, to show that the hypothesis is true or
   false. For UI flows, navigate and read. For APIs, use safe `GET` calls and other read
   calls. For a CLI, use read-only invocations.
3. Return **one structured finding for each cell** through `opts.schema`. Return a
   finding also for a "nothing surprising found" result, so that the coverage is
   provable.

The read-only guarantee applies to each of these agents.

**Budget-scaled fleet.** Before you build `CELLS`, use `budget.remaining()` (and
`budget.total`) to select the size of the matrix:

- For a small budget, run the `functional` and `security` dimensions on each flow. For
  low-risk flows, drop `perf`, `a11y`, and `ux`.
- For a large budget, run the full matrix on each flow.

If a follow-up wave is necessary after the fan-out, read `budget.remaining()` again
before you spend more. For example, a follow-up wave can probe again a cell that an agent
returned as low-confidence.

The Workflow runtime automatically limits the number of agents that run at the same
time to about `min(16, cores-2)`. Give the full `CELLS` matrix to the runtime, and let
the runtime put the cells in a queue. Do not divide the matrix into chunks manually.

Do not call `Date.now()` or `Math.random()` in the script. If a cell needs an
identifier, make the identifier from `flow`/`dimension`/index instead.

## Phase 3 — Verify

Goal: examine each raw finding from Phase 2 again, as an adversary, and drop the false
positives. The [[deep-research]] skill applies the same discipline to unverified claims
before it cites the claims.

For each raw finding, dispatch (or reason through, budget permitting) an adversarial
pass. The adversarial pass actively tries to **disprove** the finding:

- Examine the `evidence` again against the `repro` steps.
- Consider environmental flakiness or a misreading of the expected behaviour as a
  possible cause.
- If a read-only run of the `repro` is cheap and safe, run the `repro` again.

Then set these fields:

- `verified: true`, only when the finding survives this adversarial re-check.
- `confidence` (0..1): how sure the verifier is that the finding is a genuine defect.

If a finding fails verification, do one of these two things:

- Drop the finding.
- Keep the finding with `verified: false` and a low `confidence`. In the report, mark
  the finding clearly as unconfirmed.

Do not silently upgrade a finding to look more certain than its evidence shows.

## Phase 4 — Report

Goal: make one human report and one machine-readable file from the verified findings.

1. Give each finding a stable `id` (`F-001`, `F-002`, …).
2. Sort the findings by `severity` (`critical` → `high` → `medium` → `low`). In each
   tier, group the findings by `dimension`.
3. Render `probe-report.md` from `references/report-template.md`. Write these parts:
   - The App Summary, from Phase 1.
   - The Coverage Matrix: the flows × dimensions that the run actually probed.
   - Each finding block.
   - The "Surprises vs Docs/Specs" section. This section gives the findings where the
     observed behaviour contradicted the docs/specs that you read in Phase 1. These
     findings are different from ordinary bugs.
4. Write `probe-findings.json` (`{ app, generatedAt, coverage, findings[] }`). Make
   sure that `probe-findings.json` validates against `references/findings.schema.json`.
   Each finding in the report must match an entry in `probe-findings.json`. Each entry
   in `probe-findings.json` must match a finding in the report.

## References

- `references/report-template.md`: the shape of the human report that Phase 4 completes.
- `references/findings.schema.json`: the JSON Schema that `probe-findings.json` must
  validate against. This schema is also the contract for the `schema` option of each
  probe agent.

## Example

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` reads the docs and the recent commits of the repo. Then `probe` maps
`checkout`, `sign-up`, and `apply-discount-code` as feature flows. `probe` starts 18
read-only probe agents (3 flows × 6 dimensions) against staging. The verify pass
examines the 5 raw findings and keeps 3 confirmed findings. Then `probe` writes
`probe-report.md` (3 ranked findings, with repro and evidence) and `probe-findings.json`
next to the report.

## Notes

- Not doing (see the plan's Intent):
  - A dogfood run is not part of *building* this skill.
  - Probes do not file GitHub issues or open PRs from findings, at any time.
  - Probes do not get write or mutate access. There are no exceptions.
- If you cannot drive the app safely and read-only at all (no sandbox, no safe reads),
  tell the user and stop. Do not guess what a live run would find.
