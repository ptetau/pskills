# Port: review

Independent reviews of one change: one reviewer per remit, each seeing only its packet.

## Operations

- **review**: given a change and a list of remits, build one packet per remit. Have a
  separate, fresh reviewer judge each packet. Return each remit's result: pass or fail,
  and its problems. Each reviewer saves its result as `review/<remit>/result.md` in the
  change folder.

## Remits

`pdlc/reviews/` describes the remits: tests, specification, security, quality,
compliance, privacy. The project may edit them, and chooses in `pdlc/config.md` which
remits run.

The tests packet holds the spec and the checks, never the code. Every other packet holds
the spec and the code, never the checks.

## Success

A change with a problem in one remit fails that remit, whatever the others say.

## Conformance check

1. Take a change that lists one app file. Make a diff that also edits a second file.
2. Review the change with the specification remit. The review fails and names the second
   file.
