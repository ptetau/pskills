#!/usr/bin/env python3
"""Keeps dashboard-builder inside .dashboard/ and its own memory folder.

Claude Code runs this before each Read, Write, Edit or Glob the agent makes. It gets the
tool call as JSON on stdin. Exit 0 allows the call; exit 2 blocks it and tells the agent why.
"""
import json
import os
import sys


def allowed(call):
    cwd = call.get("cwd") or os.getcwd()
    args = call.get("tool_input") or {}
    target = args.get("file_path") or args.get("path") or cwd
    roots = [
        os.path.realpath(os.path.join(cwd, ".dashboard")),
        os.path.realpath(os.path.expanduser("~/.claude/agent-memory/dashboard-builder")),
    ]
    paths = [os.path.realpath(os.path.join(cwd, os.path.expanduser(target)))]
    if args.get("pattern"):
        # A Glob pattern can climb out with ".." or start from "/", so check where it
        # points too.
        paths.append(os.path.realpath(os.path.join(paths[0], os.path.expanduser(args["pattern"]))))
    inside = lambda p: any(p == root or p.startswith(root + os.sep) for root in roots)
    bad = [p for p in paths if not inside(p)]
    return (bad[0] if bad else paths[0]), not bad


if __name__ == "__main__":
    path, ok = allowed(json.load(sys.stdin))
    if not ok:
        print("dashboard-builder may only use .dashboard/ and its memory folder, not %s"
              % path, file=sys.stderr)
        sys.exit(2)
