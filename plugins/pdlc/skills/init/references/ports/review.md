# Port: review

An independent review of one change. The reviewer did not write the change.

## Operations

- **review**: given a change spec, the diff for its branch, and the design specs it lists,
  return pass or fail and a list of problems. Each problem has a file, a line, what is
  wrong, and the rule it breaks.

## What the reviewer checks

1. Scope: only the change's files, one job or capability, and a job never edits a capability.
2. Acceptance: each acceptance check is met and a check really proves it.
3. Conventions: the design specs are followed.
4. Trace: each commit has its trailers and each check names its requirement ID.

## Success

A diff that edits a file outside the change's list fails review.

## Conformance check

1. Take a change that lists one file. Make a diff that also edits a second file.
2. Review it. It fails, and names the second file as out of scope.
