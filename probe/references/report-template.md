# Probe Report: [app]

*(schema: `app`, `generatedAt` — from `probe-findings.json`)*

**App:** `[app — name or path of the application that was probed]`
**Generated:** `[generatedAt — ISO-8601 timestamp of when this run completed]`

---

## App Summary

*(Source: Phase 1 Understand. The run read the docs/specs, skimmed the commit history,
and mapped the code modules. Write 3-6 sentences. Tell what the app is and who the app
is for. Also give the shape of its architecture and the feature flows that the run
identified.)*

[one paragraph app summary]

**Feature flows probed:** `[flow]`, `[flow]`, … *(schema: `coverage.flows`)*

---

## Coverage Matrix

*(schema: `coverage.flows` × `coverage.dimensions`. The matrix shows the flow × dimension
cells that this run actually probed. `x` = probed, `-` = skipped/out of scope.)*

| Flow \ Dimension | functional | robustness | security | perf | a11y | ux |
|---|---|---|---|---|---|---|
| `[flow]` | x | x | x | - | x | x |
| `[flow]` | x | x | - | x | - | x |

*(dimension enum, schema: `dimension` — functional \| robustness \| security \| perf \| a11y \| ux)*

---

## Findings

This report ranks the findings by severity (`critical` → `high` → `medium` → `low`,
schema: `severity`). In each tier, the report groups the findings by dimension. Each
finding below gives each field of a `finding` object in `findings.schema.json`: `id`,
`flow`, `dimension`, `severity`, `title`, `description`, `repro`, `evidence`,
`verified`, `confidence`.

### Critical

#### [F-001] [title — one-line summary of the surprise or bug]

- **Flow:** `[flow]` · **Dimension:** `[dimension]` · **Severity:** critical
- **Verified:** `[verified — true/false, set by the Phase 3 adversarial pass]`
  · **Confidence:** `[confidence — 0..1]`

[description — what was expected vs what actually happened, and why the finding is important]

**Repro:**

```
[repro — concrete, ordered steps to reproduce the finding]
```

**Evidence:**

```
[evidence — observed output, error text, log line, response body, or file:line pointer]
```

### High

*(same shape as Critical: one `#### [id] title` block for each finding)*

### Medium

*(same shape)*

### Low

*(same shape)*

*(If a tier has no findings, write "None found at this severity." Do not keep the tier empty.)*

---

## Surprises vs Docs/Specs

*(Give each finding where the actual behaviour of the app contradicts or diverges from
the docs/specs of Phase 1. These findings are different from ordinary
bugs. The gap is between the stated intent and the observed reality, not only "this is
broken.")*

- `[flow]` / `[dimension]`: [what the docs/spec said] vs [what was actually observed] → see `[F-00N]`
- *(or:)* "No surprises vs docs/specs — behaviour matched the app's documented intent
  everywhere it was probed."

---

## Appendix: machine-readable findings

The structured twin of this report is `probe-findings.json`. This file validates against
`probe/references/findings.schema.json`. Each finding above corresponds 1:1 to an entry
in the `findings` array of `probe-findings.json`.
