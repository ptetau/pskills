# pskills

## Writing

Write everything in this repo as `plugins/pdlc/skills/init/references/defaults/DES-writing-style.md`
(the writing rules) says. This covers skills, agents, docs, plans, code comments, commit
messages and pull request text. In short:

1. Use the core rules of Simplified Technical English (ASD-STE100), without its
   dictionary. Write short sentences. Use the active voice. Give one instruction per
   sentence.
2. Use New Zealand spelling: organise, colour, centre, analyse.
3. Explain a concept with a concrete example.
4. If "it" or "this" could mean two things, repeat the noun.
5. Give an ID with its name: "CAP-email.R3 (the reset link expires after one hour)",
   never "R3" alone.
6. Don't write conversation or task history into an artifact. State the facts as they
   are now.
7. Be concise.

Before you commit, run `python3 plugins/pdlc/skills/init/references/bin/check_writing.py <files>`
on the text you changed.
