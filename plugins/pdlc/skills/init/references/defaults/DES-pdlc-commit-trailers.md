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

Keep all trailers in one final block where you can. If other trailers are added (for
example `Co-Authored-By`), put them in the same block, after pdlc's, so git shows them as
trailers. What matters for the trace is that the lines are in the message.

## Why

These lines are how any line of code leads back to its requirement and intent.
