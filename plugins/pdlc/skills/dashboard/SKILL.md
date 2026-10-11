---
name: dashboard
description: >
  Installs pdlc's optional live dashboard, in two parts. The dashboard-builder agent keeps
  one HTML page showing tasks, questions waiting for the user, deliverables and anything
  stuck. A rule in the user's CLAUDE.md tells sessions to use the dashboard for all work
  in progress. Only installs after the user says yes. Use when the user says
  "/pdlc:dashboard", asks for a live dashboard, or says yes to it during pdlc init.
---

# pdlc dashboard

Installs the live dashboard for this user. Always ask first. This skill changes files in
the user's home folder, outside the project.

The files to install are in the `references/` folder next to this file.

## 1. Explain and ask

Say this in your own words, briefly:

- A helper agent keeps one web page, `.dashboard/index.html`. The page shows tasks and
  their status, questions waiting for you with the default action, the latest
  deliverables, and anything stuck. The page refreshes itself every 10 seconds. Open it
  with a double-click.
- A guard script lets the helper touch only `.dashboard/` and its own memory.
- The install adds a rule to your `~/.claude/CLAUDE.md`. With the rule, every session uses
  the dashboard for work in progress. When a session needs your decision, the session
  keeps going with the default.

Ask: "Install the live dashboard?" The default is **no**. Even with `defaults`, don't
install without a clear yes. The install changes files outside the project.

## 2. Install

Only after a yes:

1. If `~/.claude/agents/` doesn't exist, create it.
2. Copy `references/dashboard-builder.md` and `references/dashboard-builder-guard.py`
   there. If either file already exists and is different, show the difference. Ask
   before you replace the file.
3. If `~/.claude/CLAUDE.md` doesn't exist, create it. If the file already has a
   "## Live dashboard" section, leave the section as it is and say so. Otherwise, add
   `references/claude-md-rule.md` to the end of the file, after a blank line.
4. If this project is a git repository, add `.dashboard/` to `.git/info/exclude`. That
   way, git never commits the dashboard.

## 3. Finish

- Say what you installed, and where.
- Say the rule takes effect in the next session. On its first run, the helper asks which
  style the user likes: dark or light, dense or airy, and one accent colour.
- Say that the agent's `skills:` list may name a design skill. If that skill isn't
  installed on this machine, the user can remove it from
  `~/.claude/agents/dashboard-builder.md`.

## To remove it

Delete `~/.claude/agents/dashboard-builder.md` and `dashboard-builder-guard.py`. Remove the
"## Live dashboard" section from `~/.claude/CLAUDE.md`. The helper's saved style is in
`~/.claude/agent-memory/dashboard-builder/`.
