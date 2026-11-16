#!/usr/bin/env python3
"""slice guard. Claude Code runs this before every file tool call and every Bash call.

Hiding is two-way. The slice:implementer agent never sees the tests: it gets the run results
from `slice.py test`. The slice:test-writer agent never sees the app code: it gets the call
forms from interface.md. The test writer also writes only in the tests folder. For the
implementer, this guard blocks:
  - Read, Glob, Grep, Write, Edit, MultiEdit, and NotebookEdit on any path in the tests
    folder, and a Glob or Grep that can list the folder (a search from the project root).
  - a Bash command that names the tests folder (in the raw text, or in a word after the
    shell removes quotes), a path that a symlink leads into it, a shell wildcard that can
    match it or list it, a recursive search from the project root, a git command that shows
    file content with no path limit, the configured test runner and every known runner
    (python, python3, and python3.X count the same), and any `slice.py` subcommand but `test`.
  - Write, Edit, MultiEdit, and NotebookEdit outside the source folders and the source files.
The source files are the "source files:" line of the config: single paths and globs, relative
to the project root (`package.json, migrations/**`; `*` stays in one folder, `**` crosses
folders). A path in the tests folder or in slice/ is never one of them.
For the test writer, the same rules hide the source folders ("source folders:" line of the
config; default: src, lib, app) and the source files, including the stubs. The runner is not
blocked for it.
Every other agent, and the main session, is left alone. The check is by name and by
resolved path, so a command that builds the folder name at run time gets through. That is a
known limit.

The project is the nearest folder that holds slice/config.md, found from the file first and
then from the working folder. The tests folders are the "tests folder:" line of the config
(default: test, tests, spec, __tests__). config.md stays at the top of slice/, so the hook
needs no spec folder (slice/NNN-<name>/). Exit 2 blocks the call.
Set SLICE_GUARD_LOG to a file path to log every decision.
"""
import fnmatch
import glob
import json
import os
import re
import shlex
import sys

READS = {"Read", "Glob", "Grep"}
WRITES = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
DEFAULT_FOLDERS = ["test", "tests", "spec", "__tests__"]
DEFAULT_SOURCES = ["src", "lib", "app"]
IMPLEMENTER = "slice:implementer"
TEST_WRITER = "slice:test-writer"
HINTS = {
    IMPLEMENTER: "run `python3 ${CLAUDE_PLUGIN_ROOT}/bin/slice.py test <Sn>` for the results",
    TEST_WRITER: "take the call forms from the interface.md of the spec folder",
}
RECURSIVE = {"find", "tree", "rg", "ag", "ack", "du", "fd", "grep", "egrep", "fgrep", "ls", "cp", "tar",
             "zip", "xargs", "rsync"}
# These recurse only with a flag. tar and rsync always recurse, and find and the rest too.
NO_DEFAULT = ("tar", "rsync", "zip", "cp")  # with no folder word, these read nothing from here
FLAGGED = ("grep", "egrep", "fgrep", "ls", "cp", "zip", "xargs")
# Test runners that the implementer may not start, with or without the configured command.
RUNNER_PROGRAMS = {"pytest", "py.test", "nose2", "nose", "tox", "jest", "vitest"}
RUNNER_MODULES = {"pytest", "unittest", "nose2", "nose", "tox"}
PACKAGE_MANAGERS = {"npm", "yarn", "pnpm"}
WRAPPERS = {"npx", "uvx", "uv", "poetry", "pipenv", "pipx", "run", "exec", "env", "sudo", "time", "nice",
            "command", "nohup", "xvfb-run"}
SHELLS = {"sh", "bash", "zsh", "dash"}
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


def source_folders(root):
    value = config_value(root, "source folders")
    found = [f.strip(" `/") for f in (value or "").split(",") if f.strip(" `/")]
    return found or DEFAULT_SOURCES


def source_files(root):
    value = config_value(root, "source files")
    found = [f.strip(" `/") for f in (value or "").split(",") if f.strip(" `/")]
    return [f for f in found if f != "none" and not f.startswith("<")]


def glob_regex(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def barred(rel, root):
    """True for a path inside slice/ or a tests folder: no source-files pattern opens it."""
    return any(rel == b or rel.startswith(b + "/") for b in ["slice"] + test_folders(root))


def source_file_match(path, root):
    """True when the resolved path is one of the `source files:` of the config."""
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    if rel == "." or rel.startswith("..") or barred(rel, root):
        return False
    return any(glob_regex(p).match(rel) for p in source_files(root))


def source_file_folders(root):
    """The folders (or single paths) that the source files name before any wildcard."""
    out = []
    for p in source_files(root):
        literal = re.split(r"[*?\[]", p, maxsplit=1)[0]
        entry = p if literal == p else literal.rsplit("/", 1)[0] if "/" in literal else ""
        if entry and not barred(entry, root):
            out.append(entry)
    return out


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


def hidden_folders(agent, root):
    return test_folders(root) if agent == IMPLEMENTER else source_folders(root) + source_file_folders(root)


def label(agent):
    return "implementer" if agent == IMPLEMENTER else "test writer"


def what(agent):
    return "tests" if agent == IMPLEMENTER else "app code"


def file_decision(call, cwd, root, folders, agent=IMPLEMENTER):
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
        hidden = hidden_folders(agent, root_of)
        if hits(path, root_of, hidden) or (agent == TEST_WRITER and source_file_match(path, root_of)):
            return False, "the %s may not use the %s (%s): %s" % (
                label(agent), what(agent), os.path.relpath(path, root_of), HINTS[agent])
    if tool in WRITES:
        allowed = test_folders(root) if agent == TEST_WRITER else source_folders(root)
        if not inside(base, root, allowed) and not (agent == IMPLEMENTER and source_file_match(base, root)):
            return False, "the %s writes only in the %s folders (%s): %s" % (
                label(agent), "tests" if agent == TEST_WRITER else "source", os.path.relpath(base, root),
                HINTS[agent])
    return True, ""


def words(command):
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def split_flags(tokens):
    """Write a joined flag as two words: `-munittest` becomes `-m unittest`."""
    out = []
    for t in tokens:
        m = re.match(r"^-m([A-Za-z_][\w.]*)$", t)
        out += ["-m", m.group(1)] if m else [t]
    return out


def runner_signature(command):
    tokens = [t for t in split_flags(words(command)) if not re.match(r"^[A-Za-z_]\w*=", t)]
    tokens = [t for t in tokens if "{" not in t]
    if not tokens:
        return ""
    sig = [tokens[0]]
    if len(tokens) > 1 and tokens[1] == "-m" and len(tokens) > 2:
        sig += tokens[1:3]
    elif len(tokens) > 1 and not tokens[1].startswith("-") and "/" not in tokens[1]:
        sig.append(tokens[1])
    return " ".join(sig)


def is_python(program):
    return re.match(r"^python[\d.]*$", os.path.basename(program)) is not None


def starts_runner(tokens, depth=0):
    """True when one command (a list of words) starts a known test runner."""
    toks = [t for t in split_flags(tokens) if not re.match(r"^[A-Za-z_]\w*=", t)]
    while toks and (os.path.basename(toks[0]) in WRAPPERS):
        toks = toks[1:]
    if not toks:
        return False
    prog = os.path.basename(toks[0])
    rest = [t for t in toks[1:] if not t.startswith("-")]
    if prog in RUNNER_PROGRAMS:
        return True
    if is_python(prog):
        module = toks[toks.index("-m") + 1] if "-m" in toks[:-1] else ""
        return module.split(".")[0] in RUNNER_MODULES
    if prog == "make":
        return bool(rest) and rest[0] in ("test", "tests", "check")
    if prog in PACKAGE_MANAGERS:
        return bool(rest) and (rest[0] in ("test", "t") or rest[:2] in (["run", "test"], ["run-script", "test"]))
    if prog in ("go", "cargo"):
        return bool(rest) and rest[0] == "test"
    if prog in SHELLS and "-c" in toks[:-1] and depth < 3:
        inner = toks[toks.index("-c") + 1]
        return any(starts_runner(words(seg), depth + 1) for seg in re.split(r"\|\||&&|[|;&\n]", inner)
                   if seg.strip())
    return False


def names_folder(text, folders):
    for f in folders:
        pattern = r"(?<![\w.\-])" + r"/+".join(re.escape(p) for p in f.split("/")) + r"(?![\w.\-])"
        if re.search(pattern, text):
            return f
    return None


def wildcard_hit(token, here, root, folders, files=False):
    """True when a shell wildcard in a word can match, or list, a hidden folder."""
    for alt in expand_braces(token.replace("\\", "/") if "/" in token else token):
        parts = alt.split("/")
        wild = [i for i, part in enumerate(parts) if re.search(r"[*?\[]", part)]
        if not wild:
            continue
        first = wild[0]
        literal = "/".join(parts[:first]) or ("/" if alt.startswith("/") else ".")
        folder = os.path.realpath(os.path.join(here, os.path.expanduser(literal)))
        if inside(folder, root, folders):
            return True
        if parts[first] == "*" and hits(folder, root, folders):
            return True
        if any(fnmatch.fnmatch(os.path.basename(f), parts[first]) and parts[first] != "*" for f in folders
               if os.path.dirname(os.path.join(root, f)) == folder or "/" not in f):
            return True
        for found in glob.glob(os.path.join(here, os.path.expanduser(alt)))[:500]:
            if inside(os.path.realpath(found), root, folders) or (
                    files and source_file_match(os.path.realpath(found), root)):
                return True
    return False


def path_args(toks, here):
    """The words of one command that look like paths: they hold a slash or a dot, or they exist."""
    out = []
    for t in toks:
        if t.startswith("-") and "=" in t:
            t = t.split("=", 1)[1]
        t = re.sub(r"^[<>]+", "", t)
        if not t or t.startswith(("-", "$")) or re.search(r"[*?\[{]", t):
            continue
        if "/" in t or "." in t or os.path.lexists(os.path.join(here, os.path.expanduser(t))):
            out.append(t)
    return out


def bash_decision(call, cwd, root, folders, agent=IMPLEMENTER):
    command = (call.get("tool_input") or {}).get("command") or ""
    flat = " ".join(command.split())
    hint, noun = HINTS[agent], what(agent)
    tops = [os.path.realpath(os.path.join(root, f)) for f in folders]
    tokens = words(command)
    # The folder name, in the raw text and in each word after the shell removes quotes.
    found = names_folder(command, folders) or next(
        (n for n in (names_folder(t, folders) for t in tokens) if n), None)
    if found:
        return False, "the command names the %s folder (%s): %s" % (noun, found, hint)
    # A shell wildcard that can match or list a hidden folder, in a path word.
    for token in tokens:
        if re.search(r"[*?\[]", token) and wildcard_hit(token, cwd, root, folders, agent == TEST_WRITER):
            return False, "a wildcard in the command can match or list the %s folder: %s" % (noun, hint)
    if agent == IMPLEMENTER:
        sig = runner_signature(test_command(root))
        normal = " ".join(split_flags(tokens))
        normal = re.sub(r"(?<![\w.\-])(?:[\w./-]*/)?python[\d.]*(?![\w.\-])", "python", normal)
        flat_py = re.sub(r"(?<![\w.\-])(?:[\w./-]*/)?python[\d.]*(?![\w.\-])", "python", flat)
        sig = re.sub(r"^(?:[\w./-]*/)?python[\d.]*", "python", sig)
        if sig and (sig in flat_py or sig in normal):
            return False, "the implementer does not run the tests directly: %s" % hint
    # Paths, recursive search, and git content commands, judged by where they point.
    segments = [s for s in re.split(r"\|\||&&|[|;&\n]", command) if s.strip()]
    here = cwd
    if inside(here, root, folders):
        return False, "the working folder is the %s folder: %s" % (noun, hint)
    for seg in segments:
        toks = words(seg)
        toks = [t for t in toks if not re.match(r"^[A-Za-z_]\w*=", t)]
        if not toks:
            continue
        if toks[0] == "cd" and len(toks) > 1:
            here = os.path.realpath(os.path.join(here, os.path.expanduser(toks[1])))
            if inside(here, root, folders):
                return False, "cd leads into the %s folder: %s" % (noun, hint)
            continue
        prog = os.path.basename(toks[0])
        if agent == IMPLEMENTER and starts_runner(toks):
            return False, "the implementer does not run the tests directly: %s" % hint
        if agent == IMPLEMENTER and any(os.path.basename(t) == "slice.py" for t in toks):
            after = toks[[os.path.basename(t) for t in toks].index("slice.py") + 1:]
            sub = []
            skip = False
            for t in after:
                if skip:
                    skip = False
                elif t in ("--root", "--spec"):
                    skip = True
                elif not t.startswith("-"):
                    sub.append(t)
                    break
            if sub != ["test"]:
                return False, "the implementer runs only `slice.py test`: %s" % hint
        if not any(os.path.basename(t) == "slice.py" for t in toks):
            for a in path_args(toks if "/" in toks[0] else toks[1:], here):
                target = os.path.realpath(os.path.join(here, os.path.expanduser(a)))
                if inside(target, root, folders) or (agent == TEST_WRITER and source_file_match(target, root)):
                    return False, "a path in the command leads into the %s folder (%s): %s" % (noun, a, hint)
        args = [t for t in toks[1:] if not t.startswith("-")]
        paths = [os.path.realpath(os.path.join(here, os.path.expanduser(a))) for a in args
                 if not a.startswith("$") and not re.match(r"^[\w+]*$", a) or os.path.exists(os.path.join(here, a))]
        recursive = prog in RECURSIVE and (
            prog not in FLAGGED
            or any(re.match(r"^-\w*[rR]|^--recursive|^-d$", t) for t in toks[1:] if t.startswith("-")))
        if recursive:
            targets = [p for p in paths if os.path.isdir(p)] or ([] if prog in NO_DEFAULT else [here])
            if any(any(under(top, t) for top in tops) for t in targets):
                return False, "a recursive search from %s reaches the %s: name another folder" % (
                    os.path.relpath(targets[0], root), noun)
        if prog == "git" and len(toks) > 1:
            sub = next((t for t in toks[1:] if not t.startswith("-")), "")
            if sub in GIT_SHOWS:
                rest = toks[toks.index("--") + 1:] if "--" in toks else []
                limited = rest and all(not any(under(top, os.path.realpath(os.path.join(here, p)))
                                               or under(os.path.realpath(os.path.join(here, p)), top)
                                               for top in tops) for p in rest)
                if not limited:
                    return False, "git %s can show the %s: limit it with `-- <folder>`" % (sub, noun)
    return True, ""


def decide(call):
    """(allowed, reason) for one tool call."""
    tool = call.get("tool_name") or ""
    agent = call.get("agent_type")
    if agent not in HINTS or tool not in READS | WRITES | {"Bash"}:
        return True, ""
    cwd = os.path.realpath(call.get("cwd") or os.getcwd())
    args = call.get("tool_input") or {}
    probe = args.get("file_path") or args.get("notebook_path") or args.get("path") or ""
    probe = os.path.realpath(os.path.join(cwd, os.path.expanduser(probe))) if probe else cwd
    root = project_root(probe) or project_root(cwd) or cwd
    folders = hidden_folders(agent, root)
    if tool == "Bash":
        return bash_decision(call, cwd, root, folders, agent)
    return file_decision(call, cwd, root, folders, agent)


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
