# Port: visual

Shows a change working, the way a user would meet it, as a GIF and frames.

## Operations

- **script**: given a change spec, write `visual.json` for `pdlc/bin/record_gif.mjs`: a
  captioned sequence of steps that performs each acceptance line.
- **record**: run the recorder. It writes `review.gif` and `frames/` into the change folder.

## Success

Every acceptance line appears in at least one frame, with its requirement ID in the
caption, and no frame shows an error the spec didn't ask for.

## Conformance check

1. Script a single step for a made-up requirement `CAP-conformance.R1`.
2. Record it. `review.gif` exists and `frames/01.png` shows the caption.
