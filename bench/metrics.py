#!/usr/bin/env python3
"""The full measures of one pdlc run: time, loops, failures, tokens, and the work it made.

Usage: metrics.py [--slow] [--spread] RUN_DIR ...

The script measures each saved run, and writes metrics.json next to it. Then it prints one
column for each run. The flag --slow adds the code quality and the check strength. The flag
--spread prints the range of each measure over the runs.

RUN_DIR holds run1.json and run1.stream.jsonl, as `run_bench.py e2e --runs 1` writes them. The
project of the run must still exist for the measures from git. When it is gone, those
measures are None.

The stream gives these measures:
  - Time: the wall time, the API time, and the time of the main session by kind of work.
  - Context: the largest and the mean context of a main turn.
  - Loops: the check runs and the builds, with their failures, in each stage. For each
    builder call, the count of check runs until the first passing run.
  - Agents: the calls of each agent.
  - Failures: tool errors by tool, hook blocks by hook, permission denials, rate limits.
The git history of the project gives these measures:
  - Rounds: each lock, each `verify` round, each recording, and each send-back by stage.
  - Reviews: the failed results of each remit, and their problems.
  - Work: the changes, the statuses of the requirements, and the intents for new behaviour.
    Also the commits, the lines that the change branches add, and the requirements with
    checks.
"""
import collections
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_bench as rb  # noqa: E402

# The hooks of pdlc, by the hook event and the tool.
HOOKS = {"PreToolUse:Bash": "stdin", "PostToolUse:Bash": "commits"}
# Output that shows a failed run of checks or a failed build, also when a pipe hid the exit code.
FAILED = re.compile(r"^FAILED \(|^Traceback |test result: FAILED|^error(\[E\d+\])?: |could not compile|"
                    r"panicked at|^# fail [1-9]|^not ok \d|^FAIL\b|Ran 0 tests", re.M)
REQ = re.compile(r"(?<![A-Za-z0-9])((?:JOB|CAP|DES)[-_][A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*?)[._](R\d+)(?!\d)")


def command_kind(command, fixture):
    """The kind of work of a Bash command."""
    spec = rb.FIXTURES[fixture]
    if "record_gif" in command:
        return "recording"
    if "check_writing" in command:
        return "writing check"
    if re.search(spec.get("check_pattern", r"unittest|pytest"), command):
        return "checks"
    if spec.get("build_pattern") and re.search(spec["build_pattern"], command):
        return "build"
    if re.match(r"(cd [^&;]+&&\s*)?git\b", command.strip()):
        return "git"
    if re.search(r"pdlc/bin/", command):
        return "pdlc script"
    return "other"


def result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


def measure_stream(items, fixture="wordfreq"):
    """The measures that the event stream of one run gives."""
    stage = "ship"
    calls = {}          # tool use id -> {"stage", "kind", "tool", "main", "agent"}
    agent_of = {}       # Agent tool use id -> (stage, agent type)
    results = {}        # tool use id -> is_error
    main_events = []    # (time, "model" or tool use id)
    contexts = []
    hooks = collections.Counter()
    hook_lines = collections.Counter()
    tool_errors = collections.Counter()
    rate_limits = 0
    result = {}
    for item in items:
        event, t = item["e"], item["t"]
        kind = event.get("type")
        if kind == "result":
            result = event
        elif kind == "rate_limit_event":
            rate_limits += 1
        elif kind == "system" and event.get("subtype") == "hook_response":
            if str(event.get("exit_code")) not in ("0", "None"):
                name = event.get("hook_name") or "?"
                hook = HOOKS.get(name, "guard" if name.startswith("PreToolUse:") else name)
                text = event.get("stderr") or event.get("output") or ""
                if hook == "commits":
                    hook = "commits: writing" if "writing finding" in text else "commits: subject or trailers"
                hooks[hook] += 1
                hook_lines[hook] += sum(1 for line in text.splitlines() if line.startswith("  - "))
        elif kind == "assistant":
            message, parent = event.get("message", {}), event.get("parent_tool_use_id")
            if parent is None:
                usage = message.get("usage") or {}
                context = sum(usage.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                        "cache_read_input_tokens"))
                if context and (not contexts or contexts[-1][0] != message.get("id")):
                    contexts.append((message.get("id"), context))
                main_events.append((t, "model"))
            for block in message.get("content", []):
                if block.get("type") != "tool_use" or block["id"] in calls:
                    continue
                name, args = block["name"], block.get("input") or {}
                if parent is None:
                    stage = rb.stage_from_call(name, args, stage) or stage
                    here = stage
                else:
                    here = agent_of.get(parent, (stage, None))[0]
                if name in ("Agent", "Task"):
                    label = args.get("subagent_type") or "general-purpose"
                    agent_of[block["id"]] = (rb.agent_stage(label, args.get("prompt"), here) or here, label)
                    work = "agent"
                elif name == "Bash":
                    work = command_kind(args.get("command") or "", fixture)
                else:
                    work = name
                calls[block["id"]] = {"stage": here, "kind": work, "tool": name, "main": parent is None,
                                      "parent": parent, "t": t,
                                      "agent": agent_of.get(parent, (None, "main" if parent is None else "?"))[1]}
        elif kind == "user":
            for block in (event.get("message", {}).get("content") or []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_id = block.get("tool_use_id")
                    failed = bool(block.get("is_error"))
                    if tool_id in calls and calls[tool_id]["kind"] in ("checks", "build", "recording"):
                        failed = failed or FAILED.search(result_text(block)) is not None
                    results[tool_id] = failed
                    if tool_id in calls:
                        calls[tool_id]["seconds"] = max(0.0, t - calls[tool_id]["t"])
                    if tool_id in calls and event.get("parent_tool_use_id") is None:
                        main_events.append((t, tool_id))
                    if block.get("is_error") and tool_id in calls:
                        tool_errors["%s (%s)" % (calls[tool_id]["tool"], calls[tool_id]["agent"])] += 1

    # The time of each kind of work in every session, the agents too. Agents can run at the same
    # time, so these times can add up to more than the wall time.
    tool_time = collections.defaultdict(lambda: collections.defaultdict(float))
    for call in calls.values():
        if call["kind"] in ("checks", "build", "recording") and "seconds" in call:
            tool_time[call["agent"]][call["kind"]] += call["seconds"]
    # The time of the main session: each gap goes to the model, or to the work whose result ends it.
    time_by_kind = collections.Counter()
    main_events.sort(key=lambda pair: pair[0])
    for (t0, _), (t1, ref) in zip(main_events, main_events[1:]):
        time_by_kind["model" if ref == "model" else calls[ref]["kind"]] += t1 - t0

    loops = collections.defaultdict(lambda: {"check runs": 0, "check failures": 0, "builds": 0,
                                             "build failures": 0, "recordings": 0, "recording failures": 0})
    builder_checks = collections.defaultdict(list)
    for tool_id, call in calls.items():
        failed = results.get(tool_id, False)
        entry = loops[call["stage"]]
        if call["kind"] == "checks":
            entry["check runs"] += 1
            entry["check failures"] += failed
            if call["agent"] == "pdlc:builder":
                builder_checks[call["parent"]].append(failed)
        elif call["kind"] == "build":
            entry["builds"] += 1
            entry["build failures"] += failed
        elif call["kind"] == "recording":
            entry["recordings"] += 1
            entry["recording failures"] += failed
    # For each builder call, the check runs until the first run that passed (None: none passed).
    until_pass = [next((i + 1 for i, failed in enumerate(runs) if not failed), None)
                  for tool_id, runs in builder_checks.items()]
    builder_calls = sum(1 for _, label in agent_of.values() if label == "pdlc:builder")
    until_pass += [0] * (builder_calls - len(until_pass))
    agents = collections.Counter("%s/%s" % (stage, label) for stage, label in agent_of.values())
    usage = result.get("usage") or {}
    return {
        "time": {"wall_s": round(main_events[-1][0], 1) if main_events else 0.0,
                 "api_s": round((result.get("duration_api_ms") or 0) / 1000, 1),
                 "main_session": {k: round(v, 1) for k, v in time_by_kind.most_common()},
                 "work_by_session": {agent: {k: round(v, 1) for k, v in kinds.items()}
                                     for agent, kinds in sorted(tool_time.items())}},
        "context": {"main_turns": len(contexts),
                    "peak": max((c for _, c in contexts), default=0),
                    "mean": round(statistics.mean(c for _, c in contexts)) if contexts else 0},
        "tokens": {"input": usage.get("input_tokens", 0), "cache_write": usage.get("cache_creation_input_tokens", 0),
                   "cache_read": usage.get("cache_read_input_tokens", 0), "output": usage.get("output_tokens", 0),
                   "cost_usd": result.get("total_cost_usd", 0.0)},
        "loops": {stage: dict(entry) for stage, entry in loops.items() if any(entry.values())},
        "builder_check_runs_until_green": until_pass,
        "agents": dict(sorted(agents.items())),
        "failures": {"tool errors": dict(tool_errors.most_common()),
                     "hook blocks": dict(hooks.most_common()),
                     "hook findings": dict(hook_lines.most_common()),
                     "permission denials": len(result.get("permission_denials") or []),
                     "rate limits": rate_limits,
                     "is_error": bool(result.get("is_error"))},
    }


def git(project, *args):
    return subprocess.run(["git", *args], cwd=project, capture_output=True, text=True).stdout


def measure_project(project, fixture="wordfreq"):
    """The measures that the git history of a finished run gives. None when the project is gone."""
    project = Path(project)
    if not (project / ".git").exists():
        return None
    subjects = git(project, "log", "--all", "--format=%s").splitlines()
    count = lambda prefix: sum(1 for s in subjects if s.startswith(prefix))  # noqa: E731
    says = lambda words: sum(1 for s in subjects if re.search(words, s, re.I))  # noqa: E731
    send_backs = collections.Counter(s.rsplit(":", 1)[-1].strip() for s in subjects if s.startswith("Send back "))
    # Each version of each review result in the history, also the ones that a later round replaced.
    reviews = collections.defaultdict(lambda: {"results": 0, "failed": 0, "problems": 0})
    for commit in git(project, "log", "--all", "--format=%H", "--", "pdlc/*/review/*/result.md",
                      "pdlc/*/*/review/*/result.md").split():
        for path in git(project, "show", "--name-only", "--format=", commit).split():
            found = re.search(r"/review/([a-z]+)/result\.md$", path)
            if not found:
                continue
            text = git(project, "show", "%s:%s" % (commit, path))
            remit = reviews[found.group(1)]
            remit["results"] += 1
            if re.match(r"\s*Result:\s*fail", text, re.I):
                remit["failed"] += 1
                problems = text.split("Problems:", 1)[-1].split("\n\n", 1)[0]
                remit["problems"] += sum(1 for line in problems.splitlines() if line.strip().startswith("- "))
    branches = [b for b in git(project, "branch", "--format=%(refname:short)").split() if b != "main"]
    tip = max(branches, key=lambda b: git(project, "log", "-1", "--format=%ct", b).strip() or "0", default="main")
    lines = collections.Counter()
    for row in git(project, "diff", "--numstat", "main..." + tip).splitlines():
        added, removed, path = (row.split("\t") + ["", "", ""])[:3]
        if not added.isdigit():
            continue
        if re.match(r"pdlc/.*/review/", path):
            part = "review packets"
        elif path.startswith("pdlc/"):
            part = "pdlc records"
        elif re.search(r"(^|/)(tests?|spec|acceptance|__tests__)/|acceptance", path):
            part = "checks"
        elif path.endswith(".md"):
            part = "docs"
        else:
            part = "app code"
        lines[part + " added"] += int(added)
        lines[part + " removed"] += int(removed)
    tagged = set()
    for path in git(project, "ls-tree", "-r", "--name-only", tip).splitlines():
        if not path.startswith("pdlc/") and re.search(r"(^|/)(tests?|spec|acceptance|__tests__)/|acceptance", path):
            for spec, number in REQ.findall(git(project, "show", "%s:%s" % (tip, path))):
                tagged.add("%s.%s" % (re.sub(r"_", "-", spec), number))
    intents = git(project, "ls-tree", "-r", "--name-only", tip, "pdlc/inbox").split()
    awaiting = sum(1 for p in intents if p.endswith(".md")
                   and "Awaits approval:" in git(project, "show", "%s:%s" % (tip, p)))
    statuses = collections.Counter()
    for path in git(project, "ls-tree", "-r", "--name-only", tip, "pdlc/specs").split():
        # The status line of each requirement follows its "### <ID>" heading.
        for part in git(project, "show", "%s:%s" % (tip, path)).split("\n### ")[1:]:
            found = re.search(r"^Status:\s*([a-z ]+?)(?:\s*·|$)", part, re.M)
            if found:
                statuses[found.group(1)] += 1
    return {
        "rounds": {"acceptance locks": says(r"\block (the )?acceptance"), "tests locks": says(r"\block (the )?tests"),
                   "verify rounds": count("Verify CH-"), "recordings": count("Visual review CH-"),
                   "send-backs": dict(send_backs), "stops": count("Stop ")},
        "reviews": {remit: dict(data) for remit, data in sorted(reviews.items())},
        "work": {"changes": len({b for b in branches if b.startswith("pdlc/CH-")}),
                 "commits": len(subjects), "intents awaiting approval": awaiting,
                 "requirement statuses": dict(statuses.most_common()),
                 "lines": dict(sorted(lines.items())), "requirements with checks": len(tagged)},
    }


def clone_at(project, ref):
    """A throwaway clone of the project, checked out at ref. The caller removes it."""
    import tempfile
    folder = Path(tempfile.mkdtemp(prefix="pdlc-bench-measure-")) / "app"
    subprocess.run(["git", "clone", "-q", str(project), str(folder)], check=True)
    subprocess.run(["git", "checkout", "-q", ref], cwd=folder, check=True)
    tools = Path(project) / "pdlc" / ".tools"
    if tools.exists() and not (folder / "pdlc" / ".tools").exists():
        (folder / "pdlc" / ".tools").symlink_to(tools.resolve())
    return folder


def tip_of(project):
    branches = [b for b in git(project, "branch", "--format=%(refname:short)").split() if b != "main"]
    return max(branches, key=lambda b: git(project, "log", "-1", "--format=%ct", b).strip() or "0", default="main")


CHECK_PATH = re.compile(r"(^|/)(tests?|spec|acceptance|__tests__)/|acceptance")


def lint_count(folder, spec):
    """The findings of the linter: (in app code, in checks). None when the linter fails."""
    try:
        proc = subprocess.run(spec["lint"], cwd=folder, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = [line for line in (proc.stdout + proc.stderr).splitlines() if re.match(spec["lint_pattern"], line)]
    checks = sum(1 for line in lines if CHECK_PATH.search(line.split(":", 1)[0]))
    return len(lines) - checks, checks


def measure_quality(project, fixture="wordfreq"):
    """The findings of the linter of the language on main, and on the tip of the run."""
    import shutil
    spec = rb.FIXTURES[fixture]
    project = Path(project)
    if not spec.get("lint") or not (project / ".git").exists():
        return None
    out = {}
    for name, ref in (("main", "main"), ("tip", tip_of(project))):
        folder = clone_at(project, ref)
        try:
            out[name] = lint_count(folder, spec)
        finally:
            shutil.rmtree(folder.parent, ignore_errors=True)
    if None in (out["main"], out["tip"]):
        out["new"] = out["new in app code"] = out["new in checks"] = None
    else:
        out["new in app code"] = out["tip"][0] - out["main"][0]
        out["new in checks"] = out["tip"][1] - out["main"][1]
        out["new"] = out["new in app code"] + out["new in checks"]
        out["main"], out["tip"] = sum(out["main"]), sum(out["tip"])
    out["linter"] = spec["lint"][0] if spec["lint"][0] != "cargo" else "cargo clippy"
    return out


# Small faults for the check strength. Each operator changes one place in one added line.
MUTATIONS = [
    ("true to false", r"\btrue\b", "false"), ("false to true", r"\bfalse\b", "true"),
    ("True to False", r"\bTrue\b", "False"), ("False to True", r"\bFalse\b", "True"),
    ("== to !=", r"==", "!="), ("!= to ==", r"!=", "=="),
    ("&& to ||", r"&&", "||"), ("|| to &&", r"\|\|", "&&"),
    (">= to >", r">=", ">"), ("<= to <", r"<=", "<"),
    ("+ 1 to + 2", r"\+ 1\b", "+ 2"), ("- 1 to - 2", r"- 1\b", "- 2"),
    ("(= to (not=", r"\(= ", "(not= "), ("(inc to (dec", r"\(inc\b", "(dec"),
    ("(when to (when-not", r"\(when ", "(when-not "),
    ("a letter of a text", r'"([^"\\]*?)([A-Za-z])', None),
]


def mutants(lines):
    """Each fault: (file, line number, name, new line). `lines` is (file, number, text)."""
    out = []
    for path, number, text in lines:
        stripped = text.strip()
        if not stripped or stripped.startswith(("//", "#", ";", "--")):
            continue
        for name, pattern, replacement in MUTATIONS:
            found = re.search(pattern, text)
            if not found:
                continue
            if replacement is None:  # change the first letter inside a string literal
                letter = found.group(2)
                swap = "Y" if letter == "X" else "X"
                new = text[:found.start(2)] + swap + text[found.end(2):]
            else:
                new = text[:found.start()] + replacement + text[found.end():]
            out.append((path, number, name, new))
        if stripped.endswith(";") or (not stripped.endswith((":", "{", "(", "[", ",")) and "=" not in stripped):
            indent = text[:len(text) - len(text.lstrip())]
            out.append((path, number, "remove the line", None))
    return out


def run_ok(command, folder, timeout=300):
    try:
        return subprocess.run(command, cwd=folder, shell=isinstance(command, str), capture_output=True,
                              timeout=timeout).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def check_commands(folder):
    """The "all" command and the acceptance command of the project, from pdlc/config.md."""
    config = (folder / "pdlc" / "config.md").read_text()
    get = lambda name: (re.search(r"^- %s:\s*`([^`]+)`" % name, config, re.M) or [None, None])[1]  # noqa: E731
    acceptance, pattern = get("acceptance"), get("acceptance file")
    files = []
    if pattern and "{intent}" in pattern:
        rx = re.compile("^%s$" % r"IN[-_]?\d+".join(re.escape(part) for part in pattern.split("{intent}")), re.I)
        files = [f for f in git(folder, "ls-files").split() if rx.match(f)]
    if acceptance and files:
        acceptance = acceptance.replace("{files}", " ".join(files))
    else:
        acceptance = None
    return get("all"), acceptance


def measure_strength(project, fixture="wordfreq", limit=20):
    """How many small faults in the code that the run added the checks of pdlc catch.

    For each fault, the checks of the project run: its "all" command and its acceptance
    command. The probes of the bench run too. A fault that the probes catch but the checks
    miss is an escape: a user would see it, and pdlc did not catch it. A fault that does not
    compile is not counted.
    """
    import shutil
    spec = rb.FIXTURES[fixture]
    project = Path(project)
    if not (project / ".git").exists():
        return None
    tip = tip_of(project)
    folder = clone_at(project, tip)
    try:
        all_checks, acceptance = check_commands(folder)
        # The diffs come from the project, because the clone has only the branch of the tip.
        code = [f for f in git(project, "diff", "--name-only", "main..." + tip).split()
                if not f.startswith("pdlc/") and not f.endswith(".md")
                and not re.search(r"(^|/)(tests?|spec|acceptance|__tests__)/|acceptance", f)
                and (folder / f).is_file()]
        added = []
        for path in code:
            numbers = set()
            for hunk in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", git(project, "diff", "-U0", "main..." + tip, "--", path), re.M):
                start, count = int(hunk[0]), int(hunk[1] or 1)
                numbers.update(range(start, start + count))
            text = (folder / path).read_text().splitlines()
            added += [(path, n, text[n - 1]) for n in sorted(numbers) if 0 < n <= len(text)]
        candidates = mutants(added)
        def checks_pass():
            return run_ok(all_checks, folder) and (acceptance is None or run_ok(acceptance, folder))
        if not all_checks or not checks_pass():
            return {"error": "the checks of the run do not pass at its tip", "candidates": len(candidates)}
        step = max(1, len(candidates) // (limit * 2)) if candidates else 1
        results = []
        for path, number, name, new in candidates[::step]:
            if len(results) >= limit:
                break
            file = folder / path
            original = file.read_text()
            lines = original.splitlines(keepends=True)
            ending = "\n" if lines[number - 1].endswith("\n") else ""
            if new is None:
                indent = lines[number - 1][:len(lines[number - 1]) - len(lines[number - 1].lstrip())]
                new = indent + spec.get("noop", "")
            lines[number - 1] = new + ending
            file.write_text("".join(lines))
            try:
                if spec.get("compile") and not run_ok(spec["compile"], folder):
                    continue  # a fault that does not compile proves nothing
                caught = not checks_pass()
                probes = rb.fixture_probes(folder, fixture)
                seen = probes["passed"] < probes["total"]
                results.append({"file": path, "line": number, "fault": name, "caught": caught, "user_sees": seen})
            finally:
                file.write_text(original)
        caught = sum(r["caught"] for r in results)
        return {"faults": len(results), "caught": caught, "missed": len(results) - caught,
                "escapes": sum(1 for r in results if r["user_sees"] and not r["caught"]),
                "candidates": len(candidates), "score": round(caught / len(results), 2) if results else None,
                "details": results}
    finally:
        shutil.rmtree(folder.parent, ignore_errors=True)


def measure(run_dir, fixture=None, slow=False):
    """The measures of one saved run folder. With slow, also the code quality and the check
    strength, which build and test the app again (about a minute)."""
    run_dir = Path(run_dir)
    run = json.loads((run_dir / "run1.json").read_text())
    summary_path = run_dir / "e2e.json"
    fixture = fixture or (json.loads(summary_path.read_text()).get("fixture") if summary_path.exists() else None) \
        or "wordfreq"
    items = [json.loads(line) for line in (run_dir / "run1.stream.jsonl").read_text().splitlines() if line.strip()]
    out = measure_stream(items, fixture)
    out["git"] = measure_project(run.get("project", ""), fixture)
    outcome = run.get("outcome", {})
    out["outcome"] = {"probes": "%s of %s" % (outcome.get("probes", {}).get("passed"), outcome.get("probes", {}).get("total")),
                      "checks pass": outcome.get("unit", {}).get("ok"), "checks": outcome.get("unit", {}).get("ran"),
                      "finished": rb.completed(run) if outcome.get("merge_check") is not None else False,
                      "writing findings left": (outcome.get("writing") or {}).get("count")}
    out["fixture"] = fixture
    if slow:
        out["quality"] = measure_quality(run.get("project", ""), fixture)
        strength = measure_strength(run.get("project", ""), fixture)
    else:
        saved = run_dir / "metrics.json"
        old = json.loads(saved.read_text()) if saved.exists() else {}
        out["quality"] = old.get("quality") or (run.get("metrics") or {}).get("quality")
        strength = old.get("strength") or (run.get("metrics") or {}).get("strength")
    out["strength"] = strength
    return out


def rows(data):
    """The main measures of one run, as (name, value) pairs for a table."""
    loops = data["loops"]
    total = lambda key: sum(entry.get(key, 0) for entry in loops.values())  # noqa: E731
    out = [("cost $", "%.2f" % data["tokens"]["cost_usd"]), ("wall s", "%.0f" % data["time"]["wall_s"]),
           ("main turns", data["context"]["main_turns"]), ("peak context", data["context"]["peak"]),
           ("output tokens", data["tokens"]["output"]), ("cache read tokens", data["tokens"]["cache_read"]),
           ("main model s", "%.0f" % data["time"]["main_session"].get("model", 0)),
           ("main wait on agents s", "%.0f" % data["time"]["main_session"].get("agent", 0)),
           ("check runs (failed)", "%d (%d)" % (total("check runs"), total("check failures"))),
           ("builds (failed)", "%d (%d)" % (total("builds"), total("build failures"))),
           ("builder runs to green", data["builder_check_runs_until_green"]),
           ("tool errors", sum(data["failures"]["tool errors"].values())),
           ("hook blocks", sum(data["failures"]["hook blocks"].values())),
           ("permission denials", data["failures"]["permission denials"])]
    git_data = data.get("git")
    if git_data:
        rounds, work = git_data["rounds"], git_data["work"]
        failed = sum(r["failed"] for r in git_data["reviews"].values())
        out += [("changes", work["changes"]), ("verify rounds", rounds["verify rounds"]),
                ("recordings", rounds["recordings"]), ("send-backs", sum(rounds["send-backs"].values())),
                ("failed reviews", failed), ("stops", rounds["stops"]),
                ("app lines added", work["lines"].get("app code added", 0)),
                ("check lines added", work["lines"].get("checks added", 0)),
                ("requirements with checks", work["requirements with checks"])]
    work = data["time"].get("work_by_session", {})
    out += [("check time s, all sessions", "%.0f" % sum(k.get("checks", 0) for k in work.values())),
            ("build time s, all sessions", "%.0f" % sum(k.get("build", 0) for k in work.values()))]
    quality, strength = data.get("quality"), data.get("strength")
    if quality:
        out.append(("new lint findings: app, checks", "%s, %s" % (quality.get("new in app code"),
                                                                  quality.get("new in checks"))))
    if strength and "faults" in strength:
        out += [("faults caught", "%d of %d" % (strength["caught"], strength["faults"])),
                ("faults a user sees, missed", strength["escapes"])]
    outcome = data["outcome"]
    out += [("probes", outcome["probes"]), ("finished", outcome["finished"]),
            ("writing findings left", outcome["writing findings left"])]
    return out


def number(value):
    """The number in a table value, or None: "3 (1)" gives 3, "8 of 8" gives 8."""
    found = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(value))
    return float(found.group(1)) if found and not isinstance(value, bool) else None


def spread(columns):
    """For each measure, the lowest, the mean and the highest value of the runs, and the
    range as a share of the mean."""
    out = []
    for name in columns[0][1]:
        values = [number(values.get(name)) for _, values in columns]
        values = [v for v in values if v is not None]
        if len(values) < len(columns) or not values:
            out.append((name, "", "", "", ""))
            continue
        mean = statistics.mean(values)
        share = "%.0f%%" % (100 * (max(values) - min(values)) / mean) if mean else ""
        show = lambda v: "%.0f" % v if abs(v) >= 100 or v == int(v) else "%.2f" % v  # noqa: E731
        out.append((name, show(min(values)), show(mean), show(max(values)), share))
    return out


def main(argv):
    """metrics.py [--slow] [--spread] RUN_DIR ...

    The flag --slow also measures the code quality and the check strength of each run. The
    flag --spread prints the lowest, the mean and the highest value of each measure. It
    prints them in place of one column for each run.
    """
    slow, show_spread = "--slow" in argv, "--spread" in argv
    folders = [a for a in argv if not a.startswith("--")]
    if not folders:
        print(main.__doc__)
        return 1
    columns = []
    for folder in folders:
        data = measure(folder, slow=slow)
        (Path(folder) / "metrics.json").write_text(json.dumps(data, indent=1))
        columns.append((Path(folder).name, dict(rows(data))))
    names = list(dict.fromkeys(name for _, values in columns for name in values))
    columns = [(label, {name: values.get(name, "") for name in names}) for label, values in columns]
    width = max(len(n) for n in names)
    if show_spread:
        print(" " * width + "%12s%12s%12s%8s" % ("lowest", "mean", "highest", "range"))
        for name, low, mean, high, share in spread(columns):
            print(name.ljust(width) + "%12s%12s%12s%8s" % (low, mean, high, share))
    else:
        print(" " * width + "".join("%14s" % label[:13] for label, _ in columns))
        for name in names:
            print(name.ljust(width) + "".join("%14s" % str(values[name])[:13] for _, values in columns))
    print("wrote metrics.json in each folder")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
