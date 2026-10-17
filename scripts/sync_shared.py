#!/usr/bin/env python3
"""Copy the shared files of this repository to each place that uses them.

Each skill is installed as its own folder, so each skill must have its own copy of a shared
file. This script makes each copy the same as its master file. Edit only the master file,
then run this script.

Master file                          Copies
WRITING-GUIDELINES.md                <skill>/references/writing-guidelines.md, for each skill
                                     plugins/pdlc/skills/init/references/defaults/DES-writing-style.md
                                     (the rules under a pdlc design-spec header)
improve-writing/scripts/check_writing.py
                                     decompose/scripts/check_writing.py
                                     blueprint/scripts/check_writing.py
                                     quiz-visual/scripts/check_writing.py
decompose/references/c4.md           blueprint/references/c4.md

Usage:
  python scripts/sync_shared.py           write each copy
  python scripts/sync_shared.py --check   write nothing; exit 1 if a copy is different
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDELINES = ROOT / "WRITING-GUIDELINES.md"
DES = ROOT / "plugins/pdlc/skills/init/references/defaults/DES-writing-style.md"

DES_HEADER = """# DES-writing-style · How pdlc writes

Status: agreed · Default: yes · Ask at init: yes

## Question

How must pdlc write specs, intents, change specs, and its replies to you?

- A · the pskills writing guidelines (recommended): ASD-STE100 Simplified Technical
  English, and two more rules. A pronoun refers only to a noun in the same paragraph. Each
  ID has a short description. Specs are easy to read, and agents obey plain rules more
  reliably.
- B · your own style guide: give pdlc the path of the guide that you use.

## Rule

This rule is a copy of `WRITING-GUIDELINES.md` from the pskills repository.

"""


def skills():
    return sorted(p.parent for p in ROOT.glob("*/SKILL.md"))


def des_text():
    body = GUIDELINES.read_text(encoding="utf-8")
    body = re.sub(r"\A# [^\n]*\n+", "", body)                       # the title of the file
    body = re.sub(r"^(#{2,5}) ", lambda m: "#" + m.group(1) + " ", body, flags=re.M)   # one level down
    return DES_HEADER + body


def copies():
    """[(destination, text)] for each copy."""
    out = []
    text = GUIDELINES.read_text(encoding="utf-8")
    for skill in skills():
        out.append((skill / "references" / "writing-guidelines.md", text))
    out.append((DES, des_text()))
    linter = (ROOT / "improve-writing/scripts/check_writing.py").read_text(encoding="utf-8")
    for skill in ("decompose", "blueprint", "quiz-visual"):
        out.append((ROOT / skill / "scripts" / "check_writing.py", linter))
    c4 = (ROOT / "decompose/references/c4.md").read_text(encoding="utf-8")
    out.append((ROOT / "blueprint/references/c4.md", c4))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--check", action="store_true", help="write nothing; exit 1 if a copy is different")
    opts = p.parse_args(argv)
    different = []
    for dest, text in copies():
        current = dest.read_text(encoding="utf-8") if dest.exists() else None
        if current == text:
            continue
        different.append(dest.relative_to(ROOT))
        if not opts.check:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
    verb = "different from its master file" if opts.check else "written"
    for d in different:
        print("%s: %s" % (d, verb))
    if different:
        print("%d of %d copies %s" % (len(different), len(copies()), verb))
    else:
        print("All %d copies are the same as their master files" % len(copies()))
    if opts.check and different:
        sys.exit(1)


if __name__ == "__main__":
    main()
