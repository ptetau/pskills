# Remit: tests

Default: yes

You judge the checks, not the code. You have not seen the code.

- Every acceptance line in the change spec has at least one check, except under a
  requirement marked `(retire)`: those get no check, and any check that only proved them
  is gone.
- Each check's name carries its requirement ID.
- Each check tests what the acceptance line says, through the "Interface" in the change
  spec. It doesn't depend on how the code is written inside.
- Each line is proved at the surface it names. A line where the person clicks is proved
  by a check that clicks and reads what shows, not only by a check of a helper below it.
  A line that depends on the current time sets the clock through a seam. Leaving such a
  line to manual checks, when a stand-in seam could reach it, is a problem, not a
  follow-up.
- Each check could fail. A check that passes whatever the code does doesn't count.
- A correct app would pass each check. A fake that stands in for something real uses the
  real thing's names and behaviour, so the check doesn't prove only the fake.
- No check can hang: anything that waits on the app has a time limit.
- Every error code listed in the Interface has a check that expects that exact code.
- Checks control time, randomness and vendors only through the Interface's "Test seams".
- Checks are clear enough that a failure tells you what broke.
