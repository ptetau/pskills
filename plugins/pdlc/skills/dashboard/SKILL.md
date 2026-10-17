---
name: dashboard
description: >
  Installs the optional live dashboard of pdlc. The dashboard has two parts. The first
  part is the dashboard-builder agent, which keeps one HTML page with tasks, questions for
  the user, deliverables, and anything that is stuck. The second part is a rule in the
  CLAUDE.md of the user. The rule tells each session to use the dashboard for all work in
  progress. Installs only after the user says yes. Use when the user says
  "/pdlc:dashboard", asks for a live dashboard, or says yes to the dashboard during pdlc
  init.
---

# pdlc dashboard

This skill installs the live dashboard for this user. The skill changes files in the home
folder of the user, outside the project. Thus, always ask the user first.

The files to install are in the `references/` folder, next to this file.

## 1. Tell the user and ask

Tell the user these facts in a short text, in your own words:

- A helper agent keeps one web page, `.dashboard/index.html`. The page shows the tasks and
  their status, the questions for you with the default action, the latest deliverables,
  and anything that is stuck. The page refreshes itself every 10 seconds. To open the
  page, double-click it.
- The helper can only use `.dashboard/` and its own memory. A guard script makes sure that
  the helper obeys this limit.
- The skill adds a rule to your `~/.claude/CLAUDE.md`. With the rule, each session uses
  the dashboard for work in progress. When a session needs your decision, the session
  continues with the default.

Ask: "Install the live dashboard?" The default is **no**. Do not install without a clear
yes, also when the skill runs with `defaults`. The install changes files outside the
project.

## 2. Install

Do these steps only after the user says yes:

1. If there is no `~/.claude/agents/` folder, make that folder.
2. Copy `references/dashboard-builder.md` and `references/dashboard-builder-guard.py` to
   `~/.claude/agents/`. If one of the files is there and is different, show the
   difference. Then ask the user before you replace that file.
3. If there is no `~/.claude/CLAUDE.md`, make that file. If `~/.claude/CLAUDE.md` has a
   "## Live dashboard" section, do not change the file. Tell the user that the section is
   there. If the file has no such section, add `references/claude-md-rule.md` to the end
   of `~/.claude/CLAUDE.md`, after a blank line.
4. If this project is a git repository, add `.dashboard/` to `.git/info/exclude`. Then
   the dashboard does not go into a commit.

## 3. Finish

- Tell the user what you installed, and where.
- Tell the user that the rule starts to work in the next session. Also tell the user that
  the helper asks for their style the first time: dark or light, dense or airy, and one
  accent colour.
- Tell the user that they can remove a design skill from the `skills:` list in
  `~/.claude/agents/dashboard-builder.md`. They can do this when that skill is not
  installed on this machine.

## To remove the dashboard

Delete these items:

- `~/.claude/agents/dashboard-builder.md`.
- `dashboard-builder-guard.py`, in the same folder.
- The "## Live dashboard" section in `~/.claude/CLAUDE.md`.

The dashboard-builder agent keeps its saved style in
`~/.claude/agent-memory/dashboard-builder/`.
