# Adapter: tracker-linear

Fills the tracker port with Linear.

## Setup

In `pdlc/config.md`, under "Tracker settings":

- team: the Linear team key, for example `ENG`
- project: a Linear project name, or `none`

Each column named in "Board columns" must be a workflow state of that team.

## Tools

Use the Linear tools this session has (for example the Linear MCP server). If this session
has none, stop and say so.

## Operations

- **show intent**: if the intent's `Ticket` is `none`, create an issue in the team titled
  `IN-xxxx · <name>`. Put a link to the intent file in the issue's description. Write the
  issue's key (for example `ENG-88`) into the intent's `Ticket`. Then set the issue's state
  to the column for the intent's status.
- **show change**: the same, titled `CH-xxxx · <name>`, created as a sub-issue of the
  intent's issue. Write the sub-issue's key into the change's `Ticket`. When there is a
  pull request, add its link.

Look an issue up by its key first. Never create a second issue for an ID that has one.

Linear links commits and pull requests that mention an issue key, so the `Ticket` trailer
on each commit shows up on the issue.
