# DES-pdlc-review-checklist · How changes are reviewed

Status: agreed · Default: yes · Ask at init: no

## Rule

Each change gets independent reviews, one for each remit. A fresh reviewer does each
review, and sees only its packet:

- **tests**: the spec and the checks. Do not give the reviewer the code.
- **specification, security, quality, compliance, privacy**: the spec and the code.
  Do not give the reviewer the checks.

The files in `pdlc/reviews/` tell what each remit judges. `pdlc/config.md` tells which
remits run. A change passes review only when each remit passes.

## Why

How the work was done cannot influence a reviewer who sees only what the reviewer judges.
