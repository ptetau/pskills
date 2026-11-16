# Plan: slice, a lightweight PDLC harness

## Intent

Make a small plugin, `slice`, that takes a specification to committed code in vertical
slices. A slice is a user story that cuts through every layer of the app (for example UI,
API, backend, and store). Each slice gets red acceptance tests against an agreed interface
before any code exists. The implementer sees the interface but never the tests. The pdlc
plugin stays as it is.

## User decisions

- D1 (placement): a new plugin, `plugins/slice`, listed in `.claude-plugin/marketplace.json`.
  It can copy ideas and code from pdlc. It does not import from pdlc.
- D2 (test hiding): a hook blocks every read, search, and edit of the tests by the
  `slice:implementer` agent. The implementer gets only the run results from a script.
- D3 (commits): one commit for each slice, on the current branch.
- D4 (limits): at most 5 test rounds and 3 review rounds for each slice. When a limit runs
  out, the slice stops, and the harness shows what fails and asks the user.

## Flow

1. **Spec** (`/slice:spec`). The input is a specification for one change or a whole app: a
   file path or the user's words. The skill finds each ambiguity that changes what gets
   built. It asks the user one question at a time in the quiz style (the AskUserQuestion
   tool, two to four answers, one recommended answer with a reason). When the user ratifies
   the answers, it writes `slice/spec.md`, with the decisions in the user's words.
2. **Slices** (`/slice:plan`). The skill breaks the ratified spec into vertical slices, in
   the order to build them. Each slice is a user story with acceptance criteria and the
   layers it touches. It writes `slice/slices.md`.
3. **Interface and red tests** (`/slice:interface`). The skill looks at all the slices
   together. It designs the smallest test surface that the slices need, for the project's
   stack: for example HTTP endpoints with request and response shapes, or a module's public
   functions and types. It keeps one interface that is consistent across the slices and is
   good practice for the stack. It writes `slice/interface.md`, and it creates the surface
   in code as stubs that compile and do nothing yet. Then the `slice:test-writer` agent
   writes acceptance tests for each slice against the interface only. A script runs them
   and confirms that each new test fails because the behaviour is missing, not because the
   test is broken.
4. **Build** (`/slice:build`). For each slice, in order:
   - The `slice:implementer` agent gets the spec, the slice, and the interface, and writes
     the code. The hook keeps it out of the tests.
   - A script runs the slice's tests and gives the implementer the results (test names,
     pass or fail, and failure messages). This repeats until the tests pass, at most 5
     rounds.
   - The `slice:reviewer` agent reviews the code quality and the fit to the spec, and
     returns findings marked major or minor. The implementer answers. This repeats at most
     3 rounds, and the tests must still pass after each round.
   - When the tests pass and no major finding is open, a script commits the slice and
     marks it done. The skill moves to the next slice.
5. **Run** (`/slice:run`). This runs the stages in order and continues from the state in
   `slice/`. It stops only at a question for the user or a limit.

## Records

All records are in `slice/` at the project root:

- `slice/config.md`: the stack, the test command, the tests folder, and the source folders.
- `slice/spec.md`: the ratified spec and the decisions. It has the status `draft` or
  `ratified`.
- `slice/slices.md`: one section for each slice (S1, S2, …), with its story, its acceptance
  criteria, its layers, and its status: `planned`, `red`, `building`, `review`, `done`, or
  `stopped`, with the reason.
- `slice/interface.md`: the test surface, with one section for each slice that names the
  parts of the surface it uses.

## Scripts and hooks

- `slice.py` (in the plugin, run with `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py`):
  - `status`: the state of the run, read from `slice/`.
  - `set <Sn> <status> [--reason]`: write a slice's status.
  - `test <Sn>`: run the tests of one slice. It prints the results for the implementer, and
    the names and messages, but no test source. With `--red`, it checks that each new test
    fails because behaviour is missing.
  - `commit <Sn>`: commit the slice with the subject "Slice Sn: <title>" and the trailer
    `Slice: Sn`. It refuses if the tests fail or a major review finding is open.
  - `round <Sn> test|review`: count the rounds, and refuse a round after the limit.
- `hooks/guard.py` (PreToolUse on Read, Glob, Grep, Write, Edit, MultiEdit,
  NotebookEdit, and on Bash commands that read files): when the agent is
  `slice:implementer`, it blocks any path in the tests folder of `slice/config.md`.

## Agents

- `slice:test-writer`: reads the spec, the slices, and the interface. It writes only in the
  tests folder. It does not read the app code.
- `slice:implementer`: reads the spec, the slices, the interface, and the app code. It
  writes app code. It never sees the tests.
- `slice:reviewer`: reads the spec, the slice, the interface, and the diff of the slice.
  It writes only its findings.

## Constraints

- Follow AGENTS.md "Write a skill, an agent, a plugin, or a prompt". Each skill body
  targets 200 words. Add each new skill to the `enforced` list in
  `scripts/skill_budgets.json`.
- Tests first for every script and for the hook.
- Keep it light: no handoff files, no ticket ports, no board, and no tracing beyond the
  commit trailer.

## Done when

- The plugin installs from the marketplace, and its skills pass `check_skill_form.py`.
- The script and hook tests pass, and every AGENTS.md test passes. The new tests are in
  that list.
- One smoke run on the wordfreq fixture takes a small spec to at least one committed slice,
  and the run log shows that the implementer never read a test file.

## Additions from the user (apply in the contracts pass)

- A1 (prompt form): every skill and every agent prompt uses Goal, Inputs, Outputs,
  Constraints, and Done when. One constraint in each says that its outputs give the
  downstream prompt or script exactly what it reads. Each output names its consumer and the
  form that the consumer needs.
- A2 (contract check): one contract table (for example `plugins/slice/contracts.json`)
  lists each hand-off: producer, file, required form, and consumer. A test fails when a
  skill or agent names a file, status, field, or subcommand that the table does not define,
  or when a consumer needs something that no producer makes.
- A3 (numbered specs): each spec gets a number and its own folder,
  `slice/NNN-<name>/` (for example `slice/001-top-option/`). The folder holds `spec.md`,
  `slices.md`, and `interface.md`. Inside `spec.md`, each requirement and each decision has
  a number (R1, R2, …; D1, D2, …), and slices and tests cite those numbers. `slice/config.md`
  stays at the top of `slice/`. The scripts and the hook find the current spec folder.
- A4 (reviewer remit): the reviewer checks three things, and marks each finding major or
  minor: (1) each numbered requirement of the slice is met; (2) the code fits the existing
  architecture of the codebase (its layers, patterns, and conventions); (3) the code meets
  the security guidelines.
- A5 (stack): if the spec or the codebase does not fix a stack, the spec interview suggests
  one as the recommended answer: modern, well regarded, minimal, fast, and common for that
  kind of spec, with a one-line reason. The ratified stack goes into `slice/config.md`.
- A6 (security floor): idiomatic protection against the OWASP Top 10 is the minimum for
  every slice, for the stack in use. The interface stage, the implementer, and the reviewer
  all hold to it. A reviewer finding against it is major.
- A7 (domain model first): a domain-modelling stage comes after the slices and before the
  interface. It writes `slice/NNN-<name>/domain.md`: the entities, value objects, their
  relationships, the invariants, and the bounded contexts and the boundary of the system
  (what is inside, what is outside, and each external actor or system). It is a design
  document only: it writes no code. It must show that the model and the boundary are
  sufficient for the spec: each numbered requirement maps to the parts of the model and the
  boundary that meet it, and a requirement with no mapping is a gap that stops the stage.
  The interface stage reads `domain.md`, and each part of the interface names the domain
  concepts that it exposes. The interface stage still creates compilable stubs, and the
  implementer still builds the slices.
- A8 (test writer is blind to the implementation): the hook also blocks the
  `slice:test-writer` agent from every read, search, and edit of the source folders in
  `slice/config.md`, including the stubs, and from Bash commands that name them. The test
  writer reads only the spec folder (`spec.md`, `slices.md`, `domain.md`, `interface.md`)
  and the tests folder. So `interface.md` must give it everything it needs to call the
  surface: module paths or import lines, signatures, types, endpoints, request and response
  shapes, and error forms. Hiding is two-way: the implementer never sees the tests, and the
  test writer never sees the code.
- A9 (state machines): `domain.md` gives a state machine for each domain object that has a
  lifecycle: its states, the start state, the end states, and each transition with its
  trigger, its guard, and its effect. It also names each transition that is not allowed and
  the error it gives. Each numbered requirement that changes state maps to its transitions.
  The interface stage exposes the triggers, and the test writer writes tests for the
  allowed transitions and for the refused ones.
- A10 (model binding): slice runs on Claude Opus 5.5 at medium effort. Each slice agent's
  frontmatter sets the model `claude-opus-5-5` and the effort `medium`. Each slice skill does
  the same where the skill frontmatter supports these fields (check the Claude Code docs).
  The README says so. Smoke runs use `--model claude-opus-5-5` and medium effort.
- A11 (deterministic next step): `slice.py next` reads the records and prints the next
  stage and slice, or "done", or the stop with its reason. `/slice:run` loops on it and does
  not choose the order itself.
- A12 (progress): the run and build skills say what they start, and give a short recap
  when they finish.
