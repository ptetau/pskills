#!/usr/bin/env python3
"""The scripted verdict of rubric item R7 of a pdlc vet: trailers in one block, and a clean tree.

Usage: check_trailers.py PROJECT [--since REF] [--stages]

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

With --stages, it gives the verdict of rubric item R5 instead: the stage subjects in order. The
intent and each change have their own order (README "Stages and handoffs"). A subject before a
stage that came earlier is "missed". A stage that is skipped between two stages that ran is
"partial". "Send back" lets the stages of its change run again. Update, Stop, Convention, and
the subjects on main have no place in the order.
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


# The stage subjects in their order. Each entry is (name, subject prefix).
INTENT_STAGES = [("Specify", "Specify IN-"), ("Ready", "Ready IN-"), ("Plan", "Plan IN-"),
                 ("Acceptance", "Acceptance IN-"), ("Lock acceptance", "Lock acceptance IN-"),
                 ("Review acceptance", "Review acceptance IN-"), ("Acceptance reviewed", "Acceptance reviewed IN-")]
CHANGE_STAGES = [("Start", "Start CH-"), ("Tests", "Tests CH-"), ("Lock tests", "Lock tests CH-"),
                 ("Review tests", "Review tests CH-"), ("Tests reviewed", "Tests reviewed CH-"),
                 ("Build", "Build CH-"), ("Built", "Built CH-"), ("Verify", "Verify CH-"),
                 ("Verified", "Verified CH-"), ("Visual review", "Visual review CH-"), ("Propose", "Propose CH-")]


def stage_of(subject):
    """(sequence key, stage index, stage list) of a stage subject, ("send back", key) or None."""
    found = re.search(r"\b(IN|CH)-\d+\b", subject)
    if not found:
        return None
    if subject.startswith("Send back CH-"):
        return ("send back", found.group(0))
    for stages in (INTENT_STAGES, CHANGE_STAGES):
        for index, (_, prefix) in enumerate(stages):
            if subject.startswith(prefix):
                return (found.group(0), index, stages)
    return None


def check_stages(project, since="start"):
    """The verdict of the stage order, as a dict with "verdict", "commits" and "evidence"."""
    project = Path(project)
    listed = git(project, "rev-list", "--reverse", "--topo-order", "--no-merges", "--all", "--not", since)
    if listed is None:
        raise ValueError("no such ref: %s" % since)
    seen, top, commits, order, gaps = {}, {}, [], [], []
    for sha in listed.split():
        subject = (git(project, "log", "-1", "--format=%s", sha) or "").strip()
        stage = stage_of(subject)
        if not stage:
            continue
        commits.append({"sha": sha[:12], "subject": subject})
        if stage[0] == "send back":
            top[stage[1]] = -1
            continue
        key, index, stages = stage
        seen.setdefault(key, (set(), stages))[0].add(index)
        if index < top.get(key, -1):
            order.append("%s: \"%s\" comes after \"%s\"" % (sha[:12], subject, stages[top[key]][0]))
        top[key] = max(top.get(key, -1), index)
    for key, (indexes, stages) in sorted(seen.items()):
        missing = [stages[i][0] for i in range(min(indexes), max(indexes)) if i not in indexes]
        if missing:
            gaps.append("%s: no %s commit" % (key, ", ".join("\"%s\"" % m for m in missing)))
    if not commits:
        verdict = "n/a"
    else:
        verdict = "missed" if order else "partial" if gaps else "met"
    evidence = order + gaps or ["%d stage commits in order" % len(commits)]
    return {"verdict": verdict, "commits": commits, "evidence": evidence}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project")
    parser.add_argument("--since", default="start")
    parser.add_argument("--stages", action="store_true", help="check the order of the stage subjects (R5)")
    args = parser.parse_args(argv)
    if not Path(args.project).is_dir():
        print("check_trailers: %s is not a folder" % args.project, file=sys.stderr)
        return 2
    try:
        result = (check_stages if args.stages else check)(args.project, args.since)
    except ValueError as error:
        print("check_trailers: %s" % error, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
