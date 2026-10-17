# DES-pdlc-commit-trailers · What every pdlc commit carries

Status: agreed · Default: yes · Ask at init: no

## Rule

Each commit that pdlc makes ends with these lines, after a blank line:

```
Intent: IN-0012
Change: CH-0031
Req: CAP-email.R3
Ticket: PROJ-88
```

`Req` is permitted to list more than one ID, with commas between the IDs. If there is no ticket, omit
`Ticket`.

A commit that changes only files in `pdlc/` needs `Intent` and `Change`, but not `Req`.
Examples are a commit that starts a branch, logs progress, or sets statuses. Each commit
that changes other files needs all three: `Intent`, `Change`, and `Req`.

Keep all trailers in one block at the end of the message, when possible. If the commit
has other trailers (for example `Co-Authored-By`), put them in the same block, after the
pdlc trailers. Then git shows them as trailers. For the trace, the important point is that
the lines are in the message.

## Why

These lines connect each line of code to its requirement and its intent.
