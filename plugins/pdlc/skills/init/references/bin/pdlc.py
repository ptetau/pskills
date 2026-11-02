#!/usr/bin/env python3
"""Write the structured outputs of pdlc: commits, handoffs, header fields, and specs.

Usage: python3 pdlc/bin/pdlc.py <subcommand> [options]

Subcommands: commit, message, handoff, stop, set, intent, change.

Exit codes, for every subcommand:
  0  done
  1  a contract problem (one line for each problem, and nothing written)
  2  a usage error
  3  a git error
  4  not a pdlc project

Each subcommand is registered here and answers "not implemented" until its code is added
to HANDLERS.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # do not leave a __pycache__ in pdlc/bin of the project
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pdlclib  # noqa: E402

EXIT_DONE, EXIT_CONTRACT, EXIT_USAGE, EXIT_GIT, EXIT_NOT_PROJECT = 0, 1, 2, 3, 4

SUBCOMMANDS = {
    "commit": "make a pdlc commit with its subject and one trailer block",
    "message": "print the message of a pdlc commit, and make no commit",
    "handoff": "write the handoff of a stage",
    "stop": "write a stop record and commit it",
    "set": "set header fields and statuses of an intent or a change",
    "intent": "make a new intent, or change the lists of an intent",
    "change": "make the spec of a new change",
}


class Problem(Exception):
    """A contract problem: exit 1, one line for each problem, and nothing written."""

    def __init__(self, *lines):
        super().__init__("; ".join(lines))
        self.lines = list(lines)


class Usage(Exception):
    """A usage error: exit 2."""


class GitError(Exception):
    """A git command failed: exit 3."""


class NotProject(Exception):
    """The folder is not in a pdlc project: exit 4."""


# ---------------------------------------------------------------------------------------
# Shared helpers

def project(path=None):
    """The root of the pdlc project that holds the current folder."""
    root = pdlclib.project_root(path or os.getcwd())
    if not root:
        raise NotProject("not a pdlc project (no pdlc/config.md above %s)" % (path or os.getcwd()))
    return Path(root)


def run_git(root, *args, stdin=None, check=True):
    try:
        done = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                              input=stdin, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        raise GitError("git %s: %s" % (" ".join(args), error))
    if check and done.returncode != 0:
        raise GitError("git %s failed: %s" % (" ".join(args), (done.stderr or done.stdout).strip()))
    return done


def read_json(source):
    """The JSON object from a file, or from standard input when the source is "-"."""
    if source == "-":
        if sys.stdin.isatty():
            raise Usage("--json - needs the JSON on standard input (a heredoc or a pipe)")
        text = sys.stdin.read()
    else:
        try:
            text = Path(source).read_text()
        except OSError as error:
            raise Usage("cannot read %s: %s" % (source, error))
    try:
        data = json.loads(text)
    except ValueError as error:
        raise Usage("the JSON is not valid, line %s: %s" % (getattr(error, "lineno", "?"),
                                                           getattr(error, "msg", error)))
    if not isinstance(data, dict):
        raise Usage("the JSON must be an object")
    return data


def find_intent(root, intent_id):
    found = sorted((root / "pdlc" / "inbox").glob(intent_id + "-*.md"))
    plain = root / "pdlc" / "inbox" / (intent_id + ".md")
    if plain.exists():
        found.append(plain)
    if not found:
        raise Problem("%s: no intent file in pdlc/inbox/" % intent_id)
    return found[0]


def find_change(root, change_id):
    found = sorted((root / "pdlc" / "changes").glob(change_id + "-*/change.md"))
    if not found:
        raise Problem("%s: no change.md in pdlc/changes/%s-*/" % (change_id, change_id))
    return found[0]


def spec_file(root, spec_id):
    folder = {"JOB": "jobs", "CAP": "capabilities", "DES": "design"}.get(spec_id.split("-", 1)[0])
    path = root / "pdlc" / "specs" / (folder or "") / (spec_id + ".md")
    if not folder or not path.exists():
        raise Problem("%s: no spec file %s" % (spec_id, path.relative_to(root).as_posix()))
    return path


def title_name(text):
    """The name in the title line "# IN-0001 · Password reset"."""
    first = text.strip().splitlines()[0] if text.strip() else ""
    return re.sub(r"^#\s*\S+\s*[·:-]?\s*", "", first).strip()


def current_branch(root):
    branch = run_git(root, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    return branch if branch and branch != "HEAD" else None


# ---------------------------------------------------------------------------------------
# commit and message

# kind -> (what the ID is, subject format). {id} is the ID, {text} is --text, {name} is the
# intent name, {names} the change names of the intent, and {n} the number of the round.
KINDS = {
    "specify": ("IN", "Specify {id}: {name}"),
    "ready": ("IN", "Ready {id}: {name}"),
    "plan": ("IN", "Plan {id}: {names}"),
    "acceptance": ("IN", "Acceptance {id}"),
    "lock-acceptance": ("IN", "Lock acceptance {id}"),
    "review-acceptance": ("IN", "Review acceptance {id}"),
    "acceptance-reviewed": ("IN", "Acceptance reviewed {id}"),
    "convention": ("DES", "Convention {id}"),
    "start": ("CH", "Start {id}"),
    "tests": ("CH", "Tests {id}"),
    "lock-tests": ("CH", "Lock tests {id}"),
    "review-tests": ("CH", "Review tests {id}"),
    "tests-reviewed": ("CH", "Tests reviewed {id}"),
    "build": ("CH", "Build {id}: {text}"),
    "built": ("CH", "Built {id}"),
    "visual-review": ("CH", "Visual review {id}"),
    "verify": ("CH", "Verify {id}: round {n}"),
    "send-back": ("CH", "Send back {id}: {text}"),
    "verified": ("CH", "Verified {id}"),
    "propose": ("CH", "Propose {id}"),
    "update": ("IN|CH", "Update {id}: {text}"),
    "stop": ("IN|CH", "Stop {id}: {text}"),
    "setup": (None, "Set up pdlc"),
    "upgrade": (None, "Upgrade pdlc"),
    "board": (None, "Board: record card keys"),
}
NEEDS_TEXT = ("build", "send-back", "update", "stop")
ID_FORMS = {"IN": r"IN-\d+", "CH": r"CH-\d+", "DES": r"DES-[a-z0-9-]+"}
PLACEHOLDERS = {"<change>": r"CH-\d+", "<intent>": r"IN-\d+", "<n>": r"\d+",
                "<design spec>": r"DES-[a-z0-9-]+"}
TRAILER_LINE = pdlclib.TRAILER_LINE
DES_TRAILERS = Path("pdlc") / "specs" / "design" / "DES-pdlc-commit-trailers.md"


def subject_shapes(root):
    """(shape, regex) for each subject under "Subjects" in the project's copy of
    DES-pdlc-commit-trailers. [] when the project has no copy."""
    try:
        text = (root / DES_TRAILERS).read_text()
    except OSError:
        return []
    out = []
    for line in pdlclib.section(text, "Subjects").splitlines():
        if not line.lstrip().startswith("- "):
            continue
        for shape in re.findall(r"`([^`]+)`", line):
            parts = re.split(r"(<[^>]+>)", shape)
            regex = "".join(PLACEHOLDERS.get(p, ".+") if p.startswith("<") else re.escape(p)
                            for p in parts if p)
            out.append((shape, re.compile("^%s$" % regex)))
    return out


def owner_of_branch(root):
    branch = current_branch(root)
    return pdlclib.owner(root, branch) if branch else None


def intent_of(root, id_):
    """The intent ID for an IN or CH ID."""
    if id_.startswith("IN-"):
        find_intent(root, id_)
        return id_
    value = pdlclib.field(find_change(root, id_).read_text(), "Intent")
    if not value or value == "none":
        raise Problem("%s: change.md has no Intent field" % id_)
    return value


def header_ticket(root, id_):
    path = find_intent(root, id_) if id_.startswith("IN-") else find_change(root, id_)
    value = pdlclib.field(path.read_text(), "Ticket")
    return None if not value or value.lower() == "none" else value


def change_names(root, intent_id):
    """The short names of the changes in the "Changes" list of the intent, joined."""
    text = pdlclib.section(find_intent(root, intent_id).read_text(), "Changes")
    names = []
    for line in text.splitlines():
        found = re.search(r"\b(CH-\d+)\b(.*)$", line)
        if not found:
            continue
        name = re.sub(r"^[\s·:()—–-]+", "", found.group(2)).split(" · ")[0].strip(" .()")
        names.append(name or found.group(1))
    if not names:
        raise Problem("%s: the Changes list names no change" % intent_id)
    return ", ".join(names)


def check_order(root, intent_id):
    """Run check_order.py for the intent. A problem stops the commit."""
    done = subprocess.run([sys.executable, str(HERE / "check_order.py"), intent_id], cwd=str(root),
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise Problem(*(["check_order.py found a problem with the order of the changes:"]
                        + [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]))


def round_number(root, change_id):
    subjects = run_git(root, "log", "--format=%s", check=False).stdout.splitlines()
    done = [s for s in subjects if re.fullmatch(r"Verify %s: round \d+" % re.escape(change_id), s)]
    return len(done) + 1


def check_trailer_text(lines):
    """Check each --trailer or pdlc.trailer line. Return them without empty lines."""
    out = []
    for raw in lines:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            found = TRAILER_LINE.match(line)
            if not found:
                raise Problem('trailer "%s" is not in the form "Key: value"' % line)
            if found.group(1) in pdlclib.PDLC_TRAILERS + ("Review",):
                raise Problem('trailer "%s": pdlc writes %s itself' % (line, found.group(1)))
            out.append(line)
    return out


def extra_trailers(root, args):
    config = run_git(root, "config", "--get-all", "pdlc.trailer", check=False).stdout.splitlines()
    lines = check_trailer_text(list(args.trailer or []) + config)
    return list(dict.fromkeys(lines))


def build_message(root, args, files=None):
    """(subject, full message). `files` are the files of the commit, or None to leave out
    the check of Req against the files."""
    idtype, form = KINDS[args.kind]
    id_ = args.id
    if idtype is None:
        if id_:
            raise Usage("%s takes no ID" % args.kind)
    else:
        if not id_:
            raise Usage("%s needs an ID (%s)" % (args.kind, idtype.replace("|", " or ")))
        if not any(re.fullmatch(ID_FORMS[t], id_) for t in idtype.split("|")):
            raise Usage("%s needs an ID like %s, not %s" % (args.kind, idtype.replace("|", " or "), id_))
    if args.kind in NEEDS_TEXT and not args.text:
        raise Problem("%s needs --text, the words after the colon of the subject" % args.kind)
    values = {"id": id_, "text": args.text}
    if args.kind in ("specify", "ready"):
        values["name"] = title_name(find_intent(root, id_).read_text())
    if args.kind == "plan":
        values["names"] = change_names(root, id_)
        if files is not None:
            check_order(root, id_)
    if args.kind == "verify":
        values["n"] = round_number(root, id_)
    subject = form.format(**values)
    listed = subject_shapes(root)
    if listed and not any(regex.match(subject) for _, regex in listed):
        raise Problem('the subject "%s" is not one of these in %s: %s' % (
            subject, DES_TRAILERS.as_posix(), ", ".join("`%s`" % shape for shape, _ in listed)))

    pdlc = []
    if idtype is not None:
        found = owner_of_branch(root)
        if id_.startswith("CH-"):
            find_change(root, id_)
            if found and found[0] == "change" and found[1] != id_:
                raise Problem("%s is not the change of this branch (%s): switch to its branch"
                              % (id_, found[1]))
        intent = args.intent or (intent_of(root, id_) if id_[:3] in ("IN-", "CH-") else None)
        if not intent and found:
            intent = intent_of(root, found[1])
        if not intent:
            raise Problem("%s needs --intent, the intent that asks for it" % args.kind)
        change = id_ if id_.startswith("CH-") else (found[1] if found and found[0] == "change" else None)
        pdlc.append("Intent: %s" % intent)
        if change:
            pdlc.append("Change: %s" % change)
        req = [r.strip() for item in (args.req or []) for r in item.split(",") if r.strip()]
        if files is not None:
            outside = [f for f in files if not f.startswith("pdlc/")]
            if outside and not req:
                raise Problem("the commit changes %s, outside pdlc/, so it needs --req with the "
                              "requirement IDs" % outside[0])
            if files and not outside and req:
                raise Problem("the commit changes only pdlc/ files, so it takes no --req")
        if req:
            pdlc.append("Req: %s" % ", ".join(req))
        ticket = args.ticket or header_ticket(root, id_ if id_[:3] in ("IN-", "CH-") else intent)
        if ticket:
            pdlc.append("Ticket: %s" % ticket)
        if args.kind == "visual-review":
            folder = find_change(root, id_).parent
            pdlc.append("Review: %s/review.gif" % folder.relative_to(root).as_posix())
    lines = pdlc + extra_trailers(root, args)
    message = subject
    if args.text and "{text}" not in form:
        message += "\n\n" + args.text.strip()
    if lines:
        message += "\n\n" + "\n".join(lines)
    return subject, message + "\n"


def staged_files(root, amend):
    if amend:
        has_parent = run_git(root, "rev-parse", "--verify", "-q", "HEAD~1", check=False).returncode == 0
        base = "HEAD~1" if has_parent else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    else:
        base = "HEAD"
    return run_git(root, "diff", "--cached", "--name-only", base).stdout.split("\n")[:-1] \
        if base else []


def handle_commit(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    if args.amend and not args.paths:
        pass  # keep the files of the commit as they are
    else:
        paths = [os.path.relpath(os.path.abspath(p), str(root)) for p in args.paths] if args.paths else []
        run_git(root, "add", "-A", "--", *(paths or ["."]))
    files = [f for f in staged_files(root, args.amend) if f]
    if not files and not args.amend:
        raise Problem("nothing to commit: no file changed")
    subject, message = build_message(root, args, files)
    command = ["commit", "--cleanup=whitespace", "-F", "-"] + (["--amend"] if args.amend else [])
    run_git(root, *command, stdin=message)
    short = run_git(root, "rev-parse", "--short", "HEAD").stdout.strip()
    print("%s %s" % (short, subject))
    status = run_git(root, "status", "--porcelain").stdout.rstrip()
    if status:
        print("git status --porcelain (files not in the commit):")
        print(status)
    return EXIT_DONE


def handle_message(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    _, message = build_message(root, args, None)
    sys.stdout.write(message)
    return EXIT_DONE


def reject_extra(extra):
    if extra:
        raise Usage("unknown arguments: %s" % " ".join(extra))


def add_commit_options(parser):
    parser.add_argument("kind", choices=sorted(KINDS), help="the subject to use")
    parser.add_argument("id", nargs="?", help="the IN, CH, or DES ID that the subject names")
    parser.add_argument("--text", help="the words after the colon of the subject (or a body)")
    parser.add_argument("--req", nargs="+", action="extend", help="requirement IDs for Req")
    parser.add_argument("--ticket", help="the ticket key for Ticket")
    parser.add_argument("--trailer", action="append", help='another trailer, "Key: value"')
    parser.add_argument("--intent", help="the intent ID, when the ID is not an IN or CH ID")
    parser.add_argument("--amend", action="store_true", help="amend the newest commit")
    parser.add_argument("--paths", nargs="+", help="stage only these paths")


# ---------------------------------------------------------------------------------------
# handoff and stop

SECTIONS = ["Done", "Decided on defaults", "Open", "Look here", "Don't redo", "Next: do this first"]
# The keys that a transition requires, besides "next".
REQUIRED = {
    ("acceptance", "tests"): ["failing", "total", "lock", "gives"],
    ("tests", "build"): ["checks", "lock"],
    ("build", "verify"): ["passed", "total"],
    ("show", "user"): ["link", "frames", "shown", "total"],
}
OPEN_KEYS = [("reason", "Reason"), ("decide", "Decision"), ("recommend", "Recommended answer")]
LIST_KEYS = ("done", "look_here", "dont_redo")


def import_check_handoff():
    import check_handoff
    return check_handoff


def text_list(data, key):
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise Problem('"%s" must be a list of non-empty strings' % key)
    return [v.strip() for v in value]


def list_of_objects(data, key, fields):
    value = data.get(key)
    if (not isinstance(value, list) or not value
            or not all(isinstance(v, dict) and all(isinstance(v.get(f), str) and v.get(f).strip()
                                                   for f in fields) for v in value)):
        raise Problem('"%s" must be a list with at least one item, each with %s'
                      % (key, ", ".join('"%s"' % f for f in fields)))
    return value


def decided_lines(data):
    lines = []
    items = list_of_objects(data, "decided", ["id", "question", "answer"]) if data.get("decided") else []
    for item in items:
        answer = re.sub(r"\s*\(assumed\)\s*$", "", item["answer"].strip())
        lines.append("- %s: %s \u2192 %s (assumed)" % (item["id"].strip(), item["question"].strip(), answer))
    return lines


def open_triple(value):
    if (not isinstance(value, dict)
            or not all(isinstance(value.get(k), str) and value.get(k).strip() for k, _ in OPEN_KEYS)):
        raise Problem('a handoff to the user needs "open" with "reason", "decide", and "recommend", '
                      "each one sentence")
    return ["- %s: %s" % (label, value[key].strip()) for key, label in OPEN_KEYS]


def review_results(root, change_dir):
    lines = []
    for result in sorted((change_dir / "review").glob("*/result.md")):
        found = re.search(r"^\s*Result:\s*(\S+)", result.read_text(), re.M | re.I)
        lines.append("- %s: %s" % (result.parent.name, found.group(1).lower() if found else "no result"))
    if not lines:
        raise Problem("verify \u2192 show: no review results in %s/review/*/result.md"
                      % change_dir.relative_to(root).as_posix())
    return lines


def intent_path_for(root, id_):
    return find_intent(root, id_ if id_.startswith("IN-") else intent_of(root, id_))


def handoff_sections(root, id_, stage, next_, data, kept):
    """The text of each section, as lists of lines, for a handoff."""
    keys = REQUIRED.get((stage, next_), [])
    for key in keys:
        if key not in data or data[key] in (None, "", []):
            raise Problem('%s \u2192 %s needs the key "%s"' % (stage, next_, key))
    if not isinstance(data.get("next"), str) or not data["next"].strip():
        raise Problem('"next" is required: one or two sentences for the next stage')
    done = text_list(data, "done")
    look, keep = text_list(data, "look_here"), text_list(data, "dont_redo")
    open_ = None
    if stage == "acceptance" and next_ == "tests":
        gives = list_of_objects(data, "gives", ["change", "needs"])
        done.append("%s of %s acceptance checks fail, as they must before the build."
                    % (data["failing"], data["total"]))
        done += ["%s gives: %s" % (g["change"].strip(), g["needs"].strip()) for g in gives]
        keep.append("The acceptance checks are locked at %s." % data["lock"])
    elif stage == "tests" and next_ == "build":
        checks = list_of_objects(data, "checks", ["check", "req"])
        look += ["%s (proves %s)" % (c["check"].strip(), c["req"].strip()) for c in checks]
        keep.append("The checks are locked at %s." % data["lock"])
    elif stage == "build" and next_ == "verify":
        done.append("%s of %s checks pass." % (data["passed"], data["total"]))
    elif stage == "verify" and next_ == "show":
        done_lines = review_results(root, find_change(root, id_).parent)
        done += [l[2:] for l in done_lines]
        passed = pdlclib.field(intent_path_for(root, id_).read_text(), "Acceptance-Passed")
        if passed and passed != "none":
            done.append("The acceptance checks passed at %s." % passed)
    elif stage == "show" and next_ == "user":
        done.append("The recording is at %s." % data["link"])
        done.append("%s key frames. %s of %s acceptance lines are shown."
                    % (data["frames"], data["shown"], data["total"]))
    if next_ == "user" and (stage, next_) not in REQUIRED:
        open_ = open_triple(data.get("open"))
    else:
        items = data.get("open", [])
        if isinstance(items, dict):
            raise Problem('"open" is a list of sentences, except in a handoff to the user')
        open_ = ["- " + v for v in text_list(data, "open")]
    nxt = data["next"].strip()
    if next_ != "user":
        nxt = "Run `/pdlc:%s`. %s" % (next_, nxt)
    bullets = lambda items: ["- " + i for i in items] or ["- none"]  # noqa: E731
    return {
        "Done": bullets(done),
        "Decided on defaults": kept or ["- none"],
        "Open": open_ or ["- none"],
        "Look here": bullets(look),
        "Don't redo": bullets(keep),
        "Next: do this first": [nxt],
    }


def render_sections(parts, level):
    out = []
    for name in SECTIONS:
        out += [level + " " + name, ""] + parts[name] + [""]
    return "\n".join(out).rstrip("\n") + "\n"


def set_section(text, title, body, create_before=None):
    """The text with the body of '## title' replaced. The heading is added when it is not there."""
    pattern = re.compile(r"^(## %s[ \t]*\n)(.*?)(?=^## |\Z)" % re.escape(title), re.M | re.S)
    found = pattern.search(text)
    block = "\n" + body.strip("\n") + "\n"
    if found:
        more = found.end() < len(text)
        return text[:found.start(2)] + block + ("\n" if more else "") + text[found.end(2):]
    heading = "## %s\n%s\n" % (title, block)
    if create_before:
        before = re.search(r"^## %s[ \t]*$" % re.escape(create_before), text, re.M)
        if before:
            return text[:before.start()] + heading + text[before.start():]
    return text.rstrip("\n") + "\n\n" + heading


def add_notes(text, lines):
    """The text with each line added to the end of '## Notes', when it is not there yet."""
    present = {l.strip() for l in pdlclib.section(text, "Notes").splitlines()}
    new = [l for l in lines if l not in present]
    if not new:
        return text
    body = pdlclib.section(text, "Notes", None)
    current = (body or "").strip("\n")
    return set_section(text, "Notes", (current + "\n" if current else "") + "\n".join(new), "Handoff")


def write_handoff(root, id_, stage, next_, data):
    """Write the handoff, check it, and return the path. Nothing stays on a problem."""
    ch = import_check_handoff()
    if stage not in ch.NEXT:
        raise Usage("unknown stage %s" % stage)
    if not re.fullmatch(r"(IN|CH)-\d+", id_):
        raise Usage("the ID must be IN-xxxx or CH-xxxx")
    is_intent = id_.startswith("IN-")
    path = find_intent(root, id_) if is_intent else find_change(root, id_).parent / "handoff.md"
    if is_intent:
        old = pdlclib.section(path.read_text(), "Handoff", "")
        found = re.search(r"^### Decided on defaults[ \t]*\n(.*?)(?=^### |\Z)", old, re.M | re.S)
        kept = [l.strip() for l in (found.group(1) if found else "").splitlines()
                if l.strip().startswith("- ") and l.strip() != "- none"]
    else:
        kept = []
    new = decided_lines(data)
    kept = list(dict.fromkeys(kept + new))
    parts = handoff_sections(root, id_, stage, next_, data, kept)
    time = __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds")
    head = "Handoff \u00b7 %s \u00b7 %s \u2192 %s\nTime: %s\n\n" % (id_, stage, next_, time)
    intent_file = intent_path_for(root, id_)
    snapshot = {path: path.read_text() if path.exists() else None,
                intent_file: intent_file.read_text()}
    try:
        if is_intent:
            text = set_section(path.read_text(), "Handoff", head + render_sections(parts, "###"), None)
            path.write_text(add_notes(text, kept))
        else:
            path.write_text("# " + head + render_sections(parts, "##"))
            intent_file.write_text(add_notes(intent_file.read_text(), new))
        import io
        from contextlib import redirect_stdout
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ch.main(["check_handoff.py", id_, "--stage", stage], root)
        problems = [l for l in buffer.getvalue().splitlines() if l.strip()]
    except BaseException:
        restore(snapshot)
        raise
    if problems:
        restore(snapshot)
        raise Problem(*problems)
    return path


def restore(snapshot):
    for path, text in snapshot.items():
        if text is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(text)


def handle_handoff(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    data = read_json(args.json)
    path = write_handoff(root, args.id, args.stage, args.next, data)
    print("wrote the handoff %s \u2192 %s in %s" % (args.stage, args.next, path.relative_to(root).as_posix()))
    return EXIT_DONE


def options_handoff(parser):
    parser.add_argument("id", help="IN-xxxx or CH-xxxx")
    parser.add_argument("stage", choices=["intake", "ready", "change", "acceptance", "tests",
                                          "build", "verify", "show"])
    parser.add_argument("next", help="the next stage, or user")
    parser.add_argument("--json", required=True, metavar="FILE|-", help="the content, as JSON")


# ---------------------------------------------------------------------------------------
# The entry point

def not_implemented(name):
    def handler(args, extra):
        print("pdlc.py %s: not implemented" % name)
        return EXIT_USAGE
    return handler


# One handler for each subcommand: handler(args, extra) -> exit code. `args` is the parsed
# namespace, and `extra` is the list of arguments that the subcommand parser did not know.
HANDLERS = {name: not_implemented(name) for name in SUBCOMMANDS}
HANDLERS["commit"] = handle_commit
HANDLERS["message"] = handle_message
HANDLERS["handoff"] = handle_handoff

OPTIONS = {"commit": add_commit_options, "message": add_commit_options,
           "handoff": options_handoff}


def build_parser():
    parser = argparse.ArgumentParser(prog="pdlc.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True, metavar="subcommand")
    for name, text in SUBCOMMANDS.items():
        one = sub.add_parser(name, help=text, description=text)
        if name in OPTIONS:
            OPTIONS[name](one)
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args, extra = build_parser().parse_known_args(argv)
    try:
        return HANDLERS[args.command](args, extra)
    except Problem as problem:
        for line in problem.lines:
            print(line)
        return EXIT_CONTRACT
    except Usage as error:
        print("pdlc.py %s: %s" % (args.command, error), file=sys.stderr)
        return EXIT_USAGE
    except GitError as error:
        print("pdlc.py %s: %s" % (args.command, error), file=sys.stderr)
        return EXIT_GIT
    except NotProject as error:
        print("pdlc.py: %s" % error, file=sys.stderr)
        return EXIT_NOT_PROJECT


if __name__ == "__main__":
    sys.exit(main())
