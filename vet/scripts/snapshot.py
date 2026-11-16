#!/usr/bin/env python3
"""Print the git facts of a vet run's worktree as a Markdown "## Repos" section.

Usage: snapshot.py <worktree root>

Finds the worktree's own repo and every nested repo. For each repo, lists the
commits (subject and full body) and `git status --porcelain -uall`. Paths under
a `.vet-capture` or `.vet-tmp` segment are excluded by pathspec and never
listed. Never commits. Always exits 0.
"""

import os
import subprocess
import sys

VET_DIRS = (".vet-capture", ".vet-tmp")
EXCLUDES = [f":(exclude,glob)**/{d}/**" for d in VET_DIRS] + [
    f":(exclude,glob){d}/**" for d in VET_DIRS
]
SEP = "\x1e"


def git(repo, *args):
    p = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, errors="replace"
    )
    return p.stdout if p.returncode == 0 else ""


def find_repos(root):
    repos = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in VET_DIRS and d != "node_modules"]
        if ".git" in dirnames or os.path.isfile(os.path.join(dirpath, ".git")):
            repos.append(dirpath)
        dirnames[:] = [d for d in dirnames if d != ".git"]
    return sorted(repos, key=lambda p: (p != root, p))


def base_of(repo):
    """The commit the repo's HEAD started from, from the oldest HEAD reflog entry."""
    lines = git(repo, "reflog", "--format=%H", "HEAD").split()
    return lines[-1] if lines else ""


def commits(repo, is_root):
    rng = ["HEAD"]
    if is_root:
        base = base_of(repo)
        rng = [f"{base}..HEAD"] if base else ["HEAD", "--not", "--remotes", "--tags"]
    out = git(repo, "log", f"--format=%H{SEP}%B{SEP}%x00", "--reverse", *rng)
    result = []
    for rec in out.split(SEP + "\x00"):
        rec = rec.strip("\n")
        if SEP not in rec:
            continue
        sha, body = rec.split(SEP, 1)
        body = body.strip(SEP).strip()
        if body:
            result.append((sha.strip()[:12], body))
    return result


def status(repo, nested=()):
    lines = git(repo, "status", "--porcelain", "-uall", "--", ".", *EXCLUDES).splitlines()
    own = {os.path.relpath(n, repo) + "/" for n in nested}
    return [
        l
        for l in lines
        if l[3:] not in own and not any(f"/{d}/" in "/" + l[3:] + "/" for d in VET_DIRS)
    ]


def render(root):
    root = os.path.realpath(root)
    out = ["## Repos", ""]
    repos = find_repos(root)
    if not repos:
        out += ["No git repository found.", ""]
    for repo in repos:
        rel = os.path.relpath(repo, root)
        out += [f"### {rel}", "", "Commits:"]
        cs = commits(repo, repo == root)
        if not cs:
            out.append("None.")
        for sha, body in cs:
            out += ["", f"#### {sha}", "", "```", body, "```"]
        out += ["", "Status (`git status --porcelain -uall`):", "", "```"]
        out += status(repo, [r for r in repos if r != repo])
        out += ["```", ""]
    return "\n".join(out)


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print("usage: snapshot.py <worktree root>", file=sys.stderr)
        return 0
    print(render(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
