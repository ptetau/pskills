#!/usr/bin/env python3
"""Fingerprint a skill and the /vet workflow script, so that two /vet results can be compared.

Usage:
  python3 fingerprint.py SKILL_FILE [--workflow FILE]

Prints one JSON object:
  skillSha256      sha256 of the SKILL.md file.
  skillTreeSha256  sha256 of the sorted list of (relative path, sha256 of content) of each
                   file in the tree of the skill.
  skillTree        the root of that tree, relative to the git repo when possible.
  workflowSha256   sha256 of the workflow script (only with --workflow).

The tree is the skill folder. When the skill is in a plugin
(<plugin>/skills/<name>/SKILL.md, and <plugin>/.claude-plugin exists), the tree is the
whole plugin folder. The tree leaves out these folders: __pycache__, .git, .claude, evals,
.vet-tmp, .vet-capture, and node_modules. It also leaves out *.pyc files, .git files, and
.DS_Store files. Thus, the output of /vet runs does not change the hash.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

SKIP_DIRS = {"__pycache__", ".git", ".claude", "evals", ".vet-tmp", ".vet-capture", "node_modules"}
SKIP_FILES = {".git", ".DS_Store"}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_root(skill_file):
    """Return the root folder of the tree for a SKILL.md file."""
    skill_dir = os.path.dirname(os.path.realpath(skill_file))
    skills_dir = os.path.dirname(skill_dir)
    plugin_dir = os.path.dirname(skills_dir)
    if (os.path.basename(skills_dir) == "skills"
            and os.path.isdir(os.path.join(plugin_dir, ".claude-plugin"))):
        return plugin_dir
    return skill_dir


def tree_entries(root):
    """Return the sorted list of (relative path, sha256) for each file under root."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in filenames:
            if name.endswith(".pyc") or name in SKIP_FILES:
                continue
            full = os.path.join(dirpath, name)
            if not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            entries.append((rel, sha256_file(full)))
    entries.sort()
    return entries


def tree_sha256(entries):
    h = hashlib.sha256()
    for rel, digest in entries:
        h.update(("%s\t%s\n" % (rel, digest)).encode("utf-8"))
    return h.hexdigest()


def repo_relative(path):
    """Return path relative to the git repo root, or the absolute path if it is not in a repo."""
    try:
        top = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return path
    rel = os.path.relpath(path, os.path.realpath(top))
    return path if rel.startswith("..") else rel


def fingerprint(skill_file, workflow=None):
    root = tree_root(skill_file)
    out = {
        "skillSha256": sha256_file(skill_file),
        "skillTreeSha256": tree_sha256(tree_entries(root)),
        "skillTree": repo_relative(root),
    }
    if workflow:
        out["workflowSha256"] = sha256_file(workflow)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("skill_file", help="path of the SKILL.md file")
    p.add_argument("--workflow", help="path of the workflow script that runs")
    opts = p.parse_args(argv)
    for path in (opts.skill_file, opts.workflow):
        if path and not os.path.isfile(path):
            sys.exit("fingerprint.py: not a file: %s" % path)
    json.dump(fingerprint(opts.skill_file, opts.workflow), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
