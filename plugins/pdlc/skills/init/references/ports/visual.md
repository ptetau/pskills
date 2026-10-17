# Port: visual

The visual port shows a change as it works, as a user sees the change. The port shows
the change as a GIF and frames.

## Operations

- **script**: the input is a change spec. Write `visual.json` for
  `pdlc/bin/record_gif.mjs`. The file is a captioned sequence of steps that performs each
  acceptance line.
- **record**: run the recorder. The recorder writes `review.gif` and `frames/` into the
  change folder.

## Success

Each acceptance line appears in one or more frames, with its requirement ID in the
caption. No frame shows an error that the spec did not ask for.

## Conformance check

1. Script one step for the made-up requirement `CAP-conformance.R1`.
2. Record the step. `review.gif` exists, and `frames/01.png` shows the caption.
