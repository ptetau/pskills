# Adapter: checks-command

Fills the checks port with the commands in the "Checks" section of `pdlc/config.md`.

- **run all**: run the "all" command. Exit code 0 is pass. But once the project has any
  check files, a run that reports zero checks is a fail.
- **run for requirement**: run the "one requirement" command. Replace `{req}` with the
  requirement ID, in the form the project uses (`CAP-email.R3` or `CAP_email_R3`). If the
  command runs no checks, report "no checks found", not pass. Most test runners say how
  many tests ran. Zero means none found.
- **find**: search the project's check files for the requirement ID, in both forms.

If the project has no command that runs one requirement's checks, run all checks. Then
read the output for names that carry the ID.
