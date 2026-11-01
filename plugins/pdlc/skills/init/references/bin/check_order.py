#!/usr/bin/env python3
"""pdlc change order check.

The changes of an intent must be in an order that works. Change A must come after change B
when one of these is true:
  - a line of the "Requirements" of A uses an item that B builds;
  - the "Interface" of A lists an entry that B builds;
  - "Relies on" of A names the scope spec of B.
B builds an entry when the entry ends its first line with "· proposed" in the "Interface"
(also under "Test seams") of the scope spec of B. An entry with no such mark is existing
code, and gives no rule from a line or from the Interface. A line "uses" an item in four
cases only:
  - route: the key is "METHOD /path" and the line has the same method and a path that the
    key matches ("<id>", "{id}", and ":id" each match one part);
  - command: the kind is "command" and the line has a code span with the first word of the
    key and each literal word of the key (a flag matches with a space or with "=");
  - seam variable: the key is in capitals, such as WORDFREQ_NOW, and the line has it as a
    whole word;
  - function: the key has a bracket, and the line has the name, then "(" with no space.
When the script cannot tell, it makes no rule, because a false failure stops the change
stage for no reason. With --explain, it prints a "skip:" line for each such case.

The script reads the working tree only, not git. Run it from the project root:
  python3 pdlc/bin/check_order.py IN-0001             check the order of the changes
  python3 pdlc/bin/check_order.py IN-0001 --explain   also print each rule that it found
Exit 0: the order is correct. Exit 1: a problem (the last line gives a good order, if one
exists). Exit 2: a usage error.
"""
import importlib.util
import re
import sys
from pathlib import Path

USAGE = "usage: python3 pdlc/bin/check_order.py IN-xxxx [--explain]"
METHODS = "GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS"
SPEC_ID = re.compile(r"(?:JOB|CAP)-[a-z0-9-]+")
KIND = re.compile(r"^- [^`\n]*`[^`\n]+`\s*·\s*([^·\n]+?)\s*(?:·|$)")
PROPOSED = re.compile(r"·\s*proposed\b")
ROUTE_KEY = re.compile(r"^(%s) (/\S*)$" % METHODS)
ROUTE_USE = re.compile(r"\b(%s) (/[^\s`\"')]*)" % METHODS)
SEAM_KEY = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
PLACEHOLDER = re.compile(r"<[^>]*>|\[[^\]]*\]|\{[^}]*\}|\.\.\.|[A-Z][A-Z0-9_]*")
PART = re.compile(r"(<[^>/]+>|\{[^}/]+\}|(?<=/):[A-Za-z_]\w*)")
NAME = re.compile(r"<[^>/]+>|\{[^}/]+\}|:[A-Za-z_]\w*")


def load_check_merge():
    """The check_merge.py in the folder of this script, as a module. None if it is not there."""
    path = Path(__file__).resolve().with_name("check_merge.py")
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("pdlc_check_merge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def split_query(path):
    """('/a', 'q=1') for '/a?q=1'. The query is '' when there is none."""
    path, _, query = path.partition("?")
    return path, query


def route_matches(key_path, use_path):
    """True when the path of a use matches the path of a key."""
    pattern = "".join("[^/?#\\s]+" if NAME.fullmatch(p) else re.escape(p)
                      for p in PART.split(key_path) if p)
    return re.fullmatch(pattern, use_path) is not None


def literal_words(key):
    """The literal words of a command key: the words after the first, but not a placeholder.
    A flag keeps only the part before '='."""
    words = [w for w in key.split()[1:] if not PLACEHOLDER.fullmatch(w)]
    return [w.split("=")[0] if w.startswith("-") else w for w in words]


def function_name(key):
    """The name before the first bracket of a function key, or None."""
    match = re.search(r"([A-Za-z_]\w*)\s*$", key.split("(", 1)[0])
    return match.group(1) if match and len(match.group(1)) >= 3 else None


def key_class(key, kind):
    """The way a line can use this key: route, command, seam, function, or None."""
    if ROUTE_KEY.match(key):
        return "route"
    if kind == "command":
        return "command"
    if SEAM_KEY.match(key):
        return "seam"
    return "function" if "(" in key else None


class Plan:
    """The changes of one intent, what each builds, and the order rules."""

    def __init__(self, cm, root, intent):
        self.cm, self.root, self.intent = cm, root, intent
        self.problems, self.skips, self.rules = [], {}, {}
        self.order, self.specs, self.texts = [], {}, {}
        self.items = {}    # key -> (kind, builders, class)
        self.scopes = {}   # change -> scope spec ID, for a JOB or CAP scope
        self.line_hits = []

    def skip(self, text):
        self.skips.setdefault(text, None)

    def read_changes(self, inbox_file):
        """Step 1: the list, the change specs, and the problems of the list."""
        cm, intent = self.cm, self.intent
        listed = re.findall(r"\bCH-\d+\b", cm.section(inbox_file.read_text(), "Changes"))
        for found in sorted((self.root / "pdlc" / "changes").glob("CH-*/change.md")):
            self.specs.setdefault(cm.change_id(found.parent), found)
        seen = set()
        for ch in listed:
            if ch in seen:
                self.problems.append('%s is two times in the "Changes" list of %s' % (ch, intent))
                continue
            seen.add(ch)
            path = self.specs.get(ch)
            if path is None:
                self.problems.append('%s is in the "Changes" list of %s, but pdlc/changes has no '
                                     'change spec for it' % (ch, intent))
                continue
            self.texts[ch] = path.read_text()
            if cm.field(self.texts[ch], "Status") != "cancelled":
                self.order.append(ch)
        for ch, path in sorted(self.specs.items()):
            text = path.read_text()
            if (cm.field(text, "Intent") == intent and ch not in seen
                    and cm.field(text, "Status") != "cancelled"):
                self.problems.append('%s has "Intent: %s", but the "Changes" list of %s does not '
                                     'name it' % (ch, intent, intent))

    def read_items(self):
        """Step 2: the entries of each scope spec, and who builds each."""
        cm = self.cm
        builders = {}
        for ch in self.order:
            scope = cm.field(self.texts[ch], "Scope") or ""
            if not SPEC_ID.fullmatch(scope):
                if scope:
                    self.skip("skip: %s has the scope %s, so it builds nothing" % (ch, scope))
                continue
            self.scopes[ch] = scope
            for key, (first, _codes) in cm.interface_entries(cm.spec_text(self.root, scope)).items():
                kind = (KIND.match(first) or [None, ""])[1]
                entry = builders.setdefault(key, [kind, [], key_class(key, kind)])
                if PROPOSED.search(first):
                    entry[1].append(ch)
                else:
                    self.skip('skip: %s has no "proposed" mark, so it is existing code' % key)
        for key, (kind, who, cls) in builders.items():
            who = list(dict.fromkeys(who))
            if len(who) > 1:
                self.skip("skip: %s is proposed in the scope specs of %s" % (key, " and ".join(who)))
                who = []
            if who and cls is None:
                self.skip("skip: %s is not a route, a command, a function, or a seam variable"
                          % key)
            self.items[key] = (kind, who, cls)
        names = {}
        for key, (kind, who, cls) in self.items.items():
            if cls == "function" and who:
                names.setdefault(function_name(key), set()).update(who)
        self.ambiguous = {n for n, who in names.items() if len(who) > 1}
        for name in sorted(self.ambiguous):
            self.skip("skip: the functions named %s are built by more than one change" % name)

    def builder_of(self, keys):
        """The one change that builds these keys, or None."""
        who = {c for k in keys for c in self.items[k][1]}
        return next(iter(who)) if len(who) == 1 else None

    def add_rule(self, a, b, how, key):
        if a != b:
            self.rules.setdefault((a, b, how, key), None)

    def uses_in_line(self, line):
        """The keys that a line uses, as lists of keys that one use matches."""
        found = []
        route_keys = [(k, ROUTE_KEY.match(k)) for k, v in self.items.items() if v[2] == "route"]
        for method, raw in ROUTE_USE.findall(line):
            path, query = split_query(raw.rstrip(".,;:"))
            same = [(k, m) for k, m in route_keys if m.group(1) == method
                    and route_matches(split_query(m.group(2))[0], path)]
            with_query = [k for k, m in same if query and split_query(m.group(2))[1] == query]
            plain = [k for k, m in same if not split_query(m.group(2))[1]]
            found.append(with_query or plain)
        for span in re.findall(r"`([^`]+)`", line):
            words = [w.split("=")[0] if w.startswith("-") else w for w in span.split()]
            best, most = [], 0
            for key, (_k, _w, cls) in self.items.items():
                if cls != "command" or not words or key.split()[0] != words[0]:
                    continue
                literal = literal_words(key)
                if literal and all(w in words[1:] for w in literal):
                    if len(literal) > most:
                        best, most = [key], len(literal)
                    elif len(literal) == most:
                        best.append(key)
            if best:
                found.append(best)
        for key, (_k, _w, cls) in self.items.items():
            if cls == "seam" and re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(key), line):
                found.append([key])
            if cls == "function":
                name = function_name(key)
                if name and re.search(r"\b%s\(" % re.escape(name), line):
                    found.append([k for k, v in self.items.items()
                                  if v[2] == "function" and function_name(k) == name])
        return found

    def line_rules(self, a):
        """The line rule: lines of the Requirements of A that use an item of another change."""
        retire, req = False, None
        for raw in self.cm.section(self.texts[a], "Requirements").splitlines():
            heading = re.match(r"^### (\S+)(.*)$", raw)
            if heading:
                req, retire = heading.group(1), "(retire)" in heading.group(2)
                if retire:
                    self.skip("skip: %s is a retire requirement" % req)
                continue
            line = raw.strip()
            if retire or not line:
                continue
            line = re.sub(r"^- ", "", line)
            for keys in self.uses_in_line(line):
                if keys and keys[0] in self.items and self.items[keys[0]][2] == "function" \
                        and function_name(keys[0]) in self.ambiguous:
                    continue
                b = self.builder_of(keys)
                if b is None:
                    if len({c for k in keys for c in self.items[k][1]}) > 1:
                        self.skip("skip: one use in a line of %s matches keys of more than one "
                                  "change" % req)
                    continue
                key = next(k for k in keys if b in self.items[k][1])
                if b != a:
                    self.add_rule(a, b, "line rule", key)
                    self.line_hits.append((a, b, key, req, line))

    def find_rules(self):
        """Step 3: all order rules."""
        owners = {}
        for ch, scope in self.scopes.items():
            owners.setdefault(scope, []).append(ch)
        for a in self.order:
            if a not in self.scopes:
                continue  # a design scope, or no scope: no rule
            self.line_rules(a)
            for key in self.cm.interface_entries(self.texts[a]):
                if key in self.items and len(self.items[key][1]) == 1:
                    self.add_rule(a, self.items[key][1][0], "Interface", key)
            for line in self.cm.section(self.texts[a], "Relies on").splitlines():
                match = re.match(r"^-\s*`?((?:JOB|CAP)-[a-z0-9-]+)", line)
                if match and len(owners.get(match.group(1), [])) == 1:
                    self.add_rule(a, owners[match.group(1)][0], "Relies on", match.group(1))

    def report(self):
        """Step 4: the problem lines, and a good order or the loop."""
        place = {ch: i for i, ch in enumerate(self.order)}
        needs = {ch: [] for ch in self.order}
        for a, b, _how, _key in self.rules:
            if b not in needs[a]:
                needs[a].append(b)
        out, shown = [], set()
        for a, b, how, key in self.rules:
            if place[b] < place[a]:
                continue
            if how == "line rule":
                for la, lb, lkey, req, line in self.line_hits:
                    if (la, lb, lkey) == (a, b, key) and (a, b, key, req) not in shown:
                        shown.add((a, b, key, req))
                        out.append('%s comes before %s, but the line "%s" of %s uses `%s`, which '
                                   '%s builds' % (a, b, line, req, key, b))
            elif how == "Interface":
                out.append("%s comes before %s, but its Interface lists `%s`, which %s builds"
                           % (a, b, key, b))
            else:
                out.append("%s comes before %s, but it relies on %s, the scope of %s"
                           % (a, b, key, b))
        order_problems = bool(out)
        placed = []
        while len(placed) < len(self.order):
            ready = [c for c in self.order if c not in placed and all(n in placed for n in needs[c])]
            if ready:
                placed.append(ready[0])
                continue
            left = [c for c in self.order if c not in placed]
            path = [left[0]]
            while True:
                nxt = next(n for n in needs[path[-1]] if n in left)
                if nxt in path:
                    path = path[path.index(nxt):] + [nxt]
                    break
                path.append(nxt)
            out.append("No order works, because these changes need each other: %s. One change "
                       "must set up its \"Given\" with an item of an earlier change or of existing "
                       "code, or the user decides" % " → ".join(path))
            return self.problems + out
        if order_problems:
            out.append("A good order: %s" % ", ".join(placed))
        return self.problems + out


def main(argv, root=Path(".")):
    """Run the check. Returns the exit code."""
    args = [a for a in argv[1:] if a != "--explain"]
    explain = "--explain" in argv[1:]
    if len(args) != 1 or not re.fullmatch(r"IN-\d+", args[0]):
        print(USAGE)
        return 2
    cm = load_check_merge()
    if cm is None:
        print("pdlc/bin/check_merge.py is missing")
        return 2
    found = sorted((root / "pdlc" / "inbox").glob("%s-*.md" % args[0]))
    if not found:
        print("%s is not in pdlc/inbox" % args[0])
        return 2
    plan = Plan(cm, root, args[0])
    plan.read_changes(found[0])
    plan.read_items()
    plan.find_rules()
    lines = plan.report()
    if explain:
        for a, b, how, key in plan.rules:
            print("rule: %s needs %s (%s: %s)" % (a, b, how, key))
        for text in plan.skips:
            print(text)
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
