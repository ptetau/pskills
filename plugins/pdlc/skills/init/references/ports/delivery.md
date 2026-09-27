# Port: delivery

Moves a change from a branch to main.

## Operations

- **start**: given a change ID and short name, create and switch to its branch. Return the
  branch name.
- **commit**: commit staged work with the trace trailers: `Intent`, `Change`, `Req`, and
  `Ticket` if there is one.
- **propose**: open a request to merge the branch (for example a pull request) with a
  summary and a table of requirements, checks and results. Return its link.
- **gate**: run the merge check. Fail if any requirement the change touches is not
  `verified`.
- **merged?**: given a change, say whether its branch has merged.

## Success

A merge is never proposed while the gate fails.

## Conformance check

1. Start a branch for a test change. Commit an empty file with trailers. Read the commit
   back. The trailers are there.
2. Run the gate on a change whose requirement is `built`. It fails.
3. Delete the branch.
