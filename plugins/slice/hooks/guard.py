#!/usr/bin/env python3
"""slice guard. Claude Code runs this before every file tool call and every Bash call.

The slice:implementer agent never sees the tests. It gets the run results from
`slice.py test`. This guard blocks the implementer on:
  - Read, Glob, Grep, Write, Edit, MultiEdit, and NotebookEdit on any path in the tests
    folder, and a Glob or Grep that can list the folder (a search from the project root).
  - a Bash command that names the tests folder, a shell wildcard that can match it, a
    recursive search from the project root, a git command that shows file content with no
    path limit, and the project's own test runner.
Every other agent, and the main session, is left alone. The check is by name, so a command
that builds the folder name at run time gets through. That is a known limit.

The project is the nearest folder that holds slice/config.md, found from the file first and
then from the working folder. The tests folders are the "tests folder:" line of the config
(default: test, tests, spec, __tests__). Exit 2 blocks the call.
Set SLICE_GUARD_LOG to a file path to log every decision.
"""
import fnmatch
import json
import os
import re
import shlex
import sys

READS = {"Read", "Glob", "Grep"}
WRITES = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DEFAULT_FOLDERS = ["test", "tests", "spec", "__tests__"]
AGENT = "slice:implementer"
HINT = "run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py test <Sn>` for the results"
RECURSIVE = {"find", "tree", "rg", "ag", "ack", "du", "fd", "grep", "egrep", "fgrep", "ls", "cp", "tar",
             "zip", "xargs"}
GIT_SHOWS = {"diff", "show", "log", "grep", "blame", "cat-file", "stash", "archive", "format-patch",
             "whatchanged", "difftool", "restore", "checkout"}


def project_root(path):
    path = os.path.realpath(path)
    while True:
        if os.path.isfile(os.path.join(path, "slice", "config.md")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def config_value(root, key):
    try:
        with open(os.path.join(root, "slice", "config.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    line = re.search(r"^- %s:\s*(.+)$" % re.escape(key), text, re.M | re.I)
    if not line:
        return None
    value = line.group(1)
    quoted = re.findall(r"`([^`]+)`", value)
    return ", ".join(quoted) if quoted else value.strip()


def test_folders(root):
    value = config_value(root, "tests folder")
    found = [f.strip(" `/") for f in (value or "").split(",") if f.strip(" `/")]
    return found or DEFAULT_FOLDERS


def test_command(root):
    return config_value(root, "test command") or ""


def under(path, top):
    return path == top or path.startswith(top + os.sep)


def hits(path, root, folders):
    """True when path is inside a tests folder, or can list one (a folder above it)."""
    for f in folders:
        top = os.path.realpath(os.path.join(root, f))
        if under(path, top) or under(top, path):
            return True
    return False


def inside(path, root, folders):
    return any(under(path, os.path.realpath(os.path.join(root, f))) for f in folders)


def expand_braces(pattern):
    found = re.search(r"\{([^{}]*)\}", pattern)
    if not found:
        return [pattern]
    head, tail = pattern[:found.start()], pattern[found.end():]
    return [p for part in found.group(1).split(",") for p in expand_braces(head + part + tail)]


def glob_folders(base, pattern):
    """The folders that a pattern can list: the part before the first wildcard, for each
    alternative."""
    out = []
    for alt in expand_braces(os.path.join(base, os.path.expanduser(pattern))):
        literal = re.split(r"[*?\[]", alt, maxsplit=1)[0]
        if literal != alt and not literal.endswith(os.sep):
            literal = os.path.dirname(literal)
        out.append(os.path.realpath(literal))
    return out


def file_decision(call, cwd, root, folders):
    tool, args = call.get("tool_name"), call.get("tool_input") or {}
    base = args.get("file_path") or args.get("notebook_path") or args.get("path") or cwd
    base = os.path.realpath(os.path.join(cwd, os.path.expanduser(base)))
    if tool == "Glob" and args.get("pattern"):
        paths = glob_folders(base, args["pattern"])
    elif tool == "Grep" and args.get("glob") and hits(base, root, folders) and not inside(base, root, folders):
        # A glob that starts with a folder narrows a search from above the tests.
        paths = glob_folders(base, args["glob"])
        if not all(re.match(r"[^*?\[{]+/", g) for g in expand_braces(args["glob"])):
            paths = [base]
    else:
        paths = [base]
    for path in paths:
        root_of = project_root(path) or root
        if hits(path, root_of, test_folders(root_of)):
            return False, "the implementer may not use the tests (%s): %s" % (os.path.relpath(path, root_of), HINT)
    return True, ""


def words(command):
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def runner_signature(command):
    tokens = [t for t in words(command) if not re.match(r"^[A-Za-z_]\w*=", t)]
    tokens = [t for t in tokens if "{" not in t]
    if not tokens:
        return ""
    sig = [tokens[0]]
    if len(tokens) > 1 and tokens[1] == "-m" and len(tokens) > 2:
        sig += tokens[1:3]
    elif len(tokens) > 1 and not tokens[1].startswith("-") and "/" not in tokens[1]:
        sig.append(tokens[1])
    return " ".join(sig)


def bash_decision(call, cwd, root, folders):
    command = (call.get("tool_input") or {}).get("command") or ""
    flat = " ".join(command.split())
    tops = [os.path.realpath(os.path.join(root, f)) for f in folders]
    for f in folders:
        pattern = r"(?<![\w.\-])" + r"/+".join(re.escape(p) for p in f.split("/")) + r"(?![\w.\-])"
        if re.search(pattern, command):
            return False, "the command names the tests folder (%s): %s" % (f, HINT)
    # A shell wildcard that can match a folder name, in a path word.
    for token in words(command):
        if re.search(r"[*?\[]", token):
            for part in token.replace("\\", "/").split("/"):
                if re.search(r"[*?\[]", part) and any(fnmatch.fnmatch(os.path.basename(f), part) and part not in "*"
                                                      for f in folders):
                    return False, "a wildcard in the command can match the tests folder: %s" % HINT
    sig = runner_signature(test_command(root))
    if sig and sig in flat:
        return False, "the implementer does not run the tests directly: %s" % HINT
    # Recursive search and git content commands, judged by where they point.
    segments = [s for s in re.split(r"\|\||&&|[|;&\n]", command) if s.strip()]
    here = cwd
    for seg in segments:
        toks = words(seg)
        toks = [t for t in toks if not re.match(r"^[A-Za-z_]\w*=", t)]
        if not toks:
            continue
        if toks[0] == "cd" and len(toks) > 1:
            here = os.path.realpath(os.path.join(here, os.path.expanduser(toks[1])))
            continue
        prog = os.path.basename(toks[0])
        args = [t for t in toks[1:] if not t.startswith("-")]
        paths = [os.path.realpath(os.path.join(here, os.path.expanduser(a))) for a in args
                 if not a.startswith("$") and not re.match(r"^[\w+]*$", a) or os.path.exists(os.path.join(here, a))]
        recursive = prog in RECURSIVE and (
            prog not in ("grep", "egrep", "fgrep", "ls", "cp", "tar", "zip", "xargs")
            or any(re.match(r"^-\w*[rR]|^--recursive|^-d$", t) for t in toks[1:] if t.startswith("-")))
        if recursive:
            targets = [p for p in paths if os.path.isdir(p)] or [here]
            if any(any(under(top, t) for top in tops) for t in targets):
                return False, "a recursive search from %s reaches the tests: name a source folder" % \
                    os.path.relpath(targets[0], root)
        if prog == "git" and len(toks) > 1:
            sub = next((t for t in toks[1:] if not t.startswith("-")), "")
            if sub in GIT_SHOWS:
                rest = toks[toks.index("--") + 1:] if "--" in toks else []
                limited = rest and all(not any(under(top, os.path.realpath(os.path.join(here, p)))
                                               or under(os.path.realpath(os.path.join(here, p)), top)
                                               for top in tops) for p in rest)
                if not limited:
                    return False, "git %s can show the tests: limit it with `-- <source folder>`" % sub
    return True, ""


def decide(call):
    """(allowed, reason) for one tool call."""
    tool = call.get("tool_name") or ""
    if call.get("agent_type") != AGENT or tool not in READS | WRITES | {"Bash"}:
        return True, ""
    cwd = os.path.realpath(call.get("cwd") or os.getcwd())
    args = call.get("tool_input") or {}
    probe = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    probe = os.path.realpath(os.path.join(cwd, os.path.expanduser(probe))) if probe else cwd
    root = project_root(probe) or project_root(cwd) or cwd
    folders = test_folders(root)
    if tool == "Bash":
        return bash_decision(call, cwd, root, folders)
    return file_decision(call, cwd, root, folders)


def main():
    try:
        call = json.load(sys.stdin)
    except ValueError:
        return 0
    allowed, reason = decide(call)
    log = os.environ.get("SLICE_GUARD_LOG")
    if log:
        try:
            with open(log, "a") as f:
                f.write(json.dumps({"agent": call.get("agent_type"), "tool": call.get("tool_name"),
                                    "input": call.get("tool_input"), "allowed": allowed,
                                    "reason": reason}) + "\n")
        except OSError:
            pass
    if not allowed:
        print("slice guard: " + reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
