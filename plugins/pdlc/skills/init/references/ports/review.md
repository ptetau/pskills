# Port: review

Independent reviews of one change: one reviewer per remit, each seeing only its packet.

## Operations

- **review**: given a change and a list of remits, build one packet per remit and have a
  separate, fresh reviewer judge each. Return each remit's result: pass or fail, and its
  problems. Each result is saved as `review/<remit>/result.md` in the change folder.

## Remits

Described in `pdlc/reviews/`: tests, specification, security, quality, compliance,
privacy. The project may edit them and chooses which run in `pdlc/config.md`.

The tests packet holds the spec and the checks, never the code. Every other packet holds
the spec and the code, never the checks.

## Success

A change with a problem in one remit fails that remit, whatever the others say.

## Conformance check

1. Take a change that lists one app file. Make a diff that also edits a second file.
2. Review it with the specification remit. It fails and names the second file.
