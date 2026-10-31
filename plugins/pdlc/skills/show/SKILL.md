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

Show makes a short GIF, `review.gif`, and its frames, after the change passed `verify`.
They show the change do what its spec says, one acceptance line after the other, as a user
meets the change. An independent reviewer judges the frames. Then the user gets a proposal
with the GIF to approve. The skill does not merge the change.

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
- In a web app, a part of a line that a page cannot show gets a `run` step with
  `curl -si`. Examples are a status code, a header, a redirect, and the target of a form.
  The caption of a page step claims only what the page shows.
- Each part that a user sees shows on the page, with `goto`, `click`, and `type`. A `run`
  step that prints or searches the HTML of a page does not stand for the page.
- A helper script lives in the change folder. Paths are relative to the project root, so
  that anyone can record again.
- Show writes only in the change folder. Thus, the pass commit of `verify` stays valid.
- Each script ends with a `run` step that runs all checks and shows them pass.
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
- Each part of a caption is visible on screen. An exit code comes from the command that
  the caption names, not from a later command of a pipe. The input is large enough to show
  the effect, for example more words than a limit.
- A failed recording means a wrong script: a wrong selector, a missing step, or a command
  that prints nothing. Such a command prints its result, or the next command reads it.
- A step has `"unchanged": true` only when its acceptance line says that nothing changes.
- Show reads the last frame of each acceptance line itself. A frame with an error,
  incorrect content, or the screen from before the step means a wrong script.
- Show corrects the script and records again. Show does not correct the app.
- After the recording, `python3 pdlc/bin/make_packets.py CH-xxxx visual` makes the packet
  of the `visual` remit, when "Reviews" in `pdlc/config.md` lists that remit. One fresh
  `pdlc:reviewer` gets only the path of the packet. The reviewer obeys "Who does what".
- A failed visual review counts as a round ("Rounds"). Each problem goes by its kind:
  - `script`: show corrects the script, records again, and makes a new packet. The new
    reviewer judges only the frames that changed.
  - `app`: the change goes back to build. The change is `building` again, and its
    requirements are `built`. Then `verify` runs again.
- The gate of the delivery port passes, except for lines that say `not ready`. These lines
  clear when the last change of the intent is `verified`. For the last change, the gate
  passes with no exception.
- The skill corrects each other problem that the gate names:
  - A conflict with main: a merge of main into this branch. The merge keeps the text of
    main, and the statuses of this branch for its own requirements.
  - A mark that the gate names: the mark becomes `(assumed)`, with the reason outside the
    brackets, and the same meaning.
  - A correction of app files after the acceptance run: the acceptance checks run again,
    and the new commit goes on `Acceptance-Passed:`.
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
- The "Reviews" of `pdlc/config.md`, and `pdlc/templates/proposal.md`.

## Outputs

- `visual.json`, any helper script, `review.gif`, and `frames/` in the change folder.
- One commit of all these files, "Visual review CH-xxxx", with the trailers `Intent`,
  `Change`, and `Review: pdlc/changes/CH-xxxx-…/review.gif`. The packet and the result of
  the visual review go into the next commit of show.
- Each gate correction is a commit "Update CH-xxxx: <what>". A merge of main has the
  trailers `Intent` and `Change`.
- The proposal. When each change of the intent is `in review` or `merged`, the intent is
  `in review`, on the branch of the change.
- The handoff `show → user`: the link, and what the user must confirm. It also says what
  the GIF shows frame by frame, and how many acceptance lines it shows, out of how many.
- The commit "Propose CH-xxxx" (`Intent`, `Change`): the handoff and the intent.
- The user gets the link.
- When the visual review finds an `app` problem:
  - The handoff `show → build` names each such line, and its frame.
  - The commit "Send back CH-xxxx: <stage>" (`Intent`, `Change`), with build as the stage.
  - The user hears that build is next, and the skill stops.
- Show is done when the change is proposed, or when the change goes back to build. The
  GIF of a proposal shows each acceptance line, and each last frame shows what its caption
  claims.
