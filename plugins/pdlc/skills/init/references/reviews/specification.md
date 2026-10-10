# Remit: specification

Default: yes

You judge whether the code does what the spec says. You have not seen the checks.

- Each requirement's acceptance lines are met by the code. For a requirement marked
  `(retire)`, the code that served it is removed instead.
- The code does nothing the spec didn't ask for.
- Only the files in "Files" changed. In a file listed with parts, only those parts
  changed. The change stays in its one scope: a job change never edits a capability's
  code.
- No old wording survives. The spec's title and summary, the cross-references in its
  requirements, and a README in "Files" show the behaviour as it is now: what the change
  adds is described, and nothing it removes or changes is still shown the old way. The
  README says how to run the checks, and names any seam a user can set.
- If frames are listed, read each one. Each must show what its caption claims, after the
  step, not the screen before it. A blank frame, or one that shows something else, is a
  problem.
