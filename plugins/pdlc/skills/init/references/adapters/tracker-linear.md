# Adapter: tracker-linear

The tracker-linear adapter fills the tracker port with Linear.

## Setup

The tracker-linear adapter reads these settings from `pdlc/config.md`, under "Tracker
settings":

- team: the Linear team key, for example `ENG`
- project: a Linear project name, or `none`

Each column in "Board columns" must be a workflow state of that team.

## Tools

Use the Linear tools that this session has, for example the Linear MCP server. If this
session has no Linear tools, stop and tell the user.

## Operations

- **show intent**: if the `Ticket` of the intent is `none`, create an issue in the team
  with the title `IN-xxxx · <name>`. Put a link to the intent file in the description of
  the issue. Write the key of the issue (for example `ENG-88`) into the `Ticket` of the
  intent. Then set the state of the issue to the column for the status of the intent.
- **show change**: do the same steps, with the title `CH-xxxx · <name>`. Create the issue
  as a sub-issue of the issue of the intent. Write the key of the sub-issue into the
  `Ticket` of the change. When the change has a pull request, add the link to the pull
  request.

First, find the issue by its key. Do not create a second issue for an ID that has an issue.

Linear links each commit and each pull request that contains an issue key to that issue.
Thus, the `Ticket` trailer on each commit appears on the issue.
