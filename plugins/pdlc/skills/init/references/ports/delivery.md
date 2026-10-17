# Port: delivery

The delivery port moves a change from a branch to main.

## Operations

- **start**: the input is a change ID or an intent ID, a short name, and a start point.
  Create the branch, and switch to that branch. Return the branch name.
- **commit**: commit the staged work with the trace trailers `Intent`, `Change`, and
  `Req`. If there is a ticket, also add the `Ticket` trailer.
- **propose**: open a request to merge the branch, for example a pull request. Put a
  summary and a table of requirements, checks, and results in the request. Say which
  requests go together. The changes of one intent merge together, with the bottom of the
  stack first. Return the link to the request.
- **gate**: run the merge check. If a requirement that the change touches is not
  `verified`, the gate fails. The gate also fails if another change of the same intent is
  not `in review` or `merged`.
- **merged?**: the input is a change. Say if the branch of the change is merged.

## Success

The port does not propose a merge while the gate fails for the change itself. A change of
the same intent that is not ready does not stop the proposal. But nothing merges until the
gate passes for every change of the intent.

## Conformance check

1. Start a branch for a test change. Commit an empty file with the trailers. Read the
   commit back. The trailers are in the commit.
2. Run the gate on a change whose requirement is `built`. The gate fails.
3. Delete the branch.
