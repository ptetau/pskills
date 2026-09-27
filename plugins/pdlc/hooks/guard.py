#!/usr/bin/env python3
"""pdlc role guard. Claude Code runs this before every file tool call.

It keeps pdlc's agents in their lanes:
  - pdlc:test-writer reads only pdlc/ specs and check folders, and writes only checks.
    It never sees app code.
  - pdlc:builder never edits checks or pdlc/ files.
  - pdlc:reviewer reads only review packets and frames, and writes only its result.
  - pdlc:recon never writes.
Everyone else, including the main session, is left alone.

Check folders come from "check folders:" in pdlc/config.md. Exit 2 blocks the call.
"""
import json
import os
import re
import sys

READS = {"Read", "Glob", "Grep"}
WRITES = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DEFAULT_CHECK_FOLDERS = ["test", "tests", "spec", "__tests__"]


def check_folders(cwd):
    try:
        text = open(os.path.join(cwd, "pdlc", "config.md")).read()
    except OSError:
        return DEFAULT_CHECK_FOLDERS
    line = re.search(r"^- check folders:\s*(.+)$", text, re.M)
    if not line:
        return DEFAULT_CHECK_FOLDERS
    return [f.strip(" `/") for f in line.group(1).split(",") if f.strip(" `/")]


def targets(cwd, tool, args):
    """Every path this call could touch, made absolute."""
    base = args.get("file_path") or args.get("notebook_path") or args.get("path") or cwd
    paths = [os.path.realpath(os.path.join(cwd, os.path.expanduser(base)))]
    if tool == "Glob" and args.get("pattern"):
        paths.append(os.path.realpath(os.path.join(paths[0], args["pattern"])))
    return paths


def inside(path, cwd, *folders):
    for folder in folders:
        root = os.path.realpath(os.path.join(cwd, folder))
        if path == root or path.startswith(root + os.sep):
            return True
    return False


def rel(path, cwd):
    return os.path.relpath(path, os.path.realpath(cwd)).replace(os.sep, "/")


def decide(call):
    """(allowed, reason) for one tool call."""
    agent = call.get("agent_type") or ""
    tool = call.get("tool_name") or ""
    cwd = call.get("cwd") or os.getcwd()
    args = call.get("tool_input") or {}
    if tool not in READS | WRITES or not agent.startswith("pdlc:"):
        return True, ""
    role = agent.split(":", 1)[1]
    checks = check_folders(cwd)

    for path in targets(cwd, tool, args):
        name = rel(path, cwd)
        in_review = re.match(r"pdlc/changes/[^/]+/review/", name)
        if role == "test-writer":
            if tool in READS and not ((inside(path, cwd, "pdlc") and not in_review)
                                      or inside(path, cwd, *checks)):
                return False, "the test writer may not read %s: it writes checks from the spec, without seeing app code" % name
            if tool in WRITES and not inside(path, cwd, *checks):
                return False, "the test writer may only write checks, not %s" % name
        elif role == "builder":
            if tool in WRITES and inside(path, cwd, *checks):
                return False, "the builder may not change checks (%s); if a check looks wrong, stop and say why" % name
            if tool in WRITES and inside(path, cwd, "pdlc"):
                return False, "the builder may not change pdlc files (%s)" % name
        elif role == "reviewer":
            if tool in {"Glob", "Grep"}:
                return False, "a reviewer reads only its packet; it may not search the project"
            if tool == "Read" and not re.match(r"pdlc/changes/[^/]+/(review/[^/]+/packet\.md|frames/[^/]+)$", name):
                return False, "a reviewer reads only its own packet and the frames, not %s" % name
            if tool in WRITES and not re.match(r"pdlc/changes/[^/]+/review/[^/]+/result\.md$", name):
                return False, "a reviewer writes only its result.md, not %s" % name
        elif role == "recon":
            if tool in WRITES:
                return False, "recon is read-only"
    return True, ""


if __name__ == "__main__":
    allowed, reason = decide(json.load(sys.stdin))
    if not allowed:
        print("pdlc guard: " + reason, file=sys.stderr)
        sys.exit(2)
