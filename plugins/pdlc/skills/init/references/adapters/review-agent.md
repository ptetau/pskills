# Adapter: review-agent

Fills the review port with independent `pdlc:reviewer` agents, one per remit.

- **review**: build the packets with `python3 pdlc/bin/make_packets.py <change> <remits…>`.
  For each remit, start a fresh `pdlc:reviewer` agent and give it only the path of its
  packet. Start them all at once. Never give a reviewer the build conversation, another
  reviewer's result, or anything outside its packet. A guard in the pdlc plugin stops a
  reviewer reading anything else.
