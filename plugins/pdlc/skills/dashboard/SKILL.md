---
name: dashboard
description: >
  Installs the optional live dashboard of pdlc. The dashboard-builder agent keeps one HTML
  page with tasks, questions for the user, deliverables, and anything that is stuck. A
  rule in the CLAUDE.md of the user tells each session to use the dashboard for all work
  in progress. Installs only after the user says yes. Use when the
  user says "/pdlc:dashboard", asks for a live dashboard, or says yes to the dashboard
  during pdlc init.
---

# pdlc dashboard

## Goal

The live dashboard runs for this user, only after a clear yes. The install changes
files outside the project.

## Inputs

- The user's yes or no.
- `references/dashboard-builder.md`, `references/dashboard-builder-guard.py`, and
  `references/claude-md-rule.md`.

## Outputs

- After a yes: `dashboard-builder.md` and `dashboard-builder-guard.py` in
  `~/.claude/agents/`, the rule in `~/.claude/CLAUDE.md`, and `.dashboard/` in
  `.git/info/exclude`.
- A reply that says what the skill installed, and that the rule starts next session. It also says how to remove it: delete the two agent files and the
  "## Live dashboard" section. The style stays in
  `~/.claude/agent-memory/dashboard-builder/`.

## Constraints

- The question is "Install the live dashboard?". The default is **no**, also with
  `defaults`.
- Before the question, tell the user three facts:
  - One page, `.dashboard/index.html`, shows the work. It refreshes every 10 seconds.
  - The helper uses only `.dashboard/` and its memory, by a guard script.
  - Sessions use the default when they need a decision.
- A different existing file: show the diff. Replace it only after the user agrees.
- A `~/.claude/CLAUDE.md` with a "## Live dashboard" section does not change.

## Done when

After a yes, the files are in place. After a no, no file changed.
