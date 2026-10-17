# Adapter: delivery-github

The delivery-github adapter fills the delivery port with git and GitHub pull requests.

- **start**: run `git switch -c <branch> <base>`. Name the branch as
  `specs/design/DES-pdlc-branches.md` tells you (by default `pdlc/<change-id>-<short-name>`).
  The base is the `Base:` of the change. For the first change, the base is main. Update main
  before you create the branch. For each other change, the base is the branch of the change
  before it.
- **commit**: run `git commit`. Put the trailers at the end of the message, after a blank
  line, with one trailer on each line. Put other trailers in the same block, with no
  blank line between them. Make sure that pdlc's trailers show in the output of
  `git log -1 --format=%(trailers)`.
- **propose**: push the branch. Use the GitHub tool that this session has (the `gh` CLI
  or GitHub tools) to open a pull request against the base of the change. Put the tables
  in the body of the pull request. Embed the GIF with its full address, so that the GIF
  plays in the pull request:
  `![visual review](https://github.com/<owner>/<repo>/blob/<branch>/pdlc/changes/<folder>/review.gif?raw=true)`.
  This pull request can have a different pull request as its base. When that base pull
  request merges, retarget this pull request to the base of the merged pull request.
- **gate**: run `python3 pdlc/bin/check_merge.py <change-id>`.
- **merged?**: find if the pull request is merged. If there is no pull request, and
  `git merge-base --is-ancestor <branch> main` succeeds, the branch counts as merged.

If you do not have GitHub access, push the branch and then stop. Tell the user the name of
the branch.
