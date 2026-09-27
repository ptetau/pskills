# Installing pdlc

pdlc is a Claude Code plugin. It works in any project that uses git, whatever the language,
framework or kind of system.

> pdlc is new. See `OUTLINE.md` for the design and `plans/build-pdlc-v1.plan.md` at the
> repo root for build progress.

## What you need

- Claude Code.
- A project in a git repository.

## 1. Add the marketplace

This repository is a plugin marketplace called `pskills`. In Claude Code, run:

```
/plugin marketplace add ptetau/pskills
```

Or from a terminal:

```
claude plugin marketplace add ptetau/pskills
```

## 2. Install the plugin

Pick a scope:

- **project**: for everyone who works on this project. The setting is saved in the project's
  `.claude/settings.json`, which you commit.
- **user**: just for you, in every project.

```
claude plugin install pdlc@pskills --scope project
```

Check it worked:

```
claude plugin list
```

You should see `pdlc@pskills` marked enabled.

## 3. Set up your project

Open Claude Code in your project and run:

```
/pdlc:init
```

Init creates a `pdlc/` folder in your project. If you already have code, it maps it first and
asks you to confirm what it found. Then it asks you about a few defaults, one at a time.
Reply `skip` to accept the recommended answer.

When init finishes, the quickest start is:

```
/pdlc:ship <what you want, in your own words>
```

It runs every stage below on recommended answers, stacks the changes, and stops only when
it needs you. Or go a stage at a time:

```
/pdlc:intake <what you want>   turn it into spec changes
/pdlc:ready        clear up anything vague, check for contradictions
/pdlc:change       split it into changes, one job or capability each
/pdlc:tests        a test writer writes the checks from the spec; they're locked
/pdlc:build        a builder writes code until the locked checks pass
/pdlc:show         record the change working as a GIF
/pdlc:verify       run checks and independent reviews, then propose the merge
```

The visual review needs Node. `show` installs its tools (Playwright, gifenc, pngjs) into
`pdlc/.tools/` the first time.

Add `defaults` to any of them to take the recommended answer instead of being asked.

## Showing work on a board

pdlc can show intents and changes as cards on a GitHub project or in Linear. In
`pdlc/config.md`, set `tracker:` to `tracker-github-projects` or `tracker-linear`, fill in
"Tracker settings" as the adapter file in `pdlc/adapters/` describes, and run:

```
/pdlc:board dry-run    see what would change
/pdlc:board            create and move the cards
```

The session needs access to the board: the `gh` CLI for GitHub projects, or a Linear
connection for Linear.

## Optional: live dashboard

pdlc can install a helper agent, `dashboard-builder`, that keeps one web page showing tasks
and their status, questions waiting for you with the default action, the latest
deliverables, and anything stuck. It refreshes every 10 seconds; open
`.dashboard/index.html` with a double-click. The first time, it asks what style you like.

`/pdlc:init` offers it, or run `/pdlc:dashboard` any time. It asks before installing,
because it adds files to `~/.claude/agents/` and a rule to `~/.claude/CLAUDE.md`.

## Enforcing the merge check

pdlc runs its merge check before proposing a merge, but git itself doesn't know about it.
To make sure nothing unverified reaches main, have your CI run this on every pull request
and make it a required check:

```
python3 pdlc/bin/check_merge.py
```

It finds the change whose branch is being merged (from `GITHUB_HEAD_REF` in GitHub Actions,
or the current git branch) and fails if any requirement that change touches isn't
`verified`. If no change uses the branch, it checks every change marked `in review`.

## Checking the guard

pdlc's plugin includes a guard that keeps its agents in their lanes: the test writer can't
read app code, the builder can't change checks, and each reviewer sees only its packet. To
see every decision it makes, start Claude Code with `PDLC_GUARD_LOG=/tmp/pdlc-guard.log`.

## Sharing with your team

With the project scope, `.claude/settings.json` ends up like this:

```json
{
  "extraKnownMarketplaces": {
    "pskills": {
      "source": { "source": "github", "repo": "ptetau/pskills" }
    }
  },
  "enabledPlugins": {
    "pdlc@pskills": true
  }
}
```

Commit it. Each teammate then runs this once:

```
claude plugin install pdlc@pskills --scope project
```

## Updating and removing

```
claude plugin update pdlc@pskills
claude plugin uninstall pdlc@pskills
```

Uninstalling leaves your project's `pdlc/` folder alone. Your specs, intents and change
specs stay in git.

## Trying a local copy

To try pdlc from a checkout without installing it:

```
claude --plugin-dir ./plugins/pdlc
```

To check the plugin files are valid:

```
claude plugin validate ./plugins/pdlc
```

## Using pdlc on this repository

pdlc can manage changes to `pskills` itself, including changes to pdlc. See "pdlc on
itself" in `OUTLINE.md`. The short version:

1. Install the released pdlc from the marketplace, not from your working copy.
2. Run `/pdlc:init` at the root of `pskills`. Its state goes in `pdlc/` at the root, next to
   `plugins/pdlc/`, which is the plugin's source.
3. Changes to `plugins/pdlc/` are built by the installed version. The new version only
   takes effect after it merges and you run `claude plugin update pdlc@pskills`.
