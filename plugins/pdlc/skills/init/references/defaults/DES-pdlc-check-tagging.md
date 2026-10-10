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

If the check runner doesn't allow `.` or `-` in names (Python's `unittest`, for example),
write the ID with underscores instead: `test_CAP_email_R3_sends_from_a_template`. Both forms
count as the same ID. Use one form per project.

Lay checks out the same way everywhere:

- New check files go in the check folder (`tests/` in a project that had none). Each is
  named after the spec it proves, in the form the runner finds: `test_CAP_email.py`,
  `CAP-email.test.js`.
- Inside, one group per requirement (a test class or a `describe` block), named with its
  ID: `class CAP_email_R3(unittest.TestCase)`, `describe("CAP-email.R3", ...)`.
- Each check's name still starts with the ID, then says what it proves.

## Why

The trace from requirement to check is only as good as this naming, so it must be simple
and the same everywhere.
