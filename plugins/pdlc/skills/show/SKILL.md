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

Record each acceptance line as `review.gif`. A fresh reviewer judges the frames. The
proposal shows the GIF. Do not merge.

## Inputs

- The named change, else the first `in review` one with handoff `verify → show`.
- The visual port and adapter, `pdlc/config.md`, `pdlc/templates/proposal.md`.

## Outputs

- `visual.json`, `review.gif`, `frames/`: `pdlc.py commit visual-review CH-xxxx`.
- Record: `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.
  Review: `python3 pdlc/bin/make_packets.py CH-xxxx visual` (one `pdlc:reviewer`), when "Reviews" lists `visual`.
- Gate fixes: `pdlc.py commit update CH-xxxx`.
- Handoff (link, frames, lines shown): `pdlc.py handoff CH-xxxx show user`, then `pdlc.py commit propose CH-xxxx`.
- An `app` problem: `pdlc.py set CH-xxxx --status building --reqs built`, `pdlc.py handoff CH-xxxx show build`, then `pdlc.py commit send-back CH-xxxx --text build`. Stop.

## Constraints

- Follow `pdlc/README.md`: "Bookkeeping on main" first, "Commits", "Who does what", "Rounds".
- Unverified: run `/pdlc:verify`.
- A capability uses `"kind": "terminal"`. A `setup:` caption marks a preparing step.
- Write only in the change folder. Fix scripts, not the app.
- Missing browser: `npx --prefix pdlc/.tools playwright install chromium`.

## Done when

- Proposed or sent back.
- Each line has a step. Each last frame, which you read, shows its caption.
