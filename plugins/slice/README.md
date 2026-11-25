# slice

A light harness that takes a specification to committed code, one vertical slice at a
time. A slice is a user story through every layer.

## First run

1. Install the plugin: `claude plugin install slice@pskills --scope project`. The marketplace is
   `ptetau/pskills`.
2. Open Claude Code in a git project, and run `/slice:run <your specification, or its file path>`.
3. Answer the questions of `/slice:spec`, one at a time. Then confirm the summary. This is the
   only stop: you ratify the spec. The skill sets `Status: ratified` in
   `slice/NNN-<name>/spec.md`.
4. Wait while `/slice:plan` and `/slice:domain` write `slices.md` and `domain.md`. They ask nothing.
5. Wait while `/slice:build` builds each slice, writes its acceptance tests, and reviews both. To see where the run is, run
   `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py status`.
6. If a slice stops, read the reason that `slice.py next` prints. Answer it, then run
   `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py resume Sn` (`Sn` is the slice ID), or run `/slice:run` again.

To run one stage alone, use its own command, for example `/slice:spec`.

## Flow

1. `/slice:spec`: find the ambiguities in the specification and ask the user about each,
   one question at a time. The interview recommends a stack and a security scanner if none
   is fixed. The user ratifies the result in `slice/NNN-<name>/spec.md`, with numbered
   requirements (R1) and decisions (D1).
2. `/slice:plan`: break the spec into vertical slices in `slices.md`. Each slice names its
   requirements.
3. `/slice:domain`: model the entities, the state machines, and the boundary in
   `domain.md`. Each requirement must map to the model. It holds no code. A state machine is a
   `### Machine: <Object>` section with `- T1: <from> -> <to> on <trigger> [<guard>] / <effect>`
   and `- X1: <from> on <trigger> refused: <error>` lines, or the line `- Machines: none`. A
   requirement cites transitions as `Order.T1`. `status` reports an undefined citation, an uncited
   transition, a machine with no start state, and an unreachable state; `next` prints `domain` until
   none is left.
4. `/slice:build`: for the slice that `next` names, `slice:implementer` builds the code (and optional
   unit tests in `unit tests folder`). Next, `slice:test-writer` writes acceptance tests against the
   boundary from `spec.md` and `domain.md` (plus read-only `boundary files`), while `guard.py`
   hides internal app code and unit tests. `slice:reviewer` immediately checks requirements,
   architecture, security, and tests (`review/Sn.md` and `review/Sn.tests.md`), any findings go to
   their owner, and `slice.py commit Sn` commits the slice.
5. `/slice:run`: loop on `slice.py next` (a stage, `build Sn`, `stop Sn: reason`, or `done`). Run and build recap.
   After the user answers a stop, `slice.py resume Sn` restarts the slice.

## Model

The frontmatter sets the model of each job.

| Job | Model | Effort |
|---|---|---|
| `spec`, `plan`, `domain` | `claude-opus-5-5` | medium |
| `run`, `build`, `slice:test-writer` | `claude-sonnet-5-5` | medium |
| `slice:implementer` | `claude-sonnet-5-5`. `opus` for `- Tier: hard`, and from test round 3 | medium |
| `slice:reviewer` | `claude-opus-5-5` | high |

`/slice:plan` writes the `- Tier:` line. `CLAUDE_CODE_EFFORT_LEVEL` overrides `effort`. A skill's `model`
lasts one turn, and an allowlist or auto mode can drop it.

The Workflow script `workflows/slice-build.js` runs the build with this routing. It starts the plugin
agents by type (`slice:test-writer`, `slice:implementer`, `slice:reviewer`), so the guard hook applies
when the plugin is loaded. The script names the paths of one project (`docs/`, `tests/Rail.Tests`, C#
test files). Copy it and change those paths for another project.

## Records

`slice/config.md` (stack, test command, tests folder, source folders, optional `unit tests folder`,
`unit test command`, `source files`, `boundary files`, and `security scan`) is at the top of `slice/`.
Each spec has a folder, `slice/NNN-<name>/`, with `spec.md`, `slices.md`, `domain.md`,
`review/Sn.md`, and `review/Sn.tests.md`. The scripts use the highest number, or
the folder that `--spec` names. The templates are in `templates/`. `contracts.json` lists each
hand-off between the prompts and the scripts.

## Script, hook, and test names

`bin/slice.py` holds the state of the run: `status`, `next`, `set`, `round`, `resume`, `test`,
`commit`, and `scan`. `slice.py scan` runs the optional security scan of `slice/config.md`. Run it with `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`. The hook
`hooks/guard.py` keeps the implementer out of the tests, and the test writer out of the code. Each
test name holds its spec number, slice ID, and requirement ID: `test_NNN_Sn_Rn_<what>`. For the
rules of each command, the hook, and the names, read `REFERENCE.md`.

## Tests

`(cd plugins/slice && python3 -m unittest discover -s tests)`
