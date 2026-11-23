# Plan: tidy the pskills repository

## Intent

A person who opens this repository for the first time can find out, in a few minutes, what
is here, which part to use, and how to start. The repository holds no stale or duplicate
file that this person must read around. Behaviour does not change: no skill, script, hook,
or test changes what it does.

## Ground truth (surveyed at master 290cc3c)

- The root `README.md` has 679 lines. It describes each skill and pdlc. It does not
  mention the slice plugin.
- `plugins/pdlc` has `INSTALL.md` and `OUTLINE.md`, and no `README.md`. `plugins/slice`
  has a `README.md` and a new `workflows/slice-build.js` (PR #31).
- `plans/` holds six plan files. `build-probe-skill.plan.md` is at the root. Most plans
  are done.
- `evals/` is 17 MB in 764 tracked files. Most of it is `runs/` folders from many vet
  rounds. Many runs used older suites, runners, or workflows, so `compare_vet.py` cannot
  compare them with a new run.
- `bench/` is 15 MB. `bench/results/` has 113 folders, and `bench/sections/` is 11 MB.
- `AGENTS.md` holds the rules and the test list. `CLAUDE.md` points to it.

## Outputs

### T1: one front door (docs)

- **Root `README.md`:** rewrite it as a short front door of at most 150 lines:
  - what the repository is, in three sentences;
  - a "Start here" table with one row for each need ("clarify a request", "design a
    system", "turn a spec into code", "check a skill"), the skill or plugin to use, and a
    link to its own page;
  - how to install (the marketplace commands, checked against
    `.claude-plugin/marketplace.json`);
  - "pdlc or slice?": a short comparison, with slice as the light harness and pdlc as
    the full lifecycle;
  - a map of the repository, one line for each top-level folder;
  - links to `AGENTS.md` (rules for contributors and agents) and `WRITING-GUIDELINES.md`.
- **Skill pages:** move each long skill section out of the root README into that skill's
  folder as `README.md` (for example `argue/README.md`), if the folder has none. Keep the
  text, and fix only the links. Do not rewrite a `SKILL.md`.
- **`plugins/pdlc/README.md`:** a new front page for pdlc of at most 120 lines: what it
  does, the stages in order with one line each, the first three commands to run, and
  links to `INSTALL.md` and `OUTLINE.md`. Take each fact from the skills, `pdlc.py`, and
  the project README template. Do not invent a command.
- **`plugins/slice/README.md`:** check it against the code after PRs #28 to #31 (the
  model routing, `- Tier:`, `workflows/slice-build.js`, `resume`, `scan`,
  `commit tests`, `source files:`). Fix what is stale. Add a "First run" section: the
  commands and the two questions that the user answers (ratify the spec, approve the
  interface).
- **`docs/GLOSSARY.md`:** move "Words used here" from the root README, and add the pdlc
  and slice terms that a newcomer meets first (intent, change, slice, handoff, red,
  vet, bench). One line for each term.

### T2: one place for plans

- Move `build-probe-skill.plan.md` into `plans/`.
- Add `plans/README.md`: one line for each plan, with its state (done, superseded, or
  open) and the pull request that finished it, if the git log shows one. Move each done
  or superseded plan into `plans/archive/`.

### T3: smaller eval and bench data

- For each `evals/<suite>/runs/`: keep the newest run of each label family that a
  current comparison needs (for the pdlc suites, the `plugin-M*` and `plugin-N*` runs and
  their pooled files; for the other suites, the newest run). Delete each older run folder
  with `git rm`. Git history keeps them.
- Add `evals/README.md`: what a suite is, what a run folder holds, which runs remain and
  why, and the command that compares two runs.
- For `bench/results/`: keep `pr27-*` and each folder that `bench/baseline.json`,
  `bench/reference*.json`, or a test names. Delete the other folders with `git rm`. Keep
  only the newest `bench/reference*.json` and `bench/baseline*.json` if no code reads the
  older ones.
- Add `bench/README.md`: what the bench is, the fixtures, how to run one end-to-end run,
  what it costs (about $2 for wordfreq, about $7 for todo-rust), and what each results
  folder is.
- Before each delete, grep the repository for the path. A path that a script, a test, a
  suite, or `scripts/skill_budgets.json` (its "evidence" fields) names stays, or the
  reference is updated to a kept path in the same commit.

### T4: small repository hygiene

- Check `.gitignore` against the files that tools create here (`__pycache__`,
  `.vet-capture/`, `.vet-tmp/`, `slice/` smoke folders). Add what is missing.
- Find each dead link in every tracked Markdown file with a script, and fix it.
- Report, and do not delete, each remote branch that is fully merged into master. The
  user deletes branches.

## Constraints

- Behaviour stays the same. Change no `SKILL.md`, agent, hook, or script, except to fix a
  path that a move or a delete broke.
- Follow `AGENTS.md` and `WRITING-GUIDELINES.md` for every text. Run
  `python3 plugins/pdlc/skills/init/references/bin/check_writing.py` on each new or
  changed Markdown file, and fix each finding in new text.
- Every fact in a doc comes from the code or a file in this repository. If the code and
  an old doc disagree, the code wins, and the doc says what the code does.
- One commit for each of T1 to T4, or smaller. Each commit passes every test in
  `AGENTS.md`.
- Do not push, and do not delete a remote branch.

## Done when

- The root README is at most 150 lines, names every skill and both plugins, and each of
  its links resolves.
- Each skill folder and each plugin has a `README.md`.
- `plans/README.md`, `evals/README.md`, `bench/README.md`, and `docs/GLOSSARY.md` exist.
- No tracked Markdown file has a dead relative link.
- Every test in `AGENTS.md` passes on the last commit.
- The report lists the size of `evals/` and `bench/` before and after, each deleted
  folder family, and each merged remote branch.
