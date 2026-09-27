# DES-pdlc-ids · How pdlc names things

Status: agreed · Default: yes · Ask at init: no

## Rule

- Intents: `IN-` and four digits, for example `IN-0012`.
- Changes: `CH-` and four digits, for example `CH-0031`.
- Specs: `JOB-`, `CAP-` or `DES-` and a short lowercase name with dashes, for example
  `CAP-email`.
- Requirements: the spec ID, a dot, `R` and a number, for example `CAP-email.R3`.
- IDs never change and are never reused.

## Why

Short, stable IDs make every link greppable, in files, commits and check names.
