# pskills

pskills is a collection of Claude Code skills and two plugins. The skills clarify a
request, design a system, check a text, and test a skill. The plugin `pdlc` runs a full
development lifecycle. The plugin `slice` is a lighter harness that builds a specification
one slice at a time.

All text in the repository follows `WRITING-GUIDELINES.md`. Short sentences, active voice,
and the answer first.

## Start here

| You want to | Use | Page |
|---|---|---|
| Clarify a request with a few questions | `/quiz` | [quiz/README.md](quiz/README.md) |
| Clarify a request with a visual page | `/quiz-visual` | [quiz-visual/README.md](quiz-visual/README.md) |
| Plan a change, then run the plan | `/quiz-plan`, `/quiz-plan-execute` | [quiz-plan/README.md](quiz-plan/README.md), [quiz-plan-execute/README.md](quiz-plan-execute/README.md) |
| Design a system | `/decompose` | [decompose/README.md](decompose/README.md) |
| Turn a design into a spec that an agent can build | `/blueprint` | [blueprint/README.md](blueprint/README.md) |
| Turn a spec into code, with the full lifecycle | `pdlc` | [plugins/pdlc/README.md](plugins/pdlc/README.md) |
| Turn a spec into code, with a light harness | `slice` | [plugins/slice/README.md](plugins/slice/README.md) |
| Find contradictions in a text | `/argue` | [argue/README.md](argue/README.md) |
| Rewrite a text to the writing guidelines | `/improve-writing` | [improve-writing/README.md](improve-writing/README.md) |
| Hunt for bugs in a running app | `/probe` | [probe/README.md](probe/README.md) |
| Check a skill for quality and stability | `/vet` | [vet/README.md](vet/README.md) |

Words that you do not know are in [docs/GLOSSARY.md](docs/GLOSSARY.md).

## Install

A skill installs by copy. Copy its folder into `~/.claude/skills/`. Claude Code then finds
it. For example:

```
cp -r quiz ~/.claude/skills/
```

A plugin installs from the marketplace of this repository
(`.claude-plugin/marketplace.json`). Run these commands:

```
/plugin marketplace add ptetau/pskills
claude plugin install pdlc@pskills --scope project
claude plugin install slice@pskills --scope project
```

Install only the plugin that you want. `plugins/pdlc/INSTALL.md` gives the full steps for
`pdlc`.

## pdlc or slice?

| | `pdlc` | `slice` |
|---|---|---|
| Size | The full lifecycle: 15 skills and 4 agents | The light harness: 5 skills and 3 agents |
| Unit of work | A change: one job or one capability | A slice: one user story through every layer |
| Records | Intents, specs, changes, and traces in `pdlc/` | A spec folder in `slice/` |
| Your stops | Each merge, and each question that pdlc cannot answer | One: ratify the spec |
| Extras | Board, dashboard, merge check for CI, GIF review | Security scan, workflow script for the build |

Use `slice` when you have a specification and want committed code fast. Use `pdlc` when
you need an inbox, traceability from code to intent, and independent reviews.

## The chain: decompose, blueprint, pdlc

For a new system, the tools work as a chain. Each tool takes the output of the tool before
it. You can also use each tool alone.

```
/decompose a notifications service
/blueprint notifications.design.md
/pdlc:init
/pdlc:intake notifications.blueprint.md
```

The design and the blueprint are frozen inputs. After intake, the pdlc specs lead. To
change the design later, run `/decompose` on the real code, then `/blueprint`, then
`/pdlc:intake` again. For the mapping between the blueprint and pdlc, and the four rules that keep the chain consistent, read [docs/CHAIN.md](docs/CHAIN.md).

## Writing guidelines

`WRITING-GUIDELINES.md` is the standard for all text in the repository, and for the text
that the skills write. It has the 53 rules of ASD-STE100 Simplified Technical English
(Issue 9) in short form, the local-references rule, and the described-IDs rule. To check a
file, run:

```
python3 improve-writing/scripts/check_writing.py FILE.md
```

Each skill has a copy of the guidelines in `references/writing-guidelines.md`. Edit only
the root file, then run `python3 scripts/sync_shared.py`. To make the guidelines your
default style, run:

```
cp WRITING-GUIDELINES.md ~/.claude/WRITING-GUIDELINES.md
echo '@~/.claude/WRITING-GUIDELINES.md' >> ~/.claude/CLAUDE.md
```

## Map of the repository

| Folder | Holds |
|---|---|
| `argue/`, `blueprint/`, `decompose/`, `improve-writing/`, `probe/`, `quiz/`, `quiz-plan/`, `quiz-plan-execute/`, `quiz-visual/`, `vet/` | One skill each, with its own `README.md` |
| `plugins/pdlc/` | The pdlc plugin |
| `plugins/slice/` | The slice plugin |
| `.claude-plugin/` | The marketplace file |
| `docs/` | The glossary, and the notes on the chain |
| `plans/` | Plans for changes to this repository. See `plans/README.md` |
| `evals/` | Saved `/vet` suites and runs. See `evals/README.md` |
| `bench/` | The pdlc benchmark. See `bench/README.md` |
| `scripts/` | Repository checks, and the script that syncs the shared files |

## For contributors and agents

- [AGENTS.md](AGENTS.md): the rules for contributors and agents, and the list of tests to
  run before each commit.
- [WRITING-GUIDELINES.md](WRITING-GUIDELINES.md): the writing standard.
