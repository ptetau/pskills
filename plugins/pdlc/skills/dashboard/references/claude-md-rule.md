## Live dashboard

For any work in progress (anything with more than one step):

1. Before starting, have the dashboard-builder agent set up `.dashboard/index.html`. Tell
   me the path once, so I can double-click it.
2. After every step, have dashboard-builder update it. Give it the whole picture: every
   task and its status, questions waiting for me with their default action, the latest
   deliverables, and anything stuck. Take times from the real clock (`date -Iseconds`).
   Never guess them. Run it in the background so the work doesn't wait.
3. When you need a decision from me, don't stop. Add it to the questions list with the
   default action, and keep going with that default. If I answer later, switch to my
   answer and tell me what changed.
4. If dashboard-builder replies `STYLE NEEDED`, ask me the style question in chat as well,
   and pass my answer back to it.
5. Keep `.dashboard/` out of git by adding it to `.git/info/exclude`.
