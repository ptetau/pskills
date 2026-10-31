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

On any branch, it also runs the writing check of the project (pdlc/bin/check_writing.py) on
the lines that the commit wrote in the specs, the intents, and the change folders. It skips
the review packets and results. The findings go to Claude in the same way, so that Claude
can amend the commit. The hook reports one set of findings once for each parent commit, and
at most three sets for one parent. So a finding that Claude cannot fix does not block the
work.

This hook is the only writing check of a pdlc stage. The message tells Claude to fix all the
findings in one edit and to amend the commit one time. The message also tells Claude not to
run check_writing.py itself.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

DES = os.path.join("pdlc", "specs", "design", "DES-pdlc-commit-trailers.md")
WRITING_CHECK = os.path.join("pdlc", "bin", "check_writing.py")
# The text that the stages write. The review folders hold packets (copies) and the results
# of the reviewers. The other pdlc/ files come from the plugin.
WRITTEN_TEXT = re.compile(r"^pdlc/(?:specs|inbox|changes)/(?!.*/review/).*\.md$")
REPORTED = "pdlc-writing-reported"  # under .git: the sets of findings that this hook reported
MAX_REPORTS = 3
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


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch. The value is
    bare: "IN-0001 (poll-input-errors)" gives "IN-0001", and "`pdlc/CH-0001-x`" gives
    "pdlc/CH-0001-x"."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    if not match:
        return None
    value = match.group(1).replace("`", "")
    return re.sub(r"\s+\(.*\)$", "", value).strip()


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
    places = [("change", os.path.join(root, "pdlc", "changes", "CH-*", "change.md")),
              ("intent", os.path.join(root, "pdlc", "inbox", "IN-*.md"))]
    for kind, pattern in places:
        for path in sorted(glob.glob(pattern)):
            try:
                text = open(path).read()
            except OSError:
                continue
            if field(text, "Branch") == branch:
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


def fresh_commit(root):
    """True when HEAD is the commit that this Bash call made or amended, with one parent.
    A checkout, a merge, or a root commit gets no writing check."""
    newest = git(root, "reflog", "-1", "--format=%gs") or ""
    parents = (git(root, "rev-list", "--parents", "-n", "1", "HEAD") or "").split()
    return newest.startswith("commit") and len(parents) == 2


def written_text(root):
    """The .md files of the newest commit that a pdlc stage wrote, and that still exist."""
    files = (git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") or "").split()
    return [f for f in files if WRITTEN_TEXT.match(f) and os.path.isfile(os.path.join(root, f))]


def writing_findings(root):
    """The findings of the writing check in the lines that the newest commit wrote, or []."""
    if not os.path.isfile(os.path.join(root, WRITING_CHECK)) or not fresh_commit(root):
        return []
    files = written_text(root)
    if not files:
        return []
    try:
        done = subprocess.run([sys.executable, WRITING_CHECK, "--since", "HEAD~1", *files],
                              cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    return [line for line in done.stdout.splitlines() if " \u00b7 " in line]


def reported_before(root, findings):
    """True when this hook already reported this set of findings for a commit with the same
    parent, or already reported MAX_REPORTS sets for that parent. If not, it records the set
    and returns False. The record is under .git, so the working tree stays clean."""
    parent = git(root, "rev-parse", "HEAD~1") or "none"
    plain = sorted(re.sub(r":\d+ \u00b7 ", " \u00b7 ", line) for line in findings)
    key = hashlib.sha1("\n".join(plain).encode()).hexdigest()[:12]
    git_dir = git(root, "rev-parse", "--absolute-git-dir") or os.path.join(root, ".git")
    path = os.path.join(git_dir, REPORTED)
    try:
        lines = open(path).read().splitlines()
    except OSError:
        lines = []
    seen = [line.split()[1] for line in lines if line.startswith(parent + " ") and len(line.split()) > 1]
    if key in seen or len(seen) >= MAX_REPORTS:
        return True
    try:
        with open(path, "a") as record:
            record.write("%s %s\n" % (parent, key))
    except OSError:
        pass
    return False


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (call.get("tool_input") or {}).get("command") or ""
    if call.get("tool_name") != "Bash" or not re.search(r"\bgit\b[^\n;|&]*\bcommit\b", command):
        return 0
    root = project_root(call.get("cwd") or os.getcwd())
    if not root:
        return 0
    try:
        wrong = problems(root)
        findings = writing_findings(root)
        if findings and reported_before(root, findings):
            findings = []
    except Exception:  # a broken check must never get in the way of work
        return 0
    if not wrong and not findings:
        return 0
    sha = git(root, "rev-parse", "--short", "HEAD")
    if wrong:
        print("pdlc: commit %s doesn't follow DES-pdlc-commit-trailers:" % sha, file=sys.stderr)
        for line in wrong:
            print("  - %s" % line, file=sys.stderr)
        print("Fix it now, while it is the newest commit: `git commit --amend` with the right "
              "subject and trailers. Its files stay as they are.", file=sys.stderr)
    if findings:
        print("pdlc: commit %s has %d writing finding%s in the text that it wrote (DES-writing-style):"
              % (sha, len(findings), "" if len(findings) == 1 else "s"), file=sys.stderr)
        for line in findings:
            print("  - %s" % line, file=sys.stderr)
        print("Fix all of these findings in one edit. Then amend the commit one time with "
              "`git commit --amend -a --no-edit`. If the subject or a trailer also needs a fix, give "
              "the full message with `-m` in place of `--no-edit`. Do not run check_writing.py "
              "yourself, because this hook checks the amended commit. A finding that you cannot "
              "fix, for example in a quoted message, can stay. This hook reports a set of findings "
              "once.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
