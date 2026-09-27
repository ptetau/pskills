# Adapter: checks-command

Fills the checks port with the commands in the "Checks" section of `pdlc/config.md`.

- **run all**: run the "all" command. Exit code 0 is pass.
- **run for requirement**: run the "one requirement" command with `{req}` replaced by the
  ID. If it runs no checks, report "no checks found", not pass. Most test runners say how
  many tests ran; zero means none found.
- **find**: search the project's check files for the requirement ID.

If the project has no command for running one requirement's checks, run all checks and
read the output for names that carry the ID.
