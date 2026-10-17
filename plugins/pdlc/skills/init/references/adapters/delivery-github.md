# Adapter: delivery-github

The delivery-github adapter fills the delivery port with git and GitHub pull requests.

- **start**: run `git switch -c <branch> <start>`. Name the branch as
  `specs/design/DES-pdlc-branches.md` tells you (by default `pdlc/<ID>-<short-name>`).
  The start is one of these:
  - For a change, the start is the `Base:` of the change. For the first change of an
    intent, the start is the `Branch:` of the intent, if the intent has one.
  - For an intent, the start is the newest unmerged branch.

  If the start is main and there is a remote, pull main before you create the branch.
- **commit**: run `git commit`. Put the trailers at the end of the message, after a blank
  line, with one trailer on each line. Put other trailers in the same block, with no
  blank line between them. Make sure that pdlc's trailers show in the output of
  `git log -1 --format=%(trailers)`.
- **propose**: push the branch. Use the GitHub tool that this session has (the `gh` CLI
  or GitHub tools) to open a pull request against the base of the change.
  - Use the description from `pdlc/templates/proposal.md` as the body of the pull
    request. Embed the GIF with its full address, so that the GIF plays in the pull
    request:
    `![visual review](https://github.com/<owner>/<repo>/blob/<branch>/pdlc/changes/<folder>/review.gif?raw=true)`.
  - This pull request can have a different pull request as its base. When that base pull
    request merges, retarget this pull request to the base of the merged pull request.
  - Under "Merge together", list the other changes of the intent in stack order, with
    their pull requests where the pull requests exist. Tell the user to merge the changes
    together, with the bottom change first. Also tell the user to point each next pull
    request at main when the pull request below it merges. On GitHub, deleting the merged
    branch does that.
- **gate**: run `python3 pdlc/bin/check_merge.py <change-id>`.
- **merged?**: find if the pull request is merged. If there is no pull request, and
  `git merge-base --is-ancestor <branch> main` succeeds, the branch counts as merged.

If you do not have GitHub access, push the branch and then stop. Tell the user the name of
the branch.

If the repository has no remote, do not push. **propose** writes the description to
`pdlc/changes/<folder>/proposal.md`. The verify stage commits that file with its handoff
("Propose CH-xxxx"). The change then counts as proposed. The user merges the branches of
the intent into main locally, together, with the bottom branch first. **merged?** then
uses `merge-base`.
