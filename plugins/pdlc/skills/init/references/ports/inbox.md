# Port: inbox

Where intents come in, and where pdlc keeps their status.

## Operations

- **list**: return every intent's ID, name and status.
- **read**: given an ID, return the intent's full text.
- **add**: given a name and a short "what and why", create an intent with status `new`.
  Return its ID.
- **set status**: given an ID and a status, record the status. Allowed statuses: new,
  specifying, ready, building, in review, done, paused, cancelled.
- **write**: given an ID, save updated requirements, changes or notes.

## Success

Reading an intent back returns the text it was added with. After **set status**, **list**
shows that status.

## Conformance check

1. Add an intent called "conformance test".
2. List intents. It appears with status `new`.
3. Set its status to `cancelled`. List again. It shows `cancelled`.
4. Read it. The text matches what you added.
