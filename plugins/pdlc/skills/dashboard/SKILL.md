---
name: dashboard
description: >
  Installs pdlc's optional live dashboard: the dashboard-builder agent, which keeps one
  HTML page showing tasks, questions waiting for the user, deliverables and anything
  stuck, plus a rule in the user's CLAUDE.md to use it for all work in progress. Only
  installs after the user says yes. Use when the user says "/pdlc:dashboard", asks for a
  live dashboard, or says yes to it during pdlc init.
---

# pdlc dashboard

Installs the live dashboard for this user. It changes files in the user's home folder,
outside the project, so always ask first.

The files to install are in the `references/` folder next to this file.

## 1. Explain and ask

Say this in your own words, briefly:

- A helper agent keeps one web page, `.dashboard/index.html`, showing tasks and their
  status, questions waiting for you with the default action, the latest deliverables, and
  anything stuck. It refreshes itself every 10 seconds; open it with a double-click.
- The helper can only touch `.dashboard/` and its own memory. A guard script enforces this.
- A rule is added to your `~/.claude/CLAUDE.md` so every session uses it for work in
  progress, and keeps going with the default when it needs your decision.

Ask: "Install the live dashboard?" The default is **no**. Even when run with `defaults`,
don't install without a clear yes, because this changes files outside the project.

## 2. Install

Only after a yes:

1. Create `~/.claude/agents/` if it doesn't exist.
2. Copy `references/dashboard-builder.md` and `references/dashboard-builder-guard.py`
   there. If either file already exists and is different, show the difference and ask
   before replacing it.
3. Add `references/claude-md-rule.md` to the end of `~/.claude/CLAUDE.md`, after a blank
   line. Create the file if it doesn't exist. If it already has a "## Live dashboard"
   section, leave it alone and say so.
4. If this project is a git repository, add `.dashboard/` to `.git/info/exclude` so the
   dashboard never gets committed.

## 3. Finish

- Say what was installed, and where.
- Say the rule takes effect in the next session, and that the first time, the helper will
  ask what style they like: dark or light, dense or airy, and one accent color.
- Say that if a design skill in the agent's `skills:` list isn't installed on this
  machine, they can remove it from `~/.claude/agents/dashboard-builder.md`.

## To remove it

Delete `~/.claude/agents/dashboard-builder.md` and `dashboard-builder-guard.py`, and the
"## Live dashboard" section from `~/.claude/CLAUDE.md`. Its saved style is in
`~/.claude/agent-memory/dashboard-builder/`.
