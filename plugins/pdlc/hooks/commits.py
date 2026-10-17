#!/usr/bin/env python3
"""pdlc commit check. Claude Code runs this after every Bash call.

A pdlc branch is one that a change spec or an intent names as its Branch. When the call
made a commit on a pdlc branch, this checks the commit against the project's
DES-pdlc-commit-trailers (commit subjects and trailers):
  - its subject is one of the shapes under "Subjects", and a change it names is this
    branch's change;
  - it carries Intent; on a change's branch, Change with that change; and Req exactly
    when it changes files outside pdlc/.
It runs while the commit is still the newest, so `git commit --amend` fixes the commit at
once. It leaves merge commits, other branches and projects without pdlc alone. Exit 2
shows the problems to Claude.
"""
import glob
import json
import os
import re
import subprocess
import sys

DES = os.path.join("pdlc", "specs", "design", "DES-pdlc-commit-trailers.md")
PLACEHOLDERS = {"<change>": r"CH-\d+", "<intent>": r"IN-\d+", "<n>": r"\d+",
                "<design spec>": r"DES-[a-z0-9-]+"}


def git(root, *args):
    """git's output, stripped, or None when it fails."""
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def project_root(path):
    """The nearest folder at or above path that holds pdlc/config.md, or None."""
    path = os.path.realpath(path)
    while True:
        if os.path.isfile(os.path.join(path, "pdlc", "config.md")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def shapes(text):
    """(shape, regex) for each subject listed under "Subjects"."""
    found = []
    for line in section(text, "Subjects").splitlines():
        if line.lstrip().startswith("- "):
            found += re.findall(r"`([^`]+)`", line)
    out = []
    for shape in found:
        parts = re.split(r"(<[^>]+>)", shape)
        regex = "".join(PLACEHOLDERS.get(p, ".+") if p.startswith("<") else re.escape(p)
                        for p in parts if p)
        out.append((shape, re.compile("^%s$" % regex)))
    return out


def owner(root, branch):
    """("change", "CH-0031") or ("intent", "IN-0012") for the spec whose Branch is this one."""
    named = re.compile(r"\bBranch:[ \t]*%s[ \t]*(?:·|$)" % re.escape(branch), re.M)
    places = [("change", os.path.join(root, "pdlc", "changes", "CH-*", "change.md")),
              ("intent", os.path.join(root, "pdlc", "inbox", "IN-*.md"))]
    for kind, pattern in places:
        for path in sorted(glob.glob(pattern)):
            try:
                text = open(path).read()
            except OSError:
                continue
            if named.search(text):
                name = os.path.basename(os.path.dirname(path) if kind == "change" else path)
                return kind, "-".join(name.split("-", 2)[:2])
    return None


def problems(root):
    """What is wrong with the newest commit, or [] when it is fine or not pdlc's."""
    try:
        text = open(os.path.join(root, DES)).read()
    except OSError:
        return []
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    found = owner(root, branch) if branch and branch != "HEAD" else None
    newest = git(root, "reflog", "-1", "--format=%gs") or ""
    parents = (git(root, "rev-list", "--parents", "-n", "1", "HEAD") or "").split()
    if not found or not newest.startswith("commit") or len(parents) > 2:
        return []
    kind, spec_id = found
    subject = git(root, "log", "-1", "--format=%s") or ""
    # Trailer lines count wherever they sit in the message, as the trace finds them.
    body = git(root, "log", "-1", "--format=%b") or ""
    trailers = dict(re.findall(r"^(Intent|Change|Req|Ticket):[ \t]*(\S.*?)\s*$", body, re.M))
    files = (git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD") or "").split()

    wrong, listed = [], shapes(text)
    if listed and not any(regex.match(subject) for _, regex in listed):
        wrong.append('the subject "%s" is not one of these: %s'
                     % (subject, ", ".join("`%s`" % shape for shape, _ in listed)))
    for other in re.findall(r"\bCH-\d+\b", subject):
        if kind == "change" and other != spec_id:
            wrong.append("the subject names %s, but this is %s's branch" % (other, spec_id))
    if not trailers.get("Intent"):
        wrong.append("it has no Intent trailer")
    if kind == "change" and trailers.get("Change") != spec_id:
        wrong.append("it needs the trailer Change: %s" % spec_id)
    outside = [f for f in files if not f.startswith("pdlc/")]
    if outside and not trailers.get("Req"):
        wrong.append("it changes %s, outside pdlc/, so it needs a Req trailer" % outside[0])
    if not outside and "Req" in trailers:
        wrong.append("it changes only pdlc/ files, so it carries no Req trailer")
    return wrong


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (call.get("tool_input") or {}).get("command") or ""
    if call.get("tool_name") != "Bash" or not re.search(r"\bgit\b[^\n;|&]*\bcommit\b", command):
        return 0
    root = project_root(call.get("cwd") or os.getcwd())
    try:
        wrong = problems(root) if root else []
    except Exception:  # a broken check must never get in the way of work
        return 0
    if not wrong:
        return 0
    sha = git(root, "rev-parse", "--short", "HEAD")
    print("pdlc: commit %s doesn't follow DES-pdlc-commit-trailers:" % sha, file=sys.stderr)
    for line in wrong:
        print("  - %s" % line, file=sys.stderr)
    print("Fix it now, while it is the newest commit: `git commit --amend` with the right "
          "subject and trailers. Its files stay as they are.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
