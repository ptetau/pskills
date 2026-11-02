#!/usr/bin/env python3
"""Write the structured outputs of pdlc: commits, handoffs, header fields, and specs.

Usage: python3 pdlc/bin/pdlc.py <subcommand> [options]

Subcommands: commit, message, handoff, stop, set, intent, change, start.

Exit codes, for every subcommand:
  0  done
  1  a contract problem (one line for each problem, and nothing written)
  2  a usage error
  3  a git error
  4  not a pdlc project

Run it from anywhere under the project root.
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
    "stop": "write a stop record and commit it; refuses when other files have changes",
    "set": "set header fields and statuses of an intent or a change",
    "intent": "make a new intent, or change the lists of an intent",
    "change": "make the spec of a new change",
    "start": "start a change: work out its Branch and Base, make the branch, commit the start",
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
# intent name, {names} the change names of the intent, {n} the number of the round, and
# {base} is --base, the branch that a merge brings in.
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
    "merge": ("CH", "Merge {base} into {id}"),
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


def require_round(root, kind, change_id):
    """Verified and send-back follow a "Verify <change>: round <n>" commit that is newer
    than the newest "Built <change>" or "Send back <change>" commit."""
    if kind not in ("verified", "send-back") or not change_id:
        return
    name = re.escape(change_id)
    for subject in run_git(root, "log", "--format=%s", check=False).stdout.splitlines():
        if re.fullmatch(r"Verify %s: round \d+" % name, subject):
            return
        if re.fullmatch(r"Built %s|Send back %s: .+" % (name, name), subject):
            break
    raise Problem("%s needs a round commit of %s after its last Built or Send back commit"
                  % (kind, change_id),
                  "commit the round first: python3 pdlc/bin/pdlc.py commit verify %s" % change_id)


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
    base = getattr(args, "base", None)
    if args.kind == "merge" and not base:
        raise Problem("merge needs --base, the branch that the merge brings in")
    if base and args.kind != "merge":
        raise Usage("--base is only for the merge kind")
    values = {"id": id_, "text": args.text, "base": base}
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
    require_round(root, args.kind, args.id)
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
    parser.add_argument("--base", help="the branch that a merge brings in (merge only)")
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
    return path, snapshot


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
    path, _ = write_handoff(root, args.id, args.stage, args.next, data)
    print("wrote the handoff %s \u2192 %s in %s" % (args.stage, args.next, path.relative_to(root).as_posix()))
    return EXIT_DONE


STOP_NEXT = "Answer the open question, then run `/pdlc:ship` again."


def refuse_unrelated_changes(root, id_):
    """A stop commits only its own files. Other changes are a stage's work, and it must commit them first."""
    own = {intent_path_for(root, id_)}
    if id_.startswith("CH-"):
        own.add(find_change(root, id_).parent / "handoff.md")
    own = {p.resolve().relative_to(root.resolve()).as_posix() for p in own}
    out = run_git(root, "status", "--porcelain", "-z", "--untracked-files=all").stdout
    entries = out.split("\0")
    paths, i = [], 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        paths.append(entry[3:])
        if entry[0] in "RC":
            i += 1  # skip the source path of a rename
    other = [p for p in paths if p not in own]
    if other:
        raise Problem("stop refused: these files have changes that the stop does not write: " + ", ".join(other),
                      "commit the stage first: python3 pdlc/bin/pdlc.py commit <stage> <id>")


def handle_stop(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    data = read_json(args.json)
    refuse_unrelated_changes(root, args.id)
    triple = open_triple(data.get("open"))
    data.setdefault("next", STOP_NEXT)
    reason = " ".join(data["open"]["reason"].split())
    path, snapshot = write_handoff(root, args.id, args.stage, "user", data)
    commit = argparse.Namespace(kind="stop", id=args.id, text=reason, req=args.req, ticket=args.ticket,
                                trailer=args.trailer, intent=args.intent, amend=False, paths=args.paths)
    try:
        handle_commit(commit, [])
    except BaseException:
        restore(snapshot)
        raise
    print("\n".join(triple))
    return EXIT_DONE


def options_stop(parser):
    parser.add_argument("id", help="IN-xxxx or CH-xxxx")
    parser.add_argument("--stage", required=True, choices=["intake", "ready", "change", "acceptance",
                                                           "tests", "build", "verify", "show"])
    parser.add_argument("--json", required=True, metavar="FILE|-", help="the open triple, as JSON")
    parser.add_argument("--req", nargs="+", action="extend", help="requirement IDs for Req")
    parser.add_argument("--ticket", help="the ticket key for Ticket")
    parser.add_argument("--trailer", action="append", help='another trailer, "Key: value"')
    parser.add_argument("--intent", help="the intent ID for Intent")
    parser.add_argument("--paths", nargs="+", help="stage only these paths")


def options_handoff(parser):
    parser.add_argument("id", help="IN-xxxx or CH-xxxx")
    parser.add_argument("stage", choices=["intake", "ready", "change", "acceptance", "tests",
                                          "build", "verify", "show"])
    parser.add_argument("next", help="the next stage, or user")
    parser.add_argument("--json", required=True, metavar="FILE|-", help="the content, as JSON")


# ---------------------------------------------------------------------------------------
# set

DEFAULT_STATUSES = {
    "Intent": ["new", "specifying", "ready", "building", "in review", "done", "paused", "cancelled"],
    "Change": ["planned", "testing", "building", "in review", "merged", "cancelled"],
    "Requirement": ["proposed", "ready", "built", "verified", "retiring"],
}
ENTRY = re.compile(r"^- [^`\n]*`([^`\n]+)`(.*)$")


def statuses(root):
    """The statuses of each kind, from "Statuses" in the README of the project. A kind that
    the README does not give has the default list."""
    found = {kind: list(values) for kind, values in DEFAULT_STATUSES.items()}
    try:
        text = pdlclib.section((root / "pdlc" / "README.md").read_text(), "Statuses")
    except OSError:
        return found
    for kind in found:
        line = re.search(r"^- %s:\s*(.+)$" % kind, text, re.M)
        if not line:
            continue
        main, _, also = line.group(1).partition("Also")
        words = [w.strip(" .") for w in main.split("\u2192")]
        words += [w.strip(" .") for w in also.split(",")]
        words = [w for w in words if w]
        if words:
            found[kind] = words
    return found


class Texts:
    """The files that a command changes, held in memory until it writes them all."""

    def __init__(self):
        self.new = {}

    def get(self, path):
        return self.new[path] if path in self.new else path.read_text()

    def put(self, path, text):
        self.new[path] = text

    def write(self):
        for path, text in self.new.items():
            path.write_text(text)


def set_field(text, name, value, header_only=False):
    """The text with the first field `name` set to the value, or None when it is not there."""
    cut = text.find("\n## ") if header_only else -1
    head, tail = (text[:cut], text[cut:]) if cut >= 0 else (text, "")
    found = re.search(r"(\b%s:[ \t]*)([^\u00b7\n]*?)([ \t]*(?:\u00b7|$))" % re.escape(name), head, re.M)
    if not found:
        return None
    return head[:found.start(2)] + value + head[found.end(2):] + tail


def must_set(texts, path, name, value, header_only=False):
    new = set_field(texts.get(path), name, value, header_only)
    if new is None:
        raise Problem("%s has no \"%s:\" field" % (path.name if path.name != "change.md" else path.parent.name, name))
    texts.put(path, new)


def full_hash(root, rev):
    done = run_git(root, "rev-parse", "--verify", "-q", rev + "^{commit}", check=False)
    if done.returncode != 0:
        raise GitError("git cannot find the revision %s" % rev)
    return done.stdout.strip()


def acceptance_path(root, intent_id):
    try:
        config = (root / "pdlc" / "config.md").read_text()
    except OSError:
        config = ""
    found = re.search(r"^- acceptance file:\s*`([^`]+)`", config, re.M | re.I)
    if not found or "..." in found.group(1) or "{intent}" not in found.group(1):
        raise Problem('pdlc/config.md has no usable "acceptance file" line (a path with {intent})')
    form = re.search(r"^- ID form in check names:\s*`(\w+)`", config, re.M | re.I)
    name = intent_id.replace("-", "_") if form and form.group(1) == "underscored" else intent_id
    return found.group(1).replace("{intent}", name)


def requirement_span(text, req_id):
    heading = re.search(r"^### %s\b.*$" % re.escape(req_id), text, re.M)
    if not heading:
        return None
    end = re.search(r"^##", text[heading.end():], re.M)
    return heading.end(), heading.end() + (end.start() if end else len(text) - heading.end())


def set_requirement(root, texts, req_id, status):
    path = spec_file(root, req_id.rsplit(".", 1)[0])
    text = texts.get(path)
    span = requirement_span(text, req_id)
    if not span:
        raise Problem("%s: no such requirement in %s" % (req_id, path.name))
    body = set_field(text[span[0]:span[1]], "Status", status)
    if body is None:
        raise Problem("%s has no Status line" % req_id)
    texts.put(path, text[:span[0]] + body + text[span[1]:])


def change_requirements(text):
    found = re.findall(r"^### ((?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+)\b(.*)$", pdlclib.section(text, "Requirements"), re.M)
    return [req for req, rest in found if "(retire)" not in rest]  # the build removed a retired one


def tick_steps(text):
    """The change spec with each open step under "## Steps" ticked."""
    span = re.search(r"^## Steps\s*$.*?(?=^## |\Z)", text, re.M | re.S)
    if not span:
        return text
    body = re.sub(r"^(### .*\u00b7 )\[ \]([ \t]*)$", r"\1[x]\2", span.group(0), flags=re.M)
    body = re.sub(r"^(\s*- )\[ \]", r"\1[x]", body, flags=re.M)
    return text[:span.start()] + body + text[span.end():]


BUILT_LOG = "built: all checks pass"


def log_built(text):
    """The change spec with one new last line in its progress log, unless it has that line."""
    if not re.search(r"^## Progress log\s*$", text, re.M):
        raise Problem("the change has no Progress log section")
    if any(BUILT_LOG in l for l in pdlclib.section(text, "Progress log").splitlines()):
        return text
    line = "- %s \u00b7 %s" % (__import__("datetime").date.today().isoformat(), BUILT_LOG)
    span = re.search(r"^## Progress log[ \t]*$\n?(.*?)(?=^## |\Z)", text, re.M | re.S)
    old = span.group(1).strip("\n")
    body = "\n" + (old + "\n" if old else "") + line + "\n"
    rest = text[span.end():]
    return text[:span.start(1)] + body + ("\n" + rest if rest else "")


def unpropose(root, texts, change_text):
    scope = pdlclib.field(change_text, "Scope")
    if not scope:
        raise Problem("the change has no Scope field")
    path = spec_file(root, scope)
    keys = {m.group(1) for m in (ENTRY.match(l) for l in pdlclib.section(change_text, "Interface").splitlines()) if m}
    out, in_interface = [], False
    for line in texts.get(path).split("\n"):
        if line.startswith("## "):
            in_interface = line.strip() == "## Interface"
        found = ENTRY.match(line) if in_interface else None
        if found and found.group(1) in keys:
            line = re.sub(r"\s*\u00b7\s*proposed\b", "", line)
        out.append(line)
    texts.put(path, "\n".join(out))


def handle_set(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    id_ = args.id
    if not re.fullmatch(r"(IN|CH)-\d+", id_):
        raise Usage("the ID must be IN-xxxx or CH-xxxx")
    wanted = [args.status, args.branch, args.base, args.tests_locked, args.acceptance_file,
              args.acceptance_locked, args.acceptance_passed, args.ticket, args.reqs, args.req,
              args.unpropose or None]
    if not any(wanted):
        raise Usage("give at least one option to set")
    path = find_intent(root, id_) if id_.startswith("IN-") else find_change(root, id_)
    kind = "Intent" if id_.startswith("IN-") else "Change"
    allowed = statuses(root)
    texts, report = Texts(), []

    def put(name, value, header_only=False):
        must_set(texts, path, name, value, header_only)
        report.append("%s: %s \u2192 %s" % (id_, name, value))

    if args.status:
        if args.status not in allowed[kind]:
            raise Problem("%s: status \"%s\" is not one of: %s" % (id_, args.status, ", ".join(allowed[kind])))
        put("Status", args.status, True)
    if args.branch:
        put("Branch", args.branch, True)
    if args.base:
        put("Base", args.base, True)
    if args.ticket:
        put("Ticket", args.ticket, True)
    if args.tests_locked:
        value = args.tests_locked if args.tests_locked == "acceptance" else full_hash(root, args.tests_locked)
        put("Tests-Locked", value, True)
    if args.acceptance_file:
        value = acceptance_path(root, id_) if args.acceptance_file == "auto" else args.acceptance_file
        put("Acceptance-File", value)
    if args.acceptance_locked:
        put("Acceptance-Locked", full_hash(root, args.acceptance_locked))
    if args.acceptance_passed:
        put("Acceptance-Passed", full_hash(root, args.acceptance_passed))
    pairs = []
    if args.reqs:
        if kind != "Change":
            raise Problem("--reqs works on a change; use --req ID=STATUS for an intent")
        pairs += [(r, args.reqs) for r in change_requirements(path.read_text())]
    for item in args.req or []:
        req_id, _, status = item.partition("=")
        if not status:
            raise Problem('--req needs the form ID=STATUS, not "%s"' % item)
        pairs.append((req_id, status))
    for req_id, status in pairs:
        if status not in allowed["Requirement"]:
            raise Problem("%s: status \"%s\" is not one of: %s" % (req_id, status, ", ".join(allowed["Requirement"])))
        set_requirement(root, texts, req_id, status)
        report.append("%s: Status \u2192 %s" % (req_id, status))
    if args.unpropose:
        if kind != "Change":
            raise Problem("--unpropose works on a change")
        unpropose(root, texts, path.read_text())
        report.append("%s: removed \u00b7 proposed from the entries of its Interface" % id_)
    if args.reqs == "built":
        text = texts.get(path)
        texts.put(path, log_built(tick_steps(text)))
        report.append("%s: steps ticked, progress log updated" % id_)
    texts.write()
    print("\n".join(report))
    return EXIT_DONE


def options_set(parser):
    parser.add_argument("id", help="IN-xxxx or CH-xxxx")
    parser.add_argument("--status")
    parser.add_argument("--branch")
    parser.add_argument("--base")
    parser.add_argument("--ticket")
    parser.add_argument("--tests-locked", metavar="REV|acceptance")
    parser.add_argument("--acceptance-file", metavar="auto|PATH")
    parser.add_argument("--acceptance-locked", metavar="REV")
    parser.add_argument("--acceptance-passed", metavar="REV")
    parser.add_argument("--reqs", metavar="STATUS", help="set each requirement that the change lists; \"built\" also ticks the steps and logs progress")
    parser.add_argument("--req", action="append", metavar="ID=STATUS")
    parser.add_argument("--unpropose", action="store_true", help="remove the proposed mark of its entries")


# ---------------------------------------------------------------------------------------
# intent

def next_id(root, prefix):
    numbers = []
    patterns = {"IN": ["pdlc/inbox/**/IN-*", "pdlc/changes/*/change.md"],
                "CH": ["pdlc/changes/CH-*"]}[prefix]
    names = []
    for pattern in patterns:
        names += [p.as_posix() for p in root.glob(pattern)]
    for name in names:
        numbers += [int(n) for n in re.findall(r"\b%s-(\d+)" % prefix, Path(name).name)]
        if name.endswith("change.md") and prefix == "IN":
            numbers += [int(n) for n in re.findall(r"\bIN-(\d+)", Path(name).read_text().split("\n## ")[0])]
    refs = run_git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/pdlc/", check=False).stdout
    numbers += [int(n) for n in re.findall(r"pdlc/%s-(\d+)" % prefix, refs)]
    return "%s-%04d" % (prefix, max(numbers or [0]) + 1)


def slug(text, limit=40):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:limit].strip("-") or "intent"


def inbox_adapter(root):
    try:
        found = re.search(r"^- inbox:\s*(\S+)", (root / "pdlc" / "config.md").read_text(), re.M)
    except OSError:
        found = None
    return found.group(1) if found else None


def list_edit(text, title, lines):
    """The text with each line added to the list under '## title'. A line with the same
    "- ID:" start replaces the old line. The placeholder "- none yet" goes."""
    current = [l for l in pdlclib.section(text, title).splitlines() if l.strip() and l.strip() != "- none yet"]
    for line in lines:
        key = line.split(":", 1)[0] + ":"
        for n, old in enumerate(current):
            if old.startswith(key):
                current[n] = line
                break
        else:
            current.append(line)
    return set_section(text, title, "\n".join(current))


def new_intent(root, args):
    if inbox_adapter(root) != "inbox-files":
        raise Problem("intent new works only with the inbox-files adapter (pdlc/config.md); "
                      "use the inbox port of the adapter in place of it")
    if args.migrate:
        spec, convention = args.migrate
        name = "Migrate %s to %s" % (spec, convention)
        what = args.what or "Change the spec %s to follow the convention %s." % (spec, convention)
    else:
        if not args.name or not args.what:
            raise Usage("intent new needs --name and --what (or --migrate SPEC DES)")
        name, what = args.name.strip(), args.what.strip()
    id_ = next_id(root, "IN")
    notes = "Awaits approval: %s" % args.awaits.strip() if args.awaits else ""
    text = (
        "# %s \u00b7 %s\n\nStatus: new \u00b7 Ticket: none \u00b7 Branch: none \u00b7 Added: %s\n\n"
        "## What and why\n\n%s\n\n## Requirements\n\n- none yet\n\n## Changes\n\n- none yet\n\n"
        "## Acceptance checks\n\nAcceptance-File: none\nAcceptance-Locked: none\nAcceptance-Passed: none\n\n"
        "## Notes\n\n%s" % (id_, name, __import__("datetime").date.today().isoformat(), what,
                            notes + "\n" if notes else ""))
    path = root / "pdlc" / "inbox" / ("%s-%s.md" % (id_, slug(name)))
    path.write_text(text)
    print("%s %s" % (id_, path.relative_to(root).as_posix()))


def handle_intent(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    if args.target == "new":
        new_intent(root, args)
        return EXIT_DONE
    if not re.fullmatch(r"IN-\d+", args.target):
        raise Usage('the first argument is "new" or an intent ID (IN-xxxx)')
    path = find_intent(root, args.target)
    text, report = path.read_text(), []
    if args.status:
        allowed = statuses(root)["Intent"]
        if args.status not in allowed:
            raise Problem("%s: status \"%s\" is not one of: %s" % (args.target, args.status, ", ".join(allowed)))
        text = set_field(text, "Status", args.status, True)
        report.append("Status \u2192 %s" % args.status)
    if args.req:
        lines = []
        for item in args.req:
            req_id, _, word = item.partition("=")
            if not re.fullmatch(r"(?:JOB|CAP|DES)-[a-z0-9-]+\.R\d+", req_id) or word not in ("added", "changed", "retiring"):
                raise Problem('--req needs the form ID=added, ID=changed, or ID=retiring, not "%s"' % item)
            lines.append("- %s: %s" % (req_id, word))
        text = list_edit(text, "Requirements", lines)
        report += ["Requirements: " + l[2:] for l in lines]
    notes = ['- %s: was "%s", now "%s"' % tuple(w) for w in (args.was or [])]
    notes += ['- README: "%s" \u2192 %s' % tuple(r) for r in (args.readme or [])]
    if notes:
        text = add_notes(text, notes)
        report += ["Notes: " + n[2:] for n in notes]
    if not report:
        raise Usage("give at least one option to change")
    path.write_text(text)
    print("\n".join("%s: %s" % (args.target, r) for r in report))
    return EXIT_DONE


def options_intent(parser):
    parser.add_argument("target", help='"new", or the intent ID (IN-xxxx)')
    parser.add_argument("--name")
    parser.add_argument("--what")
    parser.add_argument("--awaits")
    parser.add_argument("--migrate", nargs=2, metavar=("SPEC", "DES"))
    parser.add_argument("--status")
    parser.add_argument("--req", action="append", metavar="ID=added|changed|retiring")
    parser.add_argument("--was", nargs=3, action="append", metavar=("ID", "OLD", "NEW"))
    parser.add_argument("--readme", nargs=2, action="append", metavar=("OLD", "REQ"))


# ---------------------------------------------------------------------------------------
# change new

FIXED_RELIES = ["DES-writing-style", "DES-pdlc-check-tagging", "DES-errors"]
CHANGE_LISTS = ("reqs", "files", "check_files", "interface", "relies", "manual")


def interface_entries(spec_text):
    """{key: (is_seam, lines)} for each entry of "Interface" in a spec. The lines have no
    ' \u00b7 proposed' mark."""
    out, seam, current = {}, False, None
    for line in pdlclib.section(spec_text, "Interface").split("\n"):
        if line.startswith("### "):
            seam, current = line.strip().lower() == "### test seams", None
            continue
        found = ENTRY.match(line)
        if found:
            current = [re.sub(r"\s*\u00b7\s*proposed\b", "", line.rstrip())]
            out.setdefault(found.group(1), (seam, current))
        elif current is not None and line[:1] in (" ", "\t"):
            current.append(line.rstrip())
        elif line.strip() == "":
            continue
        else:
            current = None
    return {key: (seam, [l for l in lines]) for key, (seam, lines) in out.items()}


def requirement_block(root, req_id):
    """(title, text) of a requirement: the heading and its lines, without the Status line."""
    path = spec_file(root, req_id.rsplit(".", 1)[0])
    text = path.read_text()
    heading = re.search(r"^### %s\b.*$" % re.escape(req_id), text, re.M)
    if not heading:
        raise Problem("%s: no such requirement in %s" % (req_id, path.name))
    span = requirement_span(text, req_id)
    body = [l for l in text[span[0]:span[1]].split("\n") if not re.match(r"Status:", l)]
    retiring = any(re.match(r"Status:\s*retiring\b", l) for l in text[span[0]:span[1]].split("\n"))
    block = (heading.group(0) + (" (retire)" if retiring else "") + "\n" + "\n".join(body)).strip("\n")
    block = re.sub(r"\n{3,}", "\n\n", block)
    title = heading.group(0).split("\u00b7", 1)[-1].strip()
    return title, block


def req_sort_key(req_id):
    spec, _, number = req_id.rpartition(".R")
    return spec, int(number or 0)


def check_names(reqs, checks):
    norm = lambda text: re.sub(r"[-.]", "_", text)  # noqa: E731
    problems = []
    for req in reqs:
        name = checks.get(req)
        if not isinstance(name, str) or not name.strip():
            problems.append('"checks" has no check for %s' % req)
        elif name.strip() != "manual check" and norm(req) not in norm(name):
            problems.append('the check "%s" does not hold the requirement ID %s' % (name, req))
    problems += ['"checks" names %s, which is not in "reqs"' % r for r in checks if r not in reqs]
    return problems


def bullets(items, empty="- none"):
    return "\n".join("- " + i for i in items) if items else empty


def handle_change(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    data = read_json(args.json)
    if not re.fullmatch(r"IN-\d+", args.intent):
        raise Usage("the intent must be IN-xxxx")
    intent_file = find_intent(root, args.intent)
    scope_path = spec_file(root, args.scope)
    problems = []
    if not isinstance(data.get("delivers"), str) or not data["delivers"].strip():
        problems.append('"delivers" is required: one or two sentences')
    for key in CHANGE_LISTS:
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
            problems.append('"%s" is required: a list of strings (it can be empty, except "reqs")' % key)
    if not isinstance(data.get("checks"), dict):
        problems.append('"checks" is required: {"<requirement ID>": "<check name>"}')
    if not problems and not data["reqs"]:
        problems.append('"reqs" needs at least one requirement ID')
    if not problems and args.scope.startswith("JOB-") and not str(data.get("readme_done") or "").strip():
        problems.append('"readme_done" is required for a job change: what the README step finishes')
    if problems:
        raise Problem(*problems)
    reqs = sorted(dict.fromkeys(data["reqs"]), key=req_sort_key)
    problems = check_names(reqs, data["checks"])
    if problems:
        raise Problem(*problems)
    blocks = [requirement_block(root, r) for r in reqs]

    specs = [args.scope] + [s for s in dict.fromkeys(
        m for r in data["relies"] for m in re.findall(r"\b(?:JOB|CAP)-[a-z0-9-]+\b", r)) if s != args.scope]
    found = {}
    for spec_id in specs:
        try:
            spec_text = spec_file(root, spec_id).read_text()
        except Problem:
            if spec_id == args.scope:
                raise
            continue  # a spec under "relies" that has no file has no entries to copy
        for key, value in interface_entries(spec_text).items():
            found.setdefault(key, value)
    entries, seams, missing = [], [], []
    for key in data["interface"]:
        if key not in found:
            missing.append('the Interface entry "%s" is in none of the specs %s: add it to its spec first'
                           % (key, ", ".join(specs)))
        else:
            (seams if found[key][0] else entries).append("\n".join(found[key][1]).rstrip())
    if missing:
        raise Problem(*missing)

    relies = ["%s (conventions to follow)" % d for d in FIXED_RELIES]
    for item in data["relies"]:
        relies.append(item if "(" in item else item + " (used, not changed)")
    steps = []
    for n, (req, (title, _)) in enumerate(zip(reqs, blocks), 1):
        check = data["checks"][req].strip()
        done_when = "the check passes" if check != "manual check" else "the user confirms the manual check"
        steps.append("### Step %d \u00b7 %s \u00b7 [ ]\n\n- Requirement: %s\n- Check: %s\n- Done when: %s"
                     % (n, title, req, check, done_when))
    files = list(data["files"])
    if data.get("readme_done"):
        steps.append("### Step %d \u00b7 README \u00b7 [ ]\n\n- Requirement: none\n- Check: none\n- Done when: %s"
                     % (len(steps) + 1, data["readme_done"].strip()))
        if "README.md" not in files:
            files.append("README.md")

    change_id = next_id(root, "CH")
    name = args.name.strip()
    text = "\n\n".join([
        "# %s \u00b7 %s" % (change_id, name),
        "Intent: %s \u00b7 Scope: %s \u00b7 Status: planned \u00b7 Ticket: none \u00b7 Branch: none \u00b7 Base: main\n"
        "Tests-Locked: none" % (args.intent, args.scope),
        "## Delivers\n\n" + data["delivers"].strip(),
        "## Requirements\n\n" + "\n\n".join(block for _, block in blocks),
        "## Relies on\n\n" + bullets(relies),
        "## Interface\n\n" + ("\n\n".join(entries) if entries else "- none")
        + "\n\n### Test seams\n\n" + ("\n\n".join(seams) if seams else "none"),
        "## Files\n\n" + bullets(files),
        "## Check files\n\n" + bullets(data["check_files"]),
        "## Steps\n\n" + "\n\n".join(steps),
        "## Manual checks\n\n" + ("\n".join(data["manual"]) if data["manual"] else "none"),
        "## Progress log",
    ]) + "\n"
    folder = root / "pdlc" / "changes" / ("%s-%s" % (change_id, slug(name)))
    line = "- %s \u00b7 %s" % (change_id, name)
    current = [l for l in pdlclib.section(intent_file.read_text(), "Changes").splitlines()
               if l.strip() and l.strip() != "- none yet"]
    folder.mkdir(parents=True)
    (folder / "change.md").write_text(text)
    intent_file.write_text(set_section(intent_file.read_text(), "Changes", "\n".join(current + [line])))
    print("%s %s" % (change_id, (folder / "change.md").relative_to(root).as_posix()))
    return EXIT_DONE


def options_change(parser):
    parser.add_argument("action", choices=["new"])
    parser.add_argument("intent", help="IN-xxxx")
    parser.add_argument("--scope", required=True, metavar="SPEC", help="the JOB, CAP, or DES spec of the change")
    parser.add_argument("--name", required=True, metavar="SHORT")
    parser.add_argument("--json", required=True, metavar="FILE|-", help="the content, as JSON")


# ---------------------------------------------------------------------------------------
# start

def branch_exists(root, name):
    return run_git(root, "show-ref", "--verify", "--quiet", "refs/heads/" + name, check=False).returncode == 0


def merged_into_main(root, branch):
    return run_git(root, "merge-base", "--is-ancestor", branch, "main", check=False).returncode == 0


def listed_changes(root, intent_id):
    text = pdlclib.section(find_intent(root, intent_id).read_text(), "Changes")
    return [m.group(1) for m in (re.search(r"\b(CH-\d+)\b", l) for l in text.splitlines()) if m]


def stacked_base(root, change_id):
    """The base of a change, by "Stacked changes" in the README."""
    intent_id = intent_of(root, change_id)
    changes = listed_changes(root, intent_id)
    if change_id not in changes:
        raise Problem("%s is not in the Changes list of %s" % (change_id, intent_id))
    position = changes.index(change_id)
    if position:
        before = changes[position - 1]
        found = run_git(root, "for-each-ref", "--format=%(refname:short)",
                        "refs/heads/pdlc/%s-*" % before, check=False).stdout.split()
        branch = found[0] if found else None
        if not branch:
            raise Problem("%s comes before %s and has no branch: start %s first" % (before, change_id, before))
        return "main" if merged_into_main(root, branch) else branch
    branch = pdlclib.field(find_intent(root, intent_id).read_text(), "Branch")
    if branch and branch != "none" and branch_exists(root, branch):
        return branch
    own = {pdlclib.field(find_change(root, c).read_text(), "Branch") for c in changes}
    listing = run_git(root, "branch", "--no-merged", "main", "--list", "pdlc/CH-*",
                      "--sort=-committerdate", "--format=%(refname:short)", check=False).stdout.split()
    return next((b for b in listing if b not in own), "main")


def handle_start(args, extra):
    reject_extra(extra)
    root = project()
    os.chdir(str(root))
    id_ = args.id
    if not re.fullmatch(r"CH-\d+", id_):
        raise Usage("the ID must be CH-xxxx")
    path = find_change(root, id_)
    branch = pdlclib.field(path.read_text(), "Branch")
    if not branch or branch == "none":
        branch = "pdlc/" + path.parent.name
    if branch_exists(root, branch):
        run_git(root, "switch", "-q", branch)
        print("%s: the branch %s exists; its Base stays" % (id_, branch))
        return EXIT_DONE
    base = stacked_base(root, id_)
    texts = Texts()
    must_set(texts, path, "Branch", branch, True)
    must_set(texts, path, "Base", base, True)
    must_set(texts, path, "Status", "testing", True)
    run_git(root, "switch", "-q", "-c", branch, base)
    texts.write()
    print("%s: Branch \u2192 %s, Base \u2192 %s, Status \u2192 testing" % (id_, branch, base))
    return handle_commit(argparse.Namespace(kind="start", id=id_, text=None, req=None, ticket=None,
                                            trailer=None, intent=None, base=None, amend=False,
                                            paths=None), [])


def options_start(parser):
    parser.add_argument("id", help="CH-xxxx")


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
HANDLERS["stop"] = handle_stop
HANDLERS["set"] = handle_set
HANDLERS["intent"] = handle_intent
HANDLERS["change"] = handle_change
HANDLERS["start"] = handle_start

OPTIONS = {"commit": add_commit_options, "message": add_commit_options,
           "handoff": options_handoff, "stop": options_stop,
           "set": options_set, "intent": options_intent,
           "change": options_change, "start": options_start}


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
