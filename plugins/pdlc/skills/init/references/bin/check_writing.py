#!/usr/bin/env python3
"""pdlc writing check. Finds breaks of the writing rules that a script can find well.

Usage:
  python3 pdlc/bin/check_writing.py [paths...]
  python3 pdlc/bin/check_writing.py --since <branch> [paths...]

A path is a file or a folder. For a folder, it checks every .md file in the folder. With
no paths, it checks the .md files changed on this branch (git diff --name-only
main...HEAD). If there is no main, it checks every .md file under the current folder.
With --since, it reports only the lines committed since that branch.

It checks four rules of DES-writing-style (the writing rules):
  - sentence length: a sentence of more than 25 words, or an instruction of
    more than 20. An instruction starts with a command verb, such as "Run" or "Use".
  - NZ spelling: common US forms, such as "organize", "color", "center" and
    "gray". It gives the NZ form to write.
  - ID alone: a pdlc ID (IN-0001, CAP-email, CAP-email.R3) or a bare
    requirement number (R3) with no name next to it. A name is next to it when the
    sentence goes on with "(", " · ", ":", a dash and words, or a quoted name. A name
    is also next to it when the ID is in brackets after the name.
  - conversation: phrases that tell how the text came about, such as "as you
    asked", "I've" or "last round". "Here is" counts only at the start of a sentence.

It doesn't read fenced code blocks, inline code, URLs, HTML comments, or front matter
other than "description". Quoted text counts toward a sentence's length, but no other
rule reads it. These may hold an ID alone: a heading, a table row, a field line ("Req:",
"Intent:", "Status:"), a list of IDs and a placeholder (IN-xxxx). A line that ends with
<!-- writing: ok --> is a deliberate exception: the check reports nothing on it.

Reviewers judge what a script can't judge well: clear references to nouns, concrete
examples, being concise, the active voice, and the other sentence rules.

Output: one line per finding, "<file>:<line> · <rule> · <what is wrong> · <suggestion>",
then the count. Exit code 1 means it found something.
"""
import re
import subprocess
import sys
from pathlib import Path

MARKER = "<!-- writing: ok -->"
SENTENCE_LIMIT = 25
INSTRUCTION_LIMIT = 20
COMMANDS = {"run", "use", "write", "read", "set", "add", "check", "give", "keep", "make",
            "put", "start", "stop", "tell", "take", "list", "commit", "ask", "copy",
            "create", "delete", "don't", "fix", "follow", "never", "pick", "remove",
            "replace", "skip", "switch", "wait"}
RULES = ["sentence length", "NZ spelling", "ID alone", "conversation"]

# US forms and the NZ form to write. The check matches each as a whole word, in any case.
SPELLING = {
    "center": "centre", "centers": "centres", "centered": "centred", "centering": "centring",
    "theater": "theatre", "theaters": "theatres", "fiber": "fibre", "fibers": "fibres",
    "liter": "litre", "liters": "litres", "kilometer": "kilometre", "kilometers": "kilometres",
    "centimeter": "centimetre", "centimeters": "centimetres",
    "millimeter": "millimetre", "millimeters": "millimetres",
    "catalog": "catalogue", "catalogs": "catalogues", "cataloged": "catalogued",
    "cataloging": "cataloguing", "defense": "defence", "defenses": "defences",
    "offense": "offence", "offenses": "offences", "gray": "grey", "grays": "greys",
    "grayed": "greyed", "grayish": "greyish", "grayscale": "greyscale",
    "traveled": "travelled", "traveling": "travelling", "traveler": "traveller",
    "travelers": "travellers", "canceled": "cancelled", "canceling": "cancelling",
    "labeled": "labelled", "labeling": "labelling", "modeled": "modelled",
    "modeling": "modelling", "signaled": "signalled", "signaling": "signalling",
    "leveled": "levelled", "leveling": "levelling", "fulfill": "fulfil",
    "fulfills": "fulfils", "fulfillment": "fulfilment", "enroll": "enrol", "enrolls": "enrols",
    "enrollment": "enrolment", "enrollments": "enrolments", "skillful": "skilful",
    "willful": "wilful", "aluminum": "aluminium",
}
# "-or" words write "-our" in NZ, with every ending below ("color", "colors", "colorful").
for us in ["color", "behavior", "favor", "honor", "labor", "neighbor", "flavor", "humor",
           "rumor"]:
    for ending in ["", "s", "ed", "ing", "ful", "less", "al", "ally", "able", "ably", "ite",
                   "ites", "hood", "hoods", "er", "ers"]:
        SPELLING[us + ending] = us[:-2] + "our" + ending

# "-ize", "-ization" and "-yze" forms. NZ writes "-ise", "-isation" and "-yse", except in
# the words in IZE_KEEP, which are spelt with "z" in NZ too ("size", "resize", "seize").
# The list holds whole words, so "synthesize" and "emphasize" are still found.
IZE = re.compile(r"([a-z]+?)(iz|yz)(e|es|ed|ing|er|ers|ation|ations|ational|able)", re.I)
IZE_KEEP = {"size", "resize", "downsize", "upsize", "oversize", "undersize", "outsize",
            "capsize", "seize", "prize", "maize", "baize", "assize", "belize"}

ID = re.compile(r"\b(?:(?:IN|CH)-\d{4}\b|(?:JOB|CAP|DES)-[a-z0-9]+(?:-[a-z0-9]+)*(?:\.R\d+)?"
                r"|R\d+\b)")
PLACEHOLDER = re.compile(r"-(?:0+|x+|name)(?:\.R\d+)?$")
# What, later in the sentence, shows a name next to the ID.
NAMED = re.compile(r"\(|\s·\s|:|^[-–—]\w|\s[-–—]{1,2}\s*\w|—\w")
FIELD = re.compile(r"(?:[-*+]\s+)?(?:Req|Intent|Intents|Change|Changes|Status|Scope|Base|"
                   r"Branch|Ticket|Review|Tests-Locked|Source):")

CONVERSATION = re.compile(
    r"\b(?:as you asked|as requested|as discussed|per your request|the user asked|"
    r"you asked|I['’]ve|I have|we discussed|let me|note to self|in this round|last round)\b",
    re.I)
# These are conversation only at the start of a sentence: "Here is the plan."
OPENER = re.compile(r"[\s\"'*_“]*(here is|here['’]s)\b", re.I)

LIST_ITEM = re.compile(r"\s*(?:[-*+]|\d+[.)])(?:\s+|$)")
INLINE_CODE = re.compile(r"(`+)(.+?)\1")
URL = re.compile(r"<?\bhttps?://[^\s<>()]+>?")
LINK_TARGET = re.compile(r"(?<=\])\([^()\s]*\)")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
# A path, a name with "_" or "@", or a file name. Words joined by "/" ("and/or",
# "code/infra-flavoured") are prose, so a path must start with "/" or "~", or have a
# "." in it.
PATH_LIKE = re.compile(r"(?<!\S)(?:[/~]\S*|\S*[\\_@]\S*|\S*\w\.\w\S*)")
SENTENCE_END = re.compile(r"[.!?]+[\"'”’)\]*]*(?=\s|$)")
ABBREVIATION = re.compile(r"\b(?:e\.g|i\.e|vs|cf)\.$", re.I)


def prose_lines(text):
    """Each line of a Markdown file as (number, kind, prose). The kind is one of:
      - "gap": a line that ends a paragraph;
      - "item": the first line of a list item;
      - "heading", "table" or "field": a line that stands alone;
      - "text": any other line.
    Fenced code and front matter other than "description" are gaps. HTML comments are
    removed.
    """
    lines = text.split("\n")
    front = len(lines) > 1 and lines[0].strip() == "---"
    fence, comment, key = None, False, None
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if front:
            if number > 1 and stripped in ("---", "..."):
                front = False
            elif number > 1:
                top = re.match(r"([A-Za-z_][\w-]*):(.*)$", line)
                if top:
                    key, line = top.group(1), top.group(2).strip()
                    if line[:1] in "'\"" and line[-1:] == line[:1]:
                        line = line[1:-1]
                if key == "description" and line.strip() not in ("", ">", "|", ">-", "|-"):
                    yield number, "text", line.strip()
                    continue
            yield number, "gap", ""
            continue
        if fence:
            if stripped.startswith(fence) and not stripped.strip(fence[0]):
                fence = None
            yield number, "gap", ""
            continue
        opening = re.match(r"`{3,}|~{3,}", stripped)
        if opening:
            fence = opening.group(0)
            yield number, "gap", ""
            continue
        if comment:
            end = line.find("-->")
            if end < 0:
                yield number, "gap", ""
                continue
            line, comment = line[end + 3:], False
        line = re.sub(r"<!--.*?-->", " ", line)
        if "<!--" in line:
            line, comment = line[:line.index("<!--")], True
        line = re.sub(r"^\s*(?:>\s?)+", "", line)
        stripped = line.strip()
        if not stripped or re.fullmatch(r"[-=*_ ]{3,}", stripped):
            yield number, "gap", ""
        elif re.match(r"#{1,6}(?:\s|$)", stripped):
            yield number, "heading", stripped
        elif stripped.startswith("|"):
            yield number, "table", stripped
        elif FIELD.match(stripped):
            yield number, "field", stripped
        elif LIST_ITEM.match(stripped):
            yield number, "item", LIST_ITEM.sub("", stripped, count=1)
        else:
            yield number, "text", stripped


def blocks(text):
    """The prose as blocks: (kind, [(line number, prose), ...]).

    A block is a paragraph or a list item (kind "text"), or a heading, table row or field
    line on its own.
    """
    found, current = [], None
    for number, kind, line in prose_lines(text):
        if kind == "text" and current:
            current[1].append((number, line))
            continue
        current = None
        if kind in ("text", "item"):
            current = ("text", [(number, line)])
            found.append(current)
        elif kind != "gap":
            found.append((kind, [(number, line)]))
    return found


def blank(pattern, text):
    """The text with each match of the pattern blanked out, keeping every offset."""
    return pattern.sub(lambda m: "_" * len(m.group(0)), text)


def sentences(text):
    """The (start, end) of each sentence in the text."""
    spans, start = [], 0
    for end in SENTENCE_END.finditer(text):
        if ABBREVIATION.search(text, 0, end.end()):
            continue
        spans.append((start, end.end()))
        start = end.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


def nz_spelling(word):
    """The NZ form of a US word, in the word's case, or None if the word is fine."""
    lower = word.lower()
    if lower in SPELLING:
        fixed = SPELLING[lower]
    else:
        found = IZE.fullmatch(lower)
        if not found:
            return None
        stem, middle, ending = found.groups()
        if middle == "iz" and stem + "ize" in IZE_KEEP:
            return None
        fixed = stem + ("is" if middle == "iz" else "ys") + ending
    if word.isupper():
        return fixed.upper()
    if word[0].isupper():
        return fixed[0].upper() + fixed[1:]
    return fixed


def is_a_list_of_ids(text):
    """True when the text holds only IDs, perhaps after a label ("Capabilities: CAP-x")."""
    rest = re.sub(r"^\s*[A-Z][\w ]*:", "", ID.sub("", text))
    return not re.search(r"[A-Za-z0-9]", re.sub(r"\b(?:and|or)\b", "", rest))


def in_brackets_after_a_name(text, start):
    """True when the ID at start is in brackets that hold only IDs: "the rules (R3, R4)"."""
    opened = text.rfind("(", 0, start)
    if opened < 0 or ")" in text[opened:start]:
        return False
    return is_a_list_of_ids(text[opened + 1:start])


def long_sentences(raw, prose):
    """Rule 1: each sentence over its limit, as (start, end, rule, what, suggestion)."""
    found = []
    for start, end in sentences(prose):
        counted = [w for w in prose[start:end].split() if re.search(r"\w", w)]
        if not counted:
            continue
        first = re.sub(r"[^a-z']", "", counted[0].lower().replace("’", "'"))
        instruction = first in COMMANDS
        limit = INSTRUCTION_LIMIT if instruction else SENTENCE_LIMIT
        if len(counted) <= limit:
            continue
        start += len(prose[start:end]) - len(prose[start:end].lstrip())
        opening = " ".join(raw[start:end].split()[:5]).replace("·", "")
        if instruction:
            what = 'instruction of %d words, starting "%s"' % (len(counted), opening)
            suggestion = "split it: an instruction has %d words or fewer" % limit
        else:
            what = '%d words, starting "%s"' % (len(counted), opening)
            suggestion = "split it: a sentence has %d words or fewer" % limit
        found.append((start, end, RULES[0], what, suggestion))
    return found


def us_spelling(quiet):
    """Rule 2: each US form, as (start, end, rule, what, suggestion)."""
    words = PATH_LIKE.sub(lambda m: " " * len(m.group(0)), quiet)
    found = []
    for word in re.finditer(r"\b[A-Za-z]+\b", words):
        fixed = nz_spelling(word.group(0))
        if fixed:
            found.append((word.start(), word.end(), RULES[1],
                          '"%s" is US spelling' % word.group(0), 'write "%s"' % fixed))
    return found


def ids_alone(prose, quiet):
    """Rule 5: each ID with no name next to it, as (start, end, rule, what, suggestion)."""
    if is_a_list_of_ids(quiet):
        return []
    found = []
    for start, end in sentences(prose):
        for match in ID.finditer(quiet, start, end):
            name, after = match.group(0), quiet[match.end():end]
            before = quiet[match.start() - 1] if match.start() else " "
            quoted_name = re.match(r"\s*[\"“]", prose[match.end():end])
            if (before in "/-." or PLACEHOLDER.search(name) or quoted_name
                    or after.startswith(("*", "-*", "<", "-<"))
                    or in_brackets_after_a_name(quiet, match.start())
                    or NAMED.search(after)):
                continue
            found.append((match.start(), match.end(), RULES[2],
                          '"%s" has no name next to it' % name,
                          'write "%s (<short name>)"' % name))
    return found


def conversation(prose, quiet):
    """Rule 6: each phrase of conversation, as (start, end, rule, what, suggestion)."""
    phrases = [(p.start(), p.end(), p.group(0)) for p in CONVERSATION.finditer(quiet)]
    for start, end in sentences(prose):
        opener = OPENER.match(quiet, start, end)
        if opener:
            phrases.append((opener.start(1), opener.end(1), opener.group(1)))
    return [(start, end, RULES[3], '"%s" tells the conversation' % phrase,
             "state the fact as it is now") for start, end, phrase in phrases]


def check_block(kind, lines):
    """The findings in one block: (first line, last line, rule, what is wrong, suggestion)."""
    raw = " ".join(line for _, line in lines)
    prose = blank(LINK_TARGET, blank(URL, blank(INLINE_CODE, raw)))
    quiet = blank(QUOTED, prose)
    found = us_spelling(quiet) + conversation(prose, quiet)
    if kind == "text":
        found += long_sentences(raw, prose) + ids_alone(prose, quiet)

    starts, at = [], 0
    for number, line in lines:
        starts.append((at, number))
        at += len(line) + 1

    def line_at(offset):
        return [number for begin, number in starts if begin <= offset][-1]

    return [(line_at(start), line_at(max(start, end - 1)), rule, what, suggestion)
            for start, end, rule, what, suggestion in sorted(found)]


def changed_lines(path, base):
    """The numbers of the file's lines that were added or changed since the base."""
    diff = subprocess.run(["git", "diff", "-U0", base + "...HEAD", "--", str(path)],
                          capture_output=True, text=True).stdout
    numbers = set()
    for start, count in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
        numbers.update(range(int(start), int(start) + int(count or 1)))
    return numbers


def check_file(path, since=None):
    """The findings in one file, as output lines."""
    text = Path(path).read_text(errors="replace")
    marked = {n for n, line in enumerate(text.split("\n"), 1) if line.rstrip().endswith(MARKER)}
    changed = changed_lines(path, since) if since else None
    out = []
    for kind, lines in blocks(text):
        for first, last, rule, what, suggestion in check_block(kind, lines):
            span = set(range(first, last + 1))
            if span & marked or (changed is not None and not span & changed):
                continue
            out.append((rule, "%s:%d · %s · %s · %s" % (path, first, rule, what, suggestion)))
    return out


def markdown_files(paths):
    """Each path that is a file, and every .md file in each path that is a folder."""
    files = []
    for path in map(Path, paths):
        if path.is_dir():
            files += sorted(p for p in path.rglob("*.md")
                            if not {".git", "node_modules"} & set(p.parts))
        else:
            files.append(path)
    return files


def changed_files():
    """The .md files changed on this branch against main, or every .md file here."""
    listed = subprocess.run(["git", "diff", "--name-only", "--relative", "main...HEAD"],
                            capture_output=True, text=True)
    if listed.returncode != 0:
        return markdown_files(["."])
    return [Path(name) for name in listed.stdout.splitlines()
            if name.endswith(".md") and Path(name).exists()]


def main(argv):
    args = argv[1:]
    since = None
    if args[:1] == ["--since"]:
        if len(args) < 2:
            print(__doc__)
            return 2
        since, args = args[1], args[2:]
    if args[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    missing = [p for p in args if not Path(p).exists()]
    if missing:
        print("No such file or folder: %s" % ", ".join(missing))
        return 2

    findings = []
    for path in markdown_files(args) if args else changed_files():
        findings += check_file(path, since)
    for _, line in findings:
        print(line)
    if not findings:
        print("No findings.")
        return 0
    counts = []
    for rule in RULES:
        count = sum(1 for found_rule, _ in findings if found_rule == rule)
        if count:
            counts.append("%d %s" % (count, rule))
    print("%d finding%s: %s." % (len(findings), "" if len(findings) == 1 else "s",
                                 ", ".join(counts)))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
