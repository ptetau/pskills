#!/usr/bin/env python3
"""pdlc merge check.

Fails if any requirement a change touches is not verified.

Usage:
  python3 pdlc/bin/check_merge.py CH-0031   check one change
  python3 pdlc/bin/check_merge.py           check every change with status "in review"

Run it from the project root. Exit code 0 means the change may merge.
"""
import re
import sys
from pathlib import Path

REQ = re.compile(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b(.*)$", re.M)
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def status_of(root, req_id):
    """The requirement's status in its spec, or None if it isn't there."""
    spec_id = req_id.rsplit(".", 1)[0]
    spec = root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")
    if not spec.exists():
        return None
    text = spec.read_text()
    heading = re.search(r"^### %s\b.*$" % re.escape(req_id), text, re.M)
    if not heading:
        return None
    body = text[heading.end():]
    end = re.search(r"^##", body, re.M)
    body = body[:end.start()] if end else body
    status = re.search(r"^Status:\s*([a-z ]+?)\s*(?:·|$)", body, re.M)
    return status.group(1) if status else "missing"


def check_change(root, path):
    """A list of problems with one change. Empty means it may merge."""
    problems = []
    reqs = REQ.findall(section(path.read_text(), "Requirements"))
    if not reqs:
        problems.append("lists no requirements")
    for req_id, rest in reqs:
        status = status_of(root, req_id)
        if "(retire)" in rest:
            if status is not None:
                problems.append("%s is marked (retire) but is still in its spec" % req_id)
        elif status is None:
            problems.append("%s is not in its spec" % req_id)
        elif status != "verified":
            problems.append("%s is %s, not verified" % (req_id, status))
    return problems


def main(argv, root=Path(".")):
    changes = root / "pdlc" / "changes"
    if len(argv) > 1:
        paths = sorted(changes.glob(argv[1] + "-*.md"))
        if not paths:
            print("No change spec found for %s" % argv[1])
            return 1
    else:
        paths = [p for p in sorted(changes.glob("CH-*.md"))
                 if re.search(r"Status:\s*in review\b", p.read_text())]
    failed = False
    for path in paths:
        problems = check_change(root, path)
        name = path.name.split("-", 2)
        name = "-".join(name[:2])
        if problems:
            failed = True
            print("FAIL %s" % name)
            for problem in problems:
                print("  - %s" % problem)
        else:
            print("ok   %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
