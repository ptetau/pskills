# Adapter: delivery-github

Fills the delivery port with git and GitHub pull requests.

- **start**: `git switch -c <branch> <base>`. Name the branch as
  `specs/design/DES-pdlc-branches.md` says (by default `pdlc/<change-id>-<short-name>`).
  The base is the change's `Base:` (main, brought up to date, for the first change; otherwise the branch of
  the change before it).
- **commit**: `git commit` with the trailers as the last lines of the message, one per line,
  after a blank line. Any other trailers go in the same block, with no blank line between.
  Check with `git log -1 --format=%(trailers)`: pdlc's trailers must show.
- **propose**: push the branch and open a pull request against the change's base, with
  whatever GitHub tool this session has (the `gh` CLI or GitHub tools). Put the tables in
  the body. Embed the GIF with its full address, so it plays in the pull request:
  `![visual review](https://github.com/<owner>/<repo>/blob/<branch>/pdlc/changes/<folder>/review.gif?raw=true)`.
  When the pull request it is based on merges, retarget this one to that one's base.
- **gate**: run `python3 pdlc/bin/check_merge.py <change-id>`.
- **merged?**: check whether the pull request is merged. If there is no pull request, the
  branch counts as merged when `git merge-base --is-ancestor <branch> main` succeeds.

If no GitHub access is available, stop after pushing and tell the user the branch name.
