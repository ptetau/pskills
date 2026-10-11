# Adapter: inbox-files

Fills the inbox port with markdown files in `pdlc/inbox/`.

- **list**: read each `pdlc/inbox/IN-*.md`. The ID and name come from the first heading.
  The status comes from the `Status:` line.
- **read**: open `pdlc/inbox/IN-<id>-*.md`.
- **add**: take the highest intent number so far and add one. Pad the result to four
  digits: after `IN-0012` comes `IN-0013`. Create `pdlc/inbox/IN-<id>-<short-name>.md`
  from the intent template.
- **set status**: change the `Status:` word on the line under the heading.
- **write**: edit the file's sections.
