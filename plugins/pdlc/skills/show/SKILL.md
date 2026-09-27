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

## 2. Get the recorder ready

The recorder is `pdlc/bin/record_gif.mjs`. It needs Node, `playwright`, `gifenc` and `pngjs`.
If `node pdlc/bin/record_gif.mjs` says one is missing, install them into `pdlc/.tools/`:
`npm install --prefix pdlc/.tools playwright gifenc pngjs`, then
`npx --prefix pdlc/.tools playwright install chromium` if no browser is found. Make sure
`pdlc/.tools/` is in `.gitignore`.

## 3. Write the script

Follow the visual port and its adapter in `pdlc/config.md`. Write
`pdlc/changes/CH-xxxx-…/visual.json`:

- One or more steps for each acceptance line, in order. The first step for each line sets
  a caption: the requirement ID, then the acceptance line in a few words.
- Show the behaviour the way a user meets it: pages and clicks for a web app, commands and
  their output for a CLI, a short script calling the interface for a library.
- End with a step that runs all checks and shows they pass.

## 4. Record

Run `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.
Then read a few of the frames yourself. If a frame shows an error, the wrong thing, or an
empty screen, fix the script and record again. Never fix the app here.

## 5. Finish

1. Commit `visual.json`, `review.gif` and `frames/`. The message says
   "Visual review CH-xxxx" and has a line `Review: pdlc/changes/CH-xxxx-…/review.gif`, plus
   the trailers `Intent` and `Change`.
2. Write `handoff.md` for verify: what the GIF shows, frame by frame.
3. Commit the handoff with the same trailers. Tell the user `/pdlc:verify` is next.
