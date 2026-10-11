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

How the work was done can't sway a reviewer who sees only what they judge.
