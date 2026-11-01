---
name: upgrade
description: >
  Brings the pdlc files of a project up to the installed pdlc version. Refreshes each file
  that the project did not edit. Keeps each edited file and shows its diff. Records the
  version, and reports each spec that needs a newer form. Use when the user says
  "/pdlc:upgrade", "upgrade pdlc", or "update the pdlc files". Also use when a pdlc message
  says that the project files are older than the plugin.
---

# pdlc upgrade

## Goal

After the upgrade, each pdlc file that the project did not edit is the same as in the
installed pdlc. The project keeps each file that it edited, and the user sees what is
different. `pdlc/version.json` records the version, so that the next upgrade knows where it
starts.

## Constraints

- The session model is a Sonnet 5.5 class model or above.
- The script does the work: `python3 <this skill>/scripts/upgrade.py apply`. The skill does
  not copy, edit, or merge a pdlc file itself.
- If the script stops for open changes, the skill tells the user, and does nothing more.
- The script exits with 2 for a `--take` path that is not a pdlc file. It exits with 4
  outside a pdlc project, and with 5 for a git error. It exits with 6 when it wrote files
  but did not commit them. For each of these, the skill tells the user the message of the
  script, and does nothing more.
- The script decides which files are edited. The skill does not change that decision. A file
  goes to the plugin version only when the user names it, through `--take <path>`.
- The upgrade does not write a spec. Each spec that needs a newer form is in the report, and in
  one intent that waits for approval.
- The upgrade does not run another stage.

## Inputs

- The project, and the installed pdlc plugin.
- The names of the files that the user wants to take from the plugin, if any.

## Outputs

- The commit "Upgrade pdlc", or no commit when pdlc is up to date.
- For the user, from the report of the script:
  - The versions: from, and to.
  - The counts of refreshed, added, removed, and kept files.
  - Each kept (edited) file, with its diff, and the command that takes the plugin version.
  - Each spec that needs a newer form, and the ID of the filed intent.
