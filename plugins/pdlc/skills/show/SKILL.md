---
name: show
description: >
  Records a built pdlc change for its visual review. Plays each acceptance check in the
  real app: a browser for web apps, and a terminal for CLIs and libraries. Saves
  review.gif and the key frames in the folder of the change, for the reviewers and the
  pull request. Use when the user says "/pdlc:show", or when a change is built.
---

# pdlc show

This skill makes a short GIF that shows the change do what its spec says.

Read `pdlc/README.md` first and obey it. Start with its "Before any work" step. Then read
the `handoff.md` of the change.

## 1. Pick the change

Use the change that the user named. If the user did not name a change, use the first
`building` change whose requirements are all `built`. Switch to the branch of that change.

## 2. Get the recorder ready

The recorder is `pdlc/bin/record_gif.mjs`. The recorder needs Node, `playwright`,
`gifenc`, and `pngjs`.

If the recording (step 4) stops with `missing <name>`, install the packages in
`pdlc/.tools/`: `npm install --prefix pdlc/.tools playwright gifenc pngjs`. Then, if the
recorder finds no browser, run `npx --prefix pdlc/.tools playwright install chromium`.

Make sure that `pdlc/.tools/` is in `.gitignore`.

## 3. Write the script

Obey the visual port and its adapter in `pdlc/config.md`. Write
`pdlc/changes/CH-xxxx-…/visual.json`:

- Write one or more steps for each acceptance line, in order. The first step for each
  line sets a caption: the requirement ID, then the acceptance line in a few words.
- Show the behaviour as a user meets it:
  - For a web app, show pages and clicks.
  - For a CLI, show commands and their output.
  - For a library, show a short script that calls the interface.
- For a terminal script, end with a step that runs all checks and shows that they pass.
  The recorder runs commands only in terminal scripts. Thus, a web script does not have
  this step.

## 4. Record

Run `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.

Then read a few of the frames yourself. If a frame shows an error, incorrect content, or an
empty screen, correct the script and record again. Do not correct the app in this skill.

## 5. Finish

1. Commit `visual.json`, `review.gif`, and `frames/`. The message says
   "Visual review CH-xxxx", and has the line `Review: pdlc/changes/CH-xxxx-…/review.gif`.
   The message also has the trailers `Intent` and `Change`.
2. Write `handoff.md` for `/pdlc:verify`: what the GIF shows, frame by frame.
3. Commit the handoff with the same trailers. Tell the user that `/pdlc:verify` is next.
