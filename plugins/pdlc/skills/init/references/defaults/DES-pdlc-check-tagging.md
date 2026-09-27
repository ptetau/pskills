# DES-pdlc-check-tagging · How checks name their requirement

Status: agreed · Default: yes · Ask at init: yes

## Question

How should a check show which requirement it proves?

- A · in the check's name (recommended): the ID starts the test name, for example
  `CAP-email.R3 sends from a template`. Works with almost any test runner, and
  filtering by name selects one requirement's checks.
- B · as a tag or marker: use the runner's tagging, for example a pytest marker. Tidier
  names, but not every runner has tags.

## Rule

The requirement ID starts the check's name, for example `CAP-email.R3 sends from a
template`. A check that proves two requirements names both.

## Why

The trace from requirement to check is only as good as this naming, so it must be simple
and the same everywhere.
