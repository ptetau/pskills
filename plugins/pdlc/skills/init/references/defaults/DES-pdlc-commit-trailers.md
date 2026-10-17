# DES-pdlc-commit-trailers · What every pdlc commit carries

Status: agreed · Default: yes · Ask at init: no

## Rule

Each commit that pdlc makes has a subject from the list below. The commit ends with these
lines, after a blank line:

```
Intent: IN-0012
Change: CH-0031
Req: CAP-email.R3
Ticket: PROJ-88
```

`Req` is permitted to list more than one ID, with commas between the IDs. If there is no ticket, omit
`Ticket`.

- Every commit carries `Intent`.
- On the branch of a change, every commit also carries `Change`. This includes a commit
  that only sets the status of the intent.
- A commit carries `Req` exactly when the commit changes files outside `pdlc/` (code,
  checks, the README). A commit that changes only files in `pdlc/` has no `Req`.
  Examples are a commit that starts a branch, logs progress, or sets statuses.

Keep all trailers in one block at the end of the message. Put the trailers in this order:
`Intent`, `Change`, `Req`, `Ticket`, `Review` (the GIF of the visual review), and then
any other trailers (for example `Co-Authored-By`). Then git shows them all as trailers.
For the trace, the important point is that the lines are in the message.

## Subjects

The first line of each commit must be one of the subjects below, exactly. In a subject,
`<change>` is the ID of the change (`CH-0031`), `<intent>` is the ID of the intent
(`IN-0012`), and `<n>` is a number. Any other `<...>` is a few words. A merge keeps the
subject that git gives. On a pdlc branch, a hook in the pdlc plugin checks each new commit
against this list and the trailers above. Fix each problem that the hook names at once,
with `git commit --amend`.

- `Specify <intent>: <intent name>` (intake)
- `Ready <intent>: <intent name>` (ready)
- `Plan <intent>: <change names>` (change)
- `Convention <design spec>` (conventions)
- `Start <change>` (tests: branch, base and statuses)
- `Tests <change>` (tests: the checks)
- `Lock tests <change>` (tests: the lock line)
- `Review tests <change>` (tests: the packet and result)
- `Tests reviewed <change>` (tests: status and handoff)
- `Build <change>: <what changed>` (build: the app files)
- `Built <change>` (build: steps, statuses and handoff)
- `Visual review <change>` (show)
- `Verify <change>: round <n>` (verify: packets, results, new intents)
- `Send back <change>: <stage>` (verify: the handoff after a failed round)
- `Verified <change>` (verify)
- `Propose <change>` (verify)
- `Update <change>: <what>` or `Update <intent>: <what>` (any other record: a base, a
  "Files" entry, a fix that the merge check requests)
- `Stop <change>: <why>` or `Stop <intent>: <why>` (ship, when it stops)
- `Set up pdlc`, `Upgrade pdlc`, `Record merges`, `Board: record card keys` (on main)

## Why

These lines connect each line of code to its requirement and its intent. One subject for
each step makes the history of every project read the same way.
