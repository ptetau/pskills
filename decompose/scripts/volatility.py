#!/usr/bin/env python3
"""Measure volatility in a git repository.

Reads `git log` once and reports what the decompose skill needs to place walls in an
established codebase:

  1. Component volatility - how often each component (directory prefix) changes,
     in how many months, by how many people, and how long since it last changed.
  2. Component change coupling - pairs of components that keep changing in the
     same commits. High coupling across a proposed wall means the wall leaks.
  3. File hotspots and file change coupling - the same signals at file level. Tornhill
     describes a hotspot as the overlap of high change frequency and large size; this
     script's cutoff (top quartile for both, among all changed files that still exist)
     is its own choice.

Change coupling follows code-maat (Tornhill): degree = shared commits / average
commits of the pair, as a percentage, truncated. Pairs need an average of --min-revs commits
and at least --min-shared shared commits. Commits touching more than --max-changeset
files (sweeping renames, dependency bumps) are left out of coupling entirely.
The thresholds are code-maat's defaults for *listing* a pair. They are noise floors to
tune per codebase, not verdicts.

Noise filters: merge commits, whitespace-only changes, commits listed in
.git-blame-ignore-revs, lockfiles, vendored/built/generated paths (default globs plus
linguist-generated / linguist-vendored in .gitattributes). Renames are followed.

Standard library only; runs anywhere git and Python 3.8+ run (Windows included).

Examples:
  python volatility.py                          # whole repo, last 12 months
  python volatility.py --path src --depth 2     # components are src/<a>/<b>
  python volatility.py --first-parent           # one changeset per merged PR
  python volatility.py --since 2026-01-01 --until 2026-04-01   # a fixed window
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
    # lockfiles that churn mechanically
    "*package-lock.json", "*yarn.lock", "*pnpm-lock.yaml", "*Cargo.lock",
    "*poetry.lock", "*Pipfile.lock", "*go.sum", "*Gemfile.lock",
    "*composer.lock", "*uv.lock",
    # vendored, built, or generated output
    "vendor/*", "*/vendor/*", "third_party/*", "*/third_party/*",
    "node_modules/*", "*/node_modules/*", "dist/*", "*/dist/*", "build/*", "*/build/*",
    "*.min.js", "*.min.css", "*.generated.*", "*_generated.*", "*.pb.go", "*_pb2.py",
    "*__snapshots__/*", "*.snap",
]

RECORD = "\x1e"
FIELD = "\x1f"


def run_git(args, cwd, stdin=None):
    try:
        out = subprocess.run(
            ["git"] + args, cwd=cwd, input=stdin, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, check=True,
        )
    except FileNotFoundError:
        sys.exit("error: git not found on PATH")
    except subprocess.CalledProcessError as e:
        sys.exit("error: git %s failed:\n%s" % (" ".join(args[:3]), e.stderr.decode("utf-8", "replace")))
    return out.stdout.decode("utf-8", "replace")


def read_commits(repo, since, until, path, first_parent):
    """Yield (sha, timestamp, author, [(path, added, deleted)]) newest first.

    Renames are followed: older commits are reported under the file's newest name.
    """
    args = ["log", "-M", "-w", "--numstat", "-z",
            "--format=" + RECORD + "%H" + FIELD + "%at" + FIELD + "%aN"]
    if first_parent:  # each merge becomes one changeset: the whole PR
        args += ["--first-parent", "--diff-merges=first-parent"]
    else:
        args.append("--no-merges")
    if since:
        args.append("--since=" + since)
    if until:
        args.append("--until=" + until)
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
        sha, ts, author = (header.split(FIELD) + ["", ""])[:3]
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
        yield sha, int(ts or 0), author, files


def ignored_revs(repo):
    """Commits the repo already marks as noise for `git blame`."""
    try:
        with open(os.path.join(repo, ".git-blame-ignore-revs"), encoding="utf-8") as f:
            return {line.split()[0] for line in f if line.strip() and not line.startswith("#")}
    except OSError:
        return set()


def linguist_excluded(repo, paths):
    """Paths marked linguist-generated or linguist-vendored in .gitattributes."""
    if not paths:
        return set()
    out = run_git(["check-attr", "--stdin", "-z", "linguist-generated", "linguist-vendored"],
                  repo, stdin="\0".join(sorted(paths)).encode("utf-8") + b"\0")
    fields = out.split("\0")
    marked = set()
    for i in range(0, len(fields) - 2, 3):
        path, _attr, value = fields[i:i + 3]
        if value in ("set", "true"):
            marked.add(path)
    return marked


def glob_excluded(path, patterns):
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
        return (root.rstrip("/") + " (top level)") if root else "(root)"
    comp = "/".join(dirs[:depth])
    return (root.rstrip("/") + "/" + comp) if root else comp


def count_lines(repo, path):
    try:
        with open(os.path.join(repo, path), "rb") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return None  # deleted since, or not a regular file


def coupling(commit_sets, min_revs, min_shared, min_degree, limit):
    """code-maat's logical coupling over the given changesets."""
    revs, shared = Counter(), Counter()
    for entities in commit_sets:
        revs.update(entities)
        for a, b in combinations(sorted(entities), 2):
            shared[(a, b)] += 1
    rows = []
    for (a, b), n in shared.items():
        avg = (revs[a] + revs[b]) / 2.0
        if avg < min_revs or n < min_shared:
            continue
        degree = int(100.0 * n / avg)  # code-maat truncates
        if degree >= min_degree:
            rows.append({"a": a, "b": b, "shared": n, "degree": degree,
                         "revs_a": revs[a], "revs_b": revs[b]})
    rows.sort(key=lambda r: (-r["degree"], -r["shared"], r["a"], r["b"]))
    return rows[:limit]


def analyse(opts):
    repo = run_git(["rev-parse", "--show-toplevel"], opts.repo).strip()
    shallow = run_git(["rev-parse", "--is-shallow-repository"], repo).strip() == "true"
    patterns = ([] if opts.no_default_excludes else DEFAULT_EXCLUDES) + opts.exclude
    skip = ignored_revs(repo)

    commits = [c for c in read_commits(repo, opts.since, opts.until, opts.path, opts.first_parent)
               if c[0] not in skip]
    all_paths = {f[0] for c in commits for f in c[3]}
    drop = {p for p in all_paths if glob_excluded(p, patterns)}
    if not opts.no_default_excludes:
        drop |= linguist_excluded(repo, all_paths - drop)

    now = time.time()
    file_revs, file_churn, file_last = Counter(), Counter(), {}
    comp_revs, comp_churn, comp_last = Counter(), Counter(), {}
    comp_files, comp_authors, comp_months = defaultdict(set), defaultdict(set), defaultdict(set)
    file_sets, comp_sets = [], []
    analysed = bulk = 0

    for _sha, ts, author, files in commits:
        files = [f for f in files if f[0] not in drop]
        if not files:
            continue
        analysed += 1
        month = time.strftime("%Y-%m", time.gmtime(ts))
        touched_files, touched_comps = set(), set()
        for name, a, d in files:
            comp = component_of(name, opts.depth, opts.path)
            touched_files.add(name)
            touched_comps.add(comp)
            file_churn[name] += a + d
            comp_churn[comp] += a + d
            comp_files[comp].add(name)
            comp_authors[comp].add(author)
            comp_months[comp].add(month)
            file_last.setdefault(name, ts)  # newest first, so first seen = last change
            comp_last.setdefault(comp, ts)
        file_revs.update(touched_files)
        comp_revs.update(touched_comps)
        if len(touched_files) > opts.max_changeset:
            bulk += 1
            continue
        file_sets.append(touched_files)
        comp_sets.append(touched_comps)

    def age(ts):
        return int((now - ts) // 86400)

    components = []
    for comp, n in comp_revs.most_common():
        components.append({"component": comp, "commits": n, "months_active": len(comp_months[comp]),
                           "authors": len(comp_authors[comp]), "churn": comp_churn[comp],
                           "files": len(comp_files[comp]), "days_since_change": age(comp_last[comp])})

    # Tornhill: a hotspot is where high change frequency overlaps large size. The cutoff
    # (above the 75th percentile for both, over every changed file that still exists; strict,
    # so ties at the cutoff don't count) is this script's.
    loc = {name: count_lines(repo, name) for name in file_revs}
    live = [name for name in file_revs if loc[name]]
    loc_cut = sorted(loc[f] for f in live)[int(len(live) * 0.75)] if live else 0
    rev_cut = sorted(file_revs[f] for f in live)[int(len(live) * 0.75)] if live else 0
    hotspots = []
    for name, n in file_revs.most_common(opts.top):
        hotspots.append({"file": name, "commits": n, "churn": file_churn[name], "loc": loc[name],
                         "days_since_change": age(file_last[name]),
                         "hotspot": bool(loc[name]) and loc[name] > loc_cut and n > rev_cut})

    return {
        "repo": repo,
        "shallow_clone": shallow,
        "since": opts.since,
        "until": opts.until,
        "path": opts.path or ".",
        "depth": opts.depth,
        "changesets": "first-parent (one per merged PR)" if opts.first_parent else "commits (merges skipped)",
        "commits_analysed": analysed,
        "commits_excluded_from_coupling": bulk,
        "components": components,
        "component_coupling": coupling(comp_sets, opts.min_revs, opts.min_shared, opts.min_coupling, opts.top),
        "hotspots": hotspots,
        "file_coupling": coupling(file_sets, opts.min_revs, opts.min_shared, opts.min_coupling, opts.top),
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
            cells.append("" if v is None or v is False else "yes" if v is True else str(v))
        body += "| " + " | ".join(cells) + " |\n"
    return head + rule + body


def render(report, top):
    out = ["# Volatility report\n\n"]
    out.append("repo `%s` · path `%s` · since `%s`%s · depth %d · %s · %d analysed, %d bulk commits left out of coupling\n"
               % (report["repo"], report["path"], report["since"] or "all history",
                  (" until `%s`" % report["until"]) if report["until"] else "", report["depth"],
                  report["changesets"], report["commits_analysed"], report["commits_excluded_from_coupling"]))
    if report["shallow_clone"]:
        out.append("\n**Warning:** shallow clone, so history is truncated. Run `git fetch --unshallow` first.\n")
    out.append("\n## Component volatility\n\nMost-changed first. Old and quiet = stable. "
               "Frequent, recent, and spread over many months = volatile.\n\n")
    out.append(table(report["components"][:top], [
        ("component", "component"), ("commits", "commits"), ("months_active", "months active"),
        ("authors", "authors"), ("churn", "lines churned"), ("files", "files"),
        ("days_since_change", "days since change")]))
    out.append("\n## Component change coupling\n\nComponents that change in the same commits. "
               "Listed pairs are questions, not verdicts: expected coupling is cohesion; "
               "surprising coupling across a wall means it leaks, or the two belong together.\n\n")
    out.append(table(report["component_coupling"], [
        ("a", "component A"), ("b", "component B"), ("shared", "shared commits"), ("degree", "degree %")]))
    out.append("\n## File hotspots\n\nMost-changed files. `hotspot` = top quartile for both commits and size "
               "among all changed files (this script's cutoff).\n\n")
    out.append(table(report["hotspots"], [
        ("file", "file"), ("commits", "commits"), ("churn", "lines churned"), ("loc", "loc"),
        ("days_since_change", "days since change"), ("hotspot", "hotspot")]))
    out.append("\n## File change coupling\n\n")
    out.append(table(report["file_coupling"], [
        ("a", "file A"), ("b", "file B"), ("shared", "shared commits"), ("degree", "degree %")]))
    return "".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--repo", default=".", help="any path inside the repository (default: .)")
    p.add_argument("--path", default="", help="only analyse this subtree, relative to the repo root, e.g. src/billing")
    p.add_argument("--since", default="12 months ago", help='git date (committer date), e.g. "6 months ago"; "" for all history')
    p.add_argument("--until", default="", help='git date; with --since, measures a fixed window (e.g. before vs after a change)')
    p.add_argument("--depth", type=int, default=1, help="directory levels below --path that make a component (default 1)")
    p.add_argument("--first-parent", action="store_true", help="treat each merge on the main line as one changeset (PR-level coupling)")
    p.add_argument("--top", type=int, default=25, help="rows per table (default 25)")
    p.add_argument("--min-revs", type=int, default=5, help="pairs need this many commits on average (code-maat default 5)")
    p.add_argument("--min-shared", type=int, default=5, help="pairs need this many shared commits (code-maat default 5)")
    p.add_argument("--min-coupling", type=int, default=30, help="minimum coupling degree %% (code-maat default 30)")
    p.add_argument("--max-changeset", type=int, default=30, help="leave commits touching more files than this out of coupling (code-maat default 30)")
    p.add_argument("--exclude", action="append", default=[], help="extra glob to ignore; repeatable")
    p.add_argument("--no-default-excludes", action="store_true", help="keep lockfiles, vendored, built, and generated files")
    p.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    opts = p.parse_args(argv)
    opts.path = opts.path.replace("\\", "/").strip("/")

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
