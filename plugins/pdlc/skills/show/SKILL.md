---
name: show
description: >
  Records a pdlc change being verified visually: plays each acceptance check in the real
  app (a browser for web apps, a terminal for CLIs and libraries) and saves review.gif
  plus key frames in the change's folder, for the reviewers and the pull request. Use
  when the user says "/pdlc:show", or a change has been built.
---

# pdlc show

Makes a short GIF of the change doing what its spec says.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step, then read
the change's `handoff.md`.

## 1. Pick the change

Use the change the user named. Otherwise take the first change with status `building`
whose requirements are all `built`. Switch to its branch.

Every change gets its show, even one with nothing new on screen yet. A capability shows
its interface in a terminal (`"kind": "terminal"`), even in a web app. Never hold show
until later changes land.

## 2. Get the recorder ready

The recorder is `pdlc/bin/record_gif.mjs`. It needs Node, `playwright`, `gifenc` and `pngjs`.
If recording (step 4) stops with `missing <name>`, install them into `pdlc/.tools/`:
`npm install --prefix pdlc/.tools playwright gifenc pngjs`, then
`npx --prefix pdlc/.tools playwright install chromium` if no browser is found. Make sure
`pdlc/.tools/` is in `.gitignore`.

## 3. Write the script

Follow the visual port and its adapter in `pdlc/config.md`. Write
`pdlc/changes/CH-xxxx-…/visual.json`:

- One or more steps for each acceptance line, in order. The first step for each line sets
  a caption: the requirement ID, then the acceptance line in a few words. Every line gets
  a step; count them against the change spec.
- Show the behaviour the way a user meets it: pages and clicks for a web app, commands and
  their output for a CLI, a short script calling the interface for a library.
- A helper script a step runs lives in the change folder. Paths are relative to the
  project root, so anyone can record it again.
- For a terminal script, end with a step that runs all checks and shows they pass. The
  recorder runs commands only in terminal scripts, so a web script leaves this out.
- A terminal frame scrolls like a real terminal: it shows the newest lines, errors
  included. Keep each step's output under one screen, so its command stays in view.

## 4. Record

Run `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.

A frame must show what its caption claims. The recorder fails, naming the step, when a
frame is blank, or when a click, typing, a key press or a command changes nothing on
screen. Then fix the script and record again: a wrong selector, a missing step, or a
command that prints nothing (print its result, or read it with the next command). Set
`"unchanged": true` on a step only when its acceptance line says nothing changes.

Then read the last frame of each acceptance line yourself. If it shows an error, the
wrong thing, or the screen before the step, fix the script and record again. Never fix
the app here.

## 5. Finish

1. Write `handoff.md` for verify: what the GIF shows, frame by frame, and how many
   acceptance lines it shows out of how many.
2. Commit `visual.json`, any helper script, `review.gif`, `frames/` and the handoff
   together ("Visual review CH-xxxx"), with the trailers `Intent`, `Change` and
   `Review: pdlc/changes/CH-xxxx-…/review.gif`.
3. Tell the user `/pdlc:verify` is next.
