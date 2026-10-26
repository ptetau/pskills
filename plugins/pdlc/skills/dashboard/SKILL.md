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

Dashboard installs the live dashboard for this user, only after a clear yes. The install
changes files in the home folder of the user, outside the project.

## Constraints

- The files to install are in the `references/` folder next to this file.
- Before the question, the user hears these facts, in a short text in the words of the
  skill:
  - A helper agent keeps one web page, `.dashboard/index.html`. The page shows the tasks
    and their status, the questions with the default action, the latest deliverables,
    and anything that is stuck. The page refreshes itself every 10 seconds, and opens with
    a double-click.
  - The helper can use only `.dashboard/` and its own memory, and a guard script enforces
    this limit.
  - The skill adds a rule to `~/.claude/CLAUDE.md`. With the rule, each session uses the
    dashboard for work in progress, and continues with the default when it needs a
    decision of the user.
- The question is "Install the live dashboard?", and the default is **no**. There is no
  install without a clear yes, also with `defaults`.
- `~/.claude/agents/` exists, or the skill makes it. `references/dashboard-builder.md` and
  `references/dashboard-builder-guard.py` go there.
- A file that is there already and is different shows the difference to the user. The
  skill replaces it only after the user agrees.
- `~/.claude/CLAUDE.md` exists, or the skill makes it. A file with a "## Live dashboard"
  section does not change, and the user hears that the section is there. Else
  `references/claude-md-rule.md` goes at the end of the file, after a blank line.
- In a git repository, `.dashboard/` is in `.git/info/exclude`, so that the dashboard
  goes into no commit.

## Inputs

- The yes or no of the user.
- `references/dashboard-builder.md`, `references/dashboard-builder-guard.py`, and
  `references/claude-md-rule.md`.
- `~/.claude/agents/`, `~/.claude/CLAUDE.md`, and the `.git` folder of the project.

## Outputs

- After a yes, the two agent files in `~/.claude/agents/`, and the rule in
  `~/.claude/CLAUDE.md`.
- For the user:
  - What the skill installed, and where.
  - The rule starts to work in the next session.
  - The first time, the helper asks for a style: dark or light, dense or airy, and one
    accent colour.
  - The user can remove a design skill from the `skills:` list in
    `~/.claude/agents/dashboard-builder.md` when that skill is not on this machine.
- To remove the dashboard, the user deletes `~/.claude/agents/dashboard-builder.md`,
  `dashboard-builder-guard.py` in the same folder, and the "## Live dashboard" section of
  `~/.claude/CLAUDE.md`. The agent keeps its saved style in
  `~/.claude/agent-memory/dashboard-builder/`.
