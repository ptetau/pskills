#!/usr/bin/env python3
"""slice: the state, test, and commit script of the slice plugin.

Usage: slice.py [--root DIR] [--spec NNN|NAME] status
       slice.py [--root DIR] [--spec NNN|NAME] next
       slice.py [--root DIR] [--spec NNN|NAME] set Sn STATUS [--reason TEXT]
       slice.py [--root DIR] [--spec NNN|NAME] round Sn test|review
       slice.py [--root DIR] [--spec NNN|NAME] resume Sn
       slice.py [--root DIR] [--spec NNN|NAME] test Sn [--full]
       slice.py [--root DIR] [--spec NNN|NAME] scan
       slice.py [--root DIR] [--spec NNN|NAME] commit Sn [--summary TEXT]

slice/config.md is at the top of slice/. Each spec has its own folder, slice/NNN-<name>/
(for example slice/001-wordfreq/), with spec.md, domain.md, slices.md, and
review/Sn.md (the code findings of the reviewer, for the implementer) and review/Sn.tests.md
(the test findings, for the test writer; the guard hides each file from the other agent). The current spec is the folder with the highest
number, or the one that --spec names. The script keeps the round counts in slices.md.
Requirements (R1, R2, ...) and decisions (D1, D2, ...) are numbered in spec.md. A slice names
its requirements on a `- Requirements:` line, and domain.md maps each requirement.

"next" prints one line and changes nothing: the next stage (spec, plan, domain), "build Sn",
"stop Sn: <reason>" (a stopped slice: ask the user), or "done". "status" ends with "next: <that line>".
"resume" puts a stopped slice back to building, with no reason and no rounds used.
"test" prints test names, pass or fail, and failure messages. It never prints test source.
For each failing test of the slice it also prints the acceptance lines of slices.md that cite the
requirement of the test name (all lines when the name cites none). An assertion failure (unittest
FAIL, junit failure) keeps its message back until the slice has used 2 test rounds; an error
(unittest ERROR, junit error: an import error, or an exception in the code) prints its message
at once. --full prints every message at once.
After the results of the slice, it lists the regressions: tests that fail and that no unfinished
slice owns (the tests of a done slice, and tests that no slice owns).
A test belongs to a slice when its name holds the spec number and the slice, `test_NNN_Sn_Rn_<what>`
(for example test_002_S1_R2_counts_words). A name with no number belongs to the slice of the
only spec, and to no slice when there are two specs or more.
"scan" runs the command of the config line `- security scan: <command>` (default none) in the
project folder, prints one short result, and exits 1 when the command exits non-zero or runs
longer than 300 seconds. The command is the one line of the config: no part of a record is added to it.
"commit Sn [--summary TEXT]" commits the records, the source folders, the unit tests folder
(if configured), the source files, and the tests folder of one slice as "Slice Sn: <title>"
with a body describing the slice (from --summary or the slice's Story and Requirements) and
trailer `Slice: Sn`. It refuses when the slice has no tests, a test fails, a regression fails,
an open major line is in review/Sn.md or review/Sn.tests.md, or the security scan fails. The config
line `source files:` lists single paths and globs (`package.json, migrations/**`) that lie
outside the source folders.
Exit 0: ok. Exit 1: a refusal or a failing check. Exit 2: usage or record error.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

STATUSES = ["planned", "building", "review", "done", "stopped"]
LIMITS = {"test": 5, "review": 3}
FIELDS = {"test": "Test rounds", "review": "Review rounds"}
USAGE = __doc__.split("\n\n")[0]
TIMEOUT = 600
SCAN_TIMEOUT = 300


class Fail(Exception):
    def __init__(self, text, code=1):
        super().__init__(text)
        self.code = code


# Records

def find_root(start):
    path = os.path.realpath(start)
    while True:
        if os.path.isdir(os.path.join(path, "slice")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


SPEC_ARG = None
SPEC_DIR = re.compile(r"^(\d{3})-[A-Za-z0-9][\w-]*$")


def spec_names(root):
    try:
        names = os.listdir(os.path.join(root, "slice"))
    except OSError:
        return []
    return sorted(n for n in names if SPEC_DIR.match(n) and os.path.isdir(os.path.join(root, "slice", n)))


def spec_name(root):
    """The folder name of the current spec: the one that --spec names, else the highest number."""
    names = spec_names(root)
    if SPEC_ARG:
        for n in names:
            if n == SPEC_ARG or n.startswith(SPEC_ARG + "-"):
                return n
        raise Fail("no spec folder %s in slice/" % SPEC_ARG, 2)
    return names[-1] if names else None


def record_path(root, name):
    if name == "config.md":
        return os.path.join(root, "slice", name)
    spec = spec_name(root)
    return os.path.join(root, "slice", spec, name) if spec else None


def shown(root, name):
    spec = spec_name(root) or "NNN-<name>"
    return "slice/%s" % name if name == "config.md" else "slice/%s/%s" % (spec, name)


def read(root, name):
    path = record_path(root, name)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, TypeError):
        return None


def write(root, name, text):
    path = record_path(root, name)
    if path is None:
        raise Fail("no spec folder: make slice/NNN-<name>/ first", 2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def config(root):
    """The `- key: value` lines of slice/config.md. A backticked value gives its inside."""
    text = read(root, "config.md")
    if text is None:
        raise Fail("slice/config.md is missing", 2)
    out = {}
    for m in re.finditer(r"^- ([^:\n]+):[ \t]*(.*)$", text, re.M):
        value = m.group(2).strip()
        quoted = re.findall(r"`([^`]+)`", value)
        out[m.group(1).strip().lower()] = ", ".join(quoted) if quoted else value
    return out


def folders(value):
    return [f.strip(" /") for f in (value or "").split(",")
            if f.strip(" /") and f.strip(" /") != "none" and not f.strip(" /").startswith("<")]

def source_paths(root, cfg):
    """The files that the `source files:` patterns match now, never in the tests folders or slice/."""
    hidden = ["slice"] + folders(cfg.get("tests folder"))
    out = []
    for pattern in folders(cfg.get("source files")):
        if pattern == "none" or pattern.startswith("<"):
            continue
        for found in sorted(glob.glob(os.path.join(root, pattern), recursive=True)):
            rel = os.path.relpath(found, root)
            if os.path.isfile(found) and not rel.startswith("..") and "__pycache__" not in rel \
                    and not rel.endswith(".pyc") and not any(
                    rel == h or rel.startswith(h + os.sep) for h in hidden):
                out.append(rel)
    return out


def spec_status(root):
    text = read(root, "spec.md")
    if text is None:
        return "missing"
    m = re.search(r"^Status:\s*(\w+)", text, re.M)
    return m.group(1).lower() if m else "draft"



def sections(text):
    """[(id, title, start, end)] for each `## Sn: title` section of slices.md."""
    heads = list(re.finditer(r"^## (S\d+):[ \t]*(.*?)[ \t]*$", text, re.M))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        out.append((m.group(1), m.group(2), m.start(), end))
    return out


def load_slices(root):
    text = read(root, "slices.md")
    if text is None:
        raise Fail("%s is missing" % shown(root, "slices.md"), 2)
    return text, sections(text)


def find(text, sid):
    for s in sections(text):
        if s[0] == sid:
            return s
    raise Fail("no slice %s in slices.md" % sid, 2)


def get_field(block, name):
    m = re.search(r"^- %s:[ \t]*(.*)$" % re.escape(name), block, re.M)
    return m.group(1).strip() if m else ""


def set_field(text, sid, name, value):
    _, _, start, end = find(text, sid)
    block = text[start:end]
    line = "- %s: %s" % (name, value)
    pattern = re.compile(r"^- %s:.*$" % re.escape(name), re.M)
    if pattern.search(block):
        block = pattern.sub(lambda _: line, block, count=1)
    else:
        block = block.rstrip("\n") + "\n" + line + "\n" + ("\n" if end < len(text) else "")
    return text[:start] + block + text[end:]


def status_of(block):
    m = re.match(r"(\w+)(?:\s*\((.*)\))?$", get_field(block, "Status"))
    return (m.group(1), m.group(2) or "") if m else ("planned", "")


def write_status(root, sid, status, reason=""):
    text, _ = load_slices(root)
    value = "%s (%s)" % (status, reason) if reason else status
    write(root, "slices.md", set_field(text, sid, "Status", value))


# Commands

def requirement_ids(text):
    return re.findall(r"^[-*]\s+(R\d+)\b", text or "", re.M)


MAP_LINE = re.compile(r"^[-*]\s+(R\d+):[ \t]*(.*)$", re.M)
MACHINE_HEAD = re.compile(r"^###\s+Machine:[ \t]*(\S.*?)[ \t]*$", re.M)
CITE = re.compile(r"(?<![\w.-])([A-Za-z][\w-]*)\.([TX]\d+)\b")
TRANSITION = re.compile(r"^[-*]\s+(T\d+):[ \t]*(.+?)[ \t]*->[ \t]*(.+?)[ \t]+on[ \t]+\S.*$", re.M)
REFUSED = re.compile(r"^[-*]\s+(X\d+):[ \t]*(.+?)[ \t]+on[ \t]+(.+?)[ \t]+refused:[ \t]*\S.*$", re.M)
MACHINES_NONE = re.compile(r"^[-*]\s+Machines:[ \t]*none\b", re.M | re.I)


def clean_state(value):
    return value.strip().strip("`").strip()


def state_list(value):
    return [s for s in (clean_state(p) for p in value.rstrip(". ").split(",")) if s]


def machines(text):
    """{name: machine} for each `### Machine: <Object>` section of domain.md. A machine holds
    its states, start, end, transitions {Tn: (from, to)}, and refused {Xn: from}."""
    heads = list(MACHINE_HEAD.finditer(text))
    out = {}
    for m in heads:
        rest = text[m.end():]
        stop = re.search(r"^#", rest, re.M)
        body = rest[:stop.start()] if stop else rest
        name = clean_state(m.group(1))
        start = get_field(body, "Start")
        out[name] = {
            "states": state_list(get_field(body, "States")),
            "start": clean_state(start) if start else "",
            "end": [s for s in state_list(get_field(body, "End")) if s.lower() != "none"],
            "transitions": {t.group(1): (clean_state(t.group(2)), clean_state(t.group(3)))
                            for t in TRANSITION.finditer(body)},
            "refused": {x.group(1): clean_state(x.group(2)) for x in REFUSED.finditer(body)},
        }
    return out


def machine_problems(text):
    """Problems of the state machines in domain.md: a missing start, an unreachable state,
    a state that States does not list, a cited transition that no machine defines, and a
    transition that no requirement cites."""
    found = machines(text)
    problems = []
    if not found and not MACHINES_NONE.search(text):
        problems.append("no state machine: add a `### Machine: <Object>` section, or the line `- Machines: none`")
    cited = set()
    for line in MAP_LINE.finditer(text):
        for obj, tid in CITE.findall(line.group(2)):
            cited.add((obj, tid))
            if tid not in found.get(obj, {}).get("transitions", {}) and tid not in found.get(obj, {}).get("refused", {}):
                problems.append("%s cites %s.%s: no machine defines it" % (line.group(1), obj, tid))
    for name, mc in found.items():
        states = set(mc["states"])
        if not mc["start"] or mc["start"] not in states:
            problems.append("%s has no start state (the Start line names a state of States)" % name)
        for tid, (src, dst) in mc["transitions"].items():
            for s in (src, dst):
                if s not in states:
                    problems.append("%s.%s: state %s is not in States" % (name, tid, s))
        for tid, src in mc["refused"].items():
            if src not in states:
                problems.append("%s.%s: state %s is not in States" % (name, tid, src))
        reached, todo = set(), [mc["start"]] if mc["start"] in states else []
        while todo:
            s = todo.pop()
            if s in reached:
                continue
            reached.add(s)
            todo += [dst for src, dst in mc["transitions"].values() if src == s]
        if mc["start"] in states:
            for s in mc["states"]:
                if s not in reached:
                    problems.append("%s: state %s is unreachable" % (name, s))
        for tid in list(mc["transitions"]) + list(mc["refused"]):
            if (name, tid) not in cited:
                problems.append("%s.%s is not cited by any requirement" % (name, tid))
    return problems


def domain_gaps(root, reqs):
    """The requirements that domain.md does not map. None when domain.md is missing."""
    text = read(root, "domain.md")
    if text is None:
        return None
    gaps = []
    for r in reqs:
        m = re.search(r"^[-*]\s+%s:[ \t]*(.*)$" % r, text, re.M)
        value = m.group(1).strip() if m else ""
        if not value or value.upper().startswith("GAP") or value.startswith("<"):
            gaps.append(r)
    return gaps


def domain_problems(root):
    """The problems of the state machines of domain.md (none when domain.md is missing)."""
    text = read(root, "domain.md")
    return machine_problems(text) if text is not None else []


def next_step(root):
    """The next stage, "build Sn", "stop Sn: reason", or "done". The one place that picks the order."""
    if root is None or spec_name(root) is None:
        return "spec"
    text = read(root, "slices.md")
    slices = sections(text) if text else []
    reqs = requirement_ids(read(root, "spec.md"))
    covered = set(re.findall(r"R\d+", " ".join(get_field(text[s[2]:s[3]], "Requirements") for s in slices)))
    uncovered = [r for r in reqs if r not in covered]
    gaps = domain_gaps(root, reqs)
    rows = []
    for sid, _, start, end in slices:
        status, reason = status_of(text[start:end])
        rows.append((sid, status, reason))
    if spec_status(root) != "ratified":
        return "spec"
    if not slices or uncovered:
        return "plan"
    if gaps is None or gaps or domain_problems(root):
        return "domain"
    stopped = [r for r in rows if r[1] == "stopped"]
    if stopped:
        return "stop %s: %s" % (stopped[0][0], stopped[0][2] or "no reason recorded")
    open_ = [r for r in rows if r[1] != "done"]
    return "build %s" % open_[0][0] if open_ else "done"

def cmd_next(root):
    print(next_step(root))
    return 0


def cmd_status(root):
    if root is None or spec_name(root) is None:
        print("no spec folder in slice/" if root else "no slice/ folder")
        print("next: spec")
        return 0
    spec = spec_status(root)
    text = read(root, "slices.md")
    slices = sections(text) if text else []
    reqs = requirement_ids(read(root, "spec.md"))
    covered = set(re.findall(r"R\d+", " ".join(get_field(text[s[2]:s[3]], "Requirements") for s in slices)))
    uncovered = [r for r in reqs if r not in covered]
    gaps = domain_gaps(root, reqs)
    print("spec folder: %s" % spec_name(root))
    print("spec: %s" % spec)
    if reqs:
        print("requirements: %d, uncovered by a slice: %s" % (len(reqs), ", ".join(uncovered) or "none"))
    problems = domain_problems(root)
    print("domain: %s" % ("missing" if gaps is None else "gaps %s" % ", ".join(gaps) if gaps
                          else "problems" if problems else "mapped"))
    for problem in problems:
        print("  - " + problem)
    rows = []
    for sid, title, start, end in slices:
        block = text[start:end]
        status, reason = status_of(block)
        rows.append((sid, status, reason))
        extra = " (%s)" % reason if reason else ""
        print("%s %s%s  %s  [test rounds %s/%d, review rounds %s/%d]" % (
            sid, status, extra, title, get_field(block, "Test rounds") or 0, LIMITS["test"],
            get_field(block, "Review rounds") or 0, LIMITS["review"]))
    print("next: %s" % next_step(root))
    return 0


def cmd_set(root, sid, status, reason):
    if status not in STATUSES:
        raise Fail("status must be one of: %s" % ", ".join(STATUSES), 2)
    text, _ = load_slices(root)
    find(text, sid)
    write_status(root, sid, status, reason)
    print("%s %s" % (sid, status))
    return 0


def cmd_round(root, sid, kind):
    if kind not in LIMITS:
        raise Fail("round kind must be test or review", 2)
    text, _ = load_slices(root)
    sec = find(text, sid)
    used = int(get_field(text[sec[2]:sec[3]], FIELDS[kind]) or 0)
    if used >= LIMITS[kind]:
        reason = "no %s rounds left: %d used" % (kind, used)
        write_status(root, sid, "stopped", reason)
        raise Fail("%s: %s. The slice is stopped. Ask the user." % (sid, reason))
    write(root, "slices.md", set_field(text, sid, FIELDS[kind], used + 1))
    print("%s %s round %d of %d" % (sid, kind, used + 1, LIMITS[kind]))
    return 0


def cmd_resume(root, sid):
    text, _ = load_slices(root)
    sec = find(text, sid)
    status, _ = status_of(text[sec[2]:sec[3]])
    if status != "stopped":
        raise Fail("%s is %s, not stopped: resume works only on a stopped slice" % (sid, status))
    text = set_field(text, sid, "Status", "building")
    for field in FIELDS.values():
        text = set_field(text, sid, field, 0)
    write(root, "slices.md", text)
    print("%s building" % sid)
    return 0


NAME_NUMBERED = re.compile(r"(?<![0-9])(\d{3})_[Ss](\d+)(?![0-9])")
NAME_PLAIN = re.compile(r"(?<![0-9A-Za-z])[Ss](\d+)(?![0-9])|(?<=[a-z])S(\d+)(?![0-9])")


def owner(name):
    """(spec number or None, slice ID) of a test name, or None. test_002_S1_R2_x gives ("002", "S1")."""
    m = NAME_NUMBERED.search(name)
    if m:
        return m.group(1), "S" + m.group(2)
    m = NAME_PLAIN.search(name)
    return (None, "S" + (m.group(1) or m.group(2))) if m else None


def belongs(name, sid, number, single=False):
    """True when the test name holds the spec number and the slice ID as wholes (002 and S1 match
    test_002_S1_x, not S10). A name with no number matches only when the project has one spec."""
    found = owner(name)
    if not found or found[1] != sid:
        return False
    return found[0] == number if found[0] else single


def scope(root):
    """(number of the current spec, True when the project has one spec only)."""
    name = spec_name(root)
    return (name[:3] if name else None), len(spec_names(root)) == 1


def mine_of(root, results, sid):
    number, single = scope(root)
    return [r for r in results if belongs(r["name"], sid, number, single)]


def regressions(root, results):
    """The failing tests that no unfinished slice owns: the tests of a done slice, and tests that no slice owns."""
    names = spec_names(root)
    unfinished = set()
    for name in names:
        try:
            with open(os.path.join(root, "slice", name, "slices.md"), encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for sid, _, start, end in sections(text):
            if status_of(text[start:end])[0] != "done":
                unfinished.add((name[:3], sid))
    out = []
    for r in results:
        if r["status"] not in ("fail", "error"):
            continue
        found = owner(r["name"])
        if found:
            number = found[0] or (names[0][:3] if len(names) == 1 else None)
            if (number, found[1]) in unfinished:
                continue
        out.append(r)
    return out


def short(lines, limit=6):
    lines = [l.rstrip() for l in lines if l.strip()][:limit]
    return "\n".join(lines)[:500]


def parse_junit(path):
    results = []
    for tc in ET.parse(path).getroot().iter("testcase"):
        cls, name = tc.get("classname") or "", tc.get("name") or ""
        status, msg = "pass", ""
        for child in tc:
            if child.tag in ("failure", "error", "skipped"):
                status = "fail" if child.tag == "failure" else "error" if child.tag == "error" else "skip"
                msg = short(((child.get("message") or "") or (child.get("type") or "")).splitlines())
                if child.tag == "error" and child.get("type"):
                    msg = (child.get("type") + ": " + msg).strip(": ")
                break
        results.append({"name": "%s::%s" % (cls, name) if cls else name, "status": status, "message": msg})
    return results


STATUS_LINE = re.compile(r"^(.*?) \.\.\. (.*)$")
BLOCK_HEAD = re.compile(r"^(FAIL|ERROR): (.+)$")


def unittest_status(word):
    word = word.strip()
    if word in ("ok", "expected failure"):
        return "pass"
    if word in ("FAIL", "unexpected success"):
        return "fail"
    if word == "ERROR":
        return "error"
    if word.startswith("skipped"):
        return "skip"
    return None


def exception_text(block):
    """The exception line and its message from one failure block, without any frame or source."""
    start = 0
    for i, line in enumerate(block):
        if line.startswith("Traceback"):
            start = i + 1
    i = start
    while i < len(block) and (block[i].startswith(" ") or not block[i].strip()):
        i += 1
    return short(block[i:], 8)


NAME_LINE = re.compile(r"^\S+ \([\w.]+\)$")


def parse_unittest(output):
    """Results from verbose unittest output. A test with a docstring prints its name line,
    then `<docstring> ... status`: the name line gives the name."""
    lines = output.splitlines()
    results, pending = [], None
    for line in lines:
        if line.startswith("="):
            continue
        if NAME_LINE.match(line):
            pending = line
            continue
        if pending is not None and unittest_status(line):
            results.append({"name": pending, "status": unittest_status(line), "message": ""})
            pending = None
            continue
        m = STATUS_LINE.match(line)
        if not m:
            continue
        st = unittest_status(m.group(2))
        name = m.group(1) if NAME_LINE.match(m.group(1)) or pending is None else pending
        if st:
            results.append({"name": name, "status": st, "message": ""})
            pending = None
        else:
            pending = name
    i = 0
    while i < len(lines):
        head = BLOCK_HEAD.match(lines[i])
        if head and i > 0 and lines[i - 1].startswith("=" * 10):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("-" * 10) and not lines[j].startswith("=" * 10):
                j += 1  # the docstring lines, up to the separator
            j += 1
            body = []
            while j < len(lines) and not lines[j].startswith("=" * 10) and not lines[j].startswith("-" * 10 + "-"):
                body.append(lines[j])
                j += 1
            name, msg = head.group(2), exception_text(body)
            hit = [r for r in results if r["name"] == name]
            if hit:
                hit[0]["message"] = msg
            else:
                results.append({"name": name, "status": "fail" if head.group(1) == "FAIL" else "error",
                                "message": msg})
            i = j
        else:
            i += 1
    return results


def error_lines(output):
    """Lines of an exception, from output that held no parsed test: no frame and no source."""
    keep = [l.strip() for l in output.splitlines() if l and not l[0].isspace()
            and re.search(r"\b\w*(Error|Exception)\b", l)]
    return keep[-5:]


def run_tests(root):
    """Run the test command. Return (results, exit code, exception lines of the output)."""
    cfg = config(root)
    command = cfg.get("test command")
    if not command:
        raise Fail("slice/config.md has no `test command`", 2)
    fmt = cfg.get("result format") or ("junit" if "{junit}" in command else "unittest")
    with tempfile.TemporaryDirectory() as tmp:
        junit = os.path.join(tmp, "results.xml")
        try:
            proc = subprocess.run(command.replace("{junit}", junit), shell=True, cwd=root,
                                  capture_output=True, text=True, timeout=TIMEOUT,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            return [], 1, ["the test command ran longer than %d seconds" % TIMEOUT]
        output = proc.stdout + "\n" + proc.stderr
        try:
            results = parse_junit(junit) if fmt == "junit" else parse_unittest(output)
        except (OSError, ET.ParseError):
            results = []
    return results, proc.returncode, error_lines(output)


def show(r):
    word = {"pass": "PASS", "fail": "FAIL", "error": "ERROR", "skip": "SKIP"}[r["status"]]
    print("%s %s" % (word, r["name"]))
    for line in r["message"].splitlines():
        print("  " + line)


REQ_WORD = r"(?<![0-9A-Za-z])R\d+(?![0-9])"
WITHHOLD_ROUNDS = 2  # an assertion message shows once the slice has used this many test rounds


def acceptance_lines(block):
    """The acceptance lines of one slice: the indented items under its `- Acceptance:` line."""
    out, inside = [], False
    for line in block.splitlines():
        if re.match(r"^- Acceptance:", line):
            inside = True
        elif inside and re.match(r"^\s+[-*]\s+\S", line):
            out.append(re.sub(r"^\s+[-*]\s+", "", line).strip())
        elif inside and re.match(r"^\S", line):
            inside = False
    return out


def show_own(r, lines, withhold):
    """One result of the slice. A failing test shows its acceptance lines. An assertion
    failure shows its message only when withhold is False."""
    word = {"pass": "PASS", "fail": "FAIL", "error": "ERROR", "skip": "SKIP"}[r["status"]]
    print("%s %s" % (word, r["name"]))
    if r["status"] in ("fail", "error"):
        cited = set(re.findall(REQ_WORD, r["name"]))
        pick = [l for l in lines if cited & set(re.findall(REQ_WORD, l))] or lines
        for l in pick:
            print("  acceptance: " + l)
    if r["status"] == "fail" and withhold:
        print("  message withheld: it shows from test round %d, or with --full" % (WITHHOLD_ROUNDS + 1))
        return
    for line in r["message"].splitlines():
        print("  " + line)


def cmd_test(root, sid, full=False):
    text, _ = load_slices(root)
    sec = find(text, sid)
    block = text[sec[2]:sec[3]]
    results, code, errors = run_tests(root)
    mine = mine_of(root, results, sid)
    if not mine:
        print("no tests found for %s" % sid)
        for line in errors:
            print("  " + line)
        return 1
    passed = sum(1 for r in mine if r["status"] == "pass")
    print("%s: %d tests, %d passed, %d not passed" % (sid, len(mine), passed, len(mine) - passed))
    withhold = not full and int(get_field(block, "Test rounds") or 0) < WITHHOLD_ROUNDS
    lines = acceptance_lines(block)
    for r in mine:
        show_own(r, lines, withhold)
    broken = regressions(root, results)
    if broken:
        print("regressions: %d tests outside %s fail (tests of a done slice, or of no slice)" % (
            len(broken), sid))
        for r in broken:
            show(r)
    return 0 if passed == len(mine) and not broken else 1

def run_scan(root):
    """Run the security scan of the config. Return (ok, exit code or None, text). With no scanner,
    ok is True and the text is "none". The command comes from the config line only."""
    command = config(root).get("security scan", "none").strip()
    if not command or command.lower() == "none" or command.startswith("<"):
        return True, None, "none"
    try:
        proc = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True,
                              timeout=SCAN_TIMEOUT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        return False, None, "the scan ran longer than %d seconds" % SCAN_TIMEOUT
    lines = (proc.stdout + "\n" + proc.stderr).splitlines()
    return proc.returncode == 0, proc.returncode, short([l for l in lines if l.strip()][-6:], 6)


def cmd_scan(root):
    ok, code, text = run_scan(root)
    if text == "none" and code is None and ok:
        print("scan: none configured")
        return 0
    print("scan: %s" % ("ok" if ok else "failed (exit %s)" % code if code is not None else "failed"))
    if text:
        print("  " + text.replace("\n", "\n  "))
    return 0 if ok else 1


PYCACHE = [":(exclude,glob)**/__pycache__/**", ":(exclude,glob)**/*.pyc"]


def stage(root, paths):
    for p in paths:
        if not os.path.exists(os.path.join(root, p)):
            continue
        if subprocess.run(["git", "check-ignore", "-q", "--", p], cwd=root).returncode == 0:
            continue
        # The *.pyc exclude makes git skip a file path in a subfolder, so a file gets no exclude.
        git(root, "add", "--", p, *([] if os.path.isfile(os.path.join(root, p)) else PYCACHE))


def dirty(root, paths):
    out = git(root, "status", "--porcelain", "--", *paths, *PYCACHE)
    return [l for l in out.splitlines() if l.strip()]


FINDING = re.compile(r"^\s*[-*]\s+\W*(major|minor)\W*[:\-]", re.M | re.I)


def open_findings(text, kind=None):
    """The finding lines of a review file, as their kinds (major or minor). `none` holds no line."""
    return [k.lower() for k in FINDING.findall(text or "") if kind is None or k.lower() == kind]


def slice_summary(block):
    parts = []
    story = get_field(block, "Story")
    reqs = get_field(block, "Requirements")
    if story and not story.startswith("<"):
        parts.append(story)
    if reqs:
        parts.append("Requirements: %s" % reqs)
    return "\n\n".join(parts)


def cmd_commit(root, sid, summary=""):
    text, _ = load_slices(root)
    sec = find(text, sid)
    block = text[sec[2]:sec[3]]
    title = sec[1]
    status, _ = status_of(block)
    if status in ("done", "stopped"):
        raise Fail("%s is %s: it cannot be committed" % (sid, status))
    results, _, _ = run_tests(root)
    mine = mine_of(root, results, sid)
    if not mine or any(r["status"] != "pass" for r in mine):
        raise Fail("%s: the tests fail or are missing. Run: slice.py test %s" % (sid, sid))
    broken = regressions(root, results)
    if broken:
        raise Fail("%s: %d tests outside the slice fail (tests of a done slice, or of no slice): %s" % (
            sid, len(broken), ", ".join(r["name"] for r in broken)))
    for name in ("review/%s.md" % sid, "review/%s.tests.md" % sid):
        major = open_findings(read(root, name), "major")
        if major:
            raise Fail("%s: %d open major finding(s) in %s" % (sid, len(major), shown(root, name)))
    ok, code, scan_text = run_scan(root)
    if not ok:
        raise Fail("%s: the security scan fails%s: %s. Run: slice.py scan" % (
            sid, " (exit %s)" % code if code is not None else "", scan_text.replace("\n", " | ")))
    cfg = config(root)
    body = summary.strip() or slice_summary(block)
    old = text
    write_status(root, sid, "done")
    try:
        stage(root, ["slice"] + folders(cfg.get("source folders")) + folders(cfg.get("unit tests folder"))
              + source_paths(root, cfg) + folders(cfg.get("tests folder")))
        args = ["commit", "-m", "Slice %s: %s" % (sid, title)]
        if body:
            args += ["-m", body]
        args += ["-m", "Slice: %s" % sid]
        git(root, *args)
    except Fail:
        write(root, "slices.md", old)
        raise
    print("%s committed: Slice %s: %s" % (sid, sid, title))
    return 0

def git(root, *args):
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if p.returncode:
        raise Fail("git %s failed: %s" % (args[0], (p.stderr or p.stdout).strip()))
    return p.stdout


def main(argv):
    global SPEC_ARG
    root_arg = None
    while len(argv) > 1 and argv[0] in ("--root", "--spec"):
        if argv[0] == "--root":
            root_arg = argv[1]
        else:
            SPEC_ARG = argv[1]
        argv = argv[2:]
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, args = argv[0], argv[1:]
    root = os.path.realpath(root_arg) if root_arg else find_root(os.getcwd())
    try:
        if cmd == "status" and not args:
            return cmd_status(root)
        if cmd == "next" and not args:
            return cmd_next(root)
        if root is None:
            raise Fail("no slice/ folder found", 2)
        if cmd == "set" and len(args) in (2, 4) and (len(args) == 2 or args[2] == "--reason"):
            return cmd_set(root, args[0], args[1], args[3] if len(args) == 4 else "")
        if cmd == "resume" and len(args) == 1:
            return cmd_resume(root, args[0])
        if cmd == "round" and len(args) == 2:
            return cmd_round(root, args[0], args[1])
        if cmd == "test" and len(args) in (1, 2) and (len(args) == 1 or args[1] == "--full"):
            return cmd_test(root, args[0], len(args) == 2 and args[1] == "--full")
        if cmd == "scan" and not args:
            return cmd_scan(root)
        if cmd == "commit" and len(args) in (1, 3) and (len(args) == 1 or args[1] == "--summary"):
            return cmd_commit(root, args[0], args[2] if len(args) == 3 else "")
    except Fail as e:
        print(e, file=sys.stderr)
        return e.code
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
