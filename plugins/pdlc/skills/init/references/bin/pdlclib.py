#!/usr/bin/env python3
"""Code that the pdlc scripts in this folder share.

A script imports this module with its own folder on the path:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import pdlclib

The functions read the text of a spec (`section`, `field`), find the spec that owns a
branch (`owner`), and read the trailers of a commit message (`trailers`, `last_block`).
The hooks of the plugin keep their own copies, because a hook runs from the plugin and not
from a project.

`classify_red` proves "red" for the tests stage (README "Checks before code"): it reads the
output of the checks command and says whether the checks fail only for the missing behaviour
of the change. `red_inputs` and `checks_command` read what it needs from the specs and config.
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


# ---------------------------------------------------------------------------------------
# Red: do the checks fail only because the behaviour of this change is missing?

ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ENTRY = re.compile(r"^- [^`\n]*`([^`\n]+)`(.*)$")
PROPOSED = re.compile(r"\s*\u00b7\s*proposed\b")

# The output formats. The first pattern that finds a line names the language.
LANGUAGES = [
    ("rust", r"^error(\[E\d+\])?: |^\s*Running |^test \S+ \.\.\. |^running \d+ tests?|^test result:|^\s*Compiling "),
    ("python", r"test session starts|collected \d+ item|ERROR collecting|_FailedTest|^Ran \d+ tests? in|"
               r"Failed to import test module|\.\.\. (?:ok|FAIL|ERROR)$"),
    ("clojure", r"^Testing \S|Ran \d+ tests containing|^(?:FAIL|ERROR) in \(|Syntax error|CompilerException|"
                r"Unable to resolve symbol|No such var|Could not locate \S+\.clj|Exception in thread"),
]
# A compile error that names a missing item: (language, pattern). Group 1 holds the name,
# or the backticked names of a list.
MISSING = [
    ("rust", r"cannot find [a-z ]+ `([^`]+)`"),
    ("rust", r"\bno [a-z ]*?named `([^`]+)`"),
    ("rust", r"\bno field `([^`]+)` on type"),
    ("rust", r"unresolved imports? ((?:`[^`]+`|,| and )+)"),
    ("rust", r"missing fields? ((?:`[^`]+`|,| and )+) in initializer"),
    ("rust", r"could not find `([^`]+)` in"),
    ("rust", r"use of undeclared (?:type|crate or module) `([^`]+)`"),
    ("python", r"NameError: name '([^']+)' is not defined"),
    ("python", r"AttributeError: .*?has no attribute '([^']+)'"),
    ("python", r"ImportError: cannot import name '([^']+)'"),
    ("python", r"ModuleNotFoundError: No module named '([^']+)'"),
    ("clojure", r"Unable to resolve (?:symbol|var): (\S+)"),
    ("clojure", r"No such (?:var|namespace): (\S+)"),
    ("clojure", r"Could not locate (\S+?)__init\.class"),
]
# Where a compile error starts, and where its block ends.
RUST_ERROR = re.compile(r"^error(?:\[E\d+\])?: ")
RUST_SUMMARY = re.compile(r"aborting due to|could not compile|build failed|test failed|didn't exit|failed to run")
BLOCKS = {
    "python": (r"^(?:_{3,} ERROR collecting|ERROR: .*_FailedTest)", r"^(?:_{3,} |={3,}|Ran \d+ tests?)"),
    "clojure": (r"^(?:Syntax error|Execution error|Unexpected error|Exception in thread)", None),
}
# One line per check in a run: named groups name, status, and (when the line gives it) file.
RESULTS = [
    r"^test (?P<name>\S+) \.\.\. (?P<status>ok|FAILED)$",
    r"^(?P<file>\S+?)::(?P<name>\S+) (?P<status>PASSED|FAILED|ERROR)\b",
    r"^(?P<status>FAILED|ERROR) (?P<file>\S+?)::(?P<name>\S+)",
    r"^(?P<name>\w+) \((?P<file>[\w.]+)\) \.\.\. (?P<status>ok|FAIL|ERROR)$",
    r"^(?P<status>FAIL|ERROR) in \((?P<name>[^)]+)\) \((?P<file>[^:)]+)",
]
FILE_CONTEXT = re.compile(r"^\s*(?:Running (?:unittests )?|Doc-tests |Testing )(?P<file>\S+)")


def checks_command(config_text):
    """The "all:" command of the "Checks" section of pdlc/config.md, or None when the line is
    not there or is still the placeholder."""
    found = re.search(r"^- all:\s*`([^`]+)`", section(config_text, "Checks"), re.M)
    command = found.group(1).strip() if found else ""
    return command if command and command != "..." else None


def red_run_command(command):
    """The checks command as `red` runs it. A plain `cargo test` stops compiling the other
    targets after the first target fails, so the classifier would see some errors only."""
    if re.match(r"cargo test(\s|$)", command) and "--no-fail-fast" not in command:
        return re.sub(r"^cargo test", "cargo test --no-fail-fast", command, count=1)
    return command


def _tail(name):
    """The last segment of a path-like name: "a::b::C" gives "C"."""
    parts = [p for p in re.split(r"::|/|\.", name.strip().strip("`'\"()")) if p]
    return parts[-1] if parts else ""


def _norm(name):
    return name.rstrip("!?").replace("-", "_")


def _idents(key):
    """The names that a compile error can use for an Interface entry: the last path segment
    of its head, and the field names of a `{ ... }` shape."""
    key = key.strip().lstrip("(`")
    names = {_tail(re.split(r"[\s({<\[]", key, maxsplit=1)[0])}
    brace = re.search(r"\{(.*)\}", key)
    if brace:
        names |= set(re.findall(r"([A-Za-z_][\w-]*)\s*:", brace.group(1)))
    return {_norm(n) for n in names if n}


def _interface(text):
    """[(key, marked proposed)] for each entry under "Interface"."""
    out = []
    for line in section(text, "Interface").splitlines():
        found = ENTRY.match(line)
        if found:
            out.append((" ".join(found.group(1).split()), bool(PROPOSED.search(line))))
    return out


def red_inputs(change_text, scope_text=""):
    """{"entries": [(key, proposed)], "reqs": [ID], "check_files": [path]} of a change spec.
    An entry is proposed when its line in the change, or its line in the scope spec, ends
    with the proposed mark. A requirement that retires is left out."""
    scope = {key for key, proposed in _interface(scope_text) if proposed}
    entries = [(key, proposed or key in scope) for key, proposed in _interface(change_text)]
    reqs = [m.group(1) for m in re.finditer(r"^### (\S+\.R\d+)\b(.*)$", section(change_text, "Requirements"), re.M)
            if "(retire)" not in m.group(2)]
    files = []
    for line in section(change_text, "Check files").splitlines():
        found = re.match(r"^- `?([^\s`]+)`?", line)
        if found and found.group(1) != "none":
            files.append(found.group(1))
    return {"entries": entries, "reqs": reqs, "check_files": files}


def _blocks(lang, text):
    """The compile errors of an output, one text for each, or None when the run compiled."""
    lines = text.splitlines()
    if lang == "rust":
        found = [l for l in lines if RUST_ERROR.match(l) and not RUST_SUMMARY.search(l)]
        return found or None
    if lang == "clojure" and re.search(r"Ran \d+ tests containing", text):
        return None
    start, end = BLOCKS[lang]
    blocks, current = [], None
    for line in lines:
        if re.search(start, line):
            current = [line]
            blocks.append(current)
        elif current is not None and end and re.search(end, line):
            current = None
        elif current is not None:
            current.append(line)
    if lang == "python" and not blocks and re.search(r"errors? during collection", text):
        return ["(the collection error is not in the output)"]
    return ["\n".join(b) for b in blocks] or None


def _in_files(file, check_files):
    if not file:
        return True
    flat = lambda p: re.sub(r"[/.\-_]+", "_", re.sub(r"\.(?:rs|py|clj[cs]?|js|ts|go|java|rb)$", "", p.strip())).lower()  # noqa: E731
    a = flat(file)
    for item in check_files:
        b = flat(item)
        if a == b or a.startswith(b + "_") or a.endswith("_" + b) or b.endswith("_" + a):
            return True
    return False


def _results(text):
    """[{name, file, ok}] for each check that the output lists."""
    found, context = {}, None
    for line in text.splitlines():
        ctx = FILE_CONTEXT.match(line)
        if ctx:
            context = ctx.group("file")
        for pattern in RESULTS:
            m = re.match(pattern, line)
            if m:
                d = m.groupdict()
                key = (d.get("file") or context, d["name"])
                ok = d["status"] in ("ok", "PASSED")
                found[key] = found.get(key, True) and ok
                break
    return [{"name": n, "file": f, "ok": ok} for (f, n), ok in found.items()]


def _names_in(lang, block):
    names = []
    for kind, pattern in MISSING:
        if kind == lang:
            for m in re.finditer(pattern, block):
                names += re.findall(r"`([^`]+)`", m.group(1)) or [m.group(1)]
    return names


def classify_red(entries, reqs, check_files, output, exit_code, allow_pass=()):
    """Is the run of the checks red? `entries` are (key, proposed) pairs of the "Interface"
    of the change, `reqs` its requirement IDs, `check_files` its "Check files", `output` the
    text of the checks command, and `exit_code` its exit code (None for a time-out).
    `allow_pass` lists requirements whose checks may pass (existing behaviour).

    Returns {"verdict", "evidence", "missing"}. The verdict is "red" (every new check fails,
    every other check passes), "red-compile" (the checks do not compile, and each error names
    a proposed entry; "missing" lists the names), "broken", or "unknown" (the format is not
    recognised)."""
    def done(verdict, evidence, missing=()):
        return {"verdict": verdict, "evidence": list(evidence), "missing": list(missing)}

    if exit_code is None:
        return done("broken", ["the checks passed the time limit, so a check is broken"])
    text = ANSI.sub("", output or "")
    lang = next((name for name, pattern in LANGUAGES if re.search(pattern, text, re.M)), None)
    if not lang:
        return done("unknown", ["the output format is not recognised (known: rust, python, clojure); "
                                "a person must read the output"])
    proposed = set()
    for key, mark in entries:
        if mark:
            proposed |= _idents(key)
    blocks = _blocks(lang, text)
    if blocks:
        missing, bad = [], []
        for block in blocks:
            names = _names_in(lang, block)
            head = block.splitlines()[0].strip()
            if not names:
                bad.append("a compile error names no missing item: %s" % head)
            for name in names:
                (missing if _norm(_tail(name)) in proposed else bad).append(
                    _tail(name) if _norm(_tail(name)) in proposed else
                    "%s is missing, but no proposed Interface entry has that name (%s)" % (_tail(name), head))
        if bad:
            return done("broken", bad)
        unique = list(dict.fromkeys(_tail(n) for n in missing))
        return done("red-compile", ["the checks do not compile; each error names a proposed entry: %s" % ", ".join(unique)], unique)
    results = _results(text)
    if not results:
        return done("unknown", ["the output has no result for any check, so the format is not recognised"])
    allowed = set(allow_pass)
    ids = {r: re.compile(r"(?<![a-z0-9])%s(?![0-9])" % re.escape(re.sub(r"[-.]", "_", r).lower())) for r in reqs}
    hits = lambda name: {r for r, rx in ids.items() if rx.search(re.sub(r"[-.]", "_", name).lower())}  # noqa: E731
    problems, failing = [], set()
    for res in results:
        hit = hits(res["name"])
        if res["ok"]:
            if hit - allowed:
                problems.append("the new check %s passes before the code (%s)" % (res["name"], ", ".join(sorted(hit - allowed))))
        elif not hit:
            problems.append("the existing check %s fails" % res["name"])
        elif not _in_files(res["file"], check_files):
            problems.append("the check %s fails, but its file %s is not in \"Check files\"" % (res["name"], res["file"]))
        else:
            failing |= hit
    problems += ["no check for %s fails" % r for r in reqs if r not in failing and r not in allowed]
    if problems:
        return done("broken", problems)
    fails = sum(not r["ok"] for r in results)
    return done("red", ["%d new checks fail and %d other checks pass" % (fails, len(results) - fails)])


def red_line(result, allow_pass=()):
    """The text of the "Red:" line that `pdlc.py red --record` writes in a change spec."""
    detail = "missing %s" % ", ".join(result["missing"]) if result["missing"] else result["evidence"][0]
    extra = "; may pass: %s" % ", ".join(allow_pass) if allow_pass else ""
    return "Red: %s; %s%s" % (result["verdict"], detail, extra)


def red_allowed(change_text):
    """The requirements that the "Red:" line of a change spec lets pass."""
    found = re.search(r"^Red:.*?may pass: ([^;\n]+)", change_text, re.M)
    return re.findall(r"[A-Z][A-Za-z]*-[\w-]*\.R\d+", found.group(1)) if found else []
