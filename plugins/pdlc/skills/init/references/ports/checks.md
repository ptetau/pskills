# Port: checks

Runs the project's checks. A check is anything that proves a requirement with a pass or
fail: a test, a script, a lint rule, an eval or a query.

## Operations

- **run all**: run every check. Return pass or fail, and the output of anything that failed.
- **run for requirement**: given a requirement ID, run only the checks whose name carries
  that ID. Return pass or fail for each.
- **find**: given a requirement ID, list the checks that carry it.

## Success

A check that is known to fail is reported as failing. A requirement with no checks is
reported as having none, never as passing.

## Conformance check

1. Add a check named with a made-up ID, `CAP-conformance.R1`, that always fails.
2. Run for that requirement. It reports one failing check.
3. Run for `CAP-conformance.R2`. It reports no checks found.
4. Remove the check.
