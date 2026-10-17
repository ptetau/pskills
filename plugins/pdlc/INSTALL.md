# Install pdlc

pdlc is a Claude Code plugin. pdlc works in each project that uses git, for all
languages, frameworks, and types of system.

> pdlc is new. For the design, see `OUTLINE.md`. For the build progress, see
> `plans/build-pdlc-v1.plan.md` at the root of the repository.

## What you need

- Claude Code.
- A project in a git repository.

## 1. Add the marketplace

This repository is a plugin marketplace with the name `pskills`. In Claude Code, run this
command:

```
/plugin marketplace add ptetau/pskills
```

Or, from a terminal, run this command:

```
claude plugin marketplace add ptetau/pskills
```

## 2. Install the plugin

Select a scope:

- **project**: for each person who works on this project. The project's
  `.claude/settings.json` file keeps the setting, and you commit that file.
- **user**: only for you, in each of your projects.

```
claude plugin install pdlc@pskills --scope project
```

To make sure that the installation worked, run this command:

```
claude plugin list
```

The list shows `pdlc@pskills`, marked enabled.

## 3. Prepare your project

Open Claude Code in your project. Then run this command:

```
/pdlc:init
```

Init creates a `pdlc/` folder in your project. If your project already has code, init
first makes a map of the code and asks you to confirm what it found. Then init asks you
about some defaults, one at a time. To accept the recommended answer, reply `skip`.

When init is complete, the quickest start is this command:

```
/pdlc:ship <what you want, in your own words>
```

`/pdlc:ship` runs all the stages below with the recommended answers, and stacks the
changes. `/pdlc:ship` stops only when it needs you. Or, do one stage at a time:

```
/pdlc:intake <what you want>   change your words into spec changes
/pdlc:ready        make vague items clear, and look for contradictions
/pdlc:change       divide the work into changes, one job or capability each
/pdlc:tests        a test writer writes the checks from the spec, then pdlc locks them
/pdlc:build        a builder writes code until the locked checks pass
/pdlc:show         record a GIF of the change as it works
/pdlc:verify       run the checks and the independent reviews, then propose the merge
```

The visual review needs Node. The first time that `show` runs, `show` installs its tools
(Playwright, gifenc, pngjs) into `pdlc/.tools/`.

You can add `defaults` to each of these commands. Then the command uses the recommended
answer, and does not ask you.

## Show work on a board

pdlc can show intents and changes as cards on a GitHub project or in Linear. To show the
cards, do these steps:

1. In `pdlc/config.md`, set `tracker:` to `tracker-github-projects` or `tracker-linear`.
2. Complete "Tracker settings" as the adapter file in `pdlc/adapters/` tells you.
3. Run these commands:

   ```
   /pdlc:board dry-run    show what will change
   /pdlc:board            create and move the cards
   ```

The session needs access to the board. For GitHub projects, the session needs the
`gh` CLI. For Linear, the session needs a Linear connection.

## Optional: live dashboard

pdlc can install a helper agent, `dashboard-builder`. The agent keeps one web page that
shows these items:

- The tasks and their status.
- The questions that wait for you, with the default action.
- The latest deliverables.
- Each item that is stuck.

The page refreshes every 10 seconds. To open the page, double-click
`.dashboard/index.html`. The first time, the agent asks you which style you like.

`/pdlc:init` offers the dashboard. You can also run `/pdlc:dashboard` at any time. Before
pdlc installs the dashboard, pdlc asks you, because the dashboard adds files to
`~/.claude/agents/` and a rule to `~/.claude/CLAUDE.md`.

## Enforce the merge check

pdlc runs its merge check before it proposes a merge. But git itself does not know about
the merge check. To make sure that nothing unverified gets to main, make your CI run this
command on each pull request:

```
python3 pdlc/bin/check_merge.py
```

Then make this command a required check.

The script finds the change whose branch the pull request merges. The script gets the
branch from `GITHUB_HEAD_REF` in GitHub Actions, or from the current git branch. If a
requirement that the change touches is not `verified`, the script fails. If no change uses
the branch, the script examines each change with the status `in review`.

## Examine the guard

The pdlc plugin includes a guard that keeps each agent to its own role:

- The test writer cannot read app code.
- The builder cannot change checks.
- Each reviewer sees only its packet.

To see each decision of the guard, start Claude Code with
`PDLC_GUARD_LOG=/tmp/pdlc-guard.log`.

## Share pdlc with your team

When you install with the project scope, `.claude/settings.json` contains this text:

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

Commit this file. Then each teammate runs this command one time:

```
claude plugin install pdlc@pskills --scope project
```

## Update and remove the plugin

```
claude plugin update pdlc@pskills
claude plugin uninstall pdlc@pskills
```

When you uninstall the plugin, your project's `pdlc/` folder does not change. Your specs,
intents, and change specs stay in git.

## Try a local copy

To try pdlc from a checkout, and not install it, run this command:

```
claude --plugin-dir ./plugins/pdlc
```

To make sure that the plugin files are valid, run this command:

```
claude plugin validate ./plugins/pdlc
```

## Use pdlc on this repository

pdlc can manage changes to `pskills` itself, and also changes to pdlc. For the full
text, see "pdlc on itself" in `OUTLINE.md`. The short version is:

1. Install the released pdlc from the marketplace, not from your working copy.
2. Run `/pdlc:init` at the root of `pskills`. pdlc keeps its state in `pdlc/` at the
   root, next to `plugins/pdlc/`. `plugins/pdlc/` is the source of the plugin.
3. The installed version builds the changes to `plugins/pdlc/`. The new version starts to
   work only after the change merges and you run `claude plugin update pdlc@pskills`.
