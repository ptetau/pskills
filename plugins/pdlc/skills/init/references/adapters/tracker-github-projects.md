# Adapter: tracker-github-projects

Fills the tracker port with a GitHub project board (Projects).

## Setup

In `pdlc/config.md`, under "Tracker settings":

- owner: the user or organisation that owns the project
- project: the project number (from its URL)
- status field: the name of the single-select field used for columns, usually `Status`

Each column named in "Board columns" must be an option of that field.

## Tools

Use the `gh` CLI or GitHub tools that cover projects, whichever this session has. The `gh`
commands are `gh project item-list`, `gh project item-create`, `gh project item-edit` and
`gh project field-list`. If this session has neither, stop and say so.

## Operations

- **show intent**: if the intent's `Ticket` is `none`, create a draft item titled
  `IN-xxxx · <name>` with a body that links the intent file. Write the item's ID into the
  intent's `Ticket`. Then set the status field to the column for the intent's status.
- **show change**: the same, titled `CH-xxxx · <name> (IN-xxxx)`, with the change's
  `Ticket`. Once the change has a pull request, add a link to the pull request in the
  item's body. GitHub projects have no sub-items for drafts, so the title carries the
  intent ID.

Look an item up by its ID first. Never create a second item for an ID that has one.
