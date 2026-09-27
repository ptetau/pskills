# Port: inbox

Where intents come in and where their status is kept.

## Operations

- **list**: return every intent's ID, name and status.
- **read**: given an ID, return the intent's full text.
- **add**: given a name and a short "what and why", create an intent with status `new` and
  return its ID.
- **set status**: given an ID and a status, record it. Allowed statuses: new, specifying,
  ready, building, in review, done, paused, cancelled.
- **write**: given an ID, save updated requirements, changes or notes.

## Success

An intent added can be read back with the same text. A status set is the status listed.

## Conformance check

1. Add an intent called "conformance test".
2. List intents. It appears with status `new`.
3. Set its status to `cancelled`. List again. It shows `cancelled`.
4. Read it. The text matches what was added.
