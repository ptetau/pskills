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

## Success

If a check is known to fail, the port reports that check as failed. If a requirement has
no checks, the port reports that the requirement has no checks. The port does not report
that requirement as a pass.

## Conformance check

1. Add a check that always fails, with the made-up ID `CAP-conformance.R1` in its name.
2. Run for that requirement. The port reports one failed check.
3. Run for `CAP-conformance.R2`. The port reports "no checks found".
4. Remove the check.
