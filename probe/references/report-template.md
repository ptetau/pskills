# Probe Report: [app]

*(schema: `app`, `generatedAt` — from `probe-findings.json`)*

**App:** `[app — name or path of the application that was probed]`
**Generated:** `[generatedAt — ISO-8601 timestamp of when this run completed]`

---

## App Summary

*(from Phase 1 Understand — docs/specs read, commit history skimmed, code modules
mapped. 3-6 sentences: what the app is, who it's for, the shape of its architecture,
and the feature flows derived for this run.)*

[one paragraph app summary]

**Feature flows probed:** `[flow]`, `[flow]`, … *(schema: `coverage.flows`)*

---

## Coverage Matrix

*(schema: `coverage.flows` × `coverage.dimensions` — which flow × dimension cells
were actually probed this run. `x` = probed, `-` = skipped/out of scope.)*

| Flow \ Dimension | functional | robustness | security | perf | a11y | ux |
|---|---|---|---|---|---|---|
| `[flow]` | x | x | x | - | x | x |
| `[flow]` | x | x | - | x | - | x |

*(dimension enum, schema: `dimension` — functional \| robustness \| security \| perf \| a11y \| ux)*

---

## Findings

Ranked by severity (`critical` → `high` → `medium` → `low`, schema: `severity`),
grouped by dimension within each tier. Each finding below documents every field of
a `finding` object in `findings.schema.json`: `id`, `flow`, `dimension`, `severity`,
`title`, `description`, `repro`, `evidence`, `verified`, `confidence`.

### Critical

#### [F-001] [title — one-line summary of the surprise or bug]

- **Flow:** `[flow]` · **Dimension:** `[dimension]` · **Severity:** critical
- **Verified:** `[verified — true/false, set by the Phase 3 adversarial pass]`
  · **Confidence:** `[confidence — 0..1]`

[description — what was expected vs what actually happened, and why it matters]

**Repro:**

```
[repro — concrete, ordered steps to reproduce the finding]
```

**Evidence:**

```
[evidence — observed output, error text, log line, response body, or file:line pointer]
```

### High

*(same shape as Critical — one `#### [id] title` block per finding)*

### Medium

*(same shape)*

### Low

*(same shape)*

*(If a tier has no findings, write "None found at this severity." instead of leaving it empty.)*

---

## Surprises vs Docs/Specs

*(Findings where the app's actual behavior contradicts or diverges from what the
docs/specs in Phase 1 claimed — distinct from ordinary bugs because the gap is
between stated intent and observed reality, not just "this is broken.")*

- `[flow]` / `[dimension]`: [what the docs/spec said] vs [what was actually observed] → see `[F-00N]`
- *(or:)* "No surprises vs docs/specs — behavior matched the app's documented intent
  everywhere it was probed."

---

## Appendix: machine-readable findings

The structured twin of this report is `probe-findings.json`, validating against
`probe/references/findings.schema.json`. Every finding above corresponds 1:1 to an
entry in that file's `findings` array.
