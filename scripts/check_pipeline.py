#!/usr/bin/env python3
"""Check that the pdlc skills, agents, README, and adapters name only items that the
contract defines: commit kinds, subcommands and options, handoff pairs, statuses, and
header fields. Also check that each status or subject that a script needs has a producer.

Usage: check_pipeline.py [--plugin DIR]   (default: plugins/pdlc)
Exit 0 prints nothing. Exit 1 prints "<file>:<line> · <rule> · <problem>" for each problem.
The rules: 1 kinds, 2 subcommands and options, 3 handoff pairs, 4 statuses, 5 producers,
6 header fields. The check reads files only. It does not check the order of steps or prose.
"""
import argparse
import importlib.util
import re
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
BIN = Path("skills/init/references/bin")
TEMPLATES = Path("skills/init/references/templates")

# What a script needs, with the file that needs it: (kind of item, value, consumer).
CONSUMED = [
    ("Intent", "in review", "hooks/shiplog.py"),
    ("Intent", "specifying", "skills/ready"),
    ("Change", "in review", "bin/check_merge.py"),
    ("Change", "building", "skills/build"),
    ("Subject", "Stop ", "hooks/shiplog.py"),
    ("Subject", "Propose ", "hooks/shiplog.py"),
]
# What a script sets by itself: (kind of item, value, producer).
SCRIPT_PRODUCERS = [
    ("Change", "testing", "pdlc.py start"),
    ("Change", "merged", "record_merges.py"),
    ("Intent", "done", "record_merges.py"),
    ("Intent", "new", "pdlc.py intent new"),
    ("Subject", "Record merges", "record_merges.py"),
]
NOT_FIELDS = {"reqs", "req", "unpropose"}
SAMPLE = {"id": "CH-0001", "name": "x", "names": "x", "text": "x", "n": "1", "base": "main"}


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module


def spans(line):
    """The code spans of a line (the text between backticks), else the whole line."""
    found = re.findall(r"`([^`]+)`", line)
    return found if "pdlc.py" not in line or found else [line]


def samples(kind_id, subject):
    ids = {"IN": ["IN-0001"], "CH": ["CH-0001"], "DES": ["DES-x"], "IN|CH": ["IN-0001", "CH-0001"],
           None: ["x"]}[kind_id]
    return [re.sub(r"\{(\w+)\}", lambda m: i if m.group(1) == "id" else SAMPLE[m.group(1)], subject)
            for i in ids]


def check(plugin):
    bin_dir = plugin / BIN
    pdlc, handoff = load(bin_dir / "pdlc.py"), load(bin_dir / "check_handoff.py")
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "pdlc").mkdir()
        (root / pdlc.DES_TRAILERS).parent.mkdir(parents=True)
        readme = plugin / TEMPLATES / "README.md"
        (root / "pdlc" / "README.md").write_text(readme.read_text())
        (root / pdlc.DES_TRAILERS).write_text(
            (plugin / "skills/init/references/defaults/DES-pdlc-commit-trailers.md").read_text())
        statuses, shapes = pdlc.statuses(root), pdlc.subject_shapes(root)
    parsers = build_options(pdlc)
    texts = sorted(plugin.glob("skills/*/SKILL.md")) + sorted(plugin.glob("agents/*.md")) + [readme] \
        + sorted(plugin.glob("skills/init/references/adapters/*.md"))
    pairs = {(a, b) for a, nxt in handoff.NEXT.items() for b in nxt}
    named, produced = set(), set(SCRIPT_PRODUCERS_SET())
    if pdlc.DEFAULT_STATUSES != statuses:
        problems.append("%s:1 · 4 · DEFAULT_STATUSES differs from \"Statuses\" in the README" % readme)
    for key in pdlc.REQUIRED:
        if key not in pairs:
            problems.append("%s:1 · 3 · REQUIRED names %s → %s, which NEXT does not permit" % ((BIN / "pdlc.py",) + key))
    # Rule 1: the subjects of the kinds and the subjects of the design spec.
    made = [s for kind_id, subject in pdlc.KINDS.values() for s in samples(kind_id, subject)]
    for sample in made:
        if not any(regex.match(sample) for _, regex in shapes):
            problems.append("%s:1 · 1 · the subject \"%s\" is in no shape of \"Subjects\"" % (BIN / "pdlc.py", sample))
    for shape, regex in shapes:
        if shape.startswith("pdlc.py"):
            continue  # a command that the line names, not a subject
        if not any(regex.match(s) for s in made) and not any(shape.startswith(v) for k, v, _ in SCRIPT_PRODUCERS if k == "Subject"):
            problems.append("%s:1 · 1 · the shape \"%s\" has no kind" % (BIN / "pdlc.py", shape))
    made_prefix = {s.split(" ")[0] + " " for s in made}
    for path in texts:
        for number, line in enumerate(path.read_text().splitlines(), 1):
            where = "%s:%d" % (path.relative_to(plugin), number)
            for span in spans(line):
                for call in re.finditer(r"pdlc\.py (?!--)([a-z]+)\b([^\n]*?)(?=pdlc\.py|$)", span):
                    sub, rest = call.group(1), call.group(2)
                    if sub not in pdlc.SUBCOMMANDS:
                        problems.append("%s · 2 · pdlc.py has no subcommand \"%s\"" % (where, sub))
                        continue
                    words = rest.split()
                    if sub in ("commit", "message") and words and re.fullmatch(r"[a-z]+(?:-[a-z]+)*", words[0]) \
                            and words[0] not in pdlc.KINDS:
                        problems.append("%s · 1 · \"%s\" is not a commit kind" % (where, words[0]))
                    flags = re.findall(r"(?<![\w-])(--[a-z][a-z-]*)", rest)
                    for flag in flags:
                        if flag not in parsers[sub][0]:
                            problems.append("%s · 2 · pdlc.py %s has no option %s" % (where, sub, flag))
                    if re.search(r"\b(?:IN|CH)-(?:x+|\d+)\b|<ID>", rest):
                        for flag in sorted(parsers[sub][1] - {"--json"}):
                            if flag not in flags:
                                problems.append("%s · 2 · pdlc.py %s with an ID lacks %s" % (where, sub, flag))
                    if sub == "handoff" and len(words) >= 3 and words[1] in handoff.NEXT:
                        named.add((words[1], words[2]))
                    if sub in ("set", "intent"):
                        kind = "Intent" if re.search(r"\bIN-", rest) else "Change" if re.search(r"\bCH-", rest) else None
                        status = re.search(r'--status\s+("[^"]+"|\S+)', rest)
                        if status and kind:
                            value = status.group(1).strip('"`,;.')
                            produced.add((kind, value))
                            if value not in statuses[kind]:
                                problems.append("%s · 4 · \"%s\" is not a %s status" % (where, value, kind))
                        if sub == "set":
                            for value in re.findall(r"--reqs\s+(\w+)|--req\s+\S+=(\w+)", rest):
                                value = value[0] or value[1]
                                if value not in statuses["Requirement"]:
                                    problems.append("%s · 4 · \"%s\" is not a Requirement status" % (where, value))
                            for flag in flags:
                                if flag[2:] not in NOT_FIELDS and flag[2:] not in ("status",) and not header_has(plugin, flag):
                                    problems.append("%s · 6 · %s sets a field that no template header holds" % (where, flag))
            for a, b in re.findall(r"`(\w+)(?: → | )(\w+)`", line):
                if a in handoff.NEXT and (b in handoff.NEXT or b == "user"):
                    named.add((a, b))
                    if b not in handoff.NEXT[a]:
                        problems.append("%s · 3 · the handoff %s → %s is not permitted by NEXT" % (where, a, b))
            for a, b in re.findall(r"pdlc\.py handoff \S+ (\w+) (\w+)", line):
                if a in handoff.NEXT and b not in handoff.NEXT[a]:
                    problems.append("%s · 3 · the handoff %s → %s is not permitted by NEXT" % (where, a, b))
    for a, b in sorted(pairs - named):
        if b != "user":
            problems.append("%s:1 · 3 · no skill names the handoff %s → %s" % (BIN / "check_handoff.py", a, b))
    for kind, value, consumer in CONSUMED:
        if kind == "Subject":
            if value not in made_prefix and not any(value.startswith(v) for k, v, _ in SCRIPT_PRODUCERS if k == kind):
                problems.append("%s · 5 · no kind makes the subject \"%s\"" % (consumer, value))
        elif (kind, value) not in produced:
            problems.append("%s · 5 · no skill or script sets the %s status \"%s\"" % (consumer, kind, value))
    return problems


def SCRIPT_PRODUCERS_SET():
    return {(k, v) for k, v, _ in SCRIPT_PRODUCERS}


def build_options(pdlc):
    """{subcommand: (all option strings, required option strings)}."""
    sub = pdlc.build_parser()._subparsers._group_actions[0].choices
    return {name: (set(p._option_string_actions), {o for a in p._actions if a.required and a.option_strings
                                                   for o in a.option_strings[:1]})
            for name, p in sub.items()}


def header_has(plugin, flag):
    field = "-".join(w.capitalize() for w in flag[2:].split("-"))
    return any(re.search(r"\b%s:" % field, (plugin / TEMPLATES / n).read_text()) for n in ("intent.md", "change.md"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--plugin", default=str(Path(__file__).resolve().parent.parent / "plugins/pdlc"))
    plugin = Path(parser.parse_args(argv).plugin).resolve()
    problems = [p.replace(str(plugin) + "/", "") for p in check(plugin)]
    if problems:
        print("\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
