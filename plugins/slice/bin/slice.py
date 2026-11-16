#!/usr/bin/env python3
"""slice: the state, test, and commit script of the slice plugin.

Usage: slice.py [--root DIR] status
       slice.py [--root DIR] set Sn STATUS [--reason TEXT]
       slice.py [--root DIR] round Sn test|review
       slice.py [--root DIR] test Sn [--red]
       slice.py [--root DIR] commit Sn

The records are in slice/ at the project root: config.md, spec.md, slices.md, interface.md,
and review/Sn.md (the findings of the reviewer). The script keeps the round counts in
slices.md.

"test" prints test names, pass or fail, and failure messages. It never prints test source.
Exit 0: ok. Exit 1: a refusal or a failing check. Exit 2: usage or record error.
"""
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

STATUSES = ["planned", "red", "building", "review", "done", "stopped"]
LIMITS = {"test": 5, "review": 3}
FIELDS = {"test": "Test rounds", "review": "Review rounds"}
USAGE = __doc__.split("\n\n")[0]
TIMEOUT = 600
UNIMPLEMENTED = re.compile(r"not\s*(yet\s*)?implemented|unimplemented|NotImplemented", re.I)


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


def read(root, name):
    try:
        with open(os.path.join(root, "slice", name), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def write(root, name, text):
    path = os.path.join(root, "slice", name)
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
    return [f.strip(" /") for f in (value or "").split(",") if f.strip(" /")]


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
        raise Fail("slice/slices.md is missing", 2)
    return text, sections(text)


def find(text, sid):
    for s in sections(text):
        if s[0] == sid:
            return s
    raise Fail("no slice %s in slice/slices.md" % sid, 2)


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

def cmd_status(root):
    if root is None:
        print("no slice/ folder")
        print("next: spec")
        return 0
    spec = spec_status(root)
    has_interface = read(root, "interface.md") is not None
    text = read(root, "slices.md")
    slices = sections(text) if text else []
    print("spec: %s" % spec)
    print("interface: %s" % ("present" if has_interface else "missing"))
    rows = []
    for sid, title, start, end in slices:
        block = text[start:end]
        status, reason = status_of(block)
        rows.append((sid, status, reason))
        extra = " (%s)" % reason if reason else ""
        print("%s %s%s  %s  [test rounds %s/%d, review rounds %s/%d]" % (
            sid, status, extra, title, get_field(block, "Test rounds") or 0, LIMITS["test"],
            get_field(block, "Review rounds") or 0, LIMITS["review"]))
    if spec != "ratified":
        nxt = "spec"
    elif not slices:
        nxt = "plan"
    else:
        stopped = [r for r in rows if r[1] == "stopped"]
        planned = [r for r in rows if r[1] == "planned"]
        open_ = [r for r in rows if r[1] not in ("done", "stopped")]
        if stopped:
            nxt = "ask the user about %s" % stopped[0][0]
        elif planned or not has_interface:
            nxt = "interface"
        elif open_:
            nxt = "build %s" % open_[0][0]
        else:
            nxt = "all slices done"
    print("next: %s" % nxt)
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


def belongs(name, sid):
    """True when the test name holds the slice ID as a whole (S1 matches test_S1_x, not S10)."""
    n = sid[1:]
    return bool(re.search(r"(?<![0-9A-Za-z])[Ss]%s(?![0-9])|(?<=[a-z])S%s(?![0-9])" % (n, n), name))


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


def parse_unittest(output):
    lines = output.splitlines()
    results, pending = [], None
    for line in lines:
        if pending is not None and unittest_status(line):
            results.append({"name": pending, "status": unittest_status(line), "message": ""})
            pending = None
            continue
        m = STATUS_LINE.match(line)
        if m and not line.startswith("="):
            st = unittest_status(m.group(2))
            if st:
                results.append({"name": m.group(1), "status": st, "message": ""})
                pending = None
            else:
                pending = m.group(1)
    i = 0
    while i < len(lines):
        head = BLOCK_HEAD.match(lines[i])
        if head and i > 0 and lines[i - 1].startswith("=" * 10):
            j = i + 2
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
                                  capture_output=True, text=True, timeout=TIMEOUT)
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


def cmd_test(root, sid, red):
    text, _ = load_slices(root)
    find(text, sid)
    results, code, errors = run_tests(root)
    mine = [r for r in results if belongs(r["name"], sid)]
    if not mine:
        print("no tests found for %s" % sid)
        for line in errors:
            print("  " + line)
        if red:
            for r in results:
                if r["status"] == "error":
                    print("broken: %s" % r["name"])
                    print("  " + r["message"].replace("\n", "\n  "))
        return 1
    if not red:
        passed = sum(1 for r in mine if r["status"] == "pass")
        print("%s: %d tests, %d passed, %d not passed" % (sid, len(mine), passed, len(mine) - passed))
        for r in mine:
            show(r)
        return 0 if passed == len(mine) else 1
    bad, red_count = [], 0
    for r in mine:
        if r["status"] == "pass":
            bad.append("passes already: %s" % r["name"])
        elif r["status"] == "skip":
            bad.append("skipped: %s" % r["name"])
        elif r["status"] == "error" and not UNIMPLEMENTED.search(r["message"]):
            bad.append("broken: %s\n  %s" % (r["name"], r["message"].replace("\n", "\n  ")))
        else:
            red_count += 1
    # An error that no slice ID names, for example a test file that does not import.
    for r in results:
        if r["status"] == "error" and not re.search(r"(?<![0-9A-Za-z])[Ss]\d+(?![0-9])", r["name"]) \
                and not UNIMPLEMENTED.search(r["message"]):
            bad.append("broken: %s\n  %s" % (r["name"], r["message"].replace("\n", "\n  ")))
    if bad:
        print("%s not red: %d of %d tests fail for missing behaviour" % (sid, red_count, len(mine)))
        for b in bad:
            print(b)
        return 1
    print("%s red: %d tests fail for missing behaviour" % (sid, red_count))
    for r in mine:
        print("RED %s" % r["name"])
    return 0


def cmd_commit(root, sid):
    text, _ = load_slices(root)
    sec = find(text, sid)
    block = text[sec[2]:sec[3]]
    title = sec[1]
    status, _ = status_of(block)
    if status in ("done", "stopped"):
        raise Fail("%s is %s: it cannot be committed" % (sid, status))
    results, _, _ = run_tests(root)
    mine = [r for r in results if belongs(r["name"], sid)]
    if not mine or any(r["status"] != "pass" for r in mine):
        raise Fail("%s: the tests fail or are missing. Run: slice.py test %s" % (sid, sid))
    review = read(root, "review/%s.md" % sid) or ""
    major = re.findall(r"^\s*[-*]\s+\W*major\W*[:\-]", review, re.M | re.I)
    if major:
        raise Fail("%s: %d open major finding(s) in slice/review/%s.md" % (sid, len(major), sid))
    cfg = config(root)
    paths = ["slice"] + folders(cfg.get("tests folder")) + folders(cfg.get("source folders"))
    paths = [p for p in paths if os.path.exists(os.path.join(root, p))]
    old = text
    write_status(root, sid, "done")
    try:
        for p in paths:
            ignored = subprocess.run(["git", "check-ignore", "-q", "--", p], cwd=root).returncode == 0
            if not ignored:
                git(root, "add", "--", p)
        git(root, "commit", "-m", "Slice %s: %s" % (sid, title), "-m", "Slice: %s" % sid)
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
    root_arg = None
    if argv[:1] == ["--root"] and len(argv) > 1:
        root_arg, argv = argv[1], argv[2:]
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    cmd, args = argv[0], argv[1:]
    root = os.path.realpath(root_arg) if root_arg else find_root(os.getcwd())
    try:
        if cmd == "status" and not args:
            return cmd_status(root)
        if root is None:
            raise Fail("no slice/ folder found", 2)
        if cmd == "set" and len(args) in (2, 4) and (len(args) == 2 or args[2] == "--reason"):
            return cmd_set(root, args[0], args[1], args[3] if len(args) == 4 else "")
        if cmd == "round" and len(args) == 2:
            return cmd_round(root, args[0], args[1])
        if cmd == "test" and len(args) in (1, 2) and (len(args) == 1 or args[1] == "--red"):
            return cmd_test(root, args[0], len(args) == 2)
        if cmd == "commit" and len(args) == 1:
            return cmd_commit(root, args[0])
    except Fail as e:
        print(e, file=sys.stderr)
        return e.code
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
