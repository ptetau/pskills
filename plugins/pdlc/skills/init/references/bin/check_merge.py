#!/usr/bin/env python3
"""pdlc merge check.

A change may merge only when:
  - every requirement it lists is verified (and every retired one is gone from its spec);
  - its change spec and requirements write the assumption marker one way: "(assumed)";
  - its checks are locked, and no check file changed after the lock;
  - the tests review judged the checks as they are locked now: its packet carries the
    current lock;
  - the tests review names a wrong version of the code that each check fails on;
  - every review remit named in pdlc/config.md passed;
  - the branch merges into main without conflicts;
  - every other change of its intent is "in review" or "merged" on its own branch, so the
    intent's changes merge together;
  - it hasn't merged already: a merged change's branch takes no new commits.

Usage:
  python3 pdlc/bin/check_merge.py CH-0031   check one change
  python3 pdlc/bin/check_merge.py           check the change for the current branch, or,
                                            if no change uses this branch, every change
                                            with status "in review"

In CI, the script reads the current branch from GITHUB_HEAD_REF when that variable is set.
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
READY = ("in review", "merged")
# The marker with emphasis (*(assumed)*), or brackets that hold "assumed" and more text.
MARKER = re.compile(r"[*_]+\(assumed\)[*_]+|\([^()\n]*\bassumed\b[^()\n]*\)", re.I)


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def requirement_text(root, req_id):
    """The requirement's heading and text in its spec, or None if it isn't there."""
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
    return heading.group(0) + (body[:end.start()] if end else body)


def status_of(root, req_id):
    """The requirement's status in its spec, 'missing' if it has none, None if not there."""
    body = requirement_text(root, req_id)
    if body is None:
        return None
    status = re.search(r"^Status:\s*([a-z ]+?)\s*(?:·|$)", body, re.M)
    return status.group(1) if status else "missing"


def marker_problems(where, text):
    """Each assumption marker in the text written any way but "(assumed)"."""
    return ['%s: write "%s" as "(assumed)", with any reason outside the brackets'
            % (where, found.group(0)) for found in MARKER.finditer(text or "")
            if found.group(0) != "(assumed)"]


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


def reviewed_lock(folder, lock):
    """True when the tests packet carries this lock, copied from the change spec."""
    packet = folder / "review" / "tests" / "packet.md"
    if not packet.exists():
        return False
    seen = re.findall(r"^Tests-Locked:\s*([0-9a-f]{7,40})\b", packet.read_text(), re.M)
    return bool(seen) and (seen[-1].startswith(lock) or lock.startswith(seen[-1]))


def wrong_versions(folder):
    """The lines under "Wrong versions" in the tests review's result."""
    result = folder / "review" / "tests" / "result.md"
    text = result.read_text() if result.exists() else ""
    block = re.search(r"^#*\s*Wrong versions:?\s*$(.*?)(?=^[^\s-]|\Z)", text, re.M | re.S)
    lines = re.findall(r"^\s*-\s+(.+?)\s*$", block.group(1), re.M) if block else []
    return [line for line in lines if line.lower() != "none"]


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    return match.group(1) if match else None


def show(root, ref, path):
    """A file as it is on a branch, or None if git can't find it there."""
    out = git(root, "show", "%s:%s" % (ref, path))
    return out.stdout if out.returncode == 0 else None


def branches(root):
    """Every local and remote branch git knows."""
    out = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    return out.stdout.split() if out.returncode == 0 else []


def change_id(folder):
    """CH-0031 for the folder CH-0031-email-templates."""
    return "-".join(folder.name.split("-", 2)[:2])


def status_on_own_branch(root, path, refs):
    """A change's status on its own branch, the one its change spec names. A change whose
    branch is gone counts as merged if main's copy reads "in review" or "merged". None
    when it has no branch."""
    for ref in refs:
        text = show(root, ref, path)
        branch = field(text, "Branch") if text else None
        if branch and branch != "none" and (ref == branch or ref.endswith("/" + branch)):
            return field(text, "Status")
    on_main = show(root, "main", path) or show(root, "origin/main", path)
    status = field(on_main, "Status") if on_main else None
    return status if status in READY else None


def partners_not_ready(root, folder, text):
    """Problems with the other changes of this change's intent: each must be ready too."""
    intent = field(text, "Intent")
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent)) if intent else []
    if not found:
        return []
    listed = re.findall(r"\bCH-\d+\b", section(found[0].read_text(), "Changes"))
    problems, refs = [], branches(root)
    for other in dict.fromkeys(listed):
        if other == change_id(folder):
            continue
        specs = sorted((root / "pdlc" / "changes").glob(other + "-*/change.md"))
        path = "pdlc/changes/%s/change.md" % specs[0].parent.name if specs else None
        status = status_on_own_branch(root, path, refs) if path else None
        if status is None:
            problems.append("%s of %s is not ready (no branch)" % (other, intent))
        elif status not in READY:
            problems.append("%s of %s is not ready (status: %s)" % (other, intent, status))
    return problems


def merged_already(root, folder):
    """True when main says this change merged, yet this branch has commits main doesn't."""
    on_main = show(root, "main", "pdlc/changes/%s/change.md" % folder.name)
    if not on_main or field(on_main, "Status") != "merged":
        return False
    ahead = git(root, "rev-list", "--count", "main..HEAD")
    return ahead.returncode == 0 and int(ahead.stdout.strip() or 0) > 0


def conflicts_with_main(root):
    """Files that conflict when this branch merges into main. Empty when it merges
    cleanly, when there is no main, when this is main, or when git can't tell."""
    try:
        head = git(root, "rev-parse", "--verify", "-q", "HEAD")
        main = git(root, "rev-parse", "--verify", "-q", "main")
        if head.returncode or main.returncode or head.stdout == main.stdout:
            return []
        out = git(root, "merge-tree", "--write-tree", "--name-only", "--no-messages",
                  "main", "HEAD")
    except OSError:
        return []
    if out.returncode != 1:
        return []
    return sorted(set(out.stdout.split()[1:]))


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

    problems += marker_problems("change.md", text)
    for req_id, _ in reqs:
        problems += marker_problems(req_id, requirement_text(root, req_id))

    checks = check_files(text)
    # A re-lock may leave the older line in place. The newest (last) line counts.
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

    wanted = remits(root)
    if lock and "tests" in wanted and not reviewed_lock(folder, lock.group(1)):
        problems.append("tests review is not of the current lock %s; review the checks again"
                        % lock.group(1))

    for remit in wanted:
        result = folder / "review" / remit / "result.md"
        if not result.exists():
            problems.append("%s review has no result" % remit)
        elif not re.match(r"\s*Result:\s*pass\b", result.read_text(), re.I):
            problems.append("%s review did not pass" % remit)

    if checks and "tests" in wanted and (folder / "review" / "tests" / "result.md").exists():
        lines = wrong_versions(folder)
        if not lines:
            problems.append('tests review lists no "Wrong versions"; review the checks again')
        for line in lines:
            if re.search(r"·\s*passes\b", line, re.I):
                problems.append("tests review: a check passes a wrong version: %s" % line)

    for path in conflicts_with_main(root):
        problems.append("conflicts with main: %s" % path)

    problems += partners_not_ready(root, folder, text)

    if merged_already(root, folder):
        problems.append("%s already merged; new commits on its branch won't reach main. "
                        "Start a new change." % change_id(folder))
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
        name = change_id(folder)
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
