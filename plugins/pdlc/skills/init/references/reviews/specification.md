# Remit: specification

Default: yes

You judge if the code does what the spec says. You do not see the checks.

- The code meets the acceptance lines of each requirement. For a requirement marked
  `(retire)`, the change removes the code that served the requirement instead.
- The code does nothing that the spec did not ask for.
- Only the files in "Files" changed. In a file that "Files" lists with parts, only those
  parts changed. The change stays in its one scope. A job change must not edit the code of
  a capability.
- No old wording survives. The title and the summary of the spec, the cross-references in
  its requirements, and a README in "Files" show the behaviour as it is now. They include
  what the change adds. Nothing that the change removes or changes still shows the old
  way. The README says how to run the checks, and names any seam that a user can set.
- The spec text, the README text, and the code comments in the change follow the writing
  rules (`DES-writing-style`, in the packet). Each break of a rule is a problem. Give the
  line and the rule.
- Each finding under "Writing check" in the packet is a problem, unless you judge the
  finding to be a false alarm. For each false alarm, say why under "Notes".
- If the packet lists frames, read each frame. Each frame must show what its caption
  claims, after the step, not the screen before the step. A blank frame, or a frame that
  shows something else, is a problem.
