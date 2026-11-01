#!/usr/bin/env python3
"""pdlc upgrade. Brings the pdlc files of a project up to the installed pdlc plugin.

  upgrade.py plan   [--project DIR] [--json]          what would change; writes nothing
  upgrade.py apply  [--project DIR] [--take PATH ...] [--no-intent] [--no-commit] [--json]
  upgrade.py record [--project DIR]                   write pdlc/version.json (init uses it)

The script runs from the plugin, because the copy of bin/ in the project is the old version.
It decides by content, never by the version number alone:
  - A file that the project did not edit goes to the plugin version ("refreshed").
  - An edited file stays as it is, and the report shows a diff ("edited").
  - A file is edited when its hash is not the base hash in pdlc/version.json. A project with
    no marker uses references/known.json: the hash of each version of each plugin file.
Exit codes: 0 done (also "up to date"), 2 a --take path that is not a pdlc file, 3 open changes,
4 not a pdlc project, 5 a git error, 6 files written but not committed (a pdlc branch with no
intent or change spec).
The script needs only the standard library (Python 3.8 or newer).
"""
import argparse
import datetime
import difflib
import glob
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ERRORS = "specs/design/DES-errors.md"
SPEC_FORMAT_SLUG = "pdlc-spec-format"
# Lines that .gitignore needs. The upgrade adds a missing line on main only.
REQUIRED_IGNORES = ["pdlc/.tools/", "pdlc/.logs/"]
FOLDERS = ["templates", "ports", "adapters", "bin", "reviews", "specs/design"]
SKIP_NAMES = {".gitkeep", "__pycache__", ".DS_Store"}


class Stop(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, message)
        self.code = code
        self.message = message


# ---- pure functions -------------------------------------------------------------------------

def normalise(text):
    """Line ends as LF, no trailing spaces, one final newline, and no ' · Ask at init' field."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    lines = [re.sub(r" · Ask at init: (?:yes|no)", "", line) if line.startswith("Status:") else line
             for line in lines]
    return "\n".join(lines).rstrip("\n") + "\n"


def digest(text):
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()


def strip_question(text):
    """The text without its '## Question' section. Init removes it from each default spec."""
    return re.sub(r"^## Question[ \t]*\n.*?(?=^## |\Z)", "", text, flags=re.M | re.S)


def header_default(text):
    """'yes', 'no', or None: the Default field of the status line."""
    match = re.search(r"^Status:.*?\bDefault:[ \t]*(yes|no)\b", text, re.M)
    return match.group(1) if match else None


def _table(lines):
    """(header index, separator index, end index) of the first table with a 'Code' column."""
    for i, line in enumerate(lines[:-1]):
        if re.match(r"^\|\s*Code\b", line) and re.match(r"^\|[\s:|-]+\|\s*$", lines[i + 1]):
            end = i + 2
            while end < len(lines) and lines[end].startswith("|"):
                end += 1
            return i, i + 1, end
    return None


def split_error_rows(text):
    """(the text without the rows of the error table, the rows)."""
    lines = text.replace("\r\n", "\n").split("\n")
    found = _table(lines)
    if not found:
        return text, []
    _, sep, end = found
    return "\n".join(lines[:sep + 1] + lines[end:]), lines[sep + 1:end]


def join_error_rows(new_text, rows):
    """The new text with the rows under its table header."""
    lines = new_text.replace("\r\n", "\n").split("\n")
    found = _table(lines)
    if not found or not rows:
        return new_text
    _, sep, end = found
    return "\n".join(lines[:sep + 1] + rows + lines[end:])


def digest_for(path, text):
    """The hash that counts for a path. The error table holds the rows of the project, so
    its hash leaves them out."""
    if path == ERRORS:
        return digest(split_error_rows(text)[0])
    return digest(text)


def decide(path, current, new, base, known, take):
    """The status of one managed file.
    current: the project text or None. new: the text of the plugin or None.
    base: the hash that pdlc wrote last time, or None. known: hashes of old plugin versions."""
    pristine = current is not None and (
        (base is not None and digest_for(path, current) == base)
        or (base is None and digest_for(path, current) in set(known)))
    if new is None:
        if current is None:
            return "gone"
        return "removed" if pristine else "edited, no longer in pdlc"
    if current is None:
        return "added"
    if normalise(current) == normalise(new):
        return "current"
    if take:
        return "taken"
    if header_default(current) == "no":
        return "project-owned"
    if pristine:
        if path == ERRORS and split_error_rows(current)[1]:
            return "refreshed, rows kept"
        return "refreshed"
    return "edited"


def format_problems(spec_text):
    """What a job or capability spec lacks to be in the newest form."""
    problems = []
    if not re.search(r"^## Interface[ \t]*$", spec_text, re.M):
        problems.append('no "Interface" section.')
    return problems


def next_intent_id(root):
    """The next free intent ID, from the inbox and from the names of pdlc branches."""
    numbers = [0]
    for path in glob.glob(os.path.join(root, "pdlc", "inbox", "IN-*.md")):
        found = re.match(r"IN-(\d+)", os.path.basename(path))
        if found:
            numbers.append(int(found.group(1)))
    out = _git(root, "branch", "--all", "--format=%(refname:short)", check=False)
    for found in re.findall(r"pdlc/IN-(\d+)", out):
        numbers.append(int(found))
    return "IN-%04d" % (max(numbers) + 1)


def _commits_module():
    spec = importlib.util.spec_from_file_location("pdlc_commits", os.path.join(PLUGIN, "hooks", "commits.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- git ------------------------------------------------------------------------------------

def _git(root, *args, **kw):
    check = kw.get("check", True)
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if done.returncode != 0:
        if check:
            raise Stop(5, "git %s failed: %s" % (" ".join(args), (done.stderr or done.stdout).strip()))
        return ""
    return done.stdout.strip()


def default_branch(root):
    for name in ("main", "master"):
        if _git(root, "rev-parse", "--verify", "-q", "refs/heads/" + name, check=False):
            return name
    return _git(root, "rev-parse", "--abbrev-ref", "HEAD")


def target_branch(root):
    """The newest unmerged pdlc branch, or the default branch when there is none."""
    default = default_branch(root)
    out = _git(root, "branch", "--no-merged", default, "--list", "pdlc/*", "--sort=-committerdate",
               "--format=%(refname:short)", check=False)
    lines = [line.strip() for line in out.splitlines() if line.strip()]
    return lines[0] if lines else default


def trailers_for(root, branch):
    """The trailer lines that the commit hook asks for on this branch. The branch must be
    checked out, because the hook reads the specs of the working tree."""
    if not branch.startswith("pdlc/"):
        return []
    commits = _commits_module()
    found = commits.owner(root, branch)
    if not found:
        return []
    kind, spec_id = found
    if kind == "intent":
        return ["Intent: " + spec_id]
    intent = None
    for path in glob.glob(os.path.join(root, "pdlc", "changes", spec_id + "-*", "change.md")):
        intent = commits.field(open(path).read(), "Intent")
    lines = ["Intent: " + intent] if intent else []
    return lines + ["Change: " + spec_id]


# ---- the plugin and the project -------------------------------------------------------------

def plugin_version(plugin):
    with open(os.path.join(plugin, ".claude-plugin", "plugin.json")) as handle:
        return json.load(handle)["version"]


def plugin_files(plugin):
    """{path under pdlc/: text that pdlc writes} for each managed file of the plugin."""
    refs = os.path.join(plugin, "skills", "init", "references")
    files = {}

    def read(path):
        with open(path, newline="") as handle:
            return handle.read()

    files["README.md"] = read(os.path.join(refs, "templates", "README.md"))
    for folder in ("templates", "ports", "adapters", "bin", "reviews"):
        base = os.path.join(refs, folder)
        for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            full = os.path.join(base, name)
            if not os.path.isfile(full) or name in SKIP_NAMES:
                continue
            if folder == "templates" and name in ("README.md", "config.md"):
                continue
            files["%s/%s" % (folder, name)] = read(full)
    base = os.path.join(refs, "defaults")
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        files["specs/design/" + name] = strip_question(read(os.path.join(base, name)))
    return files


def project_candidates(root):
    """The paths of the files in the managed folders of the project."""
    found = []
    for folder in FOLDERS:
        base = os.path.join(root, "pdlc", folder)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if os.path.isfile(os.path.join(base, name)) and name not in SKIP_NAMES:
                found.append("%s/%s" % (folder, name))
    return found


def read_text(path):
    try:
        with open(path, newline="") as handle:
            return handle.read()
    except OSError:
        return None


def load_marker(root):
    try:
        with open(os.path.join(root, "pdlc", "version.json")) as handle:
            marker = json.load(handle)
        return marker if isinstance(marker, dict) else None
    except (OSError, ValueError):
        return None


def load_known(plugin):
    try:
        with open(os.path.join(plugin, "skills", "upgrade", "references", "known.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def config_missing(root, plugin):
    """The '##' sections of the template config.md that the project config.md lacks."""
    template = read_text(os.path.join(plugin, "skills", "init", "references", "templates", "config.md")) or ""
    mine = read_text(os.path.join(root, "pdlc", "config.md")) or ""
    have = set(re.findall(r"^## (.+?)\s*$", mine, re.M))
    return [h for h in re.findall(r"^## (.+?)\s*$", template, re.M) if h not in have]


def spec_format(root):
    """[(spec ID, problem)] for the job and capability specs."""
    found = []
    for kind in ("jobs", "capabilities"):
        for path in sorted(glob.glob(os.path.join(root, "pdlc", "specs", kind, "*.md"))):
            text = read_text(path) or ""
            first = text.split("\n", 1)[0]
            match = re.match(r"#\s+((?:JOB|CAP)-[a-z0-9-]+)", first)
            spec_id = match.group(1) if match else os.path.splitext(os.path.basename(path))[0]
            for problem in format_problems(text):
                found.append((spec_id, problem))
    return found


def missing_ignores(root):
    have = [line.strip() for line in (read_text(os.path.join(root, ".gitignore")) or "").splitlines()]
    return [line for line in REQUIRED_IGNORES if line not in have]


def compute(root, plugin, takes):
    """The decision for each managed file: a list of dicts with path, status, and the text to
    write (new), when the status writes."""
    new_files = plugin_files(plugin)
    known = load_known(plugin)
    marker = load_marker(root)
    bases = (marker or {}).get("files", {}) or {}
    entries = []
    for path in sorted(new_files):
        current = read_text(os.path.join(root, "pdlc", path))
        new = new_files[path]
        if path == ERRORS and current is not None:
            new = join_error_rows(new, split_error_rows(current)[1])
        base = bases.get(path)
        status = decide(path, current, new, base, known.get(path, []), path in takes)
        entry = {"path": path, "status": status, "new": new, "base": base}
        if status == "current":
            entry["hash"] = digest_for(path, new)
        elif status in ("added", "refreshed", "refreshed, rows kept", "taken"):
            entry["hash"] = digest_for(path, new)
        elif status == "project-owned":
            entry["hash"] = base if base is not None else digest_for(path, new)
            if base is not None and base != digest_for(path, new):
                entry["diff"] = _diff(path, current, new)
        elif status == "edited":
            entry["hash"] = base
            entry["diff"] = _diff(path, current, new)
        entries.append(entry)
    for path in project_candidates(root):
        if path in new_files or (path not in bases and path not in known):
            continue
        current = read_text(os.path.join(root, "pdlc", path))
        status = decide(path, current, None, bases.get(path), known.get(path, []), False)
        entry = {"path": path, "status": status, "new": None, "base": bases.get(path)}
        if status != "removed":
            entry["hash"] = bases.get(path)
        entries.append(entry)
    return entries


def _diff(path, current, new):
    old = normalise(current).splitlines(keepends=True)
    fresh = normalise(new).splitlines(keepends=True)
    return "".join(difflib.unified_diff(old, fresh, "project/pdlc/" + path, "plugin/pdlc/" + path))


# ---- the report -----------------------------------------------------------------------------

WRITES = ("added", "refreshed", "refreshed, rows kept", "taken", "removed")


def build_plan(root, plugin, takes):
    entries = compute(root, plugin, takes)
    marker = load_marker(root)
    return {
        "from": (marker or {}).get("pdlc", "unknown"),
        "to": plugin_version(plugin),
        "entries": entries,
        "files": [{"path": e["path"], "status": e["status"], **({"diff": e["diff"]} if e.get("diff") else {})}
                  for e in entries if e["status"] not in ("current", "gone")],
        "spec_format": ["%s: %s" % item for item in spec_format(root)],
        "config_missing": config_missing(root, plugin),
        "gitignore": missing_ignores(root),
        "gitignore_written": False,
        "intent": None,
        "branch": None,
        "committed": False,
        "changed": False,
    }


def render(data):
    out = ["# pdlc upgrade", ""]
    if data["branch"]:
        out += ["Branch: %s" % data["branch"], ""]
    rows = data["files"]
    if rows:
        out += ["| File | Status |", "|---|---|"]
        out += ["| `pdlc/%s` | %s |" % (f["path"], f["status"]) for f in rows]
        out.append("")
    for f in rows:
        if f["status"] == "edited" and f.get("diff"):
            out += ["The project edited `pdlc/%s`. The diff shows how the plugin version differs. "
                    "To take the plugin version, run `upgrade.py apply --take pdlc/%s`." % (f["path"], f["path"]),
                    "", "```diff", f["diff"].rstrip("\n"), "```", ""]
        elif f["status"] == "project-owned" and f.get("diff"):
            out += ["`pdlc/%s` belongs to the project (`Default: no`), and the plugin version changed. "
                    "The diff shows the change." % f["path"], "", "```diff", f["diff"].rstrip("\n"), "```", ""]
    if data["spec_format"]:
        out += ["These specs need a newer form:", ""] + ["- " + line for line in data["spec_format"]] + [""]
        if data["intent"]:
            out += ["Filed intent %s. It waits for approval." % data["intent"], ""]
    if data["config_missing"]:
        out += ["`pdlc/config.md` lacks these sections of the template: %s." % ", ".join(data["config_missing"]), ""]
    if data["gitignore"]:
        if data["gitignore_written"]:
            out += ["Added to `.gitignore`: %s." % ", ".join("`%s`" % l for l in data["gitignore"]), ""]
        else:
            out += ["`.gitignore` lacks %s. The next upgrade on main adds the line." %
                    ", ".join("`%s`" % l for l in data["gitignore"]), ""]
    if data.get("warning"):
        out += [data["warning"], ""]
    if data.get("warning"):
        pass
    elif data["changed"]:
        if data["from"] == data["to"]:
            out.append("Refreshed files at %s." % data["to"])
        else:
            out.append("Upgraded from %s to %s." % (data["from"], data["to"]))
    else:
        out.append("pdlc is up to date.")
    return "\n".join(out) + "\n"


def counts(entries):
    def n(*names):
        return sum(1 for e in entries if e["status"] in names)

    def plural(k, word):
        return "%d %s%s" % (k, word, "" if k == 1 else "s")

    parts = []
    if n("refreshed", "refreshed, rows kept", "taken"):
        parts.append("Refreshed %s." % plural(n("refreshed", "refreshed, rows kept", "taken"), "file"))
    if n("added"):
        parts.append("Added %s." % plural(n("added"), "file"))
    if n("removed"):
        parts.append("Removed %s." % plural(n("removed"), "file"))
    if n("edited", "edited, no longer in pdlc"):
        parts.append("Kept %s." % plural(n("edited", "edited, no longer in pdlc"), "edited file"))
    return " ".join(parts)


# ---- the commands ---------------------------------------------------------------------------

def marker_text(version, old, entries, now):
    files = {}
    for e in entries:
        if e["status"] not in ("removed", "gone"):
            files[e["path"]] = e.get("hash")
    marker = {"pdlc": version, "upgraded": now, "from": (old or {}).get("pdlc", "unknown"),
              "files": dict(sorted(files.items()))}
    return json.dumps(marker, indent=2) + "\n", marker


def write_marker_if_changed(root, version, entries, plan):
    old = load_marker(root)
    text, marker = marker_text(version, old, entries, datetime.datetime.now(datetime.timezone.utc)
                               .isoformat(timespec="seconds"))
    if old and old.get("pdlc") == marker["pdlc"] and (old.get("files") or {}) == marker["files"]:
        return False
    with open(os.path.join(root, "pdlc", "version.json"), "w") as handle:
        handle.write(text)
    return True


def file_intent(root, plugin, version, problems):
    """Write the intent that lists the specs in an old form. Returns its ID, or None when an
    intent with the same title exists."""
    title = "Bring the specs to the pdlc %s form" % version
    for path in glob.glob(os.path.join(root, "pdlc", "inbox", "IN-*.md")):
        if (read_text(path) or "").startswith("# IN-") and (read_text(path) or "").split("\n", 1)[0].endswith(" · " + title):
            return None
    intent_id = next_intent_id(root)
    template = read_text(os.path.join(plugin, "skills", "init", "references", "templates", "intent.md")) or ""
    today = datetime.date.today().isoformat()
    what = ("pdlc %s reads parts of a spec that some specs of this project do not have. The list\n"
            "below gives each spec and each missing part. Add each part, and keep the behaviour of the\n"
            "app the same.\n\n%s\n\n" % (version, "\n".join("- " + p for p in problems)))
    notes = "- Awaits approval: Upgrade pdlc filed this intent.\n\n"
    text = re.sub(r"^# IN-0000 · .*$", "# %s · %s" % (intent_id, title), template, count=1, flags=re.M)
    text = text.replace("Added: YYYY-MM-DD", "Added: " + today)
    text = re.sub(r"^(## What and why\n\n).*?(?=^## )", lambda m: m.group(1) + what, text, count=1,
                  flags=re.M | re.S)
    text = re.sub(r"^(## Notes\n\n).*?(?=^## )", lambda m: m.group(1) + notes, text, count=1,
                  flags=re.M | re.S)
    path = os.path.join(root, "pdlc", "inbox", "%s-%s.md" % (intent_id, SPEC_FORMAT_SLUG))
    with open(path, "w") as handle:
        handle.write(text)
    return intent_id


def cmd_plan(root, plugin, args):
    data = build_plan(root, plugin, set())
    data["changed"] = any(e["status"] in WRITES for e in data["entries"])
    return data


def cmd_record(root, plugin):
    new_files = plugin_files(plugin)
    entries = []
    for path, new in new_files.items():
        current = read_text(os.path.join(root, "pdlc", path))
        if current is None:
            continue
        keep = header_default(current) != "no"
        entries.append({"path": path, "status": "current",
                        "hash": digest_for(path, current if keep else new)})
    text, _ = marker_text(plugin_version(plugin), None, entries,
                          datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    text = text.replace('"from": "unknown"', '"from": "none"')
    with open(os.path.join(root, "pdlc", "version.json"), "w") as handle:
        handle.write(text)


def cmd_apply(root, plugin, args):
    if _git(root, "status", "--porcelain"):
        raise Stop(3, "Commit or remove the open changes first.")
    managed = set(plugin_files(plugin)) | set(project_candidates(root))
    for given in args.take or []:
        if re.sub(r"^pdlc/", "", given) not in managed:
            raise Stop(2, "not a pdlc file: %s" % given)
    branch = target_branch(root)
    if branch != _git(root, "rev-parse", "--abbrev-ref", "HEAD"):
        _git(root, "switch", "-q", branch)
    takes = set(re.sub(r"^pdlc/", "", t) for t in (args.take or []))
    data = build_plan(root, plugin, takes)
    data["branch"] = branch
    entries = data["entries"]
    for e in entries:
        target = os.path.join(root, "pdlc", e["path"])
        if e["status"] in ("added", "refreshed", "refreshed, rows kept", "taken"):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", newline="") as handle:
                handle.write(e["new"])
        elif e["status"] == "removed":
            os.remove(target)
    on_default = branch == default_branch(root)
    missing = missing_ignores(root)
    ignore_path = os.path.join(root, ".gitignore")
    if missing and on_default:
        old = read_text(ignore_path) or ""
        sep = "" if not old or old.endswith("\n") else "\n"
        with open(ignore_path, "w") as handle:
            handle.write(old + sep + "\n".join(missing) + "\n")
        data["gitignore_written"] = True
    if data["spec_format"] and not args.no_intent:
        data["intent"] = file_intent(root, plugin, data["to"], data["spec_format"])
    write_marker_if_changed(root, data["to"], entries, data)
    if _git(root, "status", "--porcelain"):
        data["changed"] = True
        if not args.no_commit:
            trailers = trailers_for(root, branch)
            if branch.startswith("pdlc/") and not trailers:
                data["warning"] = ("Warning: the files are written but not committed. Branch %s has no "
                                   "intent or change spec, so the commit would lack its trailers. "
                                   "Commit the files with the trailers, or reset them." % branch)
                return data
            _git(root, "add", "-A", "--", "pdlc")
            if data["gitignore_written"]:
                _git(root, "add", "--", ".gitignore")
            message = ["Upgrade pdlc"]
            body = counts(entries)
            if body:
                message.append(body)
            if trailers:
                message.append("\n".join(trailers))
            cmd = ["commit", "-q"]
            for part in message:
                cmd += ["-m", part]
            try:
                _git(root, *cmd)
            except Stop as stop:
                raise Stop(5, stop.message + "\nThe upgrade wrote its files but did not commit them. "
                           "Commit the files, or run git reset --hard and git clean -fd pdlc, "
                           "before the next run. The next run stops while changes are open.")
            data["committed"] = True
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Upgrade the pdlc files of a project.")
    parser.add_argument("command", choices=["plan", "apply", "record"])
    parser.add_argument("--project", default=".")
    parser.add_argument("--take", action="append", metavar="PATH")
    parser.add_argument("--no-intent", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project)
    try:
        if not os.path.isfile(os.path.join(root, "pdlc", "config.md")):
            raise Stop(4, "This folder is not a pdlc project: it has no pdlc/config.md.")
        if args.command == "record":
            cmd_record(root, PLUGIN)
            return 0
        data = (cmd_plan if args.command == "plan" else cmd_apply)(root, PLUGIN, args)
    except Stop as stop:
        print(stop.message)
        return stop.code
    out = {k: v for k, v in data.items() if k != "entries"}
    print(json.dumps(out, indent=2) if args.json else render(data), end="" if not args.json else "\n")
    return 6 if data.get("warning") else 0


if __name__ == "__main__":
    sys.exit(main())
