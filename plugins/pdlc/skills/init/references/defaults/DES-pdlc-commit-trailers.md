# DES-pdlc-commit-trailers · What every pdlc commit carries

Status: agreed · Default: yes · Ask at init: no

## Rule

Every commit made by pdlc ends with these lines, after a blank line:

```
Intent: IN-0012
Change: CH-0031
Req: CAP-email.R3
Ticket: PROJ-88
```

`Req` may list several IDs, separated by commas. Leave out `Ticket` if there is none.

All trailers go in one final block with no blank lines inside it. If other trailers are
added too (for example `Co-Authored-By`), put them in the same block, after pdlc's. Git
only reads the last block as trailers.

## Why

These lines are how any line of code leads back to its requirement and intent.
