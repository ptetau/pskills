## Live dashboard

For any work in progress (anything with more than one step):

1. Before starting, have the dashboard-builder agent set up `.dashboard/index.html`. Tell
   me the path once, so I can double-click it.
2. After every step, have dashboard-builder update the dashboard. Give the agent the whole
   picture:
   - every task and its status;
   - questions waiting for me, with their default action;
   - the latest deliverables;
   - anything stuck.

   Take times from the real clock (`date -Iseconds`). Never guess them. Run the agent in
   the background, so the work doesn't wait.
3. If you need a decision from me, don't stop. Add the question to the questions list,
   with its default action. Keep going with that default. If I answer later, switch to my
   answer. Tell me what changed.
4. If dashboard-builder replies `STYLE NEEDED`, ask me the style question in chat as well.
   Pass my answer back to dashboard-builder.
5. Keep `.dashboard/` out of git by adding it to `.git/info/exclude`.
