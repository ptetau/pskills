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

Each pdlc file that the project did not edit matches the installed pdlc. The project keeps
each edited file, and the user sees its diff. `pdlc/version.json` records the version.

## Inputs

- The project, the installed pdlc plugin, and the paths that the user names to take from the
  plugin, if any.

## Outputs

- The commit "Upgrade pdlc", or no commit when pdlc is up to date.
- The report of the script, unchanged. It lists versions, counts, each kept file with its
  diff, and each spec that needs a newer form.

## Constraints

- `pdlc/README.md` binds, in particular "Core rules", "pdlc's own files", and "New behaviour
  needs approval".
- The script does the work: `python3 <this skill>/scripts/upgrade.py apply`. The skill never
  copies, edits, or merges a pdlc file, and never re-judges which files are edited.
- An edited file goes to the plugin version only when the user names it, with `--take <path>`.
- On a non-zero exit, the skill gives the message of the script to the user and stops.
- The upgrade runs no other stage.

## Done when

The script exited 0 and the user has its report.
