#!/usr/bin/env python3
"""The scripted verdict of rubric item R7 of a pdlc vet: trailers in one block, and a clean tree.

Usage: check_trailers.py PROJECT [--since REF]

Reads each commit since REF (default: start), on every branch, except merge commits. A commit
counts when its subject is one of the shapes under "Subjects" in the project's
DES-pdlc-commit-trailers. The script reads its trailers with `git interpret-trailers --parse`,
as git does, and checks these rules of the design spec:
  - the commit has Intent;
  - when the subject names a change, the commit has Change with that change;
  - the commit has Req exactly when it changes a file outside pdlc/;
  - each pdlc trailer line of the message is in the last paragraph, where git reads it.
Then it checks `git status --porcelain -uall`, without the files of a vet run (vet/scripts/snapshot.py
lists these).

It prints a JSON verdict: "met" (no problem), "missed" (each pdlc commit has a problem, or there
is no pdlc commit and the tree is not clean), "partial" (any other problem), or "n/a" (no pdlc
commit and a clean tree). Exit 0 with a verdict, 2 for a usage error.
"""
import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
BIN = REPO / "plugins" / "pdlc" / "skills" / "init" / "references" / "bin"
DES_NAME = "DES-pdlc-commit-trailers.md"
DES_DEFAULT = BIN.parent / "defaults" / DES_NAME
PLACEHOLDERS = {"<change>": r"CH-\d+", "<intent>": r"IN-\d+", "<n>": r"\d+", "<design spec>": r"DES-[a-z0-9-]+"}

sys.path.insert(0, str(BIN))
import pdlclib  # noqa: E402


def _snapshot():
    spec = importlib.util.spec_from_file_location("vet_snapshot", REPO / "vet" / "scripts" / "snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(project, *args, stdin=None):
    done = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True,
                          input=stdin, errors="replace")
    return done.stdout if done.returncode == 0 else None


def subject_shapes(project):
    """A compiled regex for each subject shape of the project's design spec (or the default)."""
    path = Path(project) / "pdlc" / "specs" / "design" / DES_NAME
    text = (path if path.is_file() else DES_DEFAULT).read_text()
    shapes = []
    for line in pdlclib.section(text, "Subjects").splitlines():
        if not line.lstrip().startswith("- "):
            continue
        for shape in re.findall(r"`([^`]+)`", line):
            parts = re.split(r"(<[^>]+>)", shape)
            regex = "".join(PLACEHOLDERS.get(p, ".+") if p.startswith("<") else re.escape(p) for p in parts if p)
            shapes.append(re.compile("^%s$" % regex))
    return shapes


def commit_problems(project, sha, subject, body):
    """What is wrong with the pdlc trailers of one commit."""
    parsed = git(project, "interpret-trailers", "--parse", stdin=subject + "\n\n" + body) or ""
    block = {}
    for line in parsed.splitlines():
        found = pdlclib.TRAILER_LINE.match(line)
        if found:
            block[found.group(1)] = found.group(2)
    anywhere = pdlclib.trailers(body)
    problems = []
    lost = sorted(set(anywhere) - set(block))
    if lost:
        problems.append("%s not in the last paragraph, where git reads trailers" % ", ".join(lost))
    files = (git(project, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha) or "").split()
    outside = [f for f in files if not f.startswith("pdlc/")]
    if "Intent" not in anywhere:
        problems.append("no Intent trailer")
    named = re.findall(r"\bCH-\d+\b", subject)
    if named and anywhere.get("Change") != named[0]:
        problems.append("the subject names %s, but the Change trailer is %s" % (named[0], anywhere.get("Change", "missing")))
    if outside and "Req" not in anywhere:
        problems.append("it changes %s, outside pdlc/, but has no Req trailer" % outside[0])
    if not outside and "Req" in anywhere:
        problems.append("it changes only pdlc/ files, but has a Req trailer")
    return problems


def check(project, since="start"):
    """The verdict, as a dict with "verdict", "commits" ({sha, subject, problems}), "status" and "evidence"."""
    project = Path(project)
    listed = git(project, "rev-list", "--reverse", "--no-merges", "--all", "--not", since)
    if listed is None:
        raise ValueError("no such ref: %s" % since)
    shapes = subject_shapes(project)
    commits = []
    for sha in listed.split():
        subject = (git(project, "log", "-1", "--format=%s", sha) or "").strip()
        if not any(shape.match(subject) for shape in shapes):
            continue
        body = (git(project, "log", "-1", "--format=%b", sha) or "").strip("\n")
        commits.append({"sha": sha[:12], "subject": subject, "problems": commit_problems(project, sha, subject, body)})
    status = _snapshot().status(str(project.resolve()))
    bad = [c for c in commits if c["problems"]]
    if not commits:
        verdict = "n/a" if not status else "missed"
    elif len(bad) == len(commits):
        verdict = "missed"
    else:
        verdict = "partial" if bad or status else "met"
    evidence = ["%d of %d pdlc commits have a problem" % (len(bad), len(commits))] if commits else ["no pdlc commit since %s" % since]
    evidence += ["%s: %s" % (c["sha"], "; ".join(c["problems"])) for c in bad]
    evidence += ["stray file: %s" % line for line in status]
    return {"verdict": verdict, "commits": commits, "status": status, "evidence": evidence}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project")
    parser.add_argument("--since", default="start")
    args = parser.parse_args(argv)
    if not Path(args.project).is_dir():
        print("check_trailers: %s is not a folder" % args.project, file=sys.stderr)
        return 2
    try:
        result = check(args.project, args.since)
    except ValueError as error:
        print("check_trailers: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
