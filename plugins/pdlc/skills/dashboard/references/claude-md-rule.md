## Live dashboard

For all work in progress (work with more than one step), do these steps:

1. Before you start, use the dashboard-builder agent to prepare `.dashboard/index.html`.
   Tell me the path one time, so that I can double-click the file.
2. After each step, use dashboard-builder to update the page. Give dashboard-builder the
   full state:
   - Each task and its status.
   - The questions for me, with their default action.
   - The latest deliverables.
   - Anything that is stuck.

   Take each time from the real clock (`date -Iseconds`). Do not guess a time. Run
   dashboard-builder in the background, so that the work does not wait.
3. When you need a decision from me, do not stop. Add the question to the questions list,
   with the default action. Then continue with that default. If I answer later, change to
   my answer, and tell me what changed.
4. If dashboard-builder replies `STYLE NEEDED`, also ask me the style question in the
   chat. Then give my answer to dashboard-builder.
5. To keep `.dashboard/` out of git, add `.dashboard/` to `.git/info/exclude`.
