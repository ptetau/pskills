# Adapter: tracker-github-projects

The tracker-github-projects adapter fills the tracker port with a GitHub project board
(Projects).

## Setup

The tracker-github-projects adapter reads these settings from `pdlc/config.md`, under
"Tracker settings":

- owner: the user or organisation that owns the project
- project: the project number (from its URL)
- status field: the name of the single-select field for the columns, usually `Status`

Each column in "Board columns" must be an option of the status field.

## Tools

Use the tool that this session has for GitHub projects: the `gh` CLI
(`gh project item-list`, `gh project item-create`, `gh project item-edit`,
`gh project field-list`), or GitHub tools that cover projects. If this session has
no such tool, stop and tell the user.

## Operations

- **show intent**: if the `Ticket` of the intent is `none`, create a draft item with the
  title `IN-xxxx · <name>`. Put a link to the intent file in the body of the item. Write
  the ID of the item into the `Ticket` of the intent. Then set the status field to the
  column for the status of the intent.
- **show change**: do the same steps, with the title `CH-xxxx · <name> (IN-xxxx)` and the
  `Ticket` of the change. When the change has a pull request, add a link to the pull
  request in the body of the item. GitHub projects have no sub-items for drafts. Thus, the
  title carries the intent ID.

First, find the item by its ID. Do not create a second item for an ID that has an item.
