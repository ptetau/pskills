# Port: review

The review port gives independent reviews of one change. Each remit has one reviewer, and
each reviewer sees only its packet.

## Operations

- **review**: the input is a change and a list of remits. Build one packet for each remit.
  Give each packet to a separate, fresh reviewer to judge. Return the result of each
  remit: pass or fail, and its problems. Each result goes into
  `review/<remit>/result.md` in the change folder.

## Remits

The remits are tests, specification, security, quality, compliance, and privacy. Each
remit has a description in `pdlc/reviews/`. The project is permitted to edit the remits.
In `pdlc/config.md`, the project selects which remits run.

The tests packet holds the spec and the checks, but not the code. Each other packet holds
the spec and the code, but not the checks.

## Success

If a change has a problem in one remit, the change fails that remit. The results of the
other remits do not change the result for that remit.

## Conformance check

1. Use a change that lists one app file. Make a diff that also edits a second file.
2. Review the change with the specification remit. The remit fails, and its result gives
   the name of the second file.
