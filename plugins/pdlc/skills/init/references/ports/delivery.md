# Port: delivery

Moves a change from a branch to main.

## Operations

- **start**: given a change or intent ID, a short name and a start point, create and
  switch to its branch. Return the branch name.
- **commit**: commit staged work with the trace trailers: `Intent`, `Change`, `Req`, and
  `Ticket` if there is one.
- **propose**: open a request to merge the branch (for example a pull request) with a
  summary and a table of requirements, checks and results. Say which requests go
  together: the intent's other changes, which merge with it, bottom of the stack first.
  Return its link.
- **gate**: run the merge check. Fail if any requirement the change touches is not
  `verified`, or if any other change of its intent is not `in review` or `merged`.
- **merged?**: given a change, say whether its branch has merged.

## Success

A merge is never proposed while the gate fails for the change itself. Other changes of
its intent that aren't ready yet don't stop the proposal, but nothing merges until the
gate passes for every change of the intent.

## Conformance check

1. Start a branch for a test change. Commit an empty file with trailers. Read the commit
   back. The trailers are there.
2. Run the gate on a change whose requirement is `built`. It fails.
3. Delete the branch.
