# Remit: tests

Default: yes

You judge the checks, not the code. You have not seen the code.

- Every acceptance line in the change spec has at least one check.
- Each check's name carries its requirement ID.
- Each check tests what the acceptance line says, through the "Interface" in the change
  spec. It doesn't depend on how the code is written inside.
- Each check could fail. A check that passes whatever the code does doesn't count.
- Checks are clear enough that a failure tells you what broke.
