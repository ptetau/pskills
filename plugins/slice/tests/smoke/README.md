# Smoke run

One run of `/slice:run` on the wordfreq fixture. The spec is `spec.md` (already ratified).
The run made the plan, the domain model, and the interface. Then it built two slices.

The commits that the run made, oldest first:

- "Interface: 001-wordfreq" (trailer `Slice: interface`)
- "Slice S1: Count the words of a text" (trailer `Slice: S1`)
- "Slice S2: List the most common words" (trailer `Slice: S2`)

`slice.py status` ended with `next: all slices done`. S1 used 2 test rounds and 2 review
rounds. S2 used 1 test round and 1 review round.

`guard-log.jsonl` is the log of the guard hook (`SLICE_GUARD_LOG`), with the paths
shortened to `<project>` and `<plugin>`. It holds 11 calls of `slice:implementer`, 8 of
`slice:test-writer`, and 10 of `slice:reviewer`. The implementer touched no test file: its
only command that mentions the tests is `slice.py test <Sn>`. The test writer read only the
spec folder and wrote only in the tests folder.

To repeat the run, copy `spec.md` to `slice/001-wordfreq/` in a git project that has a
`slice/config.md`, then run `claude -p "/slice:run ..." --plugin-dir plugins/slice` with
`SLICE_GUARD_LOG` set.

## Flags for `claude -p`

A smoke run has no one to answer a permission prompt. Run it with these flags:

```
claude -p "/slice:run ..." --plugin-dir plugins/slice --model claude-opus-5-5 \
  --permission-mode acceptEdits --allowedTools "Bash Edit Write Read Glob Grep Agent Task Skill"
```

Without them, the run stops at the first edit or command. Use medium effort (the agents
and skills set it).
