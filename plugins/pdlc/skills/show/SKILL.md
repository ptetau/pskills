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

Every change gets its show, even one with nothing new on screen yet. A capability shows
its interface in a terminal (`"kind": "terminal"`), even in a web app. Do not hold show
until later changes land.

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
  line sets a caption: the requirement ID, then the acceptance line in a few words. Each
  line gets a step. Compare the count of lines with the change spec.
- Show the behaviour as a user meets it:
  - For a web app, show pages and clicks.
  - For a CLI, show commands and their output.
  - For a library, show a short script that calls the interface.
- A helper script that a step runs lives in the change folder. Paths are relative to the
  project root, so anyone can record again.
- For a terminal script, end with a step that runs all checks and shows that they pass.
  The recorder runs commands only in terminal scripts. Thus, a web script does not have
  this step.
- A terminal frame scrolls like a real terminal. The frame shows the newest lines,
  including errors. Keep the output of each step under one screen, so that the command of
  the step stays in view.

## 4. Record

Run `node pdlc/bin/record_gif.mjs pdlc/changes/CH-xxxx-…/visual.json pdlc/changes/CH-xxxx-…`.

A frame must show what its caption claims. The recorder fails and names the step in two
cases:

- A frame is blank.
- A click, typing, a key press, or a command changes nothing on screen.

If the recorder fails, correct the script. Look for a wrong selector, a missing step, or a
command that prints nothing. For a command that prints nothing, print its result, or read
the result with the next command. Then record again. Set `"unchanged": true` on a step
only when its acceptance line says that nothing changes.

Then read the last frame of each acceptance line yourself. If the frame shows an error,
incorrect content, or the screen from before the step, correct the script and record
again. Do not correct the app in this skill.

## 5. Finish

1. Write `handoff.md` for `/pdlc:verify`. Give what the GIF shows, frame by frame. Also
   give how many acceptance lines the GIF shows, out of how many.
2. Commit `visual.json`, any helper script, `review.gif`, `frames/`, and the handoff
   together. Use the message "Visual review CH-xxxx". Add the trailers `Intent`, `Change`,
   and `Review: pdlc/changes/CH-xxxx-…/review.gif`.
3. Tell the user that `/pdlc:verify` is next.
