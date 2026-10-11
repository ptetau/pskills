---
name: probe
description: >
  Autonomous exploratory tester for a running application. Builds an app map by
  reading docs/specs, commit history, and code modules, and derives user-facing feature
  flows. Then fans out a flow × dimension matrix of read-only probe agents (via a
  Workflow). Each agent first reasons about the code statically, then drives the
  running app non-destructively and records surprises and bugs with repro + evidence.
  An adversarial verify pass drops false positives. Then the skill writes a
  severity-ranked Markdown report plus a machine-readable JSON findings file. Use when
  the user says "/probe" or "probe the app". Use it when the user asks for an
  "exploratory test" or wants to "hunt for bugs". Use it when the user wants an
  autonomous bug hunt against a running app instead of a manual code read.
---

# Probe: Exploratory Tester

## Purpose

`/probe` is an autonomous exploratory tester. Today, finding bugs in an unfamiliar
app means a human reads code by hand and clicks around, hoping to get lucky. `probe`
does four things instead:

1. It reads docs/specs, commit history, and code to build an app map and derive real
   user-facing feature flows.
2. It fans out a **flow × dimension** matrix of probe agents, one per (flow, dimension)
   cell. Each agent reasons statically about the relevant code. Then the agent drives
   the running app to confirm or refute a hypothesis, entirely **read-only**.
3. It adversarially re-examines every raw finding to drop false positives.
4. It writes a severity-ranked human report plus a machine-readable findings file.

`/probe` applies the fan-out + adversarial-verify + cited-synthesis pattern of
[[deep-research]] to application behaviour instead of web sources:

- Fan out many narrow, schema-forced probes instead of one broad pass.
- Verify adversarially before trusting anything.
- Synthesise a single cited artifact. Here, `repro` + `evidence` stand in for
  citations.

## When to Use This Skill

Use `/probe` when:
- The user says `/probe`, "exploratory test this", "hunt for bugs", or "probe the app".
- There's a running (or runnable) application: a web app, API, or CLI. There are also
  specs, docs, or a code history to read that describe its intended behaviour.
- The user wants breadth-first bug hunting across many feature flows and quality
  dimensions (functional, robustness, security, perf, a11y, ux). The user doesn't want
  a deep dive on one already-known issue.

Do **not** use `/probe` when:
- There is no way to run or drive the app at all (pure static review — read the
  code by hand instead, or use `/code-review`).
- The user wants only a security-specific audit. Prefer `security-review`. Then,
  optionally, follow up with `/probe` for broader coverage.
- Progress needs an action beyond passive observation. `probe` never trades
  non-destructiveness for coverage (see the guarantee below).

## The Read-Only Guarantee

**Every probe agent is read-only and non-destructive, with no exceptions.**

Probes may:

- read code and docs;
- issue safe `GET`/read-only requests;
- navigate and read UI state;
- inspect logs and responses.

Probes may **never**:

- submit real transactions;
- create/modify/delete real data;
- send state-mutating requests (`POST`/`PUT`/`PATCH`/`DELETE`) against anything other
  than a designated sandbox/staging environment, or a scratch/test account created for
  this purpose;
- perform any action that a human reviewer wouldn't be comfortable running unattended
  against production.

If only a mutating action can exercise a flow and no safe sandbox exists, the probe
agent for that cell must stop short. The agent records the flow as **"untestable without
write access"** in its finding, and moves on. It must not take the mutating action
anyway. This guarantee is non-negotiable in every phase below, especially Phase 2
(Fan-out).

## Phase 1 — Understand

Goal: build an app map and a list of real user-facing feature flows before probing
anything.

1. **Read docs/specs.** README, CONTRIBUTING, `docs/`, ADRs, OpenAPI/GraphQL specs,
   any `.plan.md` files: anything that states intended behaviour.
2. **Read commit history.** `git log --oneline -50` and recent diffs to see what's
   actively changing (higher bug risk) and what's stable.
3. **Read code modules.** Entry points, routes/controllers, pages/components, data
   models — enough to know how the app is structured and what it talks to.
4. **Synthesise an app map**: a short structural summary (architecture, key
   modules, external dependencies). This summary becomes the report's App Summary.
5. **Derive feature flows**: named, end-to-end user journeys (e.g. "sign up",
   "checkout", "reset password", "export report"). Each flow should be something a
   real user does, not an internal function. Flag which flows look highest-risk
   (recently changed, complex, security-sensitive). Phase 2 (Fan-out) uses these flags
   to budget-scale the matrix.

Output of this phase: the app summary text and an ordered `FLOWS` list, each
optionally tagged with a risk level.

## Phase 2 — Fan-out

Goal: dispatch one read-only probe agent per **(flow, dimension)** cell. Collect their
findings into a single structured array. Author a `Workflow` script for this at
runtime. **Don't** ship a prebuilt `.workflow.js` file in the skill. Generate the script
fresh for the app under test.

The six quality dimensions: `functional`, `robustness`, `security`, `perf`, `a11y`,
`ux` (matches the `dimension` enum in `references/findings.schema.json`).

This is the only fan-out shape this skill uses. Step 1 of `build-probe-skill.plan.md`
(Prove the Workflow fan-out matrix) holds the proof that it works:

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

Each `probePrompt(cell)` tells its agent to do these steps, in order:

1. **Statically map** the code relevant to `cell.flow` for the `cell.dimension` lens.
   Form a concrete hypothesis about where it could break.
2. **Live-drive the running app**, read-only, to confirm or refute that hypothesis.
   Navigate and read for UI flows, make safe `GET`/read calls for APIs, and use
   read-only CLI invocations.
3. Return **one structured finding per cell** via `opts.schema`. Return it even for a
   "nothing surprising found" result, so coverage is provable.

The read-only guarantee applies to every one of these agents.

**Budget-scaled fleet.** Before building `CELLS`, use `budget.remaining()` (and
`budget.total`) to decide the matrix size:

- For a small budget, run the full `functional` + `security` dimensions on every flow.
  Drop `perf`/`a11y`/`ux` for low-risk flows.
- For a generous budget, run the full matrix on every flow.

A follow-up wave may be needed, e.g. to re-probe a cell that an agent returned as
low-confidence. In that case, check `budget.remaining()` again after the fan-out, before
spending more. The Workflow runtime caps concurrency across the fan-out automatically
(about `min(16, cores-2)`). Hand the runtime the whole `CELLS` matrix and let it queue.
Don't chunk the matrix by hand. Never call `Date.now()` or `Math.random()` inside the
script. If a cell needs an identifier, derive it from `flow`/`dimension`/index instead.

## Phase 3 — Verify

Goal: adversarially re-examine every raw finding from Phase 2 (Fan-out). Drop false
positives. This is the same discipline [[deep-research]] applies to unverified claims
before it cites them.

For each raw finding, dispatch (or reason through, budget permitting) an adversarial
pass that actively tries to **disprove** it. The pass does three things:

- It re-checks the `evidence` against the `repro` steps.
- It considers environmental flakiness, or a misreading of expected behaviour.
- If that's cheap and safe, it re-runs the `repro`, read-only.

Set:
- `verified: true` only once the finding survives this adversarial re-check;
- `confidence` (0..1) reflecting how sure the verifier is it's a genuine defect.

If a finding fails verification, either drop it, or keep it with `verified: false` and a
low `confidence`. Mark a kept finding clearly as unconfirmed in the report. Never
silently upgrade a finding to look more certain than the evidence supports.

## Phase 4 — Report

Goal: turn verified findings into one human report and one machine-readable file.

1. Assign each finding a stable `id` (`F-001`, `F-002`, …).
2. Sort by `severity` (`critical` → `high` → `medium` → `low`), grouped by
   `dimension` within each tier.
3. Render `probe-report.md` from `references/report-template.md`. Fill in these parts:
   - the App Summary (from Phase 1, Understand);
   - the Coverage Matrix (flows × dimensions actually probed);
   - every finding block;
   - the "Surprises vs Docs/Specs" section: findings where observed behaviour
     contradicted the docs/specs read in Phase 1, not just ordinary bugs.
4. Write `probe-findings.json` (`{ app, generatedAt, coverage, findings[] }`). It must
   validate against `references/findings.schema.json`. Every finding in the report must
   have a matching entry in this file, and vice versa.

## References

- `references/report-template.md` — the human report shape Phase 4 fills in.
- `references/findings.schema.json` — the JSON Schema `probe-findings.json` must
  validate against; also the contract each probe agent's `schema` option targets.

## Example

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` reads the repo's docs and recent commits. It maps `checkout`, `sign-up`, and
`apply-discount-code` as feature flows. It fans out 18 read-only probe agents (3 flows ×
6 dimensions) against staging. It verifies the 5 raw findings down to 3 confirmed ones.
Then it writes `probe-report.md` (3 findings, ranked, with repro + evidence) and
`probe-findings.json` alongside it.

## Notes

- Not doing (see the Intent in `build-probe-skill.plan.md`):
  - A dogfood run is not part of *building* this skill.
  - Probes never file GitHub issues or open PRs from findings.
  - Probes never get write/mutate access, full stop.
- If there is no safe way to drive the app read-only at all (no sandbox, no safe
  reads), say so. Then stop. Don't guess at what a live run would find.
