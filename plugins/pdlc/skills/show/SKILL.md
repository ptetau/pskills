---
name: show
description: >
  Records a verified pdlc change, has the recording reviewed, and proposes its merge.
  Plays each acceptance check in the real app: a browser for web apps, and a terminal for
  CLIs and libraries. Saves review.gif and the key frames in the folder of the change. A
  fresh, independent reviewer judges the frames. Then the proposal shows the GIF. Does not
  merge. Use when the user says "/pdlc:show", or when a change is verified.
---

# pdlc show

## Goal

Record each acceptance line of a verified change as `review.gif`, have a fresh reviewer
judge the frames, and propose the merge with the GIF. Never merge.

## Inputs

- The named change, else the first `in review` one with latest handoff `verify → show`.
- The visual port and adapter, `pdlc/config.md`, `pdlc/templates/proposal.md`.

## Outputs

- `visual.json`, `review.gif`, `frames/`: commit "Visual review CH-xxxx" (`Intent`, `Change`, `Review: pdlc/changes/CH-xxxx-…/review.gif`).
- Record with `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.
  Review: `python3 pdlc/bin/make_packets.py CH-xxxx visual` for one `pdlc:reviewer`.
- Gate fixes: "Update CH-xxxx: <what>".
- Handoff `show → user` (link, frames, lines shown of total) in "Propose CH-xxxx" (`Intent`, `Change`).
- An `app` problem: `building`, requirements `built`, handoff `show → build`, "Send back CH-xxxx: <stage>" (build); stop.

## Constraints

- Follow `pdlc/README.md`: "Bookkeeping on main" first, "Commits", "Who does what", "Rounds".
- Unverified: `/pdlc:verify` first.
- A capability uses `"kind": "terminal"`. A `setup:` caption marks a preparing step.
- Write only in the change folder. Fix scripts, never the app.
- Missing browser: `npx --prefix pdlc/.tools playwright install chromium`.

## Done when

- Proposed or sent back.
- Each line has a step. Each last frame, which you read, shows its caption.
