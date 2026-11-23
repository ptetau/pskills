# Glossary

This page defines the words that a newcomer meets first. Each word has one line. The
words are in two groups: the general words, then the words of this repository.

## General words

- **Decomposition**: the division of a system into components.
- **Deterministic**: gives the same result each time for the same input.
- **Invariant**: a rule that must always be true in the system.
- **Orthogonal**: independent. A change to one part does not change a different part.
- **Primitive**: a small, basic part that does one job.
- **Volatility**: how likely an item is to change.

## pdlc words

- **Intent**: something that you want to be true, but that is not true yet. Each intent
  enters through the inbox of pdlc.
- **Spec**: a file that says what the system does. A job spec tells what a user tries to
  do. A capability spec tells what the system can do. A design spec tells a convention.
- **Requirement**: one numbered line of a spec, with its acceptance lines.
- **Change**: a small unit of work that covers exactly one job or one capability. Each
  change has a change spec.
- **Check**: a test that proves a requirement. pdlc locks each check before the builder
  starts, so the builder cannot change it.
- **Handoff**: the file that one pdlc stage writes for the next stage. It lists what is
  done, what is open, and what the next stage must not redo.
- **Trace**: the link from a line of code to its commit, its requirement, and its intent.

## slice words

- **Slice**: a user story that cuts through every layer of an app. The `slice` plugin
  builds one slice at a time.
- **Interface**: the one test surface that all the slices share, for example the HTTP
  endpoints or the public functions of a module. The user approves it.
- **Red**: a test that fails because the behaviour is missing, not because the test is
  broken. In `slice`, each slice must be red before the build starts.
- **Implementer**: the agent that writes the code of a slice. A hook keeps the
  implementer out of the tests.

## Evaluation words

- **Vet**: the `/vet` skill. It scores another skill on quality and stability.
- **Suite**: the saved test prompts and rubric of one skill, in `evals/<skill>/`.
- **Run**: one execution of a suite. Its folder is in `evals/<skill>/runs/`.
- **Bench**: the pdlc benchmark in `bench/`. It runs pdlc end to end on small fixture
  projects, and records the cost and the quality of each run.
- **Fixture**: a small sample project that the bench uses as input.
