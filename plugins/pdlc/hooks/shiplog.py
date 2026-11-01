#!/usr/bin/env python3
"""pdlc ship log and end-state check. Claude Code runs this on several hook events.

Two jobs, both only while a ship run is current:

1. A debug log. Each ship run writes one file, pdlc/.logs/ship-<UTC start>.jsonl, with one
   JSON object on each line. The model writes no entry. Each entry comes from an event
   that this hook sees: run_start, stage_start, commit, agent_start, agent_end,
   agent_stop, tool_error, stop_blocked, turn_end, and hook_error. The keys of every
   entry: t (ISO time with offset), run, session, event. pdlc/.logs/current holds the name
   of the current log. The project's .gitignore lists pdlc/.logs/, so the log costs no
   commit and survives a branch switch.

2. The end-state rule, on the Stop event. While a ship run is current, the turn may end
   only when one of these is true:
     - a commit since run_start has a subject that starts with "Stop " (end state "stopped");
     - the newest pdlc branch has "Propose " as its newest subject, and its intent has
       "Status: in review" there (end state "proposed");
     - no commit was made since run_start (end state "no work").
   Else the hook blocks the end of the turn, at most 2 times in one run. After that it lets
   the turn end, with end state "unrecorded". When the turn ends, the run is over.

A session that is not a ship run is never blocked and never logged: no current run for the
session, no project (a folder that holds pdlc/config.md), a broken input, or any error
means no output and exit 0. Only the Stop rule ever prints a block.

Usage:
  python3 shiplog.py                  read the hook JSON from stdin and dispatch on it
  python3 shiplog.py summary <log>    print one row for each stage, and the end state
"""
import datetime
import json
import os
import re
import subprocess
import sys

LOGS = os.path.join("pdlc", ".logs")
CURRENT = "current"
START = re.compile(r"\s*/pdlc:ship\b")
STAGE_END = re.compile(r"^(Specify|Ready|Plan|Acceptance reviewed|Tests reviewed|Built|Verified|"
                       r"Send back|Propose|Stop)\b")
RATE_LIMIT = re.compile(r"rate.?limit|429|529|overloaded", re.I)
MAX_BLOCKS = 2
TEXT_LIMIT = 500
REASON = ('The ship run is not at an end state. Continue from the latest handoff. If the run '
          'cannot continue, write the reason under "Open" in the handoff, and commit '
          '"Stop <id>: <why>".')
NO_END = ("the log ends with no turn_end: the session ended outside the model, for example an "
          "API error or a rate limit")


def project_root(path):
    """The nearest folder at or above path that holds pdlc/config.md, or None.
    Same as commits.py."""
    path = os.path.realpath(path)
    while True:
        if os.path.isfile(os.path.join(path, "pdlc", "config.md")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def git(root, *args, stdin=None):
    """git's output, stripped, or None when it fails."""
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20,
                             input=stdin)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def plugin_version():
    base = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        with open(os.path.join(base, ".claude-plugin", "plugin.json")) as handle:
            return json.load(handle).get("version")
    except (OSError, ValueError):
        return None


def clip(value, limit=TEXT_LIMIT):
    return None if value is None else str(value)[:limit]


# The log

def read_log(path):
    """The entries of a log file. A line that is not JSON is skipped."""
    entries = []
    try:
        with open(path) as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except OSError:
        pass
    return entries


class Run:
    """The current ship run of one project and session."""

    def __init__(self, root, path, entries):
        self.root, self.path, self.entries = root, path, entries
        self.id = os.path.splitext(os.path.basename(path))[0]

    @staticmethod
    def current(root, session):
        """The current run, or None when there is none for this session."""
        try:
            with open(os.path.join(root, LOGS, CURRENT)) as handle:
                name = os.path.basename(handle.readline().strip())
        except OSError:
            return None
        path = os.path.join(root, LOGS, name)
        if not name or not os.path.isfile(path):
            return None
        entries = read_log(path)
        first = next((e for e in entries if e.get("event") == "run_start"), None)
        if not first:
            return None
        if session and first.get("session") and first["session"] != session:
            return None
        return Run(root, path, entries)

    @staticmethod
    def begin(root, session, **fields):
        folder = os.path.join(root, LOGS)
        os.makedirs(folder, exist_ok=True)
        ignore = os.path.join(folder, ".gitignore")
        if not os.path.exists(ignore):
            with open(ignore, "w") as handle:
                handle.write("*\n")
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        name, count = "ship-%s.jsonl" % stamp, 1
        while os.path.exists(os.path.join(folder, name)):
            count += 1
            name = "ship-%s-%d.jsonl" % (stamp, count)
        path = os.path.join(folder, name)
        open(path, "w").close()
        with open(os.path.join(folder, CURRENT), "w") as handle:
            handle.write(name + "\n")
        run = Run(root, path, [])
        run.add("run_start", session, **fields)
        return run

    def add(self, event, session, **fields):
        entry = {"t": now(), "run": self.id, "session": session, "event": event}
        entry.update(fields)
        with open(self.path, "a") as handle:
            handle.write(json.dumps(entry) + "\n")
        self.entries.append(entry)
        return entry

    def end(self):
        """The run is over: later turns of the session are not ship runs."""
        try:
            os.remove(os.path.join(self.root, LOGS, CURRENT))
        except OSError:
            pass

    def of(self, event):
        return [e for e in self.entries if e.get("event") == event]

    def since_stage(self):
        """The entries after the newest stage_start (all entries when there is none)."""
        last = 0
        for index, entry in enumerate(self.entries):
            if entry.get("event") == "stage_start":
                last = index
        return self.entries[last:]


# Git facts

def tips(root):
    """The hashes of the local branches and HEAD."""
    out = git(root, "for-each-ref", "--format=%(objectname)", "refs/heads/") or ""
    head = git(root, "rev-parse", "HEAD")
    return sorted(set(out.split() + ([head] if head else [])))


def excluding(base):
    """The stdin text that makes a git command skip each commit that base reaches."""
    return "".join("^%s\n" % h for h in base)


def where(root):
    return {"branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
            "head": git(root, "rev-parse", "--short", "HEAD")}


def trailers(body):
    return dict(re.findall(r"^([A-Z][A-Za-z-]*):[ \t]*(\S.*?)\s*$", body or "", re.M))


def new_commits(run):
    """(hash, subject) of each commit on any branch that the run made, oldest first."""
    start = run.of("run_start")[0]
    base = start.get("tips") or []
    out = git(run.root, "log", "--branches", "--reverse", "--format=%H%x1f%s", "--stdin",
              stdin=excluding(base))
    pairs = [tuple(line.split("\x1f", 1)) for line in (out or "").splitlines() if "\x1f" in line]
    seen = {h for h, _ in pairs}
    for entry in run.of("commit"):
        if entry.get("hash") not in seen and entry.get("subject"):
            pairs.append((entry["hash"], entry["subject"]))
    return pairs


def intent_of(root, rev):
    return trailers(git(root, "log", "-1", "--format=%b", rev)).get("Intent")


def proposed(run, pairs):
    """True when a pdlc branch ends with a Propose commit that this run made, and the intent
    of that commit is the intent of the newest commit of the run, and is in review there."""
    root = run.root
    made = {h for h, _ in pairs}
    wanted = intent_of(root, pairs[-1][0])
    branches = (git(root, "for-each-ref", "--format=%(refname:short) %(objectname)",
                    "refs/heads/pdlc/") or "").splitlines()
    for line in branches:
        branch, _, tip = line.partition(" ")
        if tip not in made or not (git(root, "log", "-1", "--format=%s", tip) or "").startswith("Propose "):
            continue
        intent = intent_of(root, tip)
        if wanted and intent and wanted != intent:
            continue
        names = (git(root, "ls-tree", "--name-only", branch, "pdlc/inbox/") or "").split()
        for name in names:
            base = os.path.basename(name)
            if not re.match(r"IN-\d+.*\.md$", base) or (intent and not base.startswith(intent)):
                continue
            text = git(root, "show", "%s:%s" % (branch, name)) or ""
            if re.search(r"\bStatus:[ \t]*in review\b", text):
                return True
    return False


def end_state(run):
    """(state, allowed): the end state of the run, and whether the turn may end."""
    pairs = new_commits(run)
    logged = {e.get("hash") for e in run.of("commit")}
    newest = pairs[-1][0] if pairs else None
    if any(subject.startswith("Stop ") and (h in logged or h == newest) for h, subject in pairs):
        return "stopped", True
    if not pairs:
        return "no work", True
    if proposed(run, pairs):
        return "proposed", True
    return "unrecorded", False


# Events

def on_prompt(data, root, session):
    if not START.match(data.get("prompt") or ""):
        # A normal prompt in a session with a current run: the user left the run (Esc, or a
        # resume after an API error). The run is over, so the Stop rule must not hold this turn.
        run = Run.current(root, session)
        if run:
            pairs = new_commits(run)
            run.add("turn_end", session, end_state="left by user", blocks=len(run.of("stop_blocked")),
                    last_subject=pairs[-1][1] if pairs else None, commits=len(pairs),
                    prompt=clip(data.get("prompt"), 300), **where(root))
            run.end()
        return None
    Run.begin(root, session, prompt=clip(data.get("prompt"), 300), plugin=plugin_version(),
              cwd=data.get("cwd"), tips=tips(root), **where(root))


def on_skill(data, root, session):
    name = (data.get("tool_input") or {}).get("skill") or ""
    run = Run.current(root, session)
    if name == "pdlc:ship":
        if not run:
            Run.begin(root, session, prompt=None, via="Skill", plugin=plugin_version(),
                      cwd=data.get("cwd"), tips=tips(root), **where(root))
        return
    if run and name.startswith("pdlc:"):
        run.add("stage_start", session, stage=name, **where(root))


def on_bash(data, root, session):
    run = Run.current(root, session)
    if not run:
        return
    head = git(root, "rev-parse", "HEAD")
    if not head or any(e.get("hash") == head for e in run.of("commit")):
        return
    start = run.of("run_start")[0].get("tips") or []
    if not git(root, "rev-list", "-1", "HEAD", "--stdin", stdin=excluding(start)):
        return  # a commit from before the run
    subject = git(root, "log", "-1", "--format=%s") or ""
    body = git(root, "log", "-1", "--format=%b") or ""
    files = (git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD") or "").split()
    run.add("commit", session, hash=head, subject=subject, trailers=trailers(body),
            files=len(files), stage_end=bool(STAGE_END.match(subject)), **where(root))


def agent_fields(data):
    tool = data.get("tool_input") or {}
    return {"agent": tool.get("subagent_type") or tool.get("agent_type"),
            "description": clip(tool.get("description"), 200), "tool_use_id": data.get("tool_use_id")}


def on_agent_start(data, root, session):
    run = Run.current(root, session)
    if not run:
        return
    fields = agent_fields(data)
    before = [e for e in run.since_stage() if e.get("event") == "agent_start" and e.get("agent") == fields["agent"]]
    run.add("agent_start", session, attempt=len(before) + 1, **fields)


def seconds_between(first, second):
    try:
        return (datetime.datetime.fromisoformat(second) - datetime.datetime.fromisoformat(first)).total_seconds()
    except (TypeError, ValueError):
        return None


def on_agent_end(data, root, session):
    run = Run.current(root, session)
    if not run:
        return
    fields = agent_fields(data)
    started = None
    for entry in run.of("agent_start"):
        if fields["tool_use_id"] and entry.get("tool_use_id") == fields["tool_use_id"]:
            started = entry
    if not started:
        done = {e.get("tool_use_id") for e in run.of("agent_end")}
        open_starts = [e for e in run.of("agent_start")
                       if e.get("agent") == fields["agent"] and e.get("tool_use_id") not in done]
        started = open_starts[-1] if open_starts else None
    seconds = seconds_between(started["t"], now()) if started else None
    run.add("agent_end", session, seconds=seconds, attempt=started.get("attempt") if started else None, **fields)


def on_failure(data, root, session):
    run = Run.current(root, session)
    if not run:
        return
    error = data.get("error")
    if error is None:
        error = data.get("tool_response")
    text = error if isinstance(error, str) else json.dumps(error)
    run.add("tool_error", session, tool=data.get("tool_name"), error=clip(text),
            rate_limit=bool(RATE_LIMIT.search(text or "")), **where(root))


def on_subagent_stop(data, root, session):
    run = Run.current(root, session)
    if run:
        run.add("agent_stop", session, agent=data.get("agent_type"), agent_id=data.get("agent_id"))


def on_stop_failure(data, root, session):
    """The turn ended on an API error. The run stays current, so a resume continues the log."""
    run = Run.current(root, session)
    if not run:
        return None
    error, details = data.get("error"), data.get("error_details")
    text = "%s %s" % (error, details)
    run.add("turn_failed", session, error=clip(error), error_details=clip(details),
            last_message=clip(data.get("last_assistant_message")),
            rate_limit=bool(re.search(r"rate|429|529|overloaded", text, re.I)), **where(root))
    return None


def on_stop(data, root, session):
    """Returns the JSON to print, or None."""
    run = Run.current(root, session)
    if not run:
        return None
    state, allowed = end_state(run)
    blocks = len(run.of("stop_blocked"))
    pairs = new_commits(run)
    last = pairs[-1][1] if pairs else None
    dirty = len((git(root, "status", "--porcelain") or "").splitlines())
    common = dict(last_subject=last, commits=len(pairs), dirty_files=dirty,
                  stop_hook_active=data.get("stop_hook_active"), **where(root))
    if not allowed and blocks < MAX_BLOCKS:
        run.add("stop_blocked", session, block=blocks + 1, reason=REASON, **common)
        return {"decision": "block", "reason": REASON}
    run.add("turn_end", session, end_state=state, blocks=blocks,
            transcript=data.get("transcript_path"),
            last_message=clip(data.get("last_assistant_message")), **common)
    run.end()
    return None


def dispatch(data):
    event = data.get("hook_event_name")
    tool = data.get("tool_name")
    session = data.get("session_id")
    root = project_root(data.get("cwd") or os.getcwd())
    if not root or not isinstance(event, str):
        return None
    if event == "UserPromptSubmit":
        return on_prompt(data, root, session)
    if event == "PostToolUse":
        if tool == "Skill":
            return on_skill(data, root, session)
        if tool == "Bash":
            return on_bash(data, root, session)
        if tool in ("Agent", "Task"):
            return on_agent_end(data, root, session)
    elif event == "PreToolUse" and tool in ("Agent", "Task"):
        return on_agent_start(data, root, session)
    elif event == "PostToolUseFailure":
        return on_failure(data, root, session)
    elif event == "SubagentStop":
        return on_subagent_stop(data, root, session)
    elif event == "StopFailure":
        return on_stop_failure(data, root, session)
    elif event == "Stop":
        return on_stop(data, root, session)
    return None


def hook():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return 0
    except ValueError:
        return 0
    try:
        out = dispatch(data)
    except Exception as error:  # the hook never fails a tool call
        try:
            root = project_root(data.get("cwd") or os.getcwd())
            run = Run.current(root, data.get("session_id")) if root else None
            if run:
                run.add("hook_error", data.get("session_id"), hook_event=data.get("hook_event_name"),
                        error=clip("%s: %s" % (type(error).__name__, error)))
        except Exception:
            pass
        return 0
    if out:
        print(json.dumps(out))
    return 0


# The summary

def stage_rows(entries):
    """One dict for each stage: the entries between a stage_start and the next one."""
    stages, current = [], None
    for entry in entries:
        if entry.get("event") == "stage_start":
            current = {"stage": entry.get("stage"), "entries": []}
            stages.append(current)
        elif entry.get("event") in ("turn_end", "stop_blocked"):
            continue
        if current is None and entry.get("event") not in ("run_start",):
            current = {"stage": "(before the first stage)", "entries": []}
            stages.append(current)
        if current is not None:
            current["entries"].append(entry)
    return stages


def clock(text):
    return (text or "")[11:19] or "-"


def summary(path):
    entries = read_log(path)
    start = next((e for e in entries if e.get("event") == "run_start"), {})
    lines = ["run %s, started %s on %s at %s, plugin %s" % (
        start.get("run") or os.path.basename(path), start.get("t"), start.get("branch"),
        start.get("head"), start.get("plugin"))]
    header = ["stage", "start", "end", "outcome", "last commit", "retries", "tool errors", "rate limits"]
    rows = []
    for stage in stage_rows(entries):
        items = stage["entries"]
        commits = [e for e in items if e.get("event") == "commit"]
        ends = [e for e in commits if e.get("stage_end")]
        errors = [e for e in items if e.get("event") == "tool_error"]
        rows.append([
            stage["stage"], clock(items[0].get("t") if items else None),
            clock(items[-1].get("t") if items else None),
            (ends[-1]["subject"] if ends else "none")[:40],
            (commits[-1]["subject"] if commits else "-")[:40],
            str(sum(1 for e in items if e.get("event") == "agent_start" and (e.get("attempt") or 1) >= 2)),
            str(len(errors)), str(sum(1 for e in errors if e.get("rate_limit")))])
    table = [header, ["-" * len(h) for h in header]] + rows
    widths = [max(len(r[i]) for r in table) for i in range(len(header))]
    for index, row in enumerate(table):
        cells = [cell.ljust(widths[i]) if i < 5 else cell.rjust(len(header[i]) if index < 2 else widths[i])
                 for i, cell in enumerate(row)]
        lines.append((" | ".join(cells)).rstrip())
    ended = [e for e in entries if e.get("event") == "turn_end"]
    blocks = sum(1 for e in entries if e.get("event") == "stop_blocked")
    bad = sum(1 for e in entries if e.get("event") == "hook_error")
    if ended:
        lines.append("end state: %s (%d block%s, last subject: %s)" % (
            ended[-1].get("end_state"), blocks, "" if blocks == 1 else "s", ended[-1].get("last_subject")))
    failed = [e for e in entries if e.get("event") == "turn_failed"]
    if failed and not ended:
        lines.append("the turn failed: %s%s (rate limit: %s); the log ends there" % (
            failed[-1].get("error"), " - %s" % failed[-1]["error_details"] if failed[-1].get("error_details") else "",
            "yes" if failed[-1].get("rate_limit") else "no"))
    elif not ended:
        lines.append(NO_END + ("" if not blocks else " (%d stop block%s logged)" % (blocks, "" if blocks == 1 else "s")))
    if bad:
        lines.append("hook errors: %d (see the hook_error entries)" % bad)
    return "\n".join(lines)


def main(argv):
    if len(argv) >= 2 and argv[1] == "summary":
        if len(argv) < 3:
            print("usage: shiplog.py summary <log>", file=sys.stderr)
            return 2
        print(summary(argv[2]))
        return 0
    return hook()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
