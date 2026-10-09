# DES-errors · The project's error codes

Status: agreed · Default: yes · Ask at init: no

## Rule

Every error the system can give has a code here, in `UPPER_SNAKE_CASE`. Acceptance lines,
Interface entries and checks all use these codes, so a check can expect the exact error.

| Code | Meaning | Whose fault | Retry helps? |
|---|---|---|---|

Add a row when a requirement needs a new error. Reuse a code when the meaning is the same.
Rows are added at intake and ready, never while a change is tested, built or verified.

The code is what checks and code match on. What a person sees (a message, a status) is
up to each requirement, and need not show the code. Where the caller can't see the code,
a check expects the exact message and status instead.

## Why

A check that expects "an error" passes for any error, even a typo. A named code makes the
check exact, and gives callers something stable to handle.
