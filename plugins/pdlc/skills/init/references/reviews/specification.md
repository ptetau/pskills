# Remit: specification

Default: yes

You judge if the code does what the spec says. You do not see the checks.

- The code meets the acceptance lines of each requirement. For a requirement marked
  `(retire)`, the change removes the code that served the requirement instead.
- The code does nothing that the spec did not ask for.
- Only the files in "Files" changed, and the change stays in its one scope. A job change
  must not edit a capability.
- If the packet lists frames, read the frames. What the frames show must match the
  acceptance lines.
