---
name: show
description: >
  Records a verified pdlc change, and proposes its merge. Plays each acceptance check in
  the real app: a browser for web apps, and a terminal for CLIs and libraries. Saves
  review.gif and the key frames in the folder of the change, and puts the GIF in the
  proposal. Does not merge. Use when the user says "/pdlc:show", or when a change is
  verified.
---

# pdlc show

## Goal

Show makes a short GIF, `review.gif`, and its frames, after the change passed `verify`.
They show the change do what its spec says, one acceptance line after the other, as a user
meets the change. Then the user gets a proposal with the GIF to approve. The skill does
not merge the change.

## Constraints

- The rules of `pdlc/README.md` hold, and "Bookkeeping on main" runs first.
- The change is the one that the user names, or else the first `in review` change whose
  latest handoff is `verify → show`. Show works on the branch of the change.
- A change that did not pass `verify` goes to `/pdlc:verify` first.
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
- Show writes only in the change folder. Thus, the pass commit of `verify` stays valid.
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
- Suppose that a correct script still shows that the app does not meet an acceptance line.
  Then the change goes back to build, and that counts as a round ("Rounds"). The change
  is `building` again, and its requirements are `built`.
- The proposal goes through the delivery port, with the base of the change as its target.
  Its description fills each section of `pdlc/templates/proposal.md`:
  - The embedded GIF (the adapter says how), and a table of each requirement, its checks,
    and their result.
  - A table of each remit and its result, with a link to each `result.md`.
  - The acceptance file, its lock, and its review. For the last change, the pass commit.
  - The lock commit (with `Tests-Locked: acceptance`, the acceptance lock), and each
    "Manual checks" item for the user to confirm.
  - Each `(assumed)` detail of the change spec and its requirements, one line each.
  - The changes that merge together, and the intents filed for new behaviour.

## Inputs

- `pdlc/README.md`, the shared rules.
- The change spec, its `handoff.md`, its review results, and the intent.
- The visual port, its adapter, and the "Visual" section of `pdlc/config.md`.
- `pdlc/templates/proposal.md`.

## Outputs

- `visual.json`, any helper script, `review.gif`, and `frames/` in the change folder.
- One commit of all these files, "Visual review CH-xxxx", with the trailers `Intent`,
  `Change`, and `Review: pdlc/changes/CH-xxxx-…/review.gif`.
- The proposal. When each change of the intent is `in review` or `merged`, the intent is
  `in review`, on the branch of the change.
- The handoff `show → user`: the link, and what the user must confirm. It also says what
  the GIF shows frame by frame, and how many acceptance lines it shows, out of how many.
- The commit "Propose CH-xxxx" (`Intent`, `Change`): the handoff and the intent.
- The user gets the link.
- When the app does not meet an acceptance line:
  - The handoff `show → build` names each such line, and its frame.
  - The commit "Send back CH-xxxx: <stage>" (`Intent`, `Change`), with build as the stage.
  - The user hears that build is next, and the skill stops.
- Show is done when the change is proposed, or when the change goes back to build. The
  GIF of a proposal shows each acceptance line, and each last frame shows what its caption
  claims.
