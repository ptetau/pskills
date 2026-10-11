---
name: show
description: >
  Records a pdlc change for visual review. Plays each acceptance check in the real app: a
  browser for web apps, a terminal for CLIs and libraries. Saves review.gif and key frames
  in the change's folder, for the reviewers and the pull request. Use when the user says
  "/pdlc:show", or a change has been built.
---

# pdlc show

Makes a short GIF of the change doing what its spec says.

Read `pdlc/README.md` first and follow it. Start with its "Before any work" step. Then
read the change's `handoff.md`.

## 1. Pick the change

If the user named a change, use that change. Otherwise, take the first change with status
`building` whose requirements are all `built`. Switch to the change's branch.

Every change gets its show, even one with nothing new on screen yet. A capability shows
its interface in a terminal (`"kind": "terminal"`), even in a web app. Never hold show
until later changes land.

## 2. Get the recorder ready

The recorder is `pdlc/bin/record_gif.mjs`. It needs Node, `playwright`, `gifenc` and
`pngjs`. If recording (step 4, record) stops with `missing <name>`, install these packages
into `pdlc/.tools/`: `npm install --prefix pdlc/.tools playwright gifenc pngjs`. If the
recorder then finds no browser, run `npx --prefix pdlc/.tools playwright install chromium`.
Make sure `pdlc/.tools/` is in `.gitignore`.

## 3. Write the script

Follow the visual port and its adapter in `pdlc/config.md`. Write
`pdlc/changes/CH-xxxx-…/visual.json`:

- One or more steps for each acceptance line, in order. The first step for each line sets
  a caption: the requirement ID, then the acceptance line in a few words. Every line gets
  a step. Compare the count of lines with the change spec.
- Show the behaviour the way a user meets it:
  - a web app: pages and clicks;
  - a CLI: commands and their output;
  - a library: a short script that calls the interface.
- A helper script that a step runs lives in the change folder. Paths are relative to the
  project root, so anyone can record again.
- For a terminal script, end with a step that runs all checks and shows that they pass.
  The recorder runs commands only in terminal scripts, so a web script leaves this step
  out.
- A terminal frame scrolls like a real terminal: it shows the newest lines, errors
  included. Keep each step's output under one screen, so its command stays in view.

## 4. Record

Run `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.

A frame must show what its caption claims. The recorder fails and names the step in two
cases:

- a frame is blank;
- a click, typing, a key press or a command changes nothing on screen.

If the recorder fails, fix the script. Look for a wrong selector, a missing step, or a
command that prints nothing. For a command that prints nothing, print its result, or read
the result with the next command. Then record again. Set `"unchanged": true` on a step
only when its acceptance line says nothing changes.

Then read the last frame of each acceptance line yourself. If the frame shows an error,
the wrong thing, or the screen before the step, fix the script. Then record again. Never
fix the app here.

## 5. Finish

1. Write `handoff.md` for verify. Give what the GIF shows, frame by frame. Give how many
   acceptance lines the GIF shows, out of how many (for example "5 of 6").
2. Commit `visual.json`, any helper script, `review.gif`, `frames/` and the handoff
   together ("Visual review CH-xxxx"). Give the commit the trailers `Intent`, `Change`
   and `Review: pdlc/changes/CH-xxxx-…/review.gif`.
3. Tell the user `/pdlc:verify` is next.
