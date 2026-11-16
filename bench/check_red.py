#!/usr/bin/env python3
"""The scripted verdict of rubric item R2 of a pdlc tests vet: was the lock red?

Usage: check_red.py PROJECT [--since REF]

Finds each change of the project whose "Tests-Locked:" line holds a commit hash that is not
in REF (default: start), on any branch. Unpacks the tree of that commit into a temporary
folder, runs the "all:" checks command of its pdlc/config.md there, and classifies the
output with `classify_red` of pdlclib. The script imports pdlclib from the plugin of this
repository, not from the project, so it also grades a project that master's plugin made. It
does not change the project: it reads with `git archive` and `git show`, and makes no
worktree, branch, or file in it.

It prints a JSON verdict {"verdict": "met"|"partial"|"missed"|"n/a", "evidence": "..."}.
"met" is red or red-compile, "missed" is broken, "partial" is unknown (or no checks command),
and "n/a" is no change that reached a lock. With more than one change, the verdict is "met"
when all are met, "missed" when all are missed, and "partial" otherwise. A project folder
without pdlc/ but with a "proj" folder (a vet run folder) uses "proj".
Exit 0 with a verdict, 2 for a usage error.
"""
import argparse
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BIN = HERE.parent / "plugins" / "pdlc" / "skills" / "init" / "references" / "bin"
TIME_LIMIT = 300

sys.path.insert(0, str(BIN))
import pdlclib  # noqa: E402

VERDICT = {"red": "met", "red-compile": "met", "broken": "missed", "unknown": "partial"}


def git(project, *args, binary=False):
    done = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=not binary,
                          errors=None if binary else "replace")
    return done.stdout if done.returncode == 0 else None


def locks(project, since):
    """[{change, commit, spec}] for each change with a lock commit that is new since `since`.
    `spec` is the text of the change spec at the tip of the newest branch that holds the lock."""
    found = {}
    refs = (git(project, "for-each-ref", "--format=%(refname)", "refs/heads") or "").split()
    for ref in refs:
        for path in (git(project, "ls-tree", "-r", "--name-only", ref, "--", "pdlc/changes") or "").split("\n"):
            if not path.endswith("/change.md"):
                continue
            text = git(project, "show", "%s:%s" % (ref, path)) or ""
            match = re.search(r"^Tests-Locked:[ \t]*`?([0-9a-f]{7,40})`?[ \t]*$", text, re.M)
            if not match:
                continue
            commit = (git(project, "rev-parse", "--verify", "-q", match.group(1) + "^{commit}") or "").strip()
            if not commit:
                continue
            if git(project, "rev-parse", "--verify", "-q", since) and \
                    subprocess.run(["git", "-C", str(project), "merge-base", "--is-ancestor", commit, since],
                                   capture_output=True).returncode == 0:
                continue
            change = path.split("/")[2].split("-", 2)[:2]
            found[("-".join(change), commit)] = {"change": "-".join(change), "commit": commit, "spec": text}
    newest = {}
    for item in found.values():
        stamp = int((git(project, "show", "-s", "--format=%ct", item["commit"]) or "0").strip() or 0)
        if item["change"] not in newest or stamp > newest[item["change"]][0]:
            newest[item["change"]] = (stamp, item)
    return [item for _, item in sorted(newest.values(), key=lambda pair: pair[1]["change"])]


def run_checks(project, commit, command):
    """(output, exit code) of the command in an unpacked copy of the tree at `commit`."""
    with tempfile.TemporaryDirectory(prefix="check-red-") as tmp:
        data = git(project, "archive", "--format=tar", commit, binary=True)
        if data is None:
            return "", None
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, members=[m for m in tar if not m.issym() and not m.islnk()], filter="data")
        try:
            done = subprocess.run(pdlclib.red_run_command(command), shell=True, cwd=tmp, capture_output=True, text=True,
                                  errors="replace", stdin=subprocess.DEVNULL, timeout=TIME_LIMIT)
        except subprocess.TimeoutExpired:
            return "", None
        return done.stdout + "\n" + done.stderr, done.returncode


def classify_lock(project, item):
    """(verdict of the classifier, evidence string) for one lock."""
    commit = item["commit"]
    name = item["change"]
    config = git(project, "show", "%s:pdlc/config.md" % commit) or ""
    command = pdlclib.checks_command(config)
    if not command:
        return "unknown", "%s: pdlc/config.md has no usable \"all:\" command at the lock %s" % (name, commit[:12])
    names = (git(project, "ls-tree", "-r", "--name-only", commit, "--", "pdlc/changes") or "").split("\n")
    path = next((p for p in names if p.startswith("pdlc/changes/%s-" % name) and p.endswith("/change.md")), None)
    text = (git(project, "show", "%s:%s" % (commit, path)) if path else None) or item["spec"]
    scope = pdlclib.field(text, "Scope") or ""
    scope_text = ""
    for folder in ("capabilities", "jobs", "design"):
        scope_text = scope_text or git(project, "show", "%s:pdlc/specs/%s/%s.md" % (commit, folder, scope)) or ""
    inputs = pdlclib.red_inputs(text, scope_text)
    output, code = run_checks(project, commit, command)
    got = pdlclib.classify_red(allow_pass=pdlclib.red_allowed(item["spec"]), output=output, exit_code=code, **inputs)
    return got["verdict"], "%s at %s: %s" % (name, commit[:12], "; ".join(got["evidence"]))


def check(project, since="start"):
    """{"verdict", "evidence"} for the project."""
    project = Path(project)
    if not (project / "pdlc").is_dir() and (project / "proj" / "pdlc").is_dir():
        project = project / "proj"
    items = locks(project, since)
    if not items:
        return {"verdict": "n/a", "evidence": "no change reached a lock of its checks since %s" % since}
    graded = [classify_lock(project, item) for item in items]
    verdicts = {VERDICT[v] for v, _ in graded}
    verdict = verdicts.pop() if len(verdicts) == 1 else "partial"
    return {"verdict": verdict, "evidence": " | ".join(e for _, e in graded)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project")
    parser.add_argument("--since", default="start")
    args = parser.parse_args(argv)
    if not Path(args.project).is_dir():
        print("check_red: %s is not a folder" % args.project, file=sys.stderr)
        return 2
    print(json.dumps(check(args.project, args.since), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
