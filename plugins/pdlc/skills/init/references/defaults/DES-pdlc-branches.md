# DES-pdlc-branches · How change branches are named

Status: agreed · Default: yes · Ask at init: yes

## Question

How should pdlc name the branches for changes?

- A · pdlc/<change>-<name> (recommended): for example `pdlc/CH-0031-email-templates`.
  Easy to spot, and sorts pdlc work together.
- B · your own pattern: tell pdlc the pattern your team already uses.

## Rule

A change's branch is `pdlc/<change ID>-<short name>`, for example
`pdlc/CH-0031-email-templates`. An intent that needs its own branch (see "Where pdlc
commits" in `pdlc/README.md`) uses its intent ID the same way:
`pdlc/IN-0012-password-reset`.
