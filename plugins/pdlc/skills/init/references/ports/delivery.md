# Port: delivery

The delivery port moves a change from a branch to main.

## Operations

- **start**: the input is a change ID and a short name. Create the branch of the change,
  and switch to that branch. Return the branch name.
- **commit**: commit the staged work with the trace trailers `Intent`, `Change`, and
  `Req`. If there is a ticket, also add the `Ticket` trailer.
- **propose**: open a request to merge the branch, for example a pull request. Put a
  summary and a table of requirements, checks, and results in the request. Return the
  link to the request.
- **gate**: run the merge check. If a requirement that the change touches is not
  `verified`, the gate fails.
- **merged?**: the input is a change. Say if the branch of the change is merged.

## Success

The port does not propose a merge while the gate fails.

## Conformance check

1. Start a branch for a test change. Commit an empty file with the trailers. Read the
   commit back. The trailers are in the commit.
2. Run the gate on a change whose requirement is `built`. The gate fails.
3. Delete the branch.
