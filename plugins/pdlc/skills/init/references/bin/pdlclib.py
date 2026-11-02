#!/usr/bin/env python3
"""Code that the pdlc scripts in this folder share.

A script imports this module with its own folder on the path:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pdlclib

The functions read the text of a spec (`section`, `field`), find the spec that owns a
branch (`owner`), and read the trailers of a commit message (`trailers`, `last_block`).
The hooks of the plugin keep their own copies, because a hook runs from the plugin and not
from a project.
"""
import glob
import os
import re
import subprocess

PDLC_TRAILERS = ("Intent", "Change", "Req", "Ticket")
TRAILER_LINE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):[ \t]*(\S.*?)\s*$")


def section(text, title, default=""):
    """The text under a '## title' heading, up to the next '## ' heading. `default` is the
    result when the heading is not there."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else default


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch. The value is
    bare: "IN-0001 (poll-input-errors)" gives "IN-0001", and "`pdlc/CH-0001-x`" gives
    "pdlc/CH-0001-x". The result is None when the field is not there."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    if not match:
        return None
    value = match.group(1).replace("`", "")
    return re.sub(r"\s+\(.*\)$", "", value).strip()


def git(root, *args):
    """git's output, stripped, or None when it fails."""
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                             timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def project_root(path):
    """The nearest folder at or above path that holds pdlc/config.md, or None."""
    path = os.path.realpath(str(path))
    while True:
        if os.path.isfile(os.path.join(path, "pdlc", "config.md")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def owner(root, branch):
    """("change", "CH-0031") or ("intent", "IN-0012") for the spec whose Branch is this one,
    or None."""
    root = str(root)
    places = [("change", os.path.join(root, "pdlc", "changes", "CH-*", "change.md")),
              ("intent", os.path.join(root, "pdlc", "inbox", "IN-*.md"))]
    for kind, pattern in places:
        for path in sorted(glob.glob(pattern)):
            try:
                text = open(path).read()
            except OSError:
                continue
            if field(text, "Branch") == branch:
                name = os.path.basename(os.path.dirname(path) if kind == "change" else path)
                return kind, "-".join(name.split("-", 2)[:2])
    return None


def trailers(body, keys=PDLC_TRAILERS):
    """{key: value} for each trailer line anywhere in a commit body, as the trace finds
    them. A later line wins. `keys` limits the result to those names; None allows any."""
    found = {}
    for line in (body or "").splitlines():
        match = TRAILER_LINE.match(line)
        if match and (keys is None or match.group(1) in keys):
            found[match.group(1)] = match.group(2)
    return found


def last_block(body):
    """[(key, value), ...] for the last paragraph of a commit body when every line of it is
    a trailer, as `git interpret-trailers --parse` reads it. [] when the last paragraph
    holds other text. A line that starts with a space or tab continues the line above."""
    paragraphs = [p for p in re.split(r"\n[ \t]*\n", (body or "").strip("\n")) if p.strip()]
    if not paragraphs:
        return []
    pairs = []
    for line in paragraphs[-1].splitlines():
        if line[:1] in (" ", "\t") and pairs:
            pairs[-1] = (pairs[-1][0], pairs[-1][1] + " " + line.strip())
            continue
        match = TRAILER_LINE.match(line)
        if not match:
            return []
        pairs.append((match.group(1), match.group(2)))
    return pairs
