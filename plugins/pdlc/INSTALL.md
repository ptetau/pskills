# Installing pdlc

pdlc is a Claude Code plugin. It works in any project that uses git, whatever the language,
framework or kind of system.

> pdlc is at the design stage. The skills install and load, but they are skeletons. See
> `OUTLINE.md` for the design and `plans/build-pdlc-v1.plan.md` at the repo root for progress.

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

When init finishes, add your first intent:

```
/pdlc:intake
```

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
