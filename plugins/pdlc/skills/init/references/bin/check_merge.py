#!/usr/bin/env python3
"""pdlc merge check.

A change may merge only when:
  - every requirement it lists is verified (and every retired one is gone from its spec);
  - its tests are locked, and no check file changed after the lock;
  - every review remit named in pdlc/config.md passed.

Usage:
  python3 pdlc/bin/check_merge.py CH-0031   check one change
  python3 pdlc/bin/check_merge.py           check the change for the current branch, or,
                                            if no change uses this branch, every change
                                            with status "in review"

In CI the current branch is read from GITHUB_HEAD_REF when it is set.
Run it from the project root. Exit code 0 means the change may merge.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REQ = re.compile(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b(.*)$", re.M)
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}
DEFAULT_REMITS = ["tests", "specification", "security", "quality", "compliance", "privacy"]


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def status_of(root, req_id):
    """The requirement's status in its spec, 'missing' if it has none, None if not there."""
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


def remits(root):
    """The review remits pdlc/config.md asks for."""
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- remits:\s*(.+)$", section(text, "Reviews"), re.M)
    if not line:
        return DEFAULT_REMITS
    return [r.strip() for r in line.group(1).split(",") if r.strip() and r.strip() != "none"]


def check_files(text):
    """The paths listed under '## Check files'."""
    paths = re.findall(r"^-\s+`?([^`\s]+)`?", section(text, "Check files"), re.M)
    return [p for p in paths if p.lower() != "none"]


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def check_change(root, folder):
    """A list of problems with one change. Empty means it may merge."""
    problems = []
    text = (folder / "change.md").read_text()

    reqs = REQ.findall(section(text, "Requirements"))
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

    checks = check_files(text)
    # A re-lock may leave the older line in place; the newest (last) one counts.
    locks = list(re.finditer(r"^Tests-Locked:\s*([0-9a-f]{7,40})\b", text, re.M))
    lock = locks[-1] if locks else None
    if checks and not lock:
        problems.append("tests are not locked (no Tests-Locked line)")
    elif checks:
        diff = git(root, "diff", "--name-only", lock.group(1), "HEAD", "--", *checks)
        if diff.returncode != 0:
            problems.append("can't compare tests with the lock %s" % lock.group(1))
        for path in diff.stdout.split():
            problems.append("changed after the tests were locked: %s" % path)

    for remit in remits(root):
        result = folder / "review" / remit / "result.md"
        if not result.exists():
            problems.append("%s review has no result" % remit)
        elif not re.match(r"\s*Result:\s*pass\b", result.read_text(), re.I):
            problems.append("%s review did not pass" % remit)
    return problems


def current_branch(root):
    """The branch being merged: GITHUB_HEAD_REF in CI, else git's current branch."""
    if os.environ.get("GITHUB_HEAD_REF"):
        return os.environ["GITHUB_HEAD_REF"]
    try:
        out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main(argv, root=Path("."), branch=None):
    changes = root / "pdlc" / "changes"
    everything = sorted(p.parent for p in changes.glob("CH-*/change.md"))
    if len(argv) > 1:
        folders = [f for f in everything if f.name.startswith(argv[1] + "-")]
        if not folders:
            print("No change spec found for %s" % argv[1])
            return 1
    else:
        branch = branch or current_branch(root)
        folders = [f for f in everything
                   if branch and re.search(r"Branch:\s*%s\s*(?:·|$)" % re.escape(branch),
                                           (f / "change.md").read_text(), re.M)]
        if not folders:
            folders = [f for f in everything
                       if re.search(r"Status:\s*in review\b", (f / "change.md").read_text())]
    failed = False
    for folder in folders:
        problems = check_change(root, folder)
        name = "-".join(folder.name.split("-", 2)[:2])
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
