#!/usr/bin/env python3
"""pdlc merge check.

A change may merge only when:
  - every requirement it lists is verified (and every retired one is gone from its spec);
  - each assumption marker in its change spec and requirements starts with "(assumed",
    with no emphasis around it: "(assumed)", "(assumed limit)", "(assumed: a reason)";
  - each entry under "Interface" in its change spec, also under "Test seams", is in the
    "Interface" of its scope spec, or of a JOB or CAP spec under "Relies on". The first
    text in backticks names an entry. Its "errors:" line is "errors: none", or has one
    line under it for each error: the code, the exact message, and the result, as in
    "- `TOP_INVALID` · `error: --top needs a whole number` · exit 2 · stderr". A command
    error ("exit <n>") ends with the stream that gets the message, stderr or stdout, and a
    route or function error has no stream. The code, message, and result (with its stream)
    of each error match those of the spec entry, a code in backticks is a row of
    DES-errors, and the spec entry does not end with "· proposed". A change whose scope
    spec has no "## Interface" heading, or a change with no candidate spec that has one
    (a spec from before this rule), skips this check;
  - its checks are locked, and no check file changed after the lock;
  - the tests review judged the checks as they are locked now: its packet carries the
    current lock;
  - the tests review names a wrong version of the code that each check fails on. A
    re-review (its packet says "Earlier review:") names one only for each check that
    changed since the earlier lock. If no check changed, it needs none;
  - a change with "Tests-Locked: acceptance" is the only change of its intent, lists no check
    files, and its intent has locked acceptance checks. The acceptance review then stands
    for its tests review, and the tests remit needs no result of its own;
  - every review remit named in pdlc/config.md passed;
  - the branch merges into main without conflicts;
  - its intent is in pdlc/inbox, and every other change of the intent is "in review" or
    "merged" on its own branch, or is "cancelled", so the intent's changes merge together;
  - the acceptance checks of its intent are locked ("Acceptance-Locked:" in the intent), the
    tests review judged them at that lock with "Wrong versions", and the acceptance file did
    not change after the lock;
  - the acceptance checks passed at the top of the stack: the intent on the branch of the
    top change says "Acceptance-Passed: <hash>", that commit comes after the lock, and only
    pdlc/ files changed after it. The top change is the one that no other change of the
    intent has as its "Base:" branch. The "Changes" list on a lower branch can be stale, so
    the check reads the list from the top branch. A change that only retires requirements
    is permitted to have "Acceptance-Locked: none";
  - it hasn't merged already: a merged change's branch takes no new commits.

Usage:
  python3 pdlc/bin/check_merge.py CH-0031   check one change
  python3 pdlc/bin/check_merge.py           check the change for the current branch, or,
                                            if no change uses this branch, every change
                                            with status "in review"

In CI, the script reads the current branch from GITHUB_HEAD_REF when that variable is set.
Run it from the project root. Exit code 0 means the change may merge.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

REQ = re.compile(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b(.*)$", re.M)
KINDS = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}
DEFAULT_REMITS = ["tests", "specification", "security", "quality", "compliance", "privacy", "visual"]
READY = ("in review", "merged")
HASH = re.compile(r"^[0-9a-f]{7,40}$")
# A marker with emphasis (*(assumed)*), or brackets that hold the word "assumed". A marker
# passes when it starts with "(assumed".
MARKER = re.compile(r"[*_]+\(assumed\b[^()\n]*\)[*_]+|\([^()\n]*\bassumed\b[^()\n]*\)", re.I)
# The first line of an Interface entry: a top-level list item with a name in backticks.
ENTRY = re.compile(r"^- [^`\n]*`([^`\n]+)`(.*)$")
SPEC_ID = re.compile(r"\b((?:JOB|CAP)-[a-z0-9-]+)\b")


def section(text, title):
    """The text under a '## title' heading, up to the next '## ' heading."""
    match = re.search(r"^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(title), text, re.M | re.S)
    return match.group(1) if match else ""


def requirement_text(root, req_id):
    """The requirement's heading and text in its spec, or None if it isn't there."""
    spec_id = req_id.rsplit(".", 1)[0]
    spec = root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")
    if not spec.exists():
        return None
    text = spec.read_text()
    heading = re.search(r"^### %s\b.*$" % re.escape(req_id), text, re.M)
    if not heading:
        return None
    body = text[heading.end():]
    end = re.search(r"^##", body, re.M)
    return heading.group(0) + (body[:end.start()] if end else body)


def status_of(root, req_id):
    """The requirement's status in its spec, 'missing' if it has none, None if not there."""
    body = requirement_text(root, req_id)
    if body is None:
        return None
    status = re.search(r"^Status:\s*([a-z ]+?)\s*(?:·|$)", body, re.M)
    return status.group(1) if status else "missing"


def marker_problems(where, text):
    """Each assumption marker in the text that does not start with "(assumed"."""
    return ['%s: write "%s" so it starts with "(assumed", for example "(assumed)"'
            % (where, found.group(0)) for found in MARKER.finditer(text or "")
            if not found.group(0).startswith("(assumed")]


# An (assumed) mark can follow the code, the message, the result, and the stream. The
# compared triple leaves the marks out. A command error ("exit <n>") names the stream that
# gets the message: "stderr" or "stdout". A route or function error names no stream.
ASSUMED = r"(?:\s+\(assumed[^)]*\))?"
ERROR_ITEM = re.compile(
    r"^\s+- (?P<code>`[A-Z][A-Z0-9_]*`|`?no code`?)" + ASSUMED
    + r" · (?P<message>``.+?``|`[^`]+`|no message)" + ASSUMED
    + r" · (?P<result>exit \d+|status \d{3}|raises `?[A-Za-z_][\w.:]*`?)" + ASSUMED
    + r"(?: · (?P<stream>`?(?:stderr|stdout)`?))?" + ASSUMED + r"\s*$")
NEW_FORM = ("write `errors: none`, or `errors:` with one line under it for each error, "
            "for example - `CODE` · `exact message` · exit 2 · stderr (or status <n>, or "
            "raises <Name>, with no stream)")


def error_triple(item):
    """(code, message, result) of one error line. The result of a command error ends with
    its stream, as in "exit 2 · stderr". A str says what is wrong with a line that is nearly
    in the form, and None means that the line is not in the form."""
    match = ERROR_ITEM.match(" " + item)
    if not match:
        return None
    code, message, result, stream = match.group("code", "message", "result", "stream")
    result, stream = result.replace("`", ""), (stream or "").strip("`")
    if result.startswith("exit") and not stream:
        return ("gives no stream. Add ` · stderr` or ` · stdout` after `%s`: the stream "
                "that gets the message" % result)
    if stream and not result.startswith("exit"):
        return "names a stream, but only a command error (`exit <n>`) has one. Remove ` · %s`" % stream
    message = message if message == "no message" else message.strip("`")
    return code.strip("`"), message, result + (" · " + stream if stream else "")


class _Entry:
    """One Interface entry while interface_entries reads it."""

    def __init__(self, first):
        self.first, self.errors, self.problems = first, set(), []
        self.indent = None  # the indent of the open "errors:" line, None when none is open
        self.none = self.bad = self.has_errors = False
        self.count = 0  # the error lines under the open "errors:" line
        self.item, self.item_indent = None, 0  # the lines of the open error item

    def flush(self):
        """Close the open error item."""
        if self.item is not None:
            text = " ".join(self.item)
            triple = error_triple(text)
            if isinstance(triple, tuple):
                self.errors.add(triple)
            elif triple:
                self.problems.append("the error line `%s` %s" % (text[2:], triple))
            else:
                self.problems.append("the error line `%s` is not in the form (%s)"
                                     % (text[2:], NEW_FORM))
            self.item = None

    def close(self):
        """Close the open "errors:" line."""
        self.flush()
        if self.indent is not None and not (self.none or self.bad or self.count):
            self.problems.append("`errors:` has no error lines, so it is not in the form (%s)"
                                 % NEW_FORM)
        self.indent, self.none, self.bad, self.count = None, False, False, 0

    def errors_line(self, line, indent):
        """Open an "errors:" line."""
        self.close()
        rest = re.match(r"^\s+-\s*errors?:(.*)$", line, re.I).group(1).strip()
        self.indent, self.none, self.has_errors = indent, rest.lower() == "none", True
        if rest and not self.none:
            self.bad = True
            kind = "in the old form" if "`" in rest else "not in the form"
            self.problems.append("the line `%s` is %s (%s)" % (line.strip()[2:], kind, NEW_FORM))

    def deeper(self, line, indent):
        """A line under the open "errors:" line."""
        text = line.strip()
        if self.none or self.bad:
            if self.none and not self.bad:
                self.bad = True
                self.problems.append("`errors: none` has lines under it, so it is not in the "
                                     "form (%s)" % NEW_FORM)
        elif text.startswith("- ") and (self.item is None or indent <= self.item_indent):
            self.flush()
            self.item, self.item_indent = [text], indent
            self.count += 1
        elif self.item is not None:
            self.item.append(text)  # a wrapped line
        else:
            self.count += 1
            self.bad = True
            self.problems.append("the line `%s` under `errors:` is not in the form (%s)"
                                 % (text, NEW_FORM))


def interface_entries(text):
    """The entries under '## Interface' of a spec or change spec, by name. The name is the
    first text in backticks on a top-level list line, with each run of whitespace as one
    space. Each value is (first line, set of (code, message, result), form problems). The
    errors are the list items under the entry's indented "errors:" line, one error on each
    item, and a deeper line continues the item above it. "errors: none" gives no errors.
    Other text (for example the old "errors: `A`, `B`") is a form problem. "### Test seams"
    is inside the section, so its entries count too."""
    found, current = {}, None
    for line in section(text or "", "Interface").splitlines():
        match = ENTRY.match(line)
        indent = len(line) - len(line.lstrip())
        if match:
            if current:
                found[current].close()
            current = " ".join(match.group(1).split())
            found[current] = _Entry(line)
        elif line.strip() and not line[0].isspace():
            if current:
                found[current].close()
            current = None  # a heading or other top-level line
        elif current and line.strip():
            entry = found[current]
            if re.match(r"^\s+-\s*errors?:", line, re.I):
                entry.errors_line(line, indent)
            elif entry.indent is not None and indent > entry.indent:
                entry.deeper(line, indent)
            else:
                entry.close()
    if current:
        found[current].close()
    for entry in found.values():
        if not entry.has_errors:
            entry.problems.append("the entry has no `errors:` line, so it is not in the form (%s)"
                                  % NEW_FORM)
    return {key: (e.first, frozenset(e.errors), e.problems) for key, e in found.items()}


def spec_text(root, spec_id):
    """The text of a spec, or None if its file is not there."""
    path = root / "pdlc" / "specs" / KINDS[spec_id.split("-", 1)[0]] / (spec_id + ".md")
    return path.read_text() if path.exists() else None


def error_codes(root):
    """The codes in the table of DES-errors, or None if the project has no DES-errors."""
    text = spec_text(root, "DES-errors")
    if text is None:
        return None
    return set(re.findall(r"^\|\s*`([A-Z][A-Z0-9_]*)`", text, re.M))


def error_differences(key, change, spec, owner):
    """The problems that come from errors that differ between a change entry and its spec
    entry. An error has a code (or, with no code, its message) as its name. An error with
    the same name in both has one problem for each field that differs."""
    def name(triple):
        return triple[0] if triple[0] != "no code" else "no code: " + triple[1]

    def show(triple):
        code, message, result = triple
        return " · ".join([code if code == "no code" else "`%s`" % code,
                           message if message == "no message" else "`%s`" % message, result])

    problems = []
    mine, theirs = sorted(change - spec), sorted(spec - change)
    for triple in list(mine):
        other = next((t for t in theirs if name(t) == name(triple)), None)
        if other is None:
            continue
        mine.remove(triple)
        theirs.remove(other)
        for field_name, index in (("message", 1), ("result", 2)):
            if triple[index] != other[index]:
                value = (lambda v: "`%s`" % v if index == 1 else v)
                problems.append("Interface entry `%s` has the error %s with the %s %s, but %s "
                                "has %s" % (key, triple[0] if triple[0] == "no code"
                                            else "`%s`" % triple[0], field_name,
                                            value(triple[index]), owner, value(other[index])))
    for triple in mine:
        problems.append("Interface entry `%s` has the error %s that %s does not have"
                        % (key, show(triple), owner))
    for triple in theirs:
        problems.append("Interface entry `%s` lacks the error %s that %s has"
                        % (key, show(triple), owner))
    return problems


def interface_problems(root, text):
    """Problems with the Interface of a change: each entry must be in the Interface of a
    candidate spec, in the form of the errors, with the same errors, and not proposed
    there."""
    entries = interface_entries(text)
    if not entries:
        return []
    scope = field(text, "Scope") or ""
    candidates = [scope] if SPEC_ID.fullmatch(scope) else []
    for found in SPEC_ID.findall(section(text, "Relies on")):
        if found not in candidates:
            candidates.append(found)
    heading = re.compile(r"^## Interface\s*$", re.M)
    if candidates and candidates[0] == scope:
        scope_text = spec_text(root, scope)
        if scope_text is not None and not heading.search(scope_text):
            return []  # a spec from before the Interface rule
    if not any(heading.search(spec_text(root, c) or "") for c in candidates):
        return []  # no candidate spec has an Interface yet, as in a change with a design scope
    specs = {spec_id: interface_entries(spec_text(root, spec_id)) for spec_id in candidates}
    known = error_codes(root)

    problems = []
    for key, (_, triples, form) in entries.items():
        problems += ["Interface entry `%s` in the change spec: %s" % (key, p) for p in form]
        if known is not None:
            problems += ["Interface entry `%s` has the error code `%s`, which is not a row of "
                         "DES-errors. Add the row at intake or ready first" % (key, code)
                         for code in sorted({t[0] for t in triples})
                         if code != "no code" and code not in known]
        owner = next((spec_id for spec_id in candidates if key in specs[spec_id]), None)
        if owner is None:
            problems.append("Interface entry `%s` is not in the Interface of %s. Add it to the "
                            "spec that owns it first"
                            % (key, ", ".join(candidates) or "a job or capability spec"))
            continue
        first, spec_triples, spec_form = specs[owner][key]
        problems += ["Interface entry `%s` in %s: %s" % (key, owner, p) for p in spec_form]
        if not form and not spec_form:
            problems += error_differences(key, triples, spec_triples, owner)
        if re.search(r"·\s*proposed\b", first):
            problems.append("Interface entry `%s` is still proposed in %s. /pdlc:verify removes "
                            "the mark when the change passes" % (key, owner))
    return problems


def remits(root):
    """The review remits pdlc/config.md asks for."""
    config = root / "pdlc" / "config.md"
    text = config.read_text() if config.exists() else ""
    line = re.search(r"^- remits:\s*(.+)$", section(text, "Reviews"), re.M)
    if not line:
        return DEFAULT_REMITS
    return [r.strip() for r in line.group(1).split(",") if r.strip() and r.strip() != "none"]


def check_files(text):
    """The paths listed under '## Check files'."""
    paths = re.findall(r"^-\s+`?([^`\s]+)`?", section(text, "Check files"), re.M)
    return [p for p in paths if p.lower() != "none"]


def has_lock(packet, lock, name="Tests-Locked"):
    """True when the text of a tests packet carries this lock, copied from the change spec
    (Tests-Locked) or from the intent (Acceptance-Locked)."""
    seen = re.findall(r"^%s:\s*([0-9a-f]{7,40})\b" % name, packet or "", re.M)
    return bool(seen) and (seen[-1].startswith(lock) or lock.startswith(seen[-1]))


def reviewed_lock(folder, lock):
    """True when the tests packet carries this lock, copied from the change spec."""
    packet = folder / "review" / "tests" / "packet.md"
    return packet.exists() and has_lock(packet.read_text(), lock)


def wrong_version_lines(text):
    """The lines under "Wrong versions" in the text of a tests review's result."""
    block = re.search(r"^#*\s*Wrong versions:?\s*$(.*?)(?=^[^\s-]|\Z)", text or "", re.M | re.S)
    lines = re.findall(r"^\s*-\s+(.+?)\s*$", block.group(1), re.M) if block else []
    return [line for line in lines if line.lower() != "none"]


def wrong_versions(folder):
    """The lines under "Wrong versions" in the tests review's result."""
    result = folder / "review" / "tests" / "result.md"
    return wrong_version_lines(result.read_text() if result.exists() else "")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def checks_unchanged_since_earlier_review(root, folder, lock, checks):
    """True when the tests packet is a re-review, and no check file changed between the
    lock that the earlier review judged and this lock."""
    packet = folder / "review" / "tests" / "packet.md"
    return unchanged_since_earlier_review(root, packet.read_text() if packet.exists() else "",
                                          lock, checks)


def unchanged_since_earlier_review(root, text, lock, checks):
    """True when the text of a tests packet is a re-review, and no check file changed
    between the lock that the earlier review judged and this lock."""
    earlier = re.search(r"^Earlier review:\s*([0-9a-f]{7,40})\b", text or "", re.M)
    if not earlier or not lock:
        return False
    diff = git(root, "diff", "--name-only", earlier.group(1), lock, "--", *checks)
    return diff.returncode == 0 and not diff.stdout.strip()


def field(text, name):
    """A header field of a change spec or intent, such as Status or Branch. The value is
    bare: "IN-0001 (poll-input-errors)" gives "IN-0001", and "`pdlc/CH-0001-x`" gives
    "pdlc/CH-0001-x"."""
    match = re.search(r"\b%s:[ \t]*([^·\n]*?)[ \t]*(?:·|$)" % name, text, re.M)
    if not match:
        return None
    value = match.group(1).replace("`", "")
    return re.sub(r"\s+\(.*\)$", "", value).strip()


def show(root, ref, path):
    """A file as it is on a branch, or None if git can't find it there."""
    out = git(root, "show", "%s:%s" % (ref, path))
    return out.stdout if out.returncode == 0 else None


def branches(root):
    """Every local and remote branch git knows."""
    out = git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes")
    return out.stdout.split() if out.returncode == 0 else []


def change_id(folder):
    """CH-0031 for the folder CH-0031-email-templates."""
    return "-".join(folder.name.split("-", 2)[:2])


def own_branch(root, path, refs):
    """The branch, as git knows it, that a change spec names as its own. None when the
    change has no branch."""
    for ref in refs:
        text = show(root, ref, path)
        branch = field(text, "Branch") if text else None
        if branch and branch != "none" and (ref == branch or ref.endswith("/" + branch)):
            return ref
    return None


def status_on_own_branch(root, path, refs):
    """A change's status on its own branch, the one its change spec names. A change whose
    branch is gone counts as merged if main's copy reads "in review" or "merged", and as
    cancelled if it reads "cancelled". None when it has no branch."""
    ref = own_branch(root, path, refs)
    if ref:
        return field(show(root, ref, path), "Status")
    on_main = show(root, "main", path) or show(root, "origin/main", path)
    status = field(on_main, "Status") if on_main else None
    return status if status in READY or status == "cancelled" else None


def intent_changes(root, intent, listed):
    """The change IDs of an intent: the listed IDs, then each other change spec whose
    "Intent:" is this intent. A stale "Changes" list on a branch leaves out some changes."""
    ids = list(dict.fromkeys(listed))
    for path in sorted((root / "pdlc" / "changes").glob("CH-*/change.md")):
        other = change_id(path.parent)
        if other not in ids and field(path.read_text(), "Intent") == intent:
            ids.append(other)
    return ids


def partners_not_ready(root, folder, text):
    """Problems with the other changes of this change's intent: each must be ready too."""
    intent = field(text, "Intent")
    if not intent or intent == "none":
        return []
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent))
    if not found:
        return ["%s is not in pdlc/inbox, so the check cannot find the other changes of the "
                "intent" % intent]
    listed = re.findall(r"\bCH-\d+\b", section(found[0].read_text(), "Changes"))
    problems, refs = [], branches(root)
    for other in intent_changes(root, intent, listed):
        if other == change_id(folder):
            continue
        specs = sorted((root / "pdlc" / "changes").glob(other + "-*/change.md"))
        path = "pdlc/changes/%s/change.md" % specs[0].parent.name if specs else None
        status = status_on_own_branch(root, path, refs) if path else None
        local = field(specs[0].read_text(), "Status") if specs else None
        if "cancelled" in (local, status):
            continue  # a cancelled change never merges, so it does not block its partners
        if status is None:
            problems.append("%s of %s is not ready (no branch)" % (other, intent))
        elif status not in READY:
            problems.append("%s of %s is not ready (status: %s)" % (other, intent, status))
    return problems


def record(text, name):
    """The value of a line such as "Acceptance-Locked: 1a2b3c4" in the "Acceptance checks"
    section of an intent: the last such line, without backticks. None if there is none."""
    found = re.findall(r"^%s:[ \t]*`?([^`\s]+)`?" % re.escape(name),
                       section(text or "", "Acceptance checks"), re.M)
    return found[-1] if found else None


def changed_files(root, old, new, *paths):
    """The files that differ between two commits, or None if git can't compare them."""
    out = git(root, "diff", "--name-only", old, new, "--", *paths)
    return out.stdout.split() if out.returncode == 0 else None


def is_ancestor(root, old, new):
    return git(root, "merge-base", "--is-ancestor", old, new).returncode == 0


def stack_top(root, listed, here, intent=None):
    """(change ID, branch) of the top of the stack of an intent. The top is the change that
    no other change of the intent has as its "Base:" branch. When the links do not pick one
    change (every change has the base main, for example), the last change in the list is the
    top. A change with a branch is preferred as the top. The changes are the listed IDs and
    each change spec whose "Intent:" is this intent. The branch is as git knows it. In CI,
    HEAD can be a merge of the pull request into main, so HEAD stands in only when the top
    is this change and git knows no such branch."""
    ids = list(listed) or [here]
    if intent is None:
        mine = sorted((root / "pdlc" / "changes").glob(here + "-*/change.md"))
        intent = field(mine[0].read_text(), "Intent") if mine else None
    if intent:
        ids = intent_changes(root, intent, ids)
    refs = branches(root)
    named, bases = {}, set()
    for change in ids:
        specs = sorted((root / "pdlc" / "changes").glob(change + "-*/change.md"))
        path = specs[0].relative_to(root).as_posix() if specs else None
        ref = own_branch(root, path, refs) if path else None
        text = show(root, ref, path) if ref else (specs[0].read_text() if specs else "")
        branch = field(text, "Branch") or ""
        named[change] = (ref, branch)
        base = field(text, "Base") or ""
        bases.add(base[len("origin/"):] if base.startswith("origin/") else base)
    tops = [c for c in ids if not named[c][1] or named[c][1] == "none" or named[c][1] not in bases]
    tops = [c for c in tops if named[c][0] or c == here] or tops
    top_id = tops[-1] if tops else ids[-1]
    top = named[top_id][0]
    if not top and top_id == here:
        top = "HEAD"
    return top_id, top


def acceptance_problems(root, folder, text, reqs):
    """Problems with the acceptance checks of this change's intent. The checks must be
    locked, reviewed at the lock, unchanged since the lock, and recorded as passing at the
    top of the stack: the branch of the top change of the intent (see stack_top)."""
    intent = field(text, "Intent")
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent)) if intent else []
    if not found:
        return []  # partners_not_ready names the missing intent
    intent_path = found[0].relative_to(root).as_posix()
    here = change_id(folder)

    def listed_in(text):
        return list(dict.fromkeys(re.findall(r"\bCH-\d+\b", section(text, "Changes"))))

    def read_at(ref, path):
        """A file at the top of the stack. This checkout stands in when the top is HEAD, or
        when the top change has no branch yet."""
        if ref and ref != "HEAD":
            return show(root, ref, path)
        return (root / path).read_text() if (root / path).exists() else None

    # The top of the stack follows the "Base:" links across the branches. The "Changes" list
    # of a lower branch can be stale (the plan can be reordered on a branch above it), so the
    # list comes from the top branch. A second pass uses that list in case it has more changes.
    listed = listed_in(found[0].read_text())
    top_id, top = stack_top(root, listed, here)
    intent_text = read_at(top, intent_path) or found[0].read_text()
    if set(listed_in(intent_text)) - set(listed):
        top_id, top = stack_top(root, listed_in(intent_text), here)
        intent_text = read_at(top, intent_path) or found[0].read_text()

    def read(path):
        return read_at(top, path)

    checks, lock = record(intent_text, "Acceptance-File"), record(intent_text, "Acceptance-Locked")
    passed = record(intent_text, "Acceptance-Passed")
    if not lock or not HASH.match(lock):
        if lock == "none" and reqs and all("(retire)" in rest for _, rest in reqs):
            return []
        return ["acceptance checks of %s are not locked (no Acceptance-Locked hash in the "
                "intent); run /pdlc:acceptance" % intent]
    if not checks or checks == "none":
        return ["%s names no Acceptance-File, so the check cannot find its acceptance checks"
                % intent]
    problems = []

    if "tests" in remits(root):
        review = "pdlc/acceptance/%s/review/tests/" % found[0].stem
        packet, result = read(review + "packet.md"), read(review + "result.md")
        if not has_lock(packet, lock, "Acceptance-Locked"):
            problems.append("acceptance review of %s is not of the current lock %s; review the "
                            "acceptance checks again" % (intent, lock))
        if result is None:
            problems.append("acceptance review of %s has no result. Run python3 "
                            "pdlc/bin/make_packets.py %s, and start a reviewer" % (intent, intent))
        elif not re.match(r"\s*Result:\s*pass\b", result, re.I):
            problems.append("acceptance review of %s did not pass" % intent)
        else:
            lines = wrong_version_lines(result)
            if not lines and not unchanged_since_earlier_review(root, packet, lock, [checks]):
                problems.append('acceptance review of %s lists no "Wrong versions"; review the '
                                'acceptance checks again' % intent)
            for line in lines:
                if re.search(r"·\s*passes\b", line, re.I):
                    problems.append("acceptance review of %s: a check passes a wrong version: %s"
                                    % (intent, line))

    # A change below a later lock holds an older copy of the file. That copy must not change
    # after the change got it, so the diff starts where this branch and the lock meet.
    since = git(root, "merge-base", "HEAD", lock).stdout.strip()
    changed = changed_files(root, since, "HEAD", checks) if since else None
    if changed is None:
        problems.append("can't compare the acceptance checks of %s with the lock %s" % (intent, lock))
    locked_changed = list(changed or [])

    if not top:
        return problems  # partners_not_ready says that the top change has no branch
    if not passed or not HASH.match(passed):
        problems.append("acceptance checks of %s are not ready: no Acceptance-Passed at the top "
                        "of the stack (%s)" % (intent, top_id))
    elif not is_ancestor(root, lock, passed):
        problems.append("Acceptance-Passed %s of %s does not come after its lock %s; run the acceptance "
                        "checks again" % (passed, intent, lock))
    elif not is_ancestor(root, passed, top):
        problems.append("Acceptance-Passed %s of %s is not on the branch of %s; run the acceptance "
                        "checks there" % (passed, intent, top_id))
    else:
        locked_changed += changed_files(root, lock, passed, checks) or []
        later = [f for f in changed_files(root, passed, top) or [] if not f.startswith("pdlc/")]
        if later:
            problems.append("files changed after the acceptance checks of %s passed: %s; run them "
                            "again" % (intent, ", ".join(later)))
    problems += ["changed after the acceptance checks were locked: %s" % path
                 for path in dict.fromkeys(locked_changed)]
    return problems


def merged_already(root, folder):
    """True when main says this change merged, yet this branch has commits main doesn't."""
    on_main = show(root, "main", "pdlc/changes/%s/change.md" % folder.name)
    if not on_main or field(on_main, "Status") != "merged":
        return False
    ahead = git(root, "rev-list", "--count", "main..HEAD")
    return ahead.returncode == 0 and int(ahead.stdout.strip() or 0) > 0


def conflicts_with_main(root):
    """Files that conflict when this branch merges into main. Empty when it merges
    cleanly, when there is no main, when this is main, or when git can't tell."""
    try:
        head = git(root, "rev-parse", "--verify", "-q", "HEAD")
        main = git(root, "rev-parse", "--verify", "-q", "main")
        if head.returncode or main.returncode or head.stdout == main.stdout:
            return []
        out = git(root, "merge-tree", "--write-tree", "--name-only", "--no-messages",
                  "main", "HEAD")
    except OSError:
        return []
    if out.returncode != 1:
        return []
    return sorted(set(out.stdout.split()[1:]))


def acceptance_serves(root, folder, text, checks):
    """Problems with a change that has "Tests-Locked: acceptance". The acceptance checks of
    its intent are also its checks. That holds only when the change lists no check files,
    when it is the only change of its intent, and when the intent has locked acceptance
    checks. The review and the pass of those checks come from acceptance_problems."""
    problems = []
    if checks:
        problems.append('Tests-Locked: acceptance needs "- none" under "Check files"')
    intent = field(text, "Intent")
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % intent)) if intent else []
    if not found:
        return problems  # partners_not_ready names the missing intent
    intent_text = found[0].read_text()
    listed = list(dict.fromkeys(re.findall(r"\bCH-\d+\b", section(intent_text, "Changes"))))
    if listed != [change_id(folder)]:
        problems.append("Tests-Locked: acceptance is only for the only change of an intent. "
                        "%s lists %s. Run /pdlc:tests" % (intent, ", ".join(listed) or "no changes"))
    lock = record(intent_text, "Acceptance-Locked")
    if not lock or not HASH.match(lock):
        problems.append("Tests-Locked: acceptance needs the acceptance checks of %s locked"
                        % intent)
    return problems


def check_change(root, folder):
    """A list of problems with one change. Empty means it may merge."""
    problems = []
    text = (folder / "change.md").read_text()

    reqs = REQ.findall(section(text, "Requirements"))
    if not reqs:
        problems.append("lists no requirements")
    for req_id, rest in reqs:
        status = status_of(root, req_id)
        if "(retire)" in rest:
            if status is not None:
                problems.append("%s is marked (retire) but is still in its spec" % req_id)
        elif status is None:
            problems.append("%s is not in its spec" % req_id)
        elif status != "verified":
            problems.append("%s is %s, not verified" % (req_id, status))

    problems += marker_problems("change.md", text)
    problems += interface_problems(root, text)
    for req_id, _ in reqs:
        problems += marker_problems(req_id, requirement_text(root, req_id))

    checks = check_files(text)
    # A re-lock may leave the older line in place. The newest (last) line counts. The value
    # "acceptance" says that the acceptance checks of the intent are also the checks of this
    # change, so this change has no tests lock and no tests review of its own.
    values = re.findall(r"^Tests-Locked:[ \t]*`?([^`\s]+)`?", text, re.M)
    by_acceptance = bool(values) and values[-1] == "acceptance"
    locks = list(re.finditer(r"^Tests-Locked:\s*([0-9a-f]{7,40})\b", text, re.M))
    lock = locks[-1] if locks and not by_acceptance else None
    if by_acceptance:
        problems += acceptance_serves(root, folder, text, checks)
    elif checks and not lock:
        problems.append("tests are not locked (no Tests-Locked line)")
    elif checks:
        diff = git(root, "diff", "--name-only", lock.group(1), "HEAD", "--", *checks)
        if diff.returncode != 0:
            problems.append("can't compare tests with the lock %s" % lock.group(1))
        for path in diff.stdout.split():
            problems.append("changed after the tests were locked: %s" % path)

    wanted = remits(root)
    if lock and "tests" in wanted and not reviewed_lock(folder, lock.group(1)):
        problems.append("tests review is not of the current lock %s; review the checks again"
                        % lock.group(1))

    for remit in wanted:
        if remit == "tests" and by_acceptance:
            continue  # acceptance_problems reads the acceptance review in its place
        result = folder / "review" / remit / "result.md"
        if not result.exists():
            problems.append("%s review has no result. Run python3 pdlc/bin/make_packets.py %s %s, "
                            "and start a reviewer if it writes a packet"
                            % (remit, change_id(folder), remit))
        elif not re.match(r"\s*Result:\s*pass\b", result.read_text(), re.I):
            problems.append("%s review did not pass" % remit)

    if (checks and not by_acceptance and "tests" in wanted
            and (folder / "review" / "tests" / "result.md").exists()):
        lines = wrong_versions(folder)
        if not lines and not checks_unchanged_since_earlier_review(
                root, folder, lock.group(1) if lock else None, checks):
            problems.append('tests review lists no "Wrong versions"; review the checks again')
        for line in lines:
            if re.search(r"·\s*passes\b", line, re.I):
                problems.append("tests review: a check passes a wrong version: %s" % line)

    for path in conflicts_with_main(root):
        problems.append("conflicts with main: %s" % path)

    problems += partners_not_ready(root, folder, text)
    problems += acceptance_problems(root, folder, text, reqs)

    if merged_already(root, folder):
        problems.append("%s already merged; new commits on its branch won't reach main. "
                        "Start a new change." % change_id(folder))
    return problems


def current_branch(root):
    """The branch being merged: GITHUB_HEAD_REF in CI, else git's current branch."""
    if os.environ.get("GITHUB_HEAD_REF"):
        return os.environ["GITHUB_HEAD_REF"]
    try:
        out = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    except OSError:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def main(argv, root=Path("."), branch=None):
    changes = root / "pdlc" / "changes"
    everything = sorted(p.parent for p in changes.glob("CH-*/change.md"))
    if len(argv) > 1:
        folders = [f for f in everything if f.name.startswith(argv[1] + "-")]
        if not folders:
            print("No change spec found for %s" % argv[1])
            return 1
    else:
        branch = branch or current_branch(root)
        folders = [f for f in everything
                   if branch and field((f / "change.md").read_text(), "Branch") == branch]
        if not folders:
            folders = [f for f in everything
                       if field((f / "change.md").read_text(), "Status") == "in review"]
    failed = False
    for folder in folders:
        problems = check_change(root, folder)
        name = change_id(folder)
        if problems:
            failed = True
            print("FAIL %s" % name)
            for problem in problems:
                print("  - %s" % problem)
        else:
            print("ok   %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
