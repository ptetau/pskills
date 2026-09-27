# DES-pdlc-review-checklist · How changes are reviewed

Status: agreed · Default: yes · Ask at init: no

## Rule

Every change gets independent reviews, one per remit, each by a fresh reviewer that sees
only its packet:

- **tests**: the spec and the checks, never the code;
- **specification, security, quality, compliance, privacy**: the spec and the code, never
  the checks.

What each remit judges is in `pdlc/reviews/`. Which remits run is in `pdlc/config.md`. A
change passes review only when every remit passes.

## Why

Reviewers who see only what they judge can't be swayed by how the work was done.
