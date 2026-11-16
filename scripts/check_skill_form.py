#!/usr/bin/env python3
"""Check a SKILL.md against the declarative form and its word budget.

Usage: check_skill_form.py [--budgets PATH] [SKILL.md ...]

With no file, the script checks plugins/pdlc/skills/<name>/SKILL.md for each name in the
"enforced" list of the budgets file. An empty list gives exit 0.

Exit 0: no problems. Exit 1: problems (one line each). Exit 2: usage error.
The budget of a skill is the entry for the name of its folder in the budgets file
(default: skill_budgets.json next to this script), plus the words of its "earned" entries.
A skill with no entry only gets the form check. A bad "earned" object gives exit 2.
"""

import json
import os
import re
import sys

SECTIONS = ["Goal", "Inputs", "Outputs", "Constraints", "Stages", "Done when"]
REQUIRED = ["Goal", "Inputs", "Outputs", "Constraints", "Done when"]
STAGE_LABELS = ["Goal", "Inputs", "Outputs", "Done when", "Constraints"]
STAGE_REQUIRED = ["Goal", "Inputs", "Outputs", "Done when"]
MAX_CONSTRAINTS = 8
MAX_STAGE_LINES = 6
DEFAULT_BUDGETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill_budgets.json")
USAGE = "usage: check_skill_form.py [--budgets PATH] [SKILL.md ...]"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FENCE = re.compile(r"^\s*(```|~~~)")

ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s+")
LABEL = re.compile(r"^[-*+]\s+(Goal|Inputs|Outputs|Done when|Constraints):")


def split_front_matter(text):
    """Return (front_matter_or_None, body)."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return None, text


def fenced_lines(lines):
    """Return the set of line indexes inside a code fence, with the fence lines."""
    out, marker = set(), None
    for i, line in enumerate(lines):
        m = FENCE.match(line)
        if m:
            out.add(i)
            if marker is None:
                marker = m.group(1)
            elif m.group(1) == marker:
                marker = None
        elif marker is not None:
            out.add(i)
    return out


def headings(body):
    """Return ([(level, title, line_index)], lines, fenced). Fenced lines hold no heading."""
    lines = body.split("\n")
    fenced = fenced_lines(lines)
    found = []
    for i, line in enumerate(lines):
        if i in fenced:
            continue
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if m:
            found.append((len(m.group(1)), m.group(2), i))
    return found, lines, fenced


def logical_lines(block_lines):
    """Count logical lines: a list item or a paragraph, with wrapped lines joined."""
    count, prev_open = 0, False
    for line in block_lines:
        if not line.strip():
            prev_open = False
            continue
        if ITEM.match(line) or not prev_open:
            count += 1
        prev_open = True
    return count


def unfenced(lines, fenced, start, end):
    return [lines[i] for i in range(start, end) if i not in fenced]


def check_stage(title, blk):  # blk: the lines of the stage, fenced lines removed
    labels = [m.group(1) for m in (LABEL.match(line) for line in blk) if m]
    if not labels:
        return [f'stage "{title}": no labels (use Goal, Inputs, Outputs, Done when)']
    problems = []
    for need in STAGE_REQUIRED:
        if need not in labels:
            problems.append(f'stage "{title}": missing label "{need}"')
    ordered = [x for x in STAGE_LABELS if x in labels]
    if labels != ordered:
        problems.append(f'stage "{title}": labels out of order or repeated (order: ' + ", ".join(STAGE_LABELS) + ")")
    n = logical_lines(blk)
    if n > MAX_STAGE_LINES:
        problems.append(f'stage "{title}": {n} lines, at most {MAX_STAGE_LINES}')
    return problems


def effective_budget(budgets, skill):
    """Return (budget, earned words): the base budget plus the earned words of the skill."""
    entries = budgets.get("earned", {}).get(skill, [])
    earned = sum(e["words"] for e in entries)
    return budgets[skill] + earned, earned


def validate_budgets(budgets):
    """Return a list of problems in the "earned" object of the budgets file."""
    earned = budgets.get("earned", {})
    if not isinstance(earned, dict):
        return ['"earned" must be an object']
    problems = []
    for skill, entries in earned.items():
        if skill not in budgets or skill in ("enforced", "earned"):
            problems.append(f'earned: "{skill}" has no budget entry')
        if not isinstance(entries, list):
            problems.append(f'earned "{skill}": must be a list')
            continue
        for n, e in enumerate(entries, 1):
            where = f'earned "{skill}" #{n}'
            if not isinstance(e, dict):
                problems.append(f"{where}: must be an object")
                continue
            for key in ("rule", "evidence"):
                v = e.get(key)
                if not isinstance(v, str) or not v.strip():
                    problems.append(f'{where}: "{key}" must be non-empty text')
            w = e.get("words")
            if isinstance(w, bool) or not isinstance(w, int) or w <= 0:
                problems.append(f'{where}: "words" must be an integer above 0')
    return problems


def check(path, text, budgets):
    problems = []
    fm, body = split_front_matter(text)
    if fm is None:
        problems.append("no front matter")
    heads, lines, fenced = headings(body)
    h1 = [h for h in heads if h[0] == 1]
    if len(h1) != 1:
        problems.append(f"expected one # title, found {len(h1)}")
    elif heads[0] is not h1[0]:
        problems.append("the # title must come first")
    names = [h[1] for h in heads if h[0] == 2]
    for name in names:
        if name not in SECTIONS:
            problems.append(f'unknown section "## {name}" (allowed: ' + ", ".join(SECTIONS) + ")")
    for need in REQUIRED:
        if need not in names:
            problems.append(f'missing section "## {need}"')
    if len(set(names)) != len(names):
        problems.append("a section repeats")
    known = [n for n in names if n in SECTIONS]
    if known != [s for s in SECTIONS if s in known]:
        problems.append("sections out of order (order: " + ", ".join(SECTIONS) + ")")

    def section_range(name):
        for idx, h in enumerate(heads):
            if h[0] == 2 and h[1] == name:
                end = len(lines)
                for nxt in heads[idx + 1:]:
                    if nxt[0] <= 2:
                        end = nxt[2]
                        break
                return h[2], end
        return None

    r = section_range("Constraints")
    if r:
        n = sum(1 for line in unfenced(lines, fenced, r[0] + 1, r[1]) if ITEM.match(line))
        if n > MAX_CONSTRAINTS:
            problems.append(f"Constraints has {n} items, at most {MAX_CONSTRAINTS}")

    r = section_range("Stages")
    if r:
        stages = [h for h in heads if h[0] == 3 and r[0] < h[2] < r[1]]
        if not stages:
            problems.append('"## Stages" has no "###" stage')
        for idx, st in enumerate(stages):
            end = stages[idx + 1][2] if idx + 1 < len(stages) else r[1]
            problems.extend(check_stage(st[1], unfenced(lines, fenced, st[2] + 1, end)))

    sr = section_range("Stages")
    for h in heads:
        if h[0] == 3 and not (sr and sr[0] < h[2] < sr[1]):
            problems.append(f'"### {h[1]}" is outside "## Stages"')

    skill = os.path.basename(os.path.dirname(os.path.abspath(path)))
    if skill in budgets:
        words = len(body.split())
        total, earned = effective_budget(budgets, skill)
        if words > total:
            problems.append(f"body has {words} words, budget {total} ({budgets[skill]} + earned {earned})")
    return problems


def run_enforced(budgets, root=ROOT):
    """Check each enforced skill. Return 0 or 1."""
    bad = False
    for name in budgets.get("enforced", []):
        path = os.path.join(root, "plugins", "pdlc", "skills", name, "SKILL.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for p in check(path, text, budgets):
            bad = True
            print(f"{path}: {p}")
    return 1 if bad else 0


def main(argv):
    budgets_path, files, i = DEFAULT_BUDGETS, [], 0
    while i < len(argv):
        if argv[i] == "--budgets":
            if i + 1 >= len(argv):
                print(USAGE, file=sys.stderr)
                return 2
            budgets_path = argv[i + 1]
            i += 2
        elif argv[i].startswith("-"):
            print(USAGE, file=sys.stderr)
            return 2
        else:
            files.append(argv[i])
            i += 1
    try:
        with open(budgets_path, encoding="utf-8") as f:
            budgets = json.load(f)
    except (OSError, ValueError) as e:
        print(f"cannot read budgets {budgets_path}: {e}", file=sys.stderr)
        return 2
    bad_file = validate_budgets(budgets)
    if bad_file:
        for p in bad_file:
            print(f"bad budgets file {budgets_path}: {p}", file=sys.stderr)
        return 2
    if not files:
        try:
            return run_enforced(budgets)
        except OSError as e:
            print(f"cannot read an enforced skill: {e}", file=sys.stderr)
            return 2
    bad = False
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"cannot read {path}: {e}", file=sys.stderr)
            return 2
        for p in check(path, text, budgets):
            bad = True
            print(f"{path}: {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
