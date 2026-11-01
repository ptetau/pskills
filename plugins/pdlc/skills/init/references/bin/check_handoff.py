#!/usr/bin/env python3
"""pdlc handoff check.

Reads the handoff of an intent ("## Handoff" in pdlc/inbox/IN-xxxx-*.md) or of a change
(pdlc/changes/CH-xxxx-*/handoff.md), and compares the working tree with HEAD. A stage runs
it before its commit. These rules hold:

  1. The title is "Handoff · <ID> · <stage> → <next>", and the pair is one that the handoff
     template permits for the stage. A leading "#" is accepted. A short description in
     brackets after the ID is accepted.
  2. "Time: <ISO 8601 time with offset>" is the next line.
  3. The six sections are present, in the order of the template.
  4. Each line of "Decided on defaults" is "- none" (then it is the only line), or
     "- <ID>: <question> → <answer> (assumed…)" with one arrow.
  5. The lines match the new "(assumed" marks in pdlc/specs/**. A mark is new when the sentence
     that holds it is not in the HEAD version of the file. The owner of a mark is the nearest
     "### <ID> ·" heading above it, or the spec ID under "## Interface" and in a design spec.
     Each owner has a line. Each line is the owner of a new mark. "- none" fails when a
     mark is new.
  6. Each line is also a line of "## Notes" in the intent (intent handoffs only). Each line of
     "## Notes" that holds "(assumed" and is not on HEAD is also a line of "Decided on
     defaults".

Usage:
  python3 pdlc/bin/check_handoff.py IN-0001 --stage intake
  python3 pdlc/bin/check_handoff.py CH-0001 --stage build

Run it from the project root. Exit code 0 prints nothing. Exit code 1 prints one line for
each problem.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

SECTIONS = ["Done", "Decided on defaults", "Open", "Look here", "Don't redo",
            "Next: do this first"]
# The titles that templates/handoff.md permits for each stage.
NEXT = {
    "intake": ["ready", "user"],
    "ready": ["change", "user"],
    "change": ["acceptance", "user"],
    "acceptance": ["tests", "build", "user"],
    "tests": ["build", "user"],
    "build": ["verify", "user"],
    "verify": ["show", "tests", "build", "acceptance", "user"],
    "show": ["user", "build"],
}
TIME = re.compile(r"^Time:\s*\d{4}-\d\d-\d\d[T ]\d\d:\d\d(:\d\d(\.\d+)?)?(Z|[+-]\d\d:?\d\d)\s*$")
TITLE = re.compile(r"^#{0,3}\s*Handoff · (\S+)(?: \([^()]*\))? · (\S+) → (\S+)\s*$")
HEADING = re.compile(r"^#{2,4}\s+(.*?)\s*$")
LINE = re.compile(r"^- ((?:JOB|CAP|DES)-[a-z0-9-]+(?:\.R\d+)?): (.+)$")
REQ_HEADING = re.compile(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+) ·")
MARK = "(assumed"


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else None


def spec_of(item):
    return item.split(".", 1)[0]


def head_text(root, path):
    """The text of a file on HEAD, or '' when HEAD does not have it."""
    try:
        done = subprocess.run(["git", "show", "HEAD:./" + path.as_posix()], cwd=root,
                              capture_output=True, text=True)
    except OSError:
        return ""
    return done.stdout if done.returncode == 0 else ""


def sentence_keys(line):
    """For each mark in a line: the text from the previous '. ' or the line start, up to and
    including the start of the mark. The text before the mark alone would also be in an
    unmarked sentence on HEAD."""
    keys = []
    for found in re.finditer(re.escape(MARK), line):
        start = line.rfind(". ", 0, found.start())
        keys.append(line[start + 2 if start >= 0 else 0:found.end()].strip())
    return keys


def new_marks(root):
    """The owners of the new marks in pdlc/specs/**: a dict of owner -> number of marks."""
    owners = {}
    for path in sorted((root / "pdlc" / "specs").rglob("*.md")):
        rel = path.relative_to(root)
        old = head_text(root, rel)
        design = path.parent.name == "design"
        owner_spec, in_interface, requirement = path.stem, False, None
        for line in path.read_text().splitlines():
            if line.startswith("## "):
                in_interface = line.strip() == "## Interface"
                requirement = None
            req = REQ_HEADING.match(line)
            if req:
                requirement = req.group(1)
            if MARK not in line:
                continue
            for key in sentence_keys(line):
                if key in old:
                    continue
                owner = owner_spec if (design or in_interface or not requirement) else requirement
                owners[owner] = owners.get(owner, 0) + 1
    return owners


def find_handoff(root, item):
    """(text of the handoff, path of the intent or None, or an error message)."""
    if item.startswith("CH-"):
        found = sorted((root / "pdlc" / "changes").glob(item + "-*/handoff.md"))
        if not found:
            return None, None, "%s: no handoff.md found in pdlc/changes/%s-*/" % (item, item)
        return found[0].read_text(), None, None
    found = sorted((root / "pdlc" / "inbox").glob(item + "-*.md")) + [root / "pdlc" / "inbox" / (item + ".md")]
    found = [path for path in found if path.exists()]
    if not found:
        return None, None, "%s: no intent file found in pdlc/inbox/" % item
    body = section(found[0].read_text(), "Handoff")
    if body is None:
        return None, found[0], "%s: the intent has no \"## Handoff\" section" % item
    return body, found[0], None


def check_head(item, stage, lines):
    """Rules 1 and 2. `lines` are the non-empty lines of the handoff."""
    problems = []
    title = TITLE.match(lines[0]) if lines else None
    if not title:
        problems.append("%s: the first line must be \"Handoff · %s · %s → <next>\"" % (item, item, stage))
    else:
        found_id, found_stage, found_next = title.groups()
        if found_id != item:
            problems.append("%s: the title names %s, not %s" % (item, found_id, item))
        if found_stage != stage or found_next not in NEXT[stage]:
            problems.append("%s: the title \"%s → %s\" is not one that stage %s permits (%s)" % (
                item, found_stage, found_next, stage,
                ", ".join("%s → %s" % (stage, n) for n in NEXT[stage])))
    if len(lines) < 2 or not TIME.match(lines[1]):
        problems.append("%s: the second line must be \"Time: <ISO 8601 time with offset>\"" % item)
    return problems


def check_sections(item, lines):
    """Rule 3. Returns (problems, the lines of 'Decided on defaults')."""
    heads = [(i, HEADING.match(line).group(1).replace("\u2019", "'"))
             for i, line in enumerate(lines) if HEADING.match(line)]
    names = [name for _, name in heads]
    if not any(name in names for name in SECTIONS):
        return ["%s: write the sections as `###` headings under `## Handoff`" % item], []
    problems = ["%s: the section \"%s\" is missing" % (item, name) for name in SECTIONS if name not in names]
    present = [name for name in names if name in SECTIONS]
    if not problems and present != SECTIONS:
        problems.append("%s: the sections are not in the order of the template (%s)" % (
            item, ", ".join(SECTIONS)))
    decided = []
    for n, (start, name) in enumerate(heads):
        if name == "Decided on defaults":
            end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
            decided = [line.strip() for line in lines[start + 1:end] if line.strip()]
            break
    return problems, decided


def line_id(line):
    found = LINE.match(line)
    return found.group(1) if found else None


def check_decided(item, decided, owners, notes, old_notes=frozenset()):
    """Rules 4 to 6."""
    problems, ids = [], []
    if decided == ["- none"]:
        pass
    elif "- none" in decided:
        problems.append("%s: \"- none\" must be the only line in Decided on defaults" % item)
    for line in decided:
        if line == "- none":
            continue
        found = LINE.match(line)
        after = line.split("→", 1)[1] if line.count("→") == 1 else ""
        if not found or line.count("→") != 1 or not re.search(r"\(assumed[^)]*\)", after):
            problems.append("%s: Decided on defaults, wrong form (need \"- <ID>: <question> → "
                            "<answer> (assumed)\"): %s" % (item, line))
            continue
        ids.append(found.group(1))
        if notes is not None and line not in notes:
            same = sorted(n for n in notes if line_id(n) == found.group(1))
            problems.append("%s: this line of Decided on defaults is not in the Notes of the "
                            "intent: %s%s" % (item, line, (" (Notes line with this ID: %s)" % same[0]) if same else ""))
    if notes is not None:
        for note in sorted(notes):
            answer = note.rsplit("→", 1)[1] if "→" in note else ""
            if MARK in answer and note not in old_notes and note not in decided:
                problems.append("%s: this (assumed) line of the Notes is not in Decided on "
                                "defaults: %s" % (item, note))
    for owner in sorted(owners):
        covered = any(i == owner or (spec_of(owner) == owner and spec_of(i) == owner) for i in ids)
        if not covered:
            what = "a new (assumed) mark" if owners[owner] == 1 else "%d new (assumed) marks" % owners[owner]
            problems.append("%s: %s has %s in the specs, and no line in Decided on defaults" % (
                item, owner, what))
    for i in ids:
        if not any(owner == i or owner == spec_of(i) for owner in owners):
            problems.append("%s: the line for %s has no new (assumed) mark in the specs" % (item, i))
    return problems


def main(argv, root=Path(".")):
    parser = argparse.ArgumentParser(prog="check_handoff.py")
    parser.add_argument("item", help="IN-xxxx or CH-xxxx")
    parser.add_argument("--stage", required=True, choices=sorted(NEXT))
    args = parser.parse_args(argv[1:])
    item = args.item
    body, intent_path, error = find_handoff(root, item)
    if error:
        print(error)
        return 1
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    problems = check_head(item, args.stage, lines)
    section_problems, decided = check_sections(item, lines)
    notes, old_notes = None, set()
    if intent_path is not None:
        old_notes = {line.strip() for line in
                     (section(head_text(root, intent_path.relative_to(root)), "Notes") or "").splitlines()
                     if line.strip()}
        notes = {line.strip() for line in
                 (section(intent_path.read_text(), "Notes") or "").splitlines() if line.strip()}
    problems += section_problems + check_decided(item, decided, new_marks(root), notes, old_notes)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
