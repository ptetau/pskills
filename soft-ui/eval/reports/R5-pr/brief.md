# R5 · Pull request review

A reviewer agent reviewed PR #212 "Apply discount codes at checkout". `pr.json` holds the
PR facts, `pr.diff` holds the change, and `review.json` holds the review findings, each
tied to a file and line.

Reader: the PR author. They need to see what the review thinks overall, which files
changed and by how much, the change itself, and each finding next to the code it is
about, most serious first.
