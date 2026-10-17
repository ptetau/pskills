# DES-pdlc-check-tagging · How checks name their requirement

Status: agreed · Default: yes · Ask at init: yes

## Question

How do you want each check to show the requirement that it proves?

- A · in the check's name (recommended): the ID starts the test name, for example
  `CAP-email.R3 sends from a template`. This form works with almost any test runner, and
  a filter on the name selects the checks of one requirement.
- B · as a tag or marker: use the tags of the runner, for example a pytest marker. The
  names are tidier, but not all runners have tags.

## Rule

The requirement ID starts the name of the check, for example `CAP-email.R3 sends from a
template`. A check that proves two requirements names the two requirements.

If the check runner does not accept `.` or `-` in names (Python's `unittest`, for
example), write the ID with underscores instead: `test_CAP_email_R3_sends_from_a_template`.
The two forms count as the same ID. Use only one form in each project.

## Why

The trace from a requirement to its checks is only as good as this naming. Thus, the
naming must be simple and the same everywhere.
