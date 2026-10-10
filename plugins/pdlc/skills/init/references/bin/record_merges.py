#!/usr/bin/env python3
"""pdlc merge records. Keeps the statuses on main true after merges.

Run it on main, before any work. It:
  - sets each change whose branch has merged into main to "merged";
  - sets each intent whose changes have all merged to "done";
  - commits those files on main, only if something changed, and prints what changed.

It never switches branches, and never commits anywhere but main.

Usage:
  python3 pdlc/bin/record_merges.py

Run it from the project root. Exit code 0 means main's records are up to date.
"""
import re
import subprocess
import sys
from pathlib import Path


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    return match.group(1) if match else None


def with_status(text, status):
    """The text with its header's status set to this one."""
    return re.sub(r"(\bStatus:[ \t]*)[^·\n]*?([ \t]*(?:·|$))", r"\g<1>%s\g<2>" % status,
                  text, count=1, flags=re.M)


def has_merged(root, branch):
    """True when every commit on the branch is in main."""
    return git(root, "merge-base", "--is-ancestor", branch, "main").returncode == 0


def main(argv, root=Path(".")):
    here = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if here != "main":
        print("Run this on main, not on %s. Nothing changed." % (here or "no branch"))
        return 1

    touched, intents, statuses = [], set(), {}
    for spec in sorted((root / "pdlc" / "changes").glob("CH-*/change.md")):
        text = spec.read_text()
        change = "-".join(spec.parent.name.split("-", 2)[:2])
        status, branch = field(text, "Status"), field(text, "Branch")
        if status not in ("merged", "cancelled") and branch not in (None, "", "none") \
                and has_merged(root, branch):
            spec.write_text(with_status(text, "merged"))
            touched.append(spec)
            intents.add(field(text, "Intent"))
            print("%s is now merged (was %s)" % (change, status))
            status = "merged"
        statuses[change] = status

    for path in sorted((root / "pdlc" / "inbox").glob("IN-*.md")):
        text = path.read_text()
        changes = re.findall(r"\bCH-\d+\b", section(text, "Changes"))
        status = field(text, "Status")
        if changes and status != "done" and all(statuses.get(c) == "merged" for c in changes):
            path.write_text(with_status(text, "done"))
            touched.append(path)
            intent = "-".join(path.name.split("-", 2)[:2])
            intents.add(intent)
            print("%s is now done (was %s)" % (intent, status))

    if not touched:
        print("Nothing to record: main is up to date.")
        return 0
    message = "Record merges\n\nIntent: %s\n" % ", ".join(sorted(i for i in intents if i))
    files = [p.relative_to(root).as_posix() for p in touched]
    out = git(root, "commit", "-q", "-m", message, "--", *files)
    if out.returncode != 0:
        print("Could not commit on main: %s" % (out.stderr.strip() or out.stdout.strip()))
        return 1
    print("Committed on main: Record merges")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
