#!/usr/bin/env python3
"""Measure volatility in a git repository.

Reads `git log` once and reports three things the decompose skill uses to place
walls in an established codebase:

  1. Component volatility - how often each component (directory prefix) changes,
     how much churns, and how long since it last changed.
  2. Component change coupling - pairs of components that keep changing in the
     same commits. High coupling across a proposed wall means the wall leaks.
  3. File hotspots and file change coupling - the same signals at file level.

Coupling degree follows code-maat: shared commits / average commits of the pair,
as a percentage. Commits touching more than --max-changeset files (bulk renames,
formatting sweeps, dependency bumps) are left out of coupling, as code-maat does.

Standard library only; works anywhere git and Python 3.8+ run (Windows included).

Examples:
  python volatility.py                          # whole repo, last 12 months
  python volatility.py --path src --depth 2     # components = src/<x>
  python volatility.py --since "2 years ago" --json > volatility.json
"""

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations

DEFAULT_EXCLUDES = [
    # lockfiles and dependency manifests that churn mechanically
    "*package-lock.json", "*yarn.lock", "*pnpm-lock.yaml", "*Cargo.lock",
    "*poetry.lock", "*Pipfile.lock", "*go.sum", "*Gemfile.lock",
    "*composer.lock", "*uv.lock",
    # vendored, built, or generated output
    "vendor/*", "*/vendor/*", "node_modules/*", "*/node_modules/*",
    "dist/*", "*/dist/*", "build/*", "*/build/*", "*.min.js", "*.min.css",
    "*.generated.*", "*_generated.*", "*.pb.go", "*_pb2.py",
    "*__snapshots__/*", "*.snap",
]

RECORD = "\x1e"
FIELD = "\x1f"


def run_git(args, cwd):
    try:
        out = subprocess.run(
            ["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True,
        )
    except FileNotFoundError:
        sys.exit("error: git not found on PATH")
    except subprocess.CalledProcessError as e:
        sys.exit("error: git %s failed:\n%s" % (" ".join(args), e.stderr.decode("utf-8", "replace")))
    return out.stdout.decode("utf-8", "replace")


def read_commits(repo, since, path):
    """Yield (hash, timestamp, [(path, added, deleted)]) newest first.

    Renames are followed: older commits are reported under the file's newest name.
    """
    args = ["log", "--no-merges", "-M", "--numstat", "-z",
            "--format=" + RECORD + "%H" + FIELD + "%at"]
    if since:
        args.append("--since=" + since)
    if path:
        args += ["--", path]
    raw = run_git(args, repo)

    alias = {}  # old path -> newest known path

    def resolve(p):
        seen = set()
        while p in alias and p not in seen:
            seen.add(p)
            p = alias[p]
        return p

    for chunk in raw.split(RECORD):
        if not chunk.strip():
            continue
        header, _, body = chunk.partition("\0")
        sha, _, ts = header.partition(FIELD)
        tokens = body.lstrip("\n").split("\0")
        files = []
        i = 0
        while i < len(tokens):
            tok = tokens[i].lstrip("\n")
            i += 1
            if not tok:
                continue
            parts = tok.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, name = parts
            if name == "":  # rename: old and new path follow as separate tokens
                if i + 1 >= len(tokens):
                    break
                old, new = tokens[i], tokens[i + 1]
                i += 2
                name = resolve(new)
                alias[old] = name
            else:
                name = resolve(name)
            a = int(added) if added.isdigit() else 0  # "-" for binary files
            d = int(deleted) if deleted.isdigit() else 0
            files.append((name, a, d))
        yield sha, int(ts or 0), files


def excluded(path, patterns):
    return any(fnmatch.fnmatch(path, p) for p in patterns)


def component_of(path, depth, root):
    """Directory prefix of `path` (relative to `root`), `depth` levels deep."""
    rel = path
    if root:
        prefix = root.rstrip("/") + "/"
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
    dirs = rel.split("/")[:-1]
    if not dirs:
        return "(root)"
    comp = "/".join(dirs[:depth])
    return (root.rstrip("/") + "/" + comp) if root else comp


def count_lines(repo, path):
    try:
        with open(os.path.join(repo, path), "rb") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return None  # deleted since, or not a regular file


def coupling(commit_sets, revs, min_revs, min_shared, min_degree, limit):
    shared = Counter()
    for entities in commit_sets:
        for a, b in combinations(sorted(entities), 2):
            shared[(a, b)] += 1
    rows = []
    for (a, b), n in shared.items():
        if revs[a] < min_revs or revs[b] < min_revs or n < min_shared:
            continue
        degree = 100.0 * n / ((revs[a] + revs[b]) / 2.0)
        if degree >= min_degree:
            rows.append({"a": a, "b": b, "shared": n, "degree": round(degree),
                         "revs_a": revs[a], "revs_b": revs[b]})
    rows.sort(key=lambda r: (-r["degree"], -r["shared"], r["a"], r["b"]))
    return rows[:limit]


def analyse(opts):
    repo = run_git(["rev-parse", "--show-toplevel"], opts.repo).strip()
    patterns = ([] if opts.no_default_excludes else DEFAULT_EXCLUDES) + opts.exclude
    now = time.time()

    file_revs, file_churn, file_last = Counter(), Counter(), {}
    comp_revs, comp_churn, comp_last = Counter(), Counter(), {}
    comp_files = defaultdict(set)
    file_sets, comp_sets = [], []
    commits = skipped_large = 0

    for _sha, ts, files in read_commits(repo, opts.since, opts.path):
        files = [f for f in files if not excluded(f[0], patterns)]
        if not files:
            continue
        commits += 1
        touched_files, touched_comps = set(), set()
        for name, a, d in files:
            comp = component_of(name, opts.depth, opts.path)
            touched_files.add(name)
            touched_comps.add(comp)
            file_churn[name] += a + d
            comp_churn[comp] += a + d
            comp_files[comp].add(name)
            file_last.setdefault(name, ts)  # newest first, so first seen = last change
            comp_last.setdefault(comp, ts)
        for name in touched_files:
            file_revs[name] += 1
        for comp in touched_comps:
            comp_revs[comp] += 1
        if len(touched_files) > opts.max_changeset:
            skipped_large += 1
            continue
        file_sets.append(touched_files)
        comp_sets.append(touched_comps)

    def age(ts):
        return int((now - ts) // 86400)

    components = []
    for comp, n in comp_revs.most_common():
        components.append({"component": comp, "commits": n, "churn": comp_churn[comp],
                           "files": len(comp_files[comp]), "days_since_change": age(comp_last[comp])})

    hotspots = []
    for name, n in file_revs.most_common(opts.top):
        loc = count_lines(repo, name)
        hotspots.append({"file": name, "commits": n, "churn": file_churn[name], "loc": loc,
                         "days_since_change": age(file_last[name])})

    # a file is a hotspot when it is both frequently changed and big
    live = [h for h in hotspots if h["loc"]]
    if live:
        loc_cut = sorted(h["loc"] for h in live)[int(len(live) * 0.75)]
        rev_cut = sorted(h["commits"] for h in live)[int(len(live) * 0.75)]
        for h in hotspots:
            h["hotspot"] = bool(h["loc"]) and h["loc"] >= loc_cut and h["commits"] >= rev_cut

    return {
        "repo": repo,
        "since": opts.since,
        "path": opts.path or ".",
        "depth": opts.depth,
        "commits_analysed": commits,
        "commits_excluded_from_coupling": skipped_large,
        "components": components,
        "component_coupling": coupling(comp_sets, comp_revs, opts.min_revs, opts.min_shared,
                                       opts.min_coupling, opts.top),
        "hotspots": hotspots,
        "file_coupling": coupling(file_sets, file_revs, opts.min_revs, opts.min_shared,
                                  opts.min_coupling, opts.top),
    }


def table(rows, cols):
    if not rows:
        return "_none above thresholds_\n"
    head = "| " + " | ".join(c[1] for c in cols) + " |\n"
    rule = "|" + "|".join("---" for _ in cols) + "|\n"
    body = ""
    for r in rows:
        cells = []
        for key, _ in cols:
            v = r.get(key)
            cells.append("" if v is None else ("yes" if v is True else "" if v is False else str(v)))
        body += "| " + " | ".join(cells) + " |\n"
    return head + rule + body


def render(report, top):
    out = []
    out.append("# Volatility report\n")
    out.append("repo `%s` · path `%s` · since `%s` · depth %d · %d commits (%d excluded from coupling as bulk changes)\n"
               % (report["repo"], report["path"], report["since"] or "all history", report["depth"],
                  report["commits_analysed"], report["commits_excluded_from_coupling"]))
    out.append("\n## Component volatility\n\nMost-changed first. Old and quiet = stable; frequent and recent = volatile.\n\n")
    out.append(table(report["components"][:top], [("component", "component"), ("commits", "commits"),
                                                  ("churn", "lines churned"), ("files", "files"),
                                                  ("days_since_change", "days since change")]))
    out.append("\n## Component change coupling\n\nComponents that change in the same commits. "
               "A high degree across a wall means the wall leaks, or the two belong together.\n\n")
    out.append(table(report["component_coupling"], [("a", "component A"), ("b", "component B"),
                                                     ("shared", "shared commits"), ("degree", "degree %")]))
    out.append("\n## File hotspots\n\nFrequently changed files. `hotspot` = top quartile for both commits and size.\n\n")
    out.append(table(report["hotspots"], [("file", "file"), ("commits", "commits"), ("churn", "lines churned"),
                                          ("loc", "loc"), ("days_since_change", "days since change"),
                                          ("hotspot", "hotspot")]))
    out.append("\n## File change coupling\n\n")
    out.append(table(report["file_coupling"], [("a", "file A"), ("b", "file B"),
                                               ("shared", "shared commits"), ("degree", "degree %")]))
    return "".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", default=".", help="any path inside the repository (default: .)")
    p.add_argument("--path", default="", help="only analyse this subtree, e.g. src/billing")
    p.add_argument("--since", default="12 months ago", help='git date, e.g. "6 months ago"; "" for all history')
    p.add_argument("--depth", type=int, default=1, help="directory levels (below --path) that make a component")
    p.add_argument("--top", type=int, default=25, help="rows per table (default 25)")
    p.add_argument("--min-revs", type=int, default=5, help="ignore entities with fewer commits (code-maat default 5)")
    p.add_argument("--min-shared", type=int, default=5, help="ignore pairs with fewer shared commits (code-maat default 5)")
    p.add_argument("--min-coupling", type=int, default=30, help="minimum coupling degree %% (code-maat default 30)")
    p.add_argument("--max-changeset", type=int, default=30, help="skip commits touching more files than this in coupling (code-maat default 30)")
    p.add_argument("--exclude", action="append", default=[], help="extra glob to ignore; repeatable")
    p.add_argument("--no-default-excludes", action="store_true", help="keep lockfiles, vendor, build output, generated code")
    p.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    opts = p.parse_args(argv)
    opts.path = opts.path.strip("/").replace("\\", "/")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # odd file names on narrow consoles
    report = analyse(opts)
    if opts.json:
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render(report, opts.top))


if __name__ == "__main__":
    main()
