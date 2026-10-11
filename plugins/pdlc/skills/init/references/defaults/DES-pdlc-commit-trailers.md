# DES-pdlc-commit-trailers · What every pdlc commit carries

Status: agreed · Default: yes · Ask at init: no

## Rule

Every commit pdlc makes has a subject from the list below. It ends with these lines, after
a blank line:

```
Intent: IN-0012
Change: CH-0031
Req: CAP-email.R3
Ticket: PROJ-88
```

`Req` may list several IDs, separated by commas. If there is no ticket, leave out `Ticket`.

- Every commit carries `Intent`.
- On a change's branch, every commit also carries `Change`, even one that only sets the
  intent's status.
- A commit carries `Req` exactly when it changes files outside `pdlc/` (code, checks,
  the README). A commit that only changes `pdlc/` files has no `Req`.

Keep all trailers in one final block, so git shows them all as trailers. Put them in this
order: `Intent`, `Change`, `Req`, `Ticket`, `Review` (the visual review's GIF), then any
others (for example `Co-Authored-By`). For the trace, what matters is that the lines are
in the message.

## Subjects

The first line is one of these, exactly. `<change>` is the change's ID (`CH-0031`),
`<intent>` the intent's (`IN-0012`), `<n>` a number, and any other `<...>` a few words.
A merge keeps git's own subject. On a pdlc branch, a hook in the pdlc plugin checks each
new commit against this list and the trailers above. Fix what the hook names at once,
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
  "Files" entry, a fix the merge check asks for)
- `Stop <change>: <why>` or `Stop <intent>: <why>` (ship, when it stops)
- `Set up pdlc`, `Upgrade pdlc`, `Record merges`, `Board: record card keys` (on main)

## Why

These lines are how any line of code leads back to its requirement and intent. One
subject per step makes every project's history read the same way.
