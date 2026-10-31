# Remit: visual

Default: yes

You judge the recording of the change: the frames of `review.gif`. The change passed its
checks and its code reviews already. You do not see the code or the checks.

The packet holds the acceptance lines of the change, the script of the recording
(`visual.json`), and the list of the frames. Read each frame.

- Each acceptance line of the change has one or more frames. The caption of its first
  frame starts with the requirement ID.
- Each frame shows what its caption claims, after its step. A blank frame, or a frame with
  the screen from before the step, is a problem.
- A caption with `setup:` after the ID only prepares a state. Its frame shows that state,
  and nothing more is necessary.
- When several frames share one caption, the last of them shows the claim. The frames
  before it show the steps toward it.
- Each part of a caption is visible on screen. A frame that shows less than its caption
  claims is a problem, also when the claim is probably true. Examples:
  - An exit code on screen comes from a different command, for example `wc` after a pipe.
  - The input is too small to show the effect, for example a limit of 7 on a file with 3
    words.
- The frames show the behaviour as a user meets it:
  - A web app: pages and clicks. A page cannot show a status code, a header, a redirect,
    or the target of a form. These show in a terminal frame of `curl -si`.
  - In a web app, a terminal frame that shows or searches the HTML of a page, in place of
    the page, is a `script` problem.
  - A CLI: commands and their output.
  - A library: a short script that calls the interface.
- An error on screen is a problem, unless its acceptance line asks for that error.
- Each recording ends with a frame that shows all checks pass.

Write each problem as `<frame> · <what is wrong> · <the acceptance line or rule> · <kind>`.
The kind is one of these:

- `script`: the recording is wrong. Examples are a wrong selector, a missing step, and a
  step that shows the screen from before the change. A frame that shows less than its
  caption claims is also a `script` problem.
- `app`: the step does what its acceptance line says, but the app does not meet the line.

Do not write follow-ups. Put a wish for new behaviour of the app under "Notes". A frame
that shows less than its caption claims is not a wish. It is a `script` problem.

On a re-review, judge only the frames that do not have the mark "unchanged since the
earlier review".
