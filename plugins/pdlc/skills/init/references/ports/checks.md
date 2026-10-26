# Port: checks

The checks port runs the checks of the project. A check is an item that proves a
requirement with a pass or a fail. A check can be a test, a script, a lint rule, an eval,
or a query.

## Operations

- **run all**: run all the checks. Return pass or fail, and the output of each check that
  failed.
- **run for requirement**: the input is a requirement ID. Run only the checks whose names
  carry that ID. Return pass or fail for each check.
- **find**: the input is a requirement ID. List the checks that carry that ID.
- **run acceptance**: the input is an intent ID. Run the checks in the acceptance file of
  that intent. Return pass or fail for each check, and the output of each check that
  failed.
- **run earlier acceptance**: the input is an intent ID. Run the acceptance files of each
  other intent whose acceptance checks passed already. The `Acceptance-Passed:` line of
  such an intent holds a hash. Return pass or fail for each check.

The **run all** operation does not run an acceptance file. Thus, the acceptance checks of
an open intent can fail, and the other checks stay green.

## Success

If a check is known to fail, the port reports that check as failed. If a requirement has
no checks, the port reports that the requirement has no checks. The port does not report
that requirement as a pass.

If an intent has no acceptance file, **run acceptance** reports "no acceptance checks
found". If the acceptance checks of no other intent passed yet, **run earlier acceptance**
reports "none", and that is a pass.

## Conformance check

1. Add a check that always fails, with the made-up ID `CAP-conformance.R1` in its name.
2. Run for that requirement. The port reports one failed check.
3. Run for `CAP-conformance.R2`. The port reports "no checks found".
4. Remove the check.
5. Write an acceptance file for the made-up intent `IN-9999`, with one check that always
   fails. Run all. The run does not include that check.
6. Run acceptance for `IN-9999`. The port reports one failed check.
7. Remove the acceptance file.
