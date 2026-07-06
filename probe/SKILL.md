---
name: probe
description: >
  Autonomous exploratory tester for a running application. Builds an app map by
  reading docs/specs, commit history, and code modules, derives user-facing feature
  flows, then fans out a flow × dimension matrix of read-only probe agents (via a
  Workflow) that statically reason about the code and then live-drive the running
  app non-destructively, recording surprises and bugs with repro + evidence. An
  adversarial verify pass drops false positives before writing a severity-ranked
  Markdown report plus a machine-readable JSON findings file. Use when the user
  says "/probe", asks for an "exploratory test", wants to "hunt for bugs", says
  "probe the app", or wants an autonomous bug hunt against a running app instead of
  a manual code read.
---

# Probe: Exploratory Tester

## Purpose

`/probe` is an autonomous exploratory tester. Today, finding bugs in an unfamiliar
app means a human reads code by hand and clicks around hoping to get lucky. `probe`
instead: (1) reads docs/specs, commit history, and code to build an app map and
derive real user-facing feature flows; (2) fans out a **flow × dimension** matrix of
probe agents — one per (flow, dimension) cell — that each statically reason about
the relevant code, then live-drive the running app to confirm or refute a
hypothesis, entirely **read-only**; (3) adversarially re-examines every raw finding
to drop false positives; (4) writes a severity-ranked human report plus a
machine-readable findings file.

It is the fan-out + adversarial-verify + cited-synthesis pattern of [[deep-research]]
applied to application behavior instead of web sources: fan out many narrow,
schema-forced probes instead of one broad pass, then verify adversarially before
trusting anything, then synthesize a single cited artifact — here, `repro` +
`evidence` stand in for citations.

## When to Use This Skill

Use `/probe` when:
- The user says `/probe`, "exploratory test this", "hunt for bugs", or "probe the app".
- There's a running (or runnable) application — web app, API, or CLI — and specs,
  docs, or a code history to read that describe its intended behavior.
- The user wants breadth-first bug hunting across many feature flows and quality
  dimensions (functional, robustness, security, perf, a11y, ux), not a deep dive on
  one already-known issue.

Do **not** use `/probe` when:
- There is no way to run or drive the app at all (pure static review — read the
  code by hand instead, or use `/code-review`).
- The user wants a security-specific audit only — prefer `security-review`, then
  optionally follow up with `/probe` for broader coverage.
- Any action beyond passive observation is required to make progress. `probe` never
  trades non-destructiveness for coverage — see the guarantee below.

## The Read-Only Guarantee

**Every probe agent is read-only and non-destructive, with no exceptions.** Probes
may: read code and docs, issue safe `GET`/read-only requests, navigate and read UI
state, inspect logs and responses. Probes may **never**: submit real transactions,
create/modify/delete real data, send state-mutating requests (`POST`/`PUT`/`PATCH`/
`DELETE`) against anything other than a designated sandbox/staging environment or a
scratch/test account created for this purpose, or perform any action a human
reviewer wouldn't be comfortable running unattended against production. If a flow
can only be exercised by a mutating action and no safe sandbox exists, the probe
agent for that cell must stop short, record the flow as **"untestable without write
access"** in its finding, and move on — it must not take the mutating action anyway.
This guarantee is non-negotiable in every phase below, especially Phase 2.

## Phase 1 — Understand

Goal: build an app map and a list of real user-facing feature flows before probing
anything.

1. **Read docs/specs.** README, CONTRIBUTING, `docs/`, ADRs, OpenAPI/GraphQL specs,
   any `.plan.md` files — anything that states intended behavior.
2. **Read commit history.** `git log --oneline -50` and recent diffs to see what's
   actively changing (higher bug risk) and what's stable.
3. **Read code modules.** Entry points, routes/controllers, pages/components, data
   models — enough to know how the app is structured and what it talks to.
4. **Synthesize an app map**: a short structural summary (architecture, key
   modules, external dependencies) — this becomes the report's App Summary.
5. **Derive feature flows**: named, end-to-end user journeys (e.g. "sign up",
   "checkout", "reset password", "export report"). Each flow should be something a
   real user does, not an internal function. Flag which flows look highest-risk
   (recently changed, complex, security-sensitive) — Phase 2 uses this to
   budget-scale the matrix.

Output of this phase: the app summary text and an ordered `FLOWS` list, each
optionally tagged with a risk level.

## Phase 2 — Fan-out

Goal: dispatch one read-only probe agent per **(flow, dimension)** cell and collect
their findings into a single structured array. Author a `Workflow` script at
runtime for this — **do not** ship a prebuilt `.workflow.js` file in the skill;
this is generated fresh for the app being probed.

The six quality dimensions: `functional`, `robustness`, `security`, `perf`, `a11y`,
`ux` (matches the `dimension` enum in `references/findings.schema.json`).

This shape was proven directly (see the plan's step 1 fan-out proof) and is the
only fan-out shape this skill uses:

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

Each `probePrompt(cell)` instructs its agent to, in order: (a) **statically map**
the code relevant to `cell.flow` for the `cell.dimension` lens and form a concrete
hypothesis about where it could break; (b) **live-drive the running app**,
read-only, to confirm or refute that hypothesis (navigate/read for UI flows, safe
`GET`/read calls for APIs, read-only CLI invocations); (c) return **one structured
finding per cell** via `opts.schema` — even a "nothing surprising found" result, so
coverage is provable. The read-only guarantee applies to every one of these agents.

**Budget-scaled fleet.** Before building `CELLS`, use `budget.remaining()` (and
`budget.total`) to decide the matrix size: for a small budget, run the full
`functional` + `security` dimensions on every flow but drop `perf`/`a11y`/`ux` for
low-risk flows; for a generous budget, run the full matrix on every flow. Check
`budget.remaining()` again after the fan-out if a follow-up wave is needed (e.g.
re-probing a cell an agent returned as low-confidence) before spending more.
Concurrency across the fan-out is auto-capped by the Workflow runtime (about
`min(16, cores-2)`) — hand it the whole `CELLS` matrix and let it queue; don't
manually chunk it. Never call `Date.now()` or `Math.random()` inside the script —
if a cell needs an identifier, derive it from `flow`/`dimension`/index instead.

## Phase 3 — Verify

Goal: adversarially re-examine every raw finding from Phase 2 and drop false
positives, the same discipline [[deep-research]] applies to unverified claims
before it will cite them.

For each raw finding, dispatch (or reason through, budget permitting) an adversarial
pass that actively tries to **disprove** it: re-check the `evidence` against the
`repro` steps, consider environmental flakiness or misreading of expected behavior,
and re-run the `repro` read-only if that's cheap and safe. Set:
- `verified: true` only once the finding survives this adversarial re-check;
- `confidence` (0..1) reflecting how sure the verifier is it's a genuine defect.

Findings that fail verification are either dropped or kept with `verified: false`
and a low `confidence` and clearly marked as unconfirmed in the report — never
silently upgraded to look more certain than the evidence supports.

## Phase 4 — Report

Goal: turn verified findings into one human report and one machine-readable file.

1. Assign each finding a stable `id` (`F-001`, `F-002`, …).
2. Sort by `severity` (`critical` → `high` → `medium` → `low`), grouped by
   `dimension` within each tier.
3. Render `probe-report.md` from `references/report-template.md` — fill in the App
   Summary (from Phase 1), the Coverage Matrix (flows × dimensions actually
   probed), every finding block, and the "Surprises vs Docs/Specs" section (findings
   where observed behavior contradicted the docs/specs read in Phase 1, not just
   ordinary bugs).
4. Write `probe-findings.json` — `{ app, generatedAt, coverage, findings[] }` —
   validating against `references/findings.schema.json`. Every finding in the
   report must have a matching entry in this file and vice versa.

## References

- `references/report-template.md` — the human report shape Phase 4 fills in.
- `references/findings.schema.json` — the JSON Schema `probe-findings.json` must
  validate against; also the contract each probe agent's `schema` option targets.

## Example

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` reads the repo's docs and recent commits, maps `checkout`, `sign-up`, and
`apply-discount-code` as feature flows, fans out 18 read-only probe agents (3 flows
× 6 dimensions) against staging, verifies the 5 raw findings down to 3 confirmed
ones, and writes `probe-report.md` (3 findings, ranked, with repro + evidence) and
`probe-findings.json` alongside it.

## Notes

- Not doing (see the plan's Intent): no dogfood run is part of *building* this
  skill; probes never file GitHub issues or open PRs from findings; probes are
  never given write/mutate access, full stop.
- If the app can't be safely driven read-only at all (no sandbox, no safe reads),
  say so and stop rather than guessing at what a live run would find.
