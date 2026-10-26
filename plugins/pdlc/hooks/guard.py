#!/usr/bin/env python3
"""pdlc role guard. Claude Code runs this before every file tool call.

It keeps pdlc's agents in their lanes:
  - pdlc:test-writer reads only pdlc/ specs and checks, and writes only checks. It does
    not see app code or a review.
  - pdlc:builder never edits checks or pdlc/ files.
  - pdlc:reviewer reads only review packets and frames, and writes only its result.
  - pdlc:recon never writes.
It leaves everyone else alone, including the main session.

The project is the nearest folder holding pdlc/config.md. The guard looks for that folder
from the file first, then from the agent's working folder. So the lanes hold wherever the
agent started. A check is a file in a check folder ("check folders:" in pdlc/config.md) or
an acceptance file. An acceptance file matches "acceptance file:" in pdlc/config.md, or
its name holds "acceptance" and an intent ID (acceptance_IN_0001.py, IN-0001.acceptance.js).
Exit 2 blocks the call.
Set PDLC_GUARD_LOG to a file path to log every decision.
"""
import json
import os
import re
import sys

READS = {"Read", "Glob", "Grep"}
WRITES = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DEFAULT_CHECK_FOLDERS = ["test", "tests", "spec", "__tests__"]
# A file name that holds the word "acceptance" and an intent ID is an acceptance file, also
# when pdlc/config.md has no "acceptance file:" line.
ACCEPTANCE_NAME = re.compile(r"(?=.*acceptance)(?=.*(?<![a-z0-9])in[-_]?\d{4}(?!\d))", re.I)
# The folders of the reviews: one for each change, and one for the acceptance checks of each
# intent.
REVIEW = r"pdlc/(?:changes|acceptance)/[^/]+/review/"


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


def config(root):
    try:
        return open(os.path.join(root, "pdlc", "config.md")).read()
    except OSError:
        return None


def check_folders(root):
    text = config(root)
    if text is None:
        return DEFAULT_CHECK_FOLDERS
    line = re.search(r"^- check folders:\s*(.+)$", text, re.M)
    if not line:
        return DEFAULT_CHECK_FOLDERS
    value = line.group(1)
    quoted = re.findall(r"`([^`]+)`", value)
    # When the line has backticked folders, take only those. Then a trailing note such as
    # "(where checks live; ...)" doesn't become part of a folder name.
    items = quoted if quoted else re.sub(r"\s*\(.*$", "", value).split(",")
    return [f.strip(" `/") for f in items if f.strip(" `/")] or DEFAULT_CHECK_FOLDERS


def acceptance_file(root):
    """A regex for the path of an acceptance file, from "acceptance file:" in the config, or
    None. "{intent}" in the path stands for any intent ID."""
    line = re.search(r"^- acceptance file:\s*`([^`]+)`", config(root) or "", re.M)
    if not line or "{intent}" not in line.group(1):
        return None
    parts = line.group(1).strip("/ ").split("{intent}")
    return re.compile("^%s$" % r"IN[-_]?\d+".join(re.escape(part) for part in parts), re.I)


def is_check(path, root, checks, acceptance):
    """True when the path is a check: in a check folder, or an acceptance file."""
    name = rel(path, root)
    return (inside(path, root, *checks) or bool(acceptance and acceptance.match(name))
            or bool(ACCEPTANCE_NAME.match(os.path.basename(path))))


def targets(cwd, tool, args):
    """Every path this call could touch, made absolute."""
    base = args.get("file_path") or args.get("notebook_path") or args.get("path") or cwd
    paths = [os.path.realpath(os.path.join(cwd, os.path.expanduser(base)))]
    if tool == "Glob" and args.get("pattern"):
        paths.append(os.path.realpath(os.path.join(paths[0], args["pattern"])))
    return paths


def inside(path, root, *folders):
    for folder in folders:
        top = os.path.realpath(os.path.join(root, folder))
        if path == top or path.startswith(top + os.sep):
            return True
    return False


def rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def decide(call):
    """(allowed, reason) for one tool call."""
    agent = call.get("agent_type") or ""
    tool = call.get("tool_name") or ""
    cwd = call.get("cwd") or os.getcwd()
    args = call.get("tool_input") or {}
    if tool not in READS | WRITES or not agent.startswith("pdlc:"):
        return True, ""
    role = agent.split(":", 1)[1]
    home = project_root(cwd) or os.path.realpath(cwd)

    for path in targets(cwd, tool, args):
        root = project_root(path) or home
        name = rel(path, root)
        check = is_check(path, root, check_folders(root), acceptance_file(root))
        if role in ("test-writer", "reviewer") and name.startswith("../"):
            return False, "%s is outside the project (%s): use the absolute path inside it" % (path, root)
        in_review = re.match(REVIEW, name)
        if role == "test-writer":
            if tool in READS and not ((inside(path, root, "pdlc") and not in_review) or check):
                return False, "the test writer may not read %s: it writes checks from the spec, without seeing app code" % name
            if tool in WRITES and not check:
                return False, "the test writer may only write checks, not %s" % name
        elif role == "builder":
            if tool in WRITES and check:
                return False, "the builder may not change checks (%s); if a check looks wrong, stop and say why" % name
            if tool in WRITES and inside(path, root, "pdlc"):
                return False, "the builder may not change pdlc files (%s)" % name
        elif role == "reviewer":
            if tool in {"Glob", "Grep"}:
                return False, "a reviewer reads only its packet; it may not search the project"
            if tool == "Read" and not (re.match(REVIEW + r"[^/]+/packet\.md$", name)
                                       or re.match(r"pdlc/changes/[^/]+/frames/[^/]+$", name)):
                return False, "a reviewer reads only its own packet and the frames, not %s" % name
            if tool in WRITES and not re.match(REVIEW + r"[^/]+/result\.md$", name):
                return False, "a reviewer writes only its result.md, not %s" % name
        elif role == "recon":
            if tool in WRITES:
                return False, "recon is read-only"
    return True, ""


if __name__ == "__main__":
    call = json.load(sys.stdin)
    allowed, reason = decide(call)
    if os.environ.get("PDLC_GUARD_LOG"):
        # If the log can't be written, a block must still block.
        try:
            with open(os.environ["PDLC_GUARD_LOG"], "a") as log:
                log.write(json.dumps({"agent": call.get("agent_type"), "tool": call.get("tool_name"),
                                      "input": call.get("tool_input"), "allowed": allowed,
                                      "reason": reason}) + "\n")
        except OSError:
            pass
    if not allowed:
        print("pdlc guard: " + reason, file=sys.stderr)
        sys.exit(2)
