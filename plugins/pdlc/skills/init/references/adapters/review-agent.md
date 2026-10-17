# Adapter: review-agent

The review-agent adapter fills the review port with independent `pdlc:reviewer` agents,
one agent for each remit.

- **review**: build the packets with `python3 pdlc/bin/make_packets.py <change> <remits…>`.
  For each remit, start a fresh `pdlc:reviewer` agent. Give the agent only the path of
  its packet. Start all the agents at the same time. Do not give a reviewer the build
  conversation, the result of a different reviewer, or anything outside its packet. If a
  reviewer tries to read anything else, a guard in the pdlc plugin stops the reviewer.
