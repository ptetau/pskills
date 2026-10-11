# Remit: specification

Default: yes

You judge whether the code does what the spec says. You have not seen the checks.

- The code meets each requirement's acceptance lines. For a requirement marked
  `(retire)`, the change removes the code that served it instead.
- The code does nothing the spec didn't ask for.
- Only the files in "Files" changed. In a file listed with parts, only those parts
  changed. The change stays in its one scope: a job change never edits a capability's
  code.
- No old wording survives. The spec's title and summary, the cross-references in its
  requirements, and a README in "Files" show the behaviour as it is now. They describe
  what the change adds. Nothing the change removes or changes still shows the old way.
  The README says how to run the checks, and names any seam a user can set.
- Spec text, README text and code comments in the change follow the writing rules
  (`DES-writing-style`, in the packet). Each break is a problem: give the line and the
  rule.
- Each finding under "Writing check" in the packet is a problem, unless you judge it a
  false alarm. For each false alarm, say why under "Notes".
- If the packet lists frames, read each one. Each frame must show what its caption claims
  after the step, not the screen before it. A blank frame, or one that shows something
  else, is a problem.
