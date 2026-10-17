# Adapter: inbox-files

The inbox-files adapter fills the inbox port with markdown files in `pdlc/inbox/`.

- **list**: read each `pdlc/inbox/IN-*.md` file. The ID and the name come from the first
  heading. The status comes from the `Status:` line.
- **read**: open `pdlc/inbox/IN-<id>-*.md`.
- **add**: add one to the highest intent number so far. Pad the result to four digits.
  Create `pdlc/inbox/IN-<id>-<short-name>.md` from the intent template.
- **set status**: change the `Status:` word on the line under the heading.
- **write**: edit the sections of the intent file.
