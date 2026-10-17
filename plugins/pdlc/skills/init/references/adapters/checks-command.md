# Adapter: checks-command

The checks-command adapter fills the checks port with the commands in the "Checks"
section of `pdlc/config.md`.

- **run all**: run the "all" command. Exit code 0 is a pass. But once the project has any
  check files, a run that reports zero checks is a fail.
- **run for requirement**: run the "one requirement" command. Replace `{req}` with the
  requirement ID, in the form that the project uses (`CAP-email.R3` or `CAP_email_R3`).
  If the command runs no checks, report "no checks found", not a pass. Most test runners
  tell how many tests ran. Zero tests means that the runner found no checks.
- **find**: search the check files of the project for the requirement ID, in the two
  forms.

If the project has no command that runs the checks of one requirement, run all the checks.
Then read the output for the names that carry the ID.
