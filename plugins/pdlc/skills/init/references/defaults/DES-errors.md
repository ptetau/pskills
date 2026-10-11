# DES-errors · The project's error codes

Status: agreed · Default: yes · Ask at init: no

## Rule

Every error the system can give has a code here, in `UPPER_SNAKE_CASE`, for example
`INVALID_ADDRESS`. Acceptance lines, Interface entries and checks all use these codes, so a
check can expect the exact error.

| Code | Meaning | Whose fault | Retry helps? |
|---|---|---|---|

If a requirement needs a new error, add a row. If the meaning is the same, reuse a code.
Add rows at intake and ready, never while a change is in tests, build or verify. When you
add a row, leave `Default:` as it is. Write each row the same way:

- the code in backticks;
- "Whose fault": `caller`, `system` or `outside service`;
- "Retry helps?": `yes` or `no`.

Checks and the app's code match on the error code. Each requirement decides what a person
sees, such as a message or a status. That message or status need not show the error code.
If the caller can't see the error code, a check expects the exact message and status
instead.

## Why

A check that expects "an error" passes for any error, even a typo. A named code makes the
check exact, and gives callers something stable to handle.
