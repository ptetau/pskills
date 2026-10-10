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
  A line that depends on the current date or time sets the clock through a seam at that
  same surface: a check that runs a command sets it by the command's environment
  variable or flag. Using the real clock, or setting the time only on a helper below the
  surface, is a problem. So is leaving such a line to manual checks when a stand-in seam
  could reach it.
- Each check could fail: it fails on a plausible wrong version of the code (see "Wrong
  versions"). A check that passes whatever the code does doesn't count.
- A correct app would pass each check. A fake that stands in for something real uses the
  real thing's names and behaviour, so the check doesn't prove only the fake.
- No check can hang: anything that waits on the app has a time limit.
- Every error code listed in the Interface has a check that expects that exact code.
- Checks control time, randomness and vendors only through the Interface's "Test seams".
- Checks are clear enough that a failure tells you what broke.

## Wrong versions

For each check, name one realistic wrong version of the code and decide whether the
check fails on it. Write one line per check under "Wrong versions" in your result: the
check, the wrong version, and `fails` or `passes`. A check that passes a plausible wrong
version is a problem: name the value or line that would catch it.

Watch for these traps:

- Examples that also fit a wrong rule. A rule about order tested with items already in
  that order, or in alphabetical order. Values that come out the same whether rounded
  up, down or to the nearest. Text already in the case the rule asks for.
- A limit not tested exactly at the edge and one past it: for "at most 20", 20 passes and
  21 fails. Values near the edge prove nothing about the edge.
- A rule about a whole class tested without a non-member. "Any other value is an error"
  needs a value close to an allowed one (another case, a space, a prefix), not only a few
  far-off ones. "Only the owner may" needs someone who isn't the owner.
