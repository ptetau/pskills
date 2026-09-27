---
name: build
description: >
  Builds one pdlc change spec on its own branch, check first. For each step it writes a
  failing check named with the requirement ID, makes it pass, tidies up, and commits with
  trace trailers. Marks requirements built. Use when the user says "/pdlc:build", or wants
  a planned pdlc change built.
---

# pdlc build

Turns one change spec into a branch with the change and its checks.

Read `pdlc/README.md` first and follow it. The change spec should be all you need. Read
the design specs it lists before writing anything.

## 1. Pick the change

- If the user named a change, use it.
- If they named an intent, take its first change that isn't `merged`.
- Otherwise take the oldest intent with status `ready` or `building`, and its first change
  that isn't `merged`.

Every earlier change in the intent's list must be `merged`. If one isn't, stop and say
which, because this change may rely on it.

## 2. Start

- Start a branch through the delivery port. Write its name into the change spec's header.
- Set the change to `building`. Set the intent to `building`. Tell the tracker port.

## 3. Work each step

For each step not yet ticked, in order:

1. **Red.** Write the check. Its name starts with the requirement ID. Run it through the
   checks port. It must fail. If it passes already, the check proves nothing: fix it.
2. **Green.** Write the least change that makes the check pass. Run it again.
3. **Tidy.** Remove repetition and follow the design specs. Run all checks. Everything
   must still pass.
4. **Commit** through the delivery port, with the trailers `Intent`, `Change`, `Req` and
   `Ticket` if there is one. Tick the step and add a line to the progress log in the same
   commit.

Only touch the files the change spec lists. If you need another file, stop and ask the
user. If they agree, add it to the change spec's "Files" first.

## 4. Finish

- Set each requirement in the change to `built` in its spec file. Remove any requirement
  marked `(retire)` from its spec, along with the code and checks it no longer needs.
- Commit with the message "Built CH-xxxx" and the trailers.
- Tell the user the change is built, and that `/pdlc:verify` is next.

## Stop and ask when

- A check you didn't expect starts failing.
- The same fix has failed twice.
- Something in the change spec is unclear.
