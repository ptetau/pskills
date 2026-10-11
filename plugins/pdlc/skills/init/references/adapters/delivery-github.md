# Adapter: delivery-github

Fills the delivery port with git and GitHub pull requests.

- **start**: `git switch -c <branch> <start>`. Name the branch as
  `specs/design/DES-pdlc-branches.md` says (by default `pdlc/<ID>-<short-name>`). The
  start is one of these:
  - for a change, the change's `Base:`, or the intent's `Branch:` for an intent's first
    change;
  - for an intent, the newest unmerged branch.

  If the start is main and there is a remote, pull main first.
- **commit**: `git commit` with the trailers as the last lines of the message, one per line,
  after a blank line. Put any other trailers in the same block, with no blank line between.
  Check with `git log -1 --format=%(trailers)`: pdlc's trailers must show.
- **propose**: push the branch. Open a pull request against the change's base. Use
  whatever GitHub tool this session has: the `gh` CLI or GitHub tools.
  - The body is the description from `pdlc/templates/proposal.md`. Embed the GIF with its
    full address, so it plays in the pull request:
    `![visual review](https://github.com/<owner>/<repo>/blob/<branch>/pdlc/changes/<folder>/review.gif?raw=true)`.
  - When the pull request this one targets merges, retarget this pull request to the
    merged one's base.
  - Under "Merge together", list the intent's other changes in stack order, with their
    pull requests where they exist. Tell the user to merge them together, bottom first.
    Also tell the user to point each next pull request at main once the one below it
    merges. On GitHub, deleting the merged branch does that.
- **gate**: run `python3 pdlc/bin/check_merge.py <change-id>`.
- **merged?**: check whether the pull request is merged. If there is no pull request, the
  branch counts as merged when `git merge-base --is-ancestor <branch> main` succeeds.

If this session has no GitHub access, stop after you push. Tell the user the branch name.

If the repository has no remote, don't push. **propose** writes the description to
`pdlc/changes/<folder>/proposal.md`. Verify commits that file with its handoff ("Propose
CH-xxxx"). The change then counts as proposed. The user merges the intent's branches into
main locally, together, bottom first. **merged?** then uses `merge-base`.
