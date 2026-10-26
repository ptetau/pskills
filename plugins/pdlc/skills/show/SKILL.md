---
name: show
description: >
  Records a built pdlc change for its visual review. Plays each acceptance check in the
  real app: a browser for web apps, and a terminal for CLIs and libraries. Saves
  review.gif and the key frames in the folder of the change, for the reviewers and the
  pull request. Use when the user says "/pdlc:show", or when a change is built.
---

# pdlc show

## Goal

Show makes a short GIF, `review.gif`, and its frames. They show the change do what its
spec says, one acceptance line after the other, as a user meets the change.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- The change is the one that the user names, or else the first `building` change whose
  requirements are all `built`. Show works on the branch of the change.
- Every change gets its show, also with nothing new on screen, and show does not wait for
  later changes. A capability shows its interface in a terminal (`"kind": "terminal"`),
  also in a web app.
- `pdlc/changes/CH-xxxx-…/visual.json` obeys the visual port and its adapter in
  `pdlc/config.md`.
- Each acceptance line gets one or more steps, in order. The first step of a line sets the
  caption: the requirement ID, then the line in a few words. The count of lines matches
  the change spec.
- The steps show the behaviour as a user meets it:
  - A web app: pages and clicks.
  - A CLI: commands and their output.
  - A library: a short script that calls the interface.
- A helper script lives in the change folder. Paths are relative to the project root, so
  that anyone can record again.
- A terminal script ends with a step that runs all checks and shows them pass. The
  recorder runs commands only in terminal scripts, so a web script has no such step.
- A terminal frame scrolls like a real terminal, and shows the newest lines, also errors.
  The output of each step stays under one screen, so that its command stays in view.
- The recorder is `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json
  pdlc/changes/CH-xxxx-…`. It needs Node, `playwright`, `gifenc`, and `pngjs`.
- After `missing <name>`, the packages go into `pdlc/.tools/` with
  `npm install --prefix pdlc/.tools playwright gifenc pngjs`. With no browser,
  `npx --prefix pdlc/.tools playwright install chromium` adds one. `.gitignore` lists
  `pdlc/.tools/`.
- Each frame shows what its caption claims. The recorder fails, and names the step, for a
  blank frame. It also fails for a click, typing, a key, or a command that changes nothing
  on screen.
- A failed recording means a wrong script: a wrong selector, a missing step, or a command
  that prints nothing. Such a command prints its result, or the next command reads it.
- A step has `"unchanged": true` only when its acceptance line says that nothing changes.
- Show reads the last frame of each acceptance line itself. A frame with an error,
  incorrect content, or the screen from before the step means a wrong script.
- Show corrects the script and records again. Show does not correct the app.

## Inputs

- `pdlc/README.md`, the shared rules.
- The change spec and its `handoff.md`.
- The visual port, its adapter, and the "Visual" section of `pdlc/config.md`.

## Outputs

- `visual.json`, any helper script, `review.gif`, and `frames/` in the change folder.
- The handoff `show → verify`: what the GIF shows, frame by frame, and how many acceptance
  lines it shows, out of how many.
- One commit of all these files, "Visual review CH-xxxx", with the trailers `Intent`,
  `Change`, and `Review: pdlc/changes/CH-xxxx-…/review.gif`.
- For the user: `/pdlc:verify` is next.
- Show is done when the GIF shows each acceptance line, and each last frame shows what its
  caption claims.
