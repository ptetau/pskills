# Port: inbox

The inbox port receives intents, and keeps the status of each intent.

## Operations

- **list**: return the ID, name, and status of each intent.
- **read**: the input is an ID. Return the full text of that intent.
- **add**: the input is a name and a short "what and why". Create an intent with the
  status `new`. Return the ID of the intent.
- **set status**: the input is an ID and a status. Record that status. The allowed
  statuses are: new, specifying, ready, building, in review, done, paused, cancelled.
- **write**: the input is an ID. Save the updated requirements, changes, or notes of that
  intent.

## Success

When the port adds an intent, **read** returns the same text for that intent. When the
port sets a status, **list** shows that status.

## Conformance check

1. Add an intent called "conformance test".
2. List the intents. The intent appears with the status `new`.
3. Set the status of the intent to `cancelled`. List the intents again. The intent shows
   `cancelled`.
4. Read the intent. The text is the same as the added text.
