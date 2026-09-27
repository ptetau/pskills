# Adapter: review-agent

Fills the review port with the `pdlc:reviewer` agent.

- **review**: start the `pdlc:reviewer` agent with a fresh context. Give it only the change
  spec, the output of `git diff <base>...<branch>`, the commit messages on the branch, and
  the design specs the change lists. Never give it the build conversation.
