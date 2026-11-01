#!/usr/bin/env python3
"""pdlc version nudge. Claude Code runs this when the user sends a prompt.

When the prompt starts with a pdlc command (/pdlc:...), except /pdlc:upgrade and /pdlc:init,
and the pdlc files of the project are older than the plugin, this prints one line. Claude
Code adds the line to the context of the prompt. The files are older when pdlc/version.json
is missing, or when its "pdlc" value is lower than the version of the plugin.

The hook never blocks: it always exits 0, and it prints nothing outside a pdlc project (a
folder that holds pdlc/config.md), or when it cannot read its input.
"""
import json
import os
import re
import sys


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


def version_tuple(text):
    return tuple(int(n) for n in re.findall(r"\d+", str(text))[:3])


def plugin_version():
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, ".claude-plugin", "plugin.json")) as handle:
        return json.load(handle)["version"]


def message(prompt, cwd):
    """The line to print, or None."""
    command = re.match(r"\s*/pdlc:([a-z-]+)", prompt or "")
    if not command or command.group(1) in ("upgrade", "init"):
        return None
    root = project_root(cwd)
    if not root:
        return None
    current = plugin_version()
    try:
        with open(os.path.join(root, "pdlc", "version.json")) as handle:
            found = json.load(handle).get("pdlc")
    except (OSError, ValueError, AttributeError):
        found = None
    if found is not None and version_tuple(found) >= version_tuple(current):
        return None
    return ("The pdlc files of this project are from %s, and the plugin is %s. "
            "Run /pdlc:upgrade before this stage." % (found or "an older version", current))


def main():
    try:
        data = json.load(sys.stdin)
        line = message(data.get("prompt", ""), data.get("cwd") or os.getcwd())
    except Exception:  # the hook never blocks a prompt
        return 0
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
