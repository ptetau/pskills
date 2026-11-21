# `/probe` — Exploratory Tester

`/probe` does autonomous, exploratory bug hunting in a running app. First, `probe` reads
the docs and specs, the commit history, and the code. From these sources, `probe` builds
an app map and derives the user-facing feature flows. Then `probe` starts a **flow ×
dimension** matrix of read-only probe agents (a fan-out, through a `Workflow`). Each agent
first examines the code statically. Then the agent drives the live app with no
destructive action, and records surprises and bugs with a repro and evidence.

An adversarial verify pass removes the false positives. Then `probe` writes a Markdown
report, ranked by severity, and a machine-readable JSON findings file.

Each probe agent is strictly read-only. A probe agent must not change the target app.

**Example**

```
/probe the staging checkout flow at https://staging.example.com
```

`probe` maps `checkout`, `sign-up`, and `apply-discount-code` as feature flows. Then
`probe` starts one read-only agent for each (flow, quality-dimension) cell. The quality
dimensions are functional, robustness, security, perf, a11y, and ux. Then `probe` runs the
adversarial verify pass on the raw findings, and writes these two files:

- `probe-report.md`: the ranked findings, with a repro and evidence for each finding.
- `probe-findings.json`: the findings, which validate against
  `probe/references/findings.schema.json`.
