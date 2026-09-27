# Adapter: delivery-github

Fills the delivery port with git and GitHub pull requests.

- **start**: `git switch -c pdlc/<change-id>-<short-name>` from an up-to-date main.
- **commit**: `git commit` with the trailers as the last lines of the message, one per line,
  after a blank line. Any other trailers go in the same block, with no blank line between.
  Check with `git log -1 --format=%(trailers)`: pdlc's trailers must show.
- **propose**: push the branch and open a pull request with whatever GitHub tool this
  session has (the `gh` CLI or GitHub tools). Put the requirements table in the body.
- **gate**: run `python3 pdlc/bin/check_merge.py <change-id>`.
- **merged?**: check whether the pull request is merged.

If no GitHub access is available, stop after pushing and tell the user the branch name.
