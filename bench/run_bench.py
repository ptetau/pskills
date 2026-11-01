#!/usr/bin/env python3
"""pdlc benchmark: run pdlc on a fixture app, measure tokens and time, and gate an edit.

Commands:
  run_bench.py init-fixture      run /pdlc:init once and keep its pdlc/ folder in the fixture
  run_bench.py e2e --label L     run the scripted intent through /pdlc:ship, one run
  run_bench.py rebuild SOURCE    build the app again from the specs alone, and score it
  metrics.py RUN_DIR ...          the full measures of saved runs: time, loops, failures,
                                 tokens, rounds, reviews and the work, in one table
  run_bench.py gate BASELINE CANDIDATE
                                 compare two result files and print the verdict
                                 With `--target writing`, the gate judges the writing findings
                                 that a run leaves in its specs, change spec and README.

A run uses `claude -p` with the plugin folder given by --plugin, in a throwaway copy of
bench/fixture-app. Nothing in the copy comes back into the repository.
"""
import argparse
import builtins
import importlib.util
import json
import keyword
import os
import re
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
FIXTURE = HERE / "fixture-app"
DEFAULT_PLUGIN = REPO / "plugins" / "pdlc"
TOOLS_CACHE = Path(os.environ.get("PDLC_BENCH_TOOLS", Path.home() / ".cache" / "pdlc-bench" / "tools"))

MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
INTENT = (
    "Add a --top N option to wordfreq. With it, the command prints only the N most "
    "common words. If N is not a whole number greater than zero, print "
    "`error: --top needs a whole number greater than zero` to standard error and exit "
    "with code 2."
)
# The intent of the to-do web apps. It needs two changes: the storage keeps the done flag
# (a capability), and the page shows it (a job).
TODO_INTENT = (
    "Let users mark a to-do item as done. Each item that is not done gets a Done button on "
    "the page, in a form that sends `POST /items/<id>/done`, which answers 303 to `/`. A done "
    "item stays done after the app restarts. A data file from before this change still loads, "
    "and its items are not done. By default the page shows only the items that are not done. "
    "A link \"Show all\" goes to `/?show=all`, which shows every item and puts \" (done)\" after "
    "the text of each done item. `POST /items/<id>/done` for an id that does not exist answers "
    "404 with `error: no item <id>`."
)
SECTIONS = HERE / "sections"
CHANGE_BRANCH = "pdlc/CH-0001-top-option"
# The snapshots of a finished run. "r5" is the first one, from an early pdlc with no acceptance
# stage. The two others come from runs with the pdlc of round 8 (see sections/README.md).
SNAPSHOTS = {
    "wordfreq": {"bundle": SECTIONS / "wordfreq.bundle", "fixture": "wordfreq", "intent": INTENT},
    "todo-rust": {"bundle": SECTIONS / "todo-rust.bundle", "fixture": "todo-rust", "intent": TODO_INTENT},
    "r5": {"bundle": SECTIONS / "project.bundle", "fixture": "wordfreq", "intent": INTENT, "legacy": True},
}
DEFAULT_SNAPSHOT = "wordfreq"
# stage: (subject of the entry commit, prompt, subject that proves the stage finished).
# The prompt of intake holds {intent}.
REPLAY_STAGES = {
    "intake": ("Set up pdlc", "/pdlc:intake defaults {intent}", "Specify IN-"),
    "ready": ("Specify IN-0001", "/pdlc:ready defaults", "Ready IN-"),
    "change": ("Ready IN-0001", "/pdlc:change defaults", "Plan IN-"),
    "acceptance": ("Plan IN-0001", "/pdlc:acceptance defaults", "Acceptance reviewed IN-"),
    "tests": ("Acceptance reviewed IN-0001", "/pdlc:tests defaults", "Tests reviewed CH-"),
    "build": ("Tests reviewed CH-0001", "/pdlc:build defaults", "Built CH-"),
    "verify": ("Built CH-0001", "/pdlc:verify defaults", "Verified CH-"),
    "show": ("Verified CH-0001", "/pdlc:show defaults", "Propose CH-"),
}
# The table of the snapshot "r5", as it was: (entry subject, branch, prompt, end subject).
LEGACY_STAGES = {
    "intake": ("Set up pdlc", "main", "/pdlc:intake defaults " + INTENT, "Specify IN-"),
    "ready": ("Specify IN-0001", "main", "/pdlc:ready defaults", "Ready IN-"),
    "change": ("Ready IN-0001", "main", "/pdlc:change defaults", "Plan IN-"),
    "tests": ("Plan IN-0001", "main", "/pdlc:tests defaults", "Tests reviewed CH-"),
    "build": ("Tests reviewed CH-0001", CHANGE_BRANCH, "/pdlc:build defaults", "Built CH-"),
    "verify": ("Built CH-0001", CHANGE_BRANCH, "/pdlc:verify defaults", "Verified CH-"),
    # The snapshot comes from an early pdlc, with show before verify and no acceptance stage.
    # So a replay of verify or show needs a new snapshot.
    "show": ("Verified CH-0001", CHANGE_BRANCH, "/pdlc:show defaults", "Visual review CH-"),
}


def stage_table(snapshot):
    """{stage: (entry subject, prompt, end subject)} of a snapshot."""
    if snapshot not in SNAPSHOTS:
        raise SystemExit("unknown snapshot %r (one of %s)" % (snapshot, ", ".join(sorted(SNAPSHOTS))))
    if SNAPSHOTS[snapshot].get("legacy"):
        return {stage: (row[0], row[2], row[3]) for stage, row in LEGACY_STAGES.items()}
    intent = SNAPSHOTS[snapshot]["intent"]
    return {stage: (row[0], row[1].replace("{intent}", intent), row[2]) for stage, row in REPLAY_STAGES.items()}


def snapshot_bundle(snapshot):
    """The bundle file of a snapshot. It stops with a message when the file is not there."""
    stage_table(snapshot)  # checks the name
    bundle = SNAPSHOTS[snapshot]["bundle"]
    if not Path(bundle).exists():
        raise SystemExit("The snapshot %s is not recorded: %s is missing. "
                         "See bench/sections/README.md." % (snapshot, bundle))
    return bundle


ALLOWED_TOOLS = (
    "Read Write Edit Glob Grep Agent Skill "
    + " ".join(
        "Bash(%s:*)" % name
        for name in (
            "git python3 node npm npx curl ls cat cp mkdir mv rm find grep sed head tail wc "
            "diff chmod touch echo printf sort timeout sleep pwd test cd env which date"
        ).split()
    )
)

# Relative prices, in input-token equivalents, used only to share a model's cost between
# its messages. The total always comes from the cost that the CLI reports.
PRICE = {"input": 1.0, "cache_write_5m": 1.25, "cache_write_1h": 2.0, "cache_read": 0.1, "output": 5.0}


# ---------------------------------------------------------------- projects


def git(cwd, *args):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        env={**os.environ, "GIT_AUTHOR_NAME": "bench", "GIT_AUTHOR_EMAIL": "bench@example.com",
             "GIT_COMMITTER_NAME": "bench", "GIT_COMMITTER_EMAIL": "bench@example.com"},
    )


def load_upgrade(plugin):
    """The upgrade script of the plugin under test, as a module."""
    path = Path(plugin) / "skills" / "upgrade" / "scripts" / "upgrade.py"
    spec = importlib.util.spec_from_file_location("pdlc_upgrade_" + str(abs(hash(str(path)))), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def upgrade_project(project, plugin):
    """Bring the pdlc files of a project up to the plugin under test, and write no commit.

    Nobody edits the files of a bench project. So a file that is not a spec, and that the
    upgrade would call edited, is taken from the plugin. A spec stays as it is.
    """
    module = load_upgrade(plugin)
    root, plugin = str(project), str(Path(plugin))
    plan = module.build_plan(root, plugin, set())
    takes = [e["path"] for e in plan["entries"] if e["status"] == "edited" and not e["path"].startswith("specs/")]
    args = Namespace(take=takes, no_intent=True, no_commit=True)
    here = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    try:
        module.cmd_apply(root, plugin, args)
    except module.Stop as stop:
        raise RuntimeError("upgrade failed (%d): %s" % (stop.code, stop.message))
    # The script works on the newest unmerged pdlc branch. A branch at the commit of main counts
    # as merged, so the script may have moved to main. The bench stays where the stage starts.
    if git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != here:
        moved = git(root, "switch", "-q", here)
        if moved.returncode != 0:
            raise RuntimeError("upgrade left branch %s: %s" % (here, moved.stderr.strip()))


def ensure_tools():
    """Install the visual review's npm packages once, into a cache that runs share."""
    if (TOOLS_CACHE / "node_modules" / "gifenc").exists():
        return TOOLS_CACHE
    TOOLS_CACHE.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    subprocess.run(["npm", "install", "--prefix", str(TOOLS_CACHE), "playwright", "gifenc", "pngjs"],
                   check=True, capture_output=True, env=env, timeout=300)
    return TOOLS_CACHE


def make_project(dest, plugin, with_pdlc=True, fixture="wordfreq"):
    """A fresh git repository from the fixture. With pdlc, the pdlc folder is in place.

    The fixture keeps only the specs, the config and the marker. The upgrade script of the
    plugin under test adds the other pdlc files, so that init is not needed.
    """
    dest = Path(dest)
    shutil.copytree(FIXTURES[fixture]["app"], dest,
                    ignore=shutil.ignore_patterns("__pycache__", "target", "pdlc" if not with_pdlc else ""))
    git(dest, "init", "-q", "-b", "main")
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "Set up pdlc" if with_pdlc else "Seed")
    if with_pdlc:
        upgrade_project(dest, plugin)
        os.symlink(ensure_tools(), dest / "pdlc" / ".tools")
        git(dest, "add", "-A")
        git(dest, "commit", "-q", "--amend", "--no-edit")
    return dest


# ---------------------------------------------------------------- running claude


def claude_command(prompt, plugin, extra=(), tools=()):
    """The command of one headless session. `tools` adds Bash commands that the fixture needs.

    With `plugin` set to None, the session loads no plugin from a folder.
    """
    return [
        "claude", "-p", prompt,
        "--model", MODEL, "--effort", EFFORT,
        *(["--plugin-dir", str(plugin)] if plugin is not None else []),
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--permission-mode", "auto",
        "--allowedTools", ALLOWED_TOOLS + "".join(" Bash(%s:*)" % name for name in tools),
        "--output-format", "stream-json", "--verbose",
        "--no-session-persistence",
        *extra,
    ]


def session_env(cwd):
    """The environment of a session that starts in `cwd`. PWD and OLDPWD name `cwd`, not the folder of the bench."""
    return {**os.environ, "PWD": str(cwd), "OLDPWD": str(cwd)}


def run_claude(prompt, cwd, plugin, log_path, timeout=3600, budget_usd=None, extra=(), tools=(), env=None):
    """Run one headless session. Write each event with its arrival time. Return the events."""
    command = claude_command(prompt, plugin, extra, tools)
    if budget_usd:
        command += ["--max-budget-usd", str(budget_usd)]
    started = time.time()
    proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
    events = []
    err = []
    drain = threading.Thread(target=lambda: err.append(proc.stderr.read()), daemon=True)
    drain.start()
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    log = open(log_path, "w")
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            item = {"t": round(time.time() - started, 2), "e": event}
            events.append(item)
            log.write(json.dumps(item) + "\n")
        proc.wait()
    finally:
        timer.cancel()
        log.close()
    drain.join(timeout=5)
    wall = round(time.time() - started, 1)
    return events, wall, "".join(err)


# ---------------------------------------------------------------- reading the stream


def message_weight(usage):
    cache = usage.get("cache_creation") or {}
    write_1h = cache.get("ephemeral_1h_input_tokens", 0)
    write_5m = cache.get("ephemeral_5m_input_tokens", 0)
    if not cache:
        write_5m = usage.get("cache_creation_input_tokens", 0)
    return (usage.get("input_tokens", 0) * PRICE["input"]
            + write_5m * PRICE["cache_write_5m"] + write_1h * PRICE["cache_write_1h"]
            + usage.get("cache_read_input_tokens", 0) * PRICE["cache_read"]
            + usage.get("output_tokens", 0) * PRICE["output"])


def tokens_of(usage):
    return {
        "input": usage.get("input_tokens", 0),
        "cache_write": usage.get("cache_creation_input_tokens", 0),
        "cache_read": usage.get("cache_read_input_tokens", 0),
        "output": usage.get("output_tokens", 0),
    }


def add_tokens(total, more):
    for key, value in more.items():
        total[key] = total.get(key, 0) + value


STAGES = ("init", "intake", "ready", "change", "acceptance", "tests", "build", "verify", "show", "ship")
# The stages that use each agent. The first one is the stage of a call from any other stage.
AGENT_STAGES = {"pdlc:recon": ("intake", "init"), "pdlc:test-writer": ("tests", "acceptance"),
                "pdlc:builder": ("build",)}
SKILL_FILE = re.compile(r"skills/(%s)/SKILL\.md" % "|".join(STAGES))
WAITING_TOOLS = {"ReadNotifications", "Monitor", "TaskOutput"}
WORK_WORDS = ("git commit", "git add", "unittest", "pytest", "npm ", "node ",
              "record_gif", "make_packets", "check_merge", "record_merges", "sed -i", "<<",
              "python3 -")


def stage_name(skill):
    return skill.split(":")[-1] if skill else "ship"


def agent_stage(label, prompt, current):
    """The stage that an agent call belongs to, or None.

    The visual reviewer counts toward show. A reviewer with another remit than tests counts
    toward verify. For the test writer and the tests reviewer, the prompt decides first: a
    change path is the tests stage, and an intent or acceptance path is the acceptance stage.
    Otherwise a stage that uses the agent keeps it.
    A pdlc:stage agent runs the stage on the "Stage:" line of its prompt.
    """
    prompt = prompt or ""
    if label == "pdlc:stage":
        found = re.search(r"^Stage:\s*([a-z]+)\s*$", prompt, re.M)
        return found.group(1) if found and found.group(1) in STAGES else current
    if label == "pdlc:reviewer" and "/review/visual/" in prompt:
        return "show"
    if label == "pdlc:reviewer" and "/review/tests/" not in prompt:
        return "verify"
    if label in ("pdlc:reviewer", "pdlc:test-writer"):
        if "pdlc/changes/CH-" in prompt:
            return "tests"
        if "pdlc/acceptance/" in prompt or "inbox/IN-" in prompt:
            return "acceptance"
    serves = ("tests", "acceptance") if label == "pdlc:reviewer" else AGENT_STAGES.get(label, ())
    if current in serves:
        return current
    return serves[0] if serves else None


def stage_from_call(name, args, current=None):
    """The stage that a top-level tool call starts, or None.

    The Skill tool names its stage. A read of one skill file also starts that stage. A
    command that reads several skill files at once reads ahead, so it starts no stage.
    An agent call starts the stage of its agent, unless the current stage uses that agent.
    """
    if name == "Skill":
        return stage_name(args.get("skill"))
    if name in ("Agent", "Task"):
        return agent_stage(args.get("subagent_type"), args.get("prompt"), current)
    text = args.get("file_path") or args.get("command") or ""
    if "record_gif" in text:
        return "show"
    found = set(SKILL_FILE.findall(text))
    if len(found) == 1 and (name == "Read" or "cat" in text.split()[:1] or text.startswith("cat ")):
        return found.pop()
    return None


def waiting_command(command):
    """A Bash command that only waits: it sleeps, or loops, and does no work."""
    waits = re.match(r"\s*(sleep\b|until\b|while\b)", command) or re.search(r"\bsleep\s+\d", command)
    return bool(waits) and not any(word in command for word in WORK_WORDS)


def is_waiting(blocks):
    """A turn that only waits for a background agent: a notification read, a monitor, a sleep."""
    calls = [b for b in blocks if b.get("type") == "tool_use"]
    if not calls:
        return False
    for call in calls:
        command = (call.get("input") or {}).get("command", "")
        if call["name"] in WAITING_TOOLS:
            continue
        if call["name"] == "Bash" and waiting_command(command):
            continue
        return False
    return True


def analyse(items):
    """Split a run into stages. Return totals and one entry per stage.

    A stage starts when the top-level session calls its skill. A message from an agent counts
    toward the stage of its agent type, under the name of the agent. A reviewer counts toward
    tests when its packet is for the tests remit, and toward verify otherwise.
    """
    messages = {}
    order = []
    stage = "ship"
    visits = [(0.0, "ship")]  # (time, stage) each time the main session moves to another stage
    stage_end = {}
    agent_of = {}
    agent_remit = {}
    agent_span = {}
    result = {}
    for item in items:
        event, t = item["e"], item["t"]
        kind = event.get("type")
        if kind == "result":
            result = event
            continue
        if kind == "system" and event.get("subtype") in ("task_started", "task_notification"):
            tool_id = event.get("tool_use_id")
            if tool_id in agent_span:
                agent_span[tool_id][1 if event["subtype"] == "task_notification" else 0] = t
            continue
        if kind == "assistant":
            message = event.get("message", {})
            parent = event.get("parent_tool_use_id")
            blocks = message.get("content", [])
            for block in blocks:
                if block.get("type") != "tool_use":
                    continue
                name, args = block.get("name"), block.get("input") or {}
                if parent is None:
                    started = stage_from_call(name, args, stage)
                    if started:
                        if started != stage:
                            visits.append((t, started))
                        stage = started
                        stage_end[stage] = t
                if name in ("Agent", "Task"):
                    label = args.get("subagent_type") or "general-purpose"
                    owner = agent_stage(label, args.get("prompt"), stage)
                    agent_of[block["id"]] = (owner or stage, label)
                    remit = re.search(r"/review/([a-z]+)/", args.get("prompt") or "")
                    if label == "pdlc:reviewer" and remit:
                        agent_remit[block["id"]] = label + "/" + remit.group(1)
                    agent_span[block["id"]] = [t, t]
            key = message.get("id") or "m%d" % len(order)
            if key not in messages:
                order.append(key)
            messages[key] = {"usage": message.get("usage") or {}, "model": message.get("model"), "stage": stage,
                             "parent": parent, "t": t, "waiting": parent is None and is_waiting(blocks)}
            stage_end[stage] = t
        elif kind == "user":
            for block in (event.get("message", {}).get("content") or []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    span = agent_span.get(block.get("tool_use_id"))
                    if span and span[1] == span[0]:
                        span[1] = t

    per_model_weight = {}
    for key in order:
        entry = messages[key]
        per_model_weight[entry["model"]] = per_model_weight.get(entry["model"], 0) + message_weight(entry["usage"])
    model_cost = {model: info.get("costUSD", 0.0) for model, info in (result.get("modelUsage") or {}).items()}

    def blank():
        return {"tokens": {}, "cost_usd": 0.0, "messages": 0, "agents": {}}

    stages = {}
    waiting = {"messages": 0, "cost_usd": 0.0}
    for key in order:
        entry = messages[key]
        label = "session"
        if entry["parent"] in agent_of:
            entry["stage"], label = agent_of[entry["parent"]]
        data = stages.setdefault(entry["stage"], blank())
        weight = per_model_weight.get(entry["model"]) or 0
        share = model_cost.get(entry["model"], 0.0) * message_weight(entry["usage"]) / weight if weight else 0.0
        add_tokens(data["tokens"], tokens_of(entry["usage"]))
        data["cost_usd"] += share
        data["messages"] += 1
        if entry["waiting"]:
            waiting["messages"] += 1
            waiting["cost_usd"] += share
        if label != "session":
            agent = data["agents"].setdefault(label, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
            add_tokens(agent["tokens"], tokens_of(entry["usage"]))
            agent["cost_usd"] += share
            agent["messages"] += 1
            sub = agent_remit.get(entry["parent"])
            if sub:
                part = data["agents"].setdefault(sub, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
                add_tokens(part["tokens"], tokens_of(entry["usage"]))
                part["cost_usd"] += share
                part["messages"] += 1
    for tool_id, (owner, label) in agent_of.items():
        data = stages.setdefault(owner, blank())
        agent = data["agents"].setdefault(label, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
        agent["calls"] += 1
        start, end = agent_span[tool_id]
        agent["wall_s"] = round(agent.get("wall_s", 0) + (end - start), 1)
        sub = agent_remit.get(tool_id)
        if sub:
            part = data["agents"].setdefault(sub, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
            part["calls"] += 1
            part["wall_s"] = round(part.get("wall_s", 0) + (end - start), 1)

    # A stage runs again for each change, so its time is the sum of its visits.
    last = max(stage_end.values(), default=0.0)
    spent = {}
    for (start, name), (end, _) in zip(visits, visits[1:] + [(last, None)]):
        spent[name] = spent.get(name, 0.0) + max(0.0, end - start)
    for name, data in stages.items():
        if name in spent:
            data["wall_s"] = round(spent[name], 1)
    for data in stages.values():
        data["cost_usd"] = round(data["cost_usd"], 4)
        for agent in data["agents"].values():
            agent["cost_usd"] = round(agent["cost_usd"], 4)
    waiting["cost_usd"] = round(waiting["cost_usd"], 4)

    totals = {"tokens": {}, "cost_usd": round(result.get("total_cost_usd", 0.0), 4),
              "duration_s": round(result.get("duration_ms", 0) / 1000.0, 1),
              "turns": result.get("num_turns"), "is_error": result.get("is_error"),
              "terminal_reason": result.get("terminal_reason"),
              "subagents": (result.get("subagent_stats") or {}).get("spawned")}
    for info in (result.get("modelUsage") or {}).values():
        add_tokens(totals["tokens"], {"input": info.get("inputTokens", 0), "cache_write": info.get("cacheCreationInputTokens", 0),
                                      "cache_read": info.get("cacheReadInputTokens", 0), "output": info.get("outputTokens", 0)})
    totals["models"] = {m: round(i.get("costUSD", 0.0), 4) for m, i in (result.get("modelUsage") or {}).items()}
    return {"totals": totals, "stages": stages, "waiting": waiting}


# ---------------------------------------------------------------- reading the outcome

SAMPLE = "the cat and the hat and the bat and the mat\n"
PROBES = [
    ("top 2 keeps the two most common", ["--top", "2"], 0, "the 4\nand 3\n", None),
    ("top 1 keeps one", ["--top", "1"], 0, "the 4\n", None),
    ("top larger than the word count keeps all", ["--top", "99"], 0, "the 4\nand 3\nbat 1\ncat 1\nhat 1\nmat 1\n", None),
    ("top 0 is an error", ["--top", "0"], 2, "", "error: --top needs a whole number greater than zero\n"),
    ("top -3 is an error", ["--top", "-3"], 2, "", "error: --top needs a whole number greater than zero\n"),
    ("top abc is an error", ["--top", "abc"], 2, "", "error: --top needs a whole number greater than zero\n"),
    ("top 2.5 is an error", ["--top", "2.5"], 2, "", "error: --top needs a whole number greater than zero\n"),
    ("no option prints every word", [], 0, "the 4\nand 3\nbat 1\ncat 1\nhat 1\nmat 1\n", None),
]


def run_probes(project):
    """Run the intent's acceptance probes against the code in `project` as it is checked out.

    The intent shows the option before the file (`--top N FILE`), so that form must work. The
    option after the file is not in the intent. It is counted apart, for information.
    """
    sample = Path(project) / ".bench-sample.txt"
    sample.write_text(SAMPLE)

    def good(ordering, code, out, err):
        try:
            proc = subprocess.run([sys.executable, "-m", "wordfreq", *ordering], cwd=project,
                                  capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return False
        return proc.returncode == code and proc.stdout == out and (err is None or proc.stderr == err)

    passed, failed, trailing_failed = 0, [], []
    for name, args, code, out, err in PROBES:
        if good(args + [str(sample)], code, out, err):
            passed += 1
        else:
            failed.append(name)
        if args and not good([str(sample)] + args, code, out, err):
            trailing_failed.append(name)
    sample.unlink()
    return {"passed": passed, "total": len(PROBES), "failed": failed, "option_after_file_failed": trailing_failed}


def run_unit_checks(project):
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=project,
                          capture_output=True, text=True, timeout=120)
    ran = re.search(r"Ran (\d+) tests?", proc.stderr)
    return {"ok": proc.returncode == 0, "ran": int(ran.group(1)) if ran else 0}


def unit_checks(project, fixture):
    """Run the checks of the fixture app. The count is the sum of each count that the runner prints."""
    spec = FIXTURES[fixture]
    if "unit" not in spec:
        return run_unit_checks(project)
    try:
        proc = subprocess.run(spec["unit"], cwd=project, capture_output=True, text=True, timeout=900)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"ok": False, "ran": 0, "error": repr(error)}
    ran = sum(int(n) for n in re.findall(spec["count"], proc.stdout + proc.stderr, re.M))
    return {"ok": proc.returncode == 0, "ran": ran}


def free_port():
    import socket
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class WebApp:
    """One run of a fixture web app, on a free port, with its own data file."""

    def __init__(self, project, command, data_file):
        self.port = free_port()
        env = {**os.environ, "PORT": str(self.port), "DATA_FILE": str(data_file)}
        self.proc = subprocess.Popen(command, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import socket
        deadline = time.time() + 60
        while time.time() < deadline and self.proc.poll() is None:
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=1).close()
                return
            except OSError:
                time.sleep(0.2)
        self.stop()
        raise RuntimeError("the app did not start on port %d" % self.port)

    def request(self, method, path, form=None):
        """(status, Location header, body) of one request, with no redirect followed."""
        import http.client
        import urllib.parse
        body = urllib.parse.urlencode(form) if form is not None else None
        headers = {"Content-Type": "application/x-www-form-urlencoded"} if form is not None else {}
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, response.getheader("Location") or "", response.read().decode("utf-8", "replace")
        finally:
            conn.close()

    def stop(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()


def visible_text(html):
    """The text of a page as a user reads it: no tags, and single spaces."""
    import html as html_lib
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", html)).split())


def has_word(text, word):
    return re.search(r"(?<!\w)%s(?!\w)" % re.escape(word), text) is not None


def todo_probes(project, fixture):
    """The acceptance probes of TODO_INTENT, over HTTP, against the app as it is checked out."""
    spec = FIXTURES[fixture]
    project = Path(project)
    names = ["done hides the item", "show all marks each done item", "each open item has a done button",
             "the page links to show all", "done stays done after a restart", "an old data file still loads",
             "an unknown id is 404", "adding and the empty-text error still work"]
    results = dict.fromkeys(names, False)
    errors = []
    work = Path(tempfile.mkdtemp(prefix="pdlc-bench-probe-"))
    try:
        if spec.get("build"):
            subprocess.run(spec["build"], cwd=project, capture_output=True, timeout=900, check=True)
        data = work / "items.txt"
        app = WebApp(project, spec["start"], data)
        try:
            add = [app.request("POST", "/items", {"text": text})[0] for text in ("milk", "eggs")]
            done = app.request("POST", "/items/1/done")
            page = app.request("GET", "/")[2]
            text = visible_text(page)
            results["done hides the item"] = (add == [303, 303] and done[0] == 303 and done[1].endswith("/")
                                              and has_word(text, "eggs") and not has_word(text, "milk"))
            every = visible_text(app.request("GET", "/?show=all")[2])
            results["show all marks each done item"] = "milk (done)" in every and has_word(every, "eggs") \
                and "eggs (done)" not in every
            results["each open item has a done button"] = (
                re.search(r"<form[^>]*action=[\"']/items/2/done[\"']", page) is not None
                and re.search(r"action=[\"']/items/1/done[\"']", page) is None)
            link = re.search(r"<a\b[^>]*href=[\"']/?\?show=all[\"'][^>]*>(.*?)</a>", page, re.S | re.I)
            results["the page links to show all"] = link is not None and visible_text(link.group(1)) == "Show all"
            missing = app.request("POST", "/items/99/done")
            results["an unknown id is 404"] = missing[0] == 404 and "error: no item 99" in missing[2]
            empty = app.request("POST", "/items", {"text": "  "})
            results["adding and the empty-text error still work"] = (
                add == [303, 303] and empty[0] == 400 and "error: text is empty" in empty[2])
        finally:
            app.stop()
        app = WebApp(project, spec["start"], data)
        try:
            text = visible_text(app.request("GET", "/")[2])
            every = visible_text(app.request("GET", "/?show=all")[2])
            results["done stays done after a restart"] = (has_word(text, "eggs") and not has_word(text, "milk")
                                                          and "milk (done)" in every)
        finally:
            app.stop()
        old = work / "old.txt"
        old.write_text("1\tbread\n2\tjam\n")
        app = WebApp(project, spec["start"], old)
        try:
            before = visible_text(app.request("GET", "/")[2])
            done = app.request("POST", "/items/2/done")[0]
            after = visible_text(app.request("GET", "/")[2])
            results["an old data file still loads"] = (has_word(before, "bread") and has_word(before, "jam")
                                                       and done == 303 and has_word(after, "bread")
                                                       and not has_word(after, "jam"))
        finally:
            app.stop()
    except Exception as error:  # a build or start failure fails each probe that did not run
        errors.append(repr(error)[:300])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    failed = [name for name, ok in results.items() if not ok]
    out = {"passed": len(names) - len(failed), "total": len(names), "failed": failed}
    if errors:
        out["error"] = errors[0]
    return out


def fixture_probes(project, fixture):
    return run_probes(project) if fixture == "wordfreq" else todo_probes(project, fixture)


# Each fixture app: its source, its intent, and how the bench checks the result. "tools" are the
# Bash commands that a run of pdlc needs beyond ALLOWED_TOOLS.
FIXTURES = {
    "wordfreq": {"app": FIXTURE, "intent": INTENT, "probes": len(PROBES), "tools": (),
                 "check_pattern": r"unittest|pytest",
                 "lint": ["ruff", "check", "--no-cache", "--output-format", "concise", "--extend-exclude", "pdlc", "."],
                 "lint_pattern": r"^\S+:\d+:\d+: ", "compile": [sys.executable, "-m", "compileall", "-q", "wordfreq"],
                 "noop": "pass"},
    "todo-rust": {"app": HERE / "fixtures" / "todo-rust", "intent": TODO_INTENT, "probes": 8,
                  "check_pattern": r"cargo test|rustc[^|;&]*--test|acceptance-bin",
                  "build_pattern": r"cargo (build|run|check)|\brustc\b",
                  "unit": ["cargo", "test", "--quiet"], "count": r"test result: \w+\. (\d+) passed",
                  "build": ["cargo", "build", "--quiet", "--release"], "start": ["target/release/todo"],
                  "tools": ("cargo", "rustc", "rustfmt"),
                  "lint": ["cargo", "clippy", "--quiet", "--all-targets", "--message-format=short"],
                  "lint_pattern": r"^\S+:\d+:\d+: (warning|error)", "compile": ["cargo", "build", "--quiet"],
                  "noop": ""},
    "todo-clojure": {"app": HERE / "fixtures" / "todo-clojure", "intent": TODO_INTENT, "probes": 8,
                     "check_pattern": r"todo\.run-tests|clojure\.test|run-tests",
                     "unit": ["clojure", "-cp", "src:test", "-m", "todo.run-tests"],
                     "count": r"^Ran (\d+) tests containing",
                     "start": ["clojure", "-cp", "src", "-m", "todo.main"],
                     "compile": ["clojure", "-cp", "src", "-e", "(require 'todo.main)"],
                     "tools": ("clojure", "java"), "noop": ""},
}


# The text whose writing the specification packet checks: the README and other docs outside
# pdlc/, the specs, and the change spec. A finding elsewhere costs no review round.
PACKET_TEXT = re.compile(r"^(?:pdlc/specs/.*\.md|pdlc/changes/[^/]+/change\.md|(?!pdlc/).*\.md)$")


def writing_findings(project, since):
    """The writing-check findings in the packet text that the commits after `since` wrote.

    Returns {"count", "files", "findings"}. It runs the project's own pdlc/bin/check_writing.py
    with --since, so the rules are the ones that the reviewers see. The project must be checked
    out at the tip that holds the text. When the script is missing or fails, "count" is None and
    "error" says why.
    """
    project = Path(project)
    changed = git(project, "diff", "--name-only", since + "...HEAD").stdout.split()
    files = [f for f in changed if PACKET_TEXT.match(f) and (project / f).is_file()]
    if not files:
        return {"count": 0, "files": [], "findings": []}
    script = project / "pdlc" / "bin" / "check_writing.py"
    if not script.is_file():
        return {"count": None, "files": files, "findings": [], "error": "no pdlc/bin/check_writing.py"}
    try:
        done = subprocess.run([sys.executable, str(script), "--since", since, *files], cwd=project,
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return {"count": None, "files": files, "findings": [], "error": repr(error)}
    findings = [line for line in done.stdout.splitlines() if " · " in line]
    return {"count": len(findings), "files": files, "findings": findings}


def inspect_project(project, fixture="wordfreq"):
    """Read what a ship run left in the project. Check each change branch as the merge would."""
    project = Path(project)
    branches = [b.strip("* ").strip() for b in git(project, "branch", "--format=%(refname:short)").stdout.split()]
    changes = sorted(p.name for p in (project / "pdlc" / "changes").glob("CH-*")) if (project / "pdlc" / "changes").exists() else []
    out = {"branches": branches, "changes": changes, "dirty": bool(git(project, "status", "--porcelain").stdout.strip())}
    status = {}
    for branch in branches:
        if branch == "main":
            continue
        git(project, "checkout", "-q", branch)
        for change in sorted((project / "pdlc" / "changes").glob("CH-*")):
            text = (change / "change.md").read_text() if (change / "change.md").exists() else ""
            match = re.search(r"(?:^|·)\s*\**Status:?\**:?\s*([a-z ]+?)\s*(?:·|$)", text, re.M | re.I)
            status.setdefault(change.name, {})[branch] = match.group(1).strip() if match else "?"
        merge = subprocess.run([sys.executable, "pdlc/bin/check_merge.py"], cwd=project, capture_output=True, text=True, timeout=120)
        out.setdefault("merge_check", {})[branch] = (merge.stdout + merge.stderr).strip().splitlines()[:3]
    out["change_status"] = status
    subjects = git(project, "log", "--all", "--format=%s").stdout.splitlines()
    out["stops"] = [x for x in subjects if x.startswith("Stop ")]
    out["verify_rounds"] = len([x for x in subjects if x.startswith("Verify CH-")])
    out["proposed"] = any(x.startswith("Propose CH-") for x in subjects)
    tip = max((b for b in branches if b != "main"), key=lambda b: git(project, "log", "-1", "--format=%ct", b).stdout.strip() or "0", default="main")
    git(project, "checkout", "-q", tip)
    out["tip"] = tip
    root = git(project, "rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
    out["writing"] = writing_findings(project, root)
    out["unit"] = unit_checks(project, fixture)
    out["probes"] = fixture_probes(project, fixture)
    git(project, "checkout", "-q", "main")
    return out


# ---------------------------------------------------------------- replaying one stage


def entry_commit(project, subject):
    """The full hash of the newest commit whose subject starts with `subject`."""
    for line in git(project, "log", "--all", "--format=%H %s").stdout.splitlines():
        commit, _, text = line.partition(" ")
        if text.startswith(subject):
            return commit
    raise RuntimeError("no commit starts with %r" % subject)


def tip_branch(project):
    """The local branch, other than main, whose last commit is the newest. Main if there is none."""
    names = git(project, "for-each-ref", "--sort=-committerdate", "--format=%(refname:short)", "refs/heads/").stdout.split()
    return next((name for name in names if name != "main"), "main")


def clone_snapshot(dest, snapshot):
    """Clone the bundle with no local branch, so that a branch from the end of the run cannot
    leak into an earlier state. The caller makes the branches that its state needs."""
    subprocess.run(["git", "clone", "-q", str(snapshot_bundle(snapshot)), str(dest)], check=True)
    git(dest, "checkout", "-q", "--detach")
    for name in git(dest, "for-each-ref", "--format=%(refname:short)", "refs/heads").stdout.split():
        git(dest, "branch", "-q", "-D", name)


def main_commit(project, commit, ref="origin/main"):
    """The last commit on the first-parent line of `ref` that is `commit` or older."""
    for line in git(project, "rev-list", "--first-parent", ref).stdout.split():
        if git(project, "merge-base", "--is-ancestor", line, commit).returncode == 0:
            return line
    return commit


def change_base(project, commit, branch):
    """`Base:` of the change spec whose `Branch:` is `branch`, read at `commit`. Main if none."""
    for name in git(project, "ls-tree", "-r", "--name-only", commit, "--", "pdlc/changes").stdout.splitlines():
        if name.endswith("/change.md"):
            text = git(project, "show", "%s:%s" % (commit, name)).stdout
            found = re.search(r"\bBranch:[ \t]*(\S+)", text)
            if found and found.group(1) == branch:
                base = re.search(r"\bBase:[ \t]*(\S+)", text)
                return base.group(1) if base else "main"
    return "main"


def make_base_branch(project, commit, branch):
    """For a stacked change, make its base branch at the last commit of origin/<base> before `commit`."""
    base = change_base(project, commit, branch)
    if base in ("main", "none", "-") or base == branch:
        return
    ref = "origin/" + base
    if git(project, "rev-parse", "--verify", "-q", ref).returncode == 0:
        git(project, "branch", "-q", "-f", base, main_commit(project, commit, ref))


def newest_pdlc_branch(project):
    """The remote pdlc branch at the top of the stack: the newest one that is not under another."""
    refs = git(project, "for-each-ref", "--sort=-committerdate", "--format=%(refname:short)",
               "refs/remotes/origin/pdlc/").stdout.split()
    for ref in refs:
        if not any(other != ref and git(project, "merge-base", "--is-ancestor", ref, other).returncode == 0
                   for other in refs):
            return ref
    return None


def work_branch(project, stage, entry):
    """The branch where a stage works, read from the spec in the entry commit.

    Intake works on main. A stage of a change reads `Branch:` of the change spec. The other
    stages read `Branch:` of the intent. The value none gives main.
    """
    if stage == "intake":
        return "main"
    names = git(project, "ls-tree", "-r", "--name-only", entry, "--", "pdlc").stdout.splitlines()
    pattern = (r"pdlc/changes/CH-0001-[^/]*/change\.md$" if stage in ("build", "verify", "show")
               else r"pdlc/inbox/IN-0001-[^/]*\.md$")
    for name in names:
        if re.match(pattern, name):
            found = re.search(r"\bBranch:[ \t]*(\S+)", git(project, "show", "%s:%s" % (entry, name)).stdout)
            if found and found.group(1) not in ("none", "main", "-"):
                return found.group(1)
    return "main"


def make_stage_project(dest, stage, plugin, snapshot=DEFAULT_SNAPSHOT):
    """Clone the snapshot to dest, with the project at the commit where the stage starts."""
    table = stage_table(snapshot)
    if stage not in table:
        raise SystemExit("The snapshot %s has no stage %s." % (snapshot, stage))
    clone_snapshot(dest, snapshot)
    # A branch is only a remote-tracking ref until it is checked out, so find the commits
    # before the remote goes.
    entry = entry_commit(dest, table[stage][0])
    if SNAPSHOTS[snapshot].get("legacy"):
        branch = LEGACY_STAGES[stage][1]
        base = entry if branch == "main" else entry_commit(dest, "Plan IN-0001")
    else:
        branch = work_branch(dest, stage, entry)
        base = entry if branch == "main" else main_commit(dest, entry)
    git(dest, "checkout", "-q", "-B", "main", base)
    if branch != "main":
        git(dest, "checkout", "-q", "-B", branch, entry)
        make_base_branch(dest, entry, branch)
    return finish_snapshot_project(dest, plugin), entry


def make_done_project(dest, plugin, snapshot=DEFAULT_SNAPSHOT):
    """Clone the snapshot to dest, with the newest pdlc branch at its last commit, the proposal."""
    clone_snapshot(dest, snapshot)
    if SNAPSHOTS[snapshot].get("legacy"):
        branch, tip = CHANGE_BRANCH, "origin/" + CHANGE_BRANCH
        base = entry_commit(dest, "Plan IN-0001")
    else:
        tip = newest_pdlc_branch(dest)
        if not tip:
            raise SystemExit("The snapshot %s has no pdlc branch." % snapshot)
        branch = tip[len("origin/"):]
        base = main_commit(dest, git(dest, "rev-parse", tip).stdout.strip())
    git(dest, "checkout", "-q", "-B", "main", base)
    git(dest, "checkout", "-q", "-B", branch, tip)
    if not SNAPSHOTS[snapshot].get("legacy"):
        make_base_branch(dest, tip, branch)
    return finish_snapshot_project(dest, plugin)


def finish_snapshot_project(dest, plugin):
    """Remove the remote, and bring the pdlc files up to the plugin under test."""
    git(dest, "remote", "remove", "origin")
    upgrade_project(dest, plugin)
    tools = Path(dest) / "pdlc" / ".tools"
    if tools.is_symlink() and not tools.exists():  # the snapshot's link points to a missing folder
        tools.unlink()
    if not tools.exists():
        os.symlink(ensure_tools(), tools)
    if git(dest, "status", "--porcelain").stdout.strip():
        git(dest, "add", "-A", "pdlc")
        git(dest, "commit", "-q", "-m", "Upgrade pdlc")
    return Path(dest)


def check_stage(project, stage, entry, snapshot=DEFAULT_SNAPSHOT):
    """Judge what a stage left in the project, from the commits after its entry commit."""
    project = Path(project)
    subjects = [s for s in git(project, "log", "--all", "--format=%s", "--not", entry).stdout.splitlines()
                if s != "Upgrade pdlc"]
    done = stage_table(snapshot)[stage][2]
    fixture = SNAPSHOTS[snapshot]["fixture"]
    finished = any(s.startswith(done) for s in subjects)
    stopped = any(s.startswith("Stop ") for s in subjects)
    extra = {}
    git(project, "checkout", "-q", tip_branch(project))
    extra["writing"] = writing_findings(project, entry)
    changes = project / "pdlc" / "changes"
    if stage == "acceptance":
        extra["locked"] = any(re.match(r"Acceptance-Locked:[ \t]*(?!none\b)\S", line)
                              for path in (project / "pdlc" / "inbox").glob("IN-*.md")
                              for line in path.read_text().splitlines())
    elif stage == "tests":
        extra["locked"] = any(line.startswith("Tests-Locked:")
                              for path in changes.glob("CH-*/change.md")
                              for line in path.read_text().splitlines())
        extra["checks_fail_first"] = not unit_checks(project, fixture)["ok"]
    elif stage == "build":
        extra["unit"] = unit_checks(project, fixture)
        # The probes of the to-do apps need a build and a server, so a replay does not run them.
        extra["probes"] = (run_probes(project) if fixture == "wordfreq" else
                           {"passed": 0, "total": 0, "failed": [], "not_run": True})
    elif stage == "show":
        extra["gif"] = any(changes.glob("CH-*/review.gif"))
        extra["frames"] = len(list(changes.glob("CH-*/frames/*.png")))
    elif stage == "verify":
        merge = subprocess.run([sys.executable, "pdlc/bin/check_merge.py"], cwd=project, capture_output=True,
                               text=True, timeout=120)
        lines = (merge.stdout + merge.stderr).strip().splitlines()
        extra["merge"] = lines[0].strip() if lines else ""
    git(project, "checkout", "-q", "main")
    if stage in ("intake", "ready", "change"):
        passed = True
    elif stage == "acceptance":
        passed = extra["locked"]
    elif stage == "tests":
        passed = extra["locked"] and extra["checks_fail_first"]
    elif stage == "build":
        passed = extra["unit"]["ok"] and not extra["probes"]["failed"]
    elif stage == "show":
        passed = extra["gif"] and extra["frames"] > 0
    else:
        passed = extra["merge"].startswith("ok")
    return {"ok": finished and not stopped and passed, "finished": finished, "stopped": stopped,
            "subjects": subjects, "extra": extra}


def stage_outcome(stage, check, entry):
    """The outcome of one stage replay, in the shape that summarise and gate read."""
    return {
        "stage": stage, "entry": entry, "check": check,
        "merge_check": {"stage": ["ok   " + stage] if check["ok"] else ["FAIL " + stage]},
        "probes": check["extra"]["probes"] if stage == "build" else {"passed": len(PROBES), "total": len(PROBES), "failed": []},
        "unit": check["extra"]["unit"] if stage == "build" else {"ok": True, "ran": 0},
        "verify_rounds": None,
        "stops": [s for s in check["subjects"] if s.startswith("Stop ")],
        "writing": check["extra"]["writing"],
    }


def command_stage(args):
    """Replay one stage from the snapshot, once for each run, and write the results."""
    plugin = Path(args.plugin).resolve()
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot = getattr(args, "snapshot", DEFAULT_SNAPSHOT)
    prompt = stage_table(snapshot)[args.stage][1]

    def one(number):
        try:
            work = Path(tempfile.mkdtemp(prefix="pdlc-stage-"))
            project, entry = make_stage_project(work / "app", args.stage, plugin, snapshot)
            events, wall, err = run_claude(prompt, project, plugin, out_dir / ("run%d.stream.jsonl" % number),
                                           timeout=args.timeout, budget_usd=args.budget,
                                           tools=FIXTURES[SNAPSHOTS[snapshot]["fixture"]]["tools"])
            analysis = analyse(events)
            check = check_stage(project, args.stage, entry, snapshot)
            analysis["outcome"] = stage_outcome(args.stage, check, entry)
            analysis.update({"wall_s": wall, "project": str(project), "stderr": err[-500:]})
            (out_dir / ("run%d.json" % number)).write_text(json.dumps(analysis, indent=1))
            return analysis
        except Exception as error:  # one failed run must not stop the others
            print("run %d failed: %r" % (number, error), file=sys.stderr)
            return None

    with ThreadPoolExecutor(max_workers=args.runs) as pool:
        results = list(pool.map(one, range(1, args.runs + 1)))
    runs = [run for run in results if run is not None]
    summary = {"label": args.label, "stage": args.stage,
               "snapshot": snapshot,
               "plugin_commit": git(plugin, "rev-parse", "--short", "HEAD").stdout.strip(),
               "model": MODEL, "effort": EFFORT, "runs": runs}
    (out_dir / "e2e.json").write_text(json.dumps(summary, indent=1))
    for number, run in enumerate(results, 1):
        if run is not None:
            print("run %d: $%.2f, %ss, ok %s" % (number, run["totals"]["cost_usd"], run["wall_s"],
                                              run["outcome"]["check"]["ok"]))


PREPARE_STATES = ["init", *REPLAY_STAGES, "done", "board"]


def prepare_states(snapshot):
    """The states that `prepare` can make from a snapshot."""
    return ["init", *stage_table(snapshot), "done", "board"]


def command_prepare(args):
    """Make a project at one state, for a run that a different tool drives, for example /vet.

    The states are: before init, the start of each replay stage, after the proposal ("done"),
    and "done" with a board tracker set. `--snapshot` names the finished run to start from. The tag `start` marks the commit where the run starts.
    """
    plugin = Path(args.plugin).resolve()
    dest = Path(args.dest)
    snapshot = getattr(args, "snapshot", DEFAULT_SNAPSHOT)
    if args.state not in prepare_states(snapshot):
        raise SystemExit("The snapshot %s has no state %s." % (snapshot, args.state))
    if args.state == "init":
        make_project(dest, plugin, with_pdlc=False, fixture=SNAPSHOTS[snapshot]["fixture"])
    elif args.state in stage_table(snapshot):
        make_stage_project(dest, args.state, plugin, snapshot)
    else:
        make_done_project(dest, plugin, snapshot)
    if args.state == "board":
        # pdlc reads the config on main before any work, so main and the branch both get the tracker.
        branch = git(dest, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        for name in ("main", branch):
            git(dest, "checkout", "-q", name)
            set_tracker(dest)
    git(dest, "tag", "start")
    print(dest.resolve())


def set_tracker(project):
    """Set a GitHub Projects tracker that no run can reach, and commit it."""
    config = Path(project) / "pdlc" / "config.md"
    text = config.read_text().replace("- tracker: none", "- tracker: tracker-github-projects")
    text = text.replace("## Tracker settings\n\nThis section is necessary only when a tracker adapter is set. "
                        "The file of the adapter\ntells what goes here.\n\n- none",
                        "## Tracker settings\n\nThis section is necessary only when a tracker adapter is set. "
                        "The file of the adapter\ntells what goes here.\n\n- owner: example-org\n- project: 7\n"
                        "- status field: Status")
    config.write_text(text)
    git(project, "commit", "-q", "-am", "Set the tracker")


# ---------------------------------------------------------------- rebuilding from the specs

# The files of a finished project that the rebuild keeps: the specs, the config, and the
# README that tells how to read a spec. Rule 10 says that these files are enough.
REBUILD_KEEP = ("pdlc/specs/", "pdlc/config.md", "pdlc/README.md")


def config_checks(text):
    """The "Checks" section of a pdlc/config.md, as a dict.

    The keys are all, acceptance, acceptance_file, check_folders (a list) and id_form. A value
    is the text inside the first pair of backticks on its line. A missing line, or the value
    none, gives None.
    """
    found = re.search(r"^## Checks[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    section = found.group(1) if found else ""

    def items(key):
        line = re.search(r"^- %s:[ \t]*(.*?)[ \t]*$" % re.escape(key), section, re.M)
        raw = line.group(1) if line else ""
        values = re.findall(r"`([^`]*)`", raw) or [raw]
        values = [v for v in values if v.strip().lower() != "none"]
        return values if raw and values else None

    def first(key):
        values = items(key)
        return values[0] if values else None

    return {"all": first("all"), "acceptance": first("acceptance"), "acceptance_file": first("acceptance file"),
            "check_folders": items("check folders"), "id_form": first("ID form in check names")}


def rebuild_source(source, run=1, ref=None):
    """The project, the ref and the fixture to rebuild from.

    `source` is a result folder of an e2e run, or a project folder. For a result folder, the
    project and the tip come from run<N>.json, and the fixture from e2e.json. pdlc does not
    merge, so the tip is the newest change branch. It raises RuntimeError when the project
    folder is gone, because /tmp can be cleaned.
    """
    source = Path(source)
    saved = source / ("run%d.json" % run)
    fixture = "wordfreq"
    if saved.is_file():
        data = json.loads(saved.read_text())
        project = Path(data["project"])
        ref = ref or (data.get("outcome") or {}).get("tip")
        summary = source / "e2e.json"
        if summary.is_file():
            fixture = json.loads(summary.read_text()).get("fixture") or fixture
    elif (source / ".git").exists():
        project = source
    elif source.is_dir():
        raise RuntimeError("no run%d.json in %s" % (run, source))
    else:
        raise RuntimeError("%s does not exist" % source)
    if not project.exists():
        raise RuntimeError("the project %s does not exist any more" % project)
    if not (project / ".git").exists():
        raise RuntimeError("%s is not a git repository" % project)
    return project, ref or tip_branch(project), fixture


def export_tree(project, ref, dest):
    """Write the tracked files of `ref` to `dest`. No .git, and no file that git ignores."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(["git", "-C", str(project), "archive", ref], capture_output=True)
    if archive.returncode:
        raise RuntimeError("git archive %s failed: %s" % (ref, archive.stderr.decode()[:300]))
    unpack = subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, capture_output=True)
    if unpack.returncode:
        raise RuntimeError("tar failed: " + unpack.stderr.decode()[:300])
    return dest


def clean_copy(tree, dest, keep=()):
    """Copy only the files of REBUILD_KEEP, and the paths in `keep`, from `tree` to `dest`.

    Return the sorted relative paths. The copy gets a new git repository with one commit, so
    that `git status` after a build shows each file that the builder wrote.
    """
    tree, dest = Path(tree), Path(dest)
    keep = set(keep)
    paths = sorted(p.relative_to(tree).as_posix() for p in tree.rglob("*")
                   if p.is_file() and not p.is_symlink())
    kept = [path for path in paths if path.startswith("pdlc/specs/") or path in REBUILD_KEEP or path in keep]
    if not kept:
        raise RuntimeError("the tree has no spec, config or README to keep")
    for path in kept:
        (dest / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tree / path, dest / path)
    dest.mkdir(parents=True, exist_ok=True)
    git(dest, "init", "-q", "-b", "main")
    git(dest, "add", "-A")
    done = git(dest, "commit", "-q", "-m", "Specs only")
    if done.returncode:
        raise RuntimeError("git commit failed: " + (done.stdout + done.stderr)[:300])
    return kept


def acceptance_matches(tree, config):
    """Each file in `tree` that the "acceptance file" line names, with the file of init."""
    pattern = config.get("acceptance_file")
    if not pattern:
        return []
    tree = Path(tree)
    # "{intent}" stands for an intent ID, so the match is exact, as make_packets.py reads it.
    exact = re.compile("^%s$" % r"IN[-_]?\d+".join(re.escape(part) for part in pattern.strip("/ ").split("{intent}")), re.I)
    found = (p.relative_to(tree).as_posix() for p in tree.glob(pattern.replace("{intent}", "IN*")) if p.is_file())
    return sorted(path for path in found if exact.match(path))


def acceptance_files(tree, config):
    """The acceptance files of the project. IN-9999 is the test file of init, so it is left out."""
    return [path for path in acceptance_matches(tree, config) if "IN-9999" not in path]


def check_files(tree, config):
    """The component checks: each file in the check folders that is not an acceptance file."""
    tree = Path(tree)
    skip = set(acceptance_matches(tree, config))
    found = []
    for folder in config.get("check_folders") or []:
        for path in (tree / folder).rglob("*"):
            relative = path.relative_to(tree).as_posix()
            if path.is_file() and relative not in skip and "__pycache__" not in path.parts:
                found.append(relative)
    return sorted(set(found))


def check_origin(project, ref, files):
    """Where each check file came from: pre-pdlc, changed by pdlc, or added by pdlc.

    It compares `ref` with the root commit. A pre-pdlc check can fail because the fixture is
    old, not because of a fault in the specs, so the report keeps the three groups apart.
    """
    root = git(project, "rev-list", "--max-parents=0", ref).stdout.split()[-1]
    status = {}
    for line in git(project, "diff", "--name-status", "--no-renames", root, ref).stdout.splitlines():
        letter, _, path = line.partition("\t")
        status[path] = letter
    names = {"A": "added by pdlc", "M": "changed by pdlc"}
    return {path: names.get(status.get(path), "pre-pdlc") for path in files}


# ---------------------------------------------------------------- scoring a rebuilt project

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# A name that every check uses and no spec has to give.
COMMON_NAMES = set(keyword.kwlist) | set(dir(builtins)) | {"self", "cls"}
# The kinds of file that hold no app code, when the bench reads the code of a project.
NOT_CODE = (".md", ".lock", ".txt", ".json", ".toml")


def parse_check_output(text):
    """Read the output of a check runner.

    It reads Python unittest, the Rust test harness (cargo test, or a rustc --test binary) and
    clojure.test. Output of another runner gives ran 0. The result has:
    - ran: how many checks ran.
    - failed: the name of each failure that the output gives. Two failures with one name
      stay two. A clojure name has the file after it.
    - failed_count: the number of failures that the summary lines give.
    - skipped: skipped checks and expected failures (unittest). They ran, but did not pass.
    - passed_names: (binary, name) of each check that the runner shows as passed (Rust). The
      binary is the path in the "Running" line, "doc" for doc tests, None before any header.
    - named: true when the runner prints the name of each check (Rust).
    """
    ran = sum(int(n) for n in re.findall(r"^Ran (\d+) tests? in ", text, re.M))
    failed = re.findall(r"^(?:FAIL|ERROR): (\S+ \(\S+\))", text, re.M)
    count = sum(int(n) for line in re.findall(r"^FAILED \((.*)\)", text, re.M)
                for n in re.findall(r"(?:failures|errors)=(\d+)", line))
    skipped = sum(int(n) for line in re.findall(r"^(?:OK|FAILED) \((.*)\)", text, re.M)
                  for n in re.findall(r"(?:skipped|expected failures)=(\d+)", line))
    results = re.findall(r"^test result: \w+\. (\d+) passed; (\d+) failed", text, re.M)
    ran += sum(int(passed) + int(bad) for passed, bad in results)
    count += sum(int(bad) for _, bad in results)
    rust = re.findall(r"^test (.+?) \.\.\. FAILED$", text, re.M)
    failed += rust or re.findall(r"^---- (.+?) stdout ----$", text, re.M)
    passed_names, binary = [], None
    for line in text.splitlines():
        header = re.match(r"\s*Running (?:unittests )?(\S+)", line)
        if header:
            binary = header.group(1)
        elif re.match(r"\s*Doc-tests ", line):
            binary = "doc"
        done = re.match(r"test (.+?) \.\.\. ok$", line)
        if done:
            passed_names.append((binary, done.group(1)))
    ran += sum(int(n) for n in re.findall(r"^Ran (\d+) tests containing", text, re.M))
    count += sum(int(a) + int(b) for a, b in re.findall(r"^(\d+) failures, (\d+) errors", text, re.M))
    for name, where in re.findall(r"^(?:FAIL|ERROR) in \((\S+)\)(?: \(([^:)]+))?", text, re.M):
        failed.append(name + (" " + where if where else ""))
    return {"ran": ran, "failed": failed, "failed_count": count, "skipped": skipped,
            "passed_names": passed_names, "named": bool(rust or passed_names)}


def run_checks(project, command, files=None, timeout=900):
    """Run a check command with bash in `project`. `{files}` stands for the quoted `files`.

    Returns ok (exit code 0), the fields of parse_check_output, and the last 2,000 characters
    of the output. At the timeout it kills the whole process group and keeps the output so far.
    """
    if files is not None:
        command = command.replace("{files}", " ".join(shlex.quote(f) for f in files))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(["bash", "-c", command], cwd=project, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, env=env, start_new_session=True)
    try:
        output = proc.communicate(timeout=timeout)[0]
        ok = proc.returncode == 0
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        output = (proc.communicate()[0] or "") + "\ntimeout after %d s\n" % timeout
        ok = False
    return {"ok": ok, **parse_check_output(output), "output": output[-2000:]}


def real_folder(root, relative):
    """Make the folder `relative` under `root` a real folder. A link on the way is removed."""
    path = Path(root)
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            path.unlink()
        path.mkdir(exist_ok=True)
    return path


def install_checks(tree, rebuilt, config):
    """Put the original checks in the rebuilt project, in place of the checks of the builder.

    It removes each file in the check folders, and each acceptance file, so that a check that
    the builder wrote cannot count. It never follows a link: a link is replaced. Then it copies
    the original checks from `tree`.
    """
    tree, rebuilt = Path(tree), Path(rebuilt)
    for folder in config.get("check_folders") or []:
        real_folder(rebuilt, folder)
        for here, dirs, names in os.walk(rebuilt / folder):
            for name in names + [d for d in dirs if (Path(here) / d).is_symlink()]:
                (Path(here) / name).unlink()
    for relative in acceptance_matches(rebuilt, config):
        (rebuilt / relative).unlink()
    for relative in check_files(tree, config) + acceptance_matches(tree, config):
        real_folder(rebuilt, Path(relative).parent)
        if (rebuilt / relative).is_symlink():
            (rebuilt / relative).unlink()
        shutil.copy2(tree / relative, rebuilt / relative)


def check_names(tree, files):
    """The names of the checks that the files define: unittest, the Rust harness, clojure.test."""
    names = []
    for relative in files:
        text = (Path(tree) / relative).read_text(errors="replace")
        names += re.findall(r"^\s*(?:async\s+)?def\s+(test\w*)", text, re.M)
        names += re.findall(r"#\[test\]\s*(?:#\[[^\]]*\]\s*)*(?:pub\s+)?fn\s+(\w+)", text)
        names += re.findall(r"\(deftest\s+([^\s()]+)", text)
    return list(dict.fromkeys(names))


def score(ran_original, result, names=(), skipped_original=0, files=None):
    """Score one run of the original checks against the rebuilt project.

    `names` are the original checks. When the runner prints the name of each check (Rust), only
    an original check that the output shows as passed counts: a unit test in src/, a doc test,
    and a check that never ran (cargo stops at the first failing binary) do not. Else `total`
    is the number of checks in the original run. A run that crashed reports fewer checks. When
    every check that ran failed, none passed, so each name in `names` goes in `failed`. When
    some passed, the checks that did not run count as not passed, but their names are not
    known. A skipped check does not pass, unless the original run skipped it too. With `files`
    (the original check files), a name counts only when its binary is one of them or unknown.
    """
    ran, failed = result["ran"], list(result["failed"])
    if result.get("named") and names:
        passed = Counter(name.split("::")[-1] for binary, name in result.get("passed_names", [])
                         if files is None or binary is None or binary in files)
        failed = []
        for name in names:
            if passed[name]:
                passed[name] -= 1
            else:
                failed.append(name)
        return {"total": len(names), "passed": len(names) - len(failed), "failed": failed}
    total = ran_original
    bad = max(len(failed), result.get("failed_count", 0))
    if ran < total and ran == bad and names:
        return {"total": total, "passed": 0, "failed": list(names)}
    not_run = max(0, total - ran)
    skipped = max(0, result.get("skipped", 0) - skipped_original)
    return {"total": total, "passed": max(0, total - bad - not_run - skipped), "failed": failed}


def missing_names(check_text, code_text, spec_text):
    """The names that a check uses and the original code has, but no spec gives.

    A spec has to give each such name in an "Interface" entry, or a builder cannot know it.
    Keywords and built-in names do not count, and nor do names of fewer than 3 characters.
    """
    wanted = {n for n in IDENTIFIER.findall(check_text) if len(n) >= 3 and n not in COMMON_NAMES}
    return sorted(wanted & set(IDENTIFIER.findall(code_text)) - set(IDENTIFIER.findall(spec_text)))


def failing_file(name, tree, files):
    """The check file that holds the failing check `name`, or None."""
    tokens = set(re.findall(r"[\w-]+", name))
    for relative in files:
        if Path(relative).stem in tokens:
            return relative
    for relative in files:
        if tokens & set(check_names(tree, [relative])):
            return relative
    return None


def requirement_of(name, specs):
    """The requirement ID in the name of a check, and the spec file that holds it.

    `specs` maps a spec file to its text. The ID form (dots or underscores) does not matter.
    """
    flat = re.sub(r"[-.]", "_", name)
    for relative in sorted(specs, key=lambda r: -len(Path(r).stem)):
        stem = Path(relative).stem
        found = re.search(re.escape(stem.replace("-", "_")) + r"_R(\d+)", flat)
        if found:
            return "%s.R%s" % (stem, found.group(1)), relative
    return None, None


def code_text_of(tree, config):
    """The text of the app code in `tree`: no spec, no check, no build folder, no doc file."""
    tree = Path(tree)
    checks = set(check_files(tree, config) + acceptance_matches(tree, config))
    skip = {"target", ".cpcache", "__pycache__", "node_modules", ".git"}
    text = ""
    for here, dirs, names in os.walk(tree):
        dirs[:] = sorted(d for d in dirs if d not in skip)
        for name in sorted(names):
            path = Path(here) / name
            relative = path.relative_to(tree).as_posix()
            if (not path.is_symlink() and not relative.startswith("pdlc/") and relative not in checks
                    and not relative.endswith(NOT_CODE)):
                text += path.read_text(errors="replace") + "\n"
    return text


def spec_gaps(tree, config, failed, code_text=None):
    """For each failing check: its requirement and spec, and the names that the specs lack.

    `code_text` is the app code. Pass it from before the checks ran, so that no file that a
    check run wrote counts as code.
    """
    tree = Path(tree)
    specs = {p.relative_to(tree).as_posix(): p.read_text(errors="replace")
             for p in sorted((tree / "pdlc" / "specs").rglob("*.md")) if p.is_file()}
    spec_text = "\n".join(specs.values())
    checks = check_files(tree, config) + acceptance_matches(tree, config)
    if code_text is None:
        code_text = code_text_of(tree, config)
    gaps = []
    for name in failed:
        file = failing_file(name, tree, checks)
        requirement, spec = requirement_of(name, specs)
        names = missing_names((tree / file).read_text(errors="replace"), code_text, spec_text) if file else []
        gaps.append({"check": name, "file": file, "requirement": requirement, "spec": spec, "missing_names": names})
    return gaps


def score_rebuild(tree, rebuilt, config, fixture, origin=None):
    """Score the rebuilt project with the original checks and the probes of the fixture.

    `tree` is the original project. It runs the checks on `tree` first, to get the totals.
    Then it installs the original checks in `rebuilt` and runs them there. Returns acceptance,
    component, probes, gaps, and original. `origin` (from check_origin) goes in `component`.
    """
    tree, rebuilt = Path(tree), Path(rebuilt)
    acceptance = acceptance_files(tree, config) if config.get("acceptance") else []
    sections = {"acceptance": (config.get("acceptance"), acceptance, check_names(tree, acceptance)),
                "component": (config.get("all"), None, check_names(tree, check_files(tree, config)))}
    code_text = code_text_of(tree, config)  # before any run: a run can write files
    owned = {"acceptance": acceptance, "component": check_files(tree, config)}
    original = {key: run_checks(tree, command, files) for key, (command, files, _) in sections.items()
                if command and (files is None or files)}
    install_checks(tree, rebuilt, config)
    out = {"original": {key: {k: v for k, v in done.items() if k != "output"} for key, done in original.items()}}
    gaps = []
    for key, (command, files, names) in sections.items():
        if key not in original:
            out[key] = {"measured": False}
            continue
        if not original[key]["ok"] or not original[key]["ran"]:
            out[key] = {"measured": False, "reason": "the original checks did not pass"}
            continue
        done = run_checks(rebuilt, command, files)
        out[key] = {"measured": True, **score(original[key]["ran"], done, names, original[key]["skipped"], owned[key]),
                    "ok": done["ok"], "output": done["output"]}
        gaps += out[key]["failed"]
    if out["component"].get("measured"):
        out["component"]["origin"] = origin or {}
        files = check_files(tree, config)
        out["component"]["failed_files"] = {n: failing_file(n, tree, files)
                                            for n in out["component"]["failed"]}
    out["probes"] = fixture_probes(rebuilt, fixture)
    out["gaps"] = spec_gaps(tree, config, gaps, code_text)
    return out


# ---------------------------------------------------------------- the rebuild command

REBUILD_PROMPT = (
    "Build the whole app in this folder from the specs alone. The specs are the files in "
    "`pdlc/specs/`: jobs, capabilities, and design. `pdlc/config.md` gives the commands that build "
    "the app and run its checks. `pdlc/README.md` tells you how to read a spec. "
    "Build each job and each capability, also a spec with the status `stub`. Make each requirement "
    "true. Keep each name, file, and error code of each \"Interface\" entry exactly as its spec gives "
    "it. Make the \"all\" command of `pdlc/config.md` run with no error. Work only in this folder. "
    "Do not read a file outside this folder. Do not look for a different copy of this app. "
    "Do not change the files in `pdlc/`. Stop when the app is complete."
)

PATH_INPUTS = ("file_path", "path", "pattern", "command")


def loaded_plugins(events):
    """The plugins that the first init event of a stream lists. An empty list if there is none."""
    for item in events:
        event = item.get("e", item)
        if event.get("type") == "system" and event.get("subtype") == "init":
            return event.get("plugins") or []
    return []


def peeked(events, forbidden):
    """Each tool input or tool output of the builder that names a path in `forbidden`.

    The inputs are file_path, path, pattern, and command. The outputs are the text of each tool
    result. The builder must not read the original project, so a run with an item here is not a
    test of the specs. A relative path, a glob or a command substitution can get past this check.
    """
    found = []
    for item in events:
        event = item.get("e", item)
        for block in (event.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if event.get("type") == "user" and block.get("type") == "tool_result":
                content = block.get("content")
                parts = [content] if isinstance(content, str) else [c.get("text", "") for c in content or [] if isinstance(c, dict)]
                found += [text for text in parts if isinstance(text, str) and any(path and path in text for path in forbidden)]
            if event.get("type") != "assistant" or block.get("type") != "tool_use":
                continue
            for key in PATH_INPUTS:
                value = (block.get("input") or {}).get(key)
                if isinstance(value, str) and any(path and path in value for path in forbidden):
                    found.append(value)
    return found


def rebuild_verdict(result):
    """holds, invalid, or broken. The verdict does not say holds without a measure.

    invalid: the builder peeked, or the original checks did not pass, so the test says nothing.
    holds: acceptance was measured, each acceptance check and each probe passed.
    broken: each other result.
    """
    acceptance, component = result.get("acceptance") or {}, result.get("component") or {}
    if result.get("peeked") or any(part.get("reason") for part in (acceptance, component)):
        return "invalid"
    probes = result.get("probes") or {}
    if (acceptance.get("measured") and acceptance.get("total") and not acceptance.get("failed")
            and acceptance.get("passed") == acceptance["total"] and acceptance.get("ok")
            and probes.get("total") and probes.get("passed") == probes["total"]):
        return "holds"
    return "broken"


def rebuild_report(result):
    """The result of a rebuild, as Markdown: the verdict, the scores, then each failing check."""
    source, acceptance, component = result["source"], result["acceptance"], result["component"]
    probes = result["probes"]

    def share(part):
        if not part.get("measured"):
            return "not measured" + (" (%s)" % part["reason"] if part.get("reason") else "")
        return "%d/%d" % (part["passed"], part["total"])

    lines = ["# Rebuild %s: %s" % (result["label"], result["verdict"]), "",
             "Peek check: tool inputs and outputs only. A relative path, a glob or a command substitution can get past it.",
             "",
             "- Source: %s at `%s` (%s)" % (source["project"], source["ref"], source["fixture"]),
             "- Acceptance: %s" % share(acceptance),
             "- Component: %s" % share(component),
             "- Probes: %d/%d" % (probes["passed"], probes["total"]),
             "- Cost: $%.2f in %ss" % (result["cost_usd"], result["wall_s"])]
    if result.get("plugin_warning"):
        lines.append("- Warning: " + result["plugin_warning"])
    if result.get("kept_extra"):
        lines.append("- Extra files kept: " + ", ".join(result["kept_extra"]))
    if result["peeked"]:
        lines += ["", "## The builder read the original", ""] + ["- `%s`" % value for value in result["peeked"][:20]]
    gaps = {gap["check"]: gap for gap in result.get("gaps") or []}
    if acceptance.get("failed"):
        lines += ["", "## Failing acceptance checks", "", "| Check | Requirement | Spec | Missing names |", "| --- | --- | --- | --- |"]
        for name in acceptance["failed"]:
            gap = gaps.get(name, {})
            lines.append("| %s | %s | %s | %s |" % (name, gap.get("requirement") or "-", gap.get("spec") or "-",
                                                    ", ".join(gap.get("missing_names") or []) or "-"))
    if component.get("failed"):
        lines += ["", "## Failing component checks", ""]
        origin = component.get("origin") or {}
        files = component.get("failed_files") or {}
        for name in component["failed"]:
            file = files.get(name)
            lines.append("- %s (%s)" % (name, origin.get(file, "origin unknown") if file else "origin unknown"))
    return "\n".join(lines) + "\n"


def command_rebuild(args, builder=None):
    """Rebuild a finished project from its specs alone, and score the new app.

    `builder(folder)` returns (events, wall seconds, stderr) as run_claude does. A test gives a
    fake one. The folder of the builder has no `pdlc-bench-` name, so that its own paths do not
    count as a peek.
    """
    project, ref, fixture = rebuild_source(args.source, args.run, args.ref)
    fixture = args.fixture or fixture
    plugin = Path(args.plugin).resolve()
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="pdlc-rebuild-"))
    commit = git(project, "rev-parse", ref).stdout.strip()  # the branch can move while the builder runs
    tree = export_tree(project, commit, work / "original")
    config = config_checks((tree / "pdlc" / "config.md").read_text())
    app = work / "app"
    kept = clean_copy(tree, app, args.keep)
    shutil.rmtree(tree)  # the builder could read it at ../original
    source = {"project": str(project), "ref": ref, "fixture": fixture,
              "commit": commit,
              "plugin_commit": git(plugin, "rev-parse", "--short", "HEAD").stdout.strip(),
              "plugin_status": git(plugin, "status", "--porcelain", ".").stdout.strip(), "plugins": None}
    result = {"label": args.label, "source": source, "model": MODEL, "effort": EFFORT}
    stream = Path(args.source) / ("run%d.stream.jsonl" % args.run)
    if stream.is_file():
        old = [json.loads(line) for line in stream.read_text().splitlines() if line.strip()]
        source["plugins"] = loaded_plugins(old)
        paths = [Path(p.get("path", "")).resolve() for p in source["plugins"] if p.get("name") == "pdlc"]
        if plugin not in paths:
            result["plugin_warning"] = ("the e2e run did not load the plugin %s. It loaded: %s"
                                        % (plugin, ", ".join(str(p) for p in paths) or "no pdlc plugin"))
    if builder is None:
        def builder(folder):
            return run_claude(REBUILD_PROMPT, folder, None, out_dir / "rebuild.stream.jsonl", timeout=args.timeout,
                              budget_usd=args.budget, tools=FIXTURES[fixture]["tools"], env=session_env(folder))
    events, wall, err = builder(app)
    analysis = analyse(events)
    forbidden = {str(project), str(project.resolve()), str(REPO), "pdlc-bench-"}
    status = git(app, "status", "--porcelain", "-uall").stdout.splitlines()
    result.update({
        "cost_usd": analysis["totals"]["cost_usd"], "wall_s": wall, "stderr": err[-500:],
        "peeked": peeked(events, forbidden), "kept": kept, "kept_extra": sorted(set(args.keep) & set(kept)),
        "builder_files": sorted(line[3:] for line in status if "__pycache__" not in line and not line.endswith(".pyc"))})
    try:
        tree = export_tree(project, commit, work / "original")
        origin = check_origin(project, commit, check_files(tree, config))
        result.update(score_rebuild(tree, app, config, fixture, origin))
    finally:
        shutil.rmtree(work / "original", ignore_errors=True)  # a later builder must not find it
    result["verdict"] = rebuild_verdict(result)
    (out_dir / "rebuild.json").write_text(json.dumps(result, indent=1))
    (out_dir / "rebuild.md").write_text(rebuild_report(result))
    share = lambda part: "%d/%d" % (part["passed"], part["total"]) if part.get("measured") else "not measured"
    print("%s: acceptance %s, component %s, probes %d/%d, $%.2f, %ss"
          % (result["verdict"], share(result["acceptance"]), share(result["component"]),
             result["probes"]["passed"], result["probes"]["total"], result["cost_usd"], result["wall_s"]))
    return result


# ---------------------------------------------------------------- the commands


def command_e2e(args):
    plugin = Path(args.plugin).resolve()
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for number in range(1, args.runs + 1):
        work = Path(tempfile.mkdtemp(prefix="pdlc-bench-"))
        fixture = FIXTURES[args.fixture]
        project = make_project(work / "app", plugin, fixture=args.fixture)
        log = out_dir / ("run%d.stream.jsonl" % number)
        events, wall, err = run_claude("/pdlc:ship defaults " + (getattr(args, "intent", None) or fixture["intent"]), project, plugin, log,
                                       timeout=args.timeout, budget_usd=args.budget,
                                       extra=("--forward-subagent-text",) if args.forward else (),
                                       tools=fixture["tools"])
        analysis = analyse(events)
        analysis["wall_s"] = wall
        try:
            analysis["outcome"] = inspect_project(project, args.fixture)
        except Exception as error:  # keep the run: its stream and its cost are already paid for
            analysis["outcome"] = {"error": repr(error), "probes": {"passed": 0, "total": fixture["probes"], "failed": []},
                                   "unit": {"ok": False, "ran": 0}}
        analysis["stderr"] = err[-500:]
        analysis["project"] = str(project)
        try:
            import metrics
            analysis["metrics"] = metrics.measure_stream(events, args.fixture)
            analysis["metrics"]["git"] = metrics.measure_project(project, args.fixture)
            analysis["metrics"]["quality"] = metrics.measure_quality(project, args.fixture)
            analysis["metrics"]["strength"] = metrics.measure_strength(project, args.fixture)
        except Exception as error:  # the measures add detail; a fault in them must not lose the run
            analysis["metrics"] = {"error": repr(error)}
        runs.append(analysis)
        (out_dir / ("run%d.json" % number)).write_text(json.dumps(analysis, indent=1))
        print("run %d: $%.2f, %ss, probes %s/%s" % (number, analysis["totals"]["cost_usd"], analysis["wall_s"],
              analysis["outcome"]["probes"]["passed"], analysis["outcome"]["probes"]["total"]))
    summary = {"label": args.label, "plugin_commit": git(plugin, "rev-parse", "--short", "HEAD").stdout.strip(),
               "model": MODEL, "effort": EFFORT, "fixture": args.fixture, "runs": runs}
    (out_dir / "e2e.json").write_text(json.dumps(summary, indent=1))
    return summary


def command_init_fixture(args):
    plugin = Path(args.plugin).resolve()
    work = Path(tempfile.mkdtemp(prefix="pdlc-bench-init-"))
    project = make_project(work / "app", plugin, with_pdlc=False, fixture=args.fixture)
    log = work / "init.stream.jsonl"
    events, wall, err = run_claude("/pdlc:init defaults", project, plugin, log, timeout=args.timeout, budget_usd=args.budget,
                                   tools=FIXTURES[args.fixture]["tools"])
    analysis = analyse(events)
    print(json.dumps({"wall_s": wall, "totals": analysis["totals"], "stderr": err[-300:]}, indent=1))
    print("project:", project)
    print("log:", log)


def noise(values):
    """The spread of repeated runs, as a share of their mean. Zero for one run."""
    if len(values) < 2:
        return 0.0
    mean = statistics.mean(values)
    return (max(values) - min(values)) / mean if mean else 0.0


def completed(run):
    """A run is complete when pdlc proposed the change and the merge check passes on its branch.

    The merge check prints nothing on an intent branch, which has no change of its own to merge.
    Such a branch does not count.
    """
    checks = [lines for lines in (run["outcome"].get("merge_check") or {}).values() if lines]
    return bool(checks) and all(lines[0].startswith("ok") for lines in checks)


def permutation_p(base, cand):
    """The chance that a candidate this much cheaper arises when the edit changes nothing.

    One-sided, exact: it tries every way to split the runs into a baseline and a candidate.
    """
    from itertools import combinations

    pooled = list(base) + list(cand)
    seen = statistics.mean(base) - statistics.mean(cand)
    total = better = 0
    for chosen in combinations(range(len(pooled)), len(cand)):
        picked = [pooled[i] for i in chosen]
        rest = [pooled[i] for i in range(len(pooled)) if i not in chosen]
        total += 1
        if statistics.mean(rest) - statistics.mean(picked) >= seen - 1e-12:
            better += 1
    return better / total


def summarise(result):
    """Reduce a result file to the numbers that the gate reads."""
    runs = result["runs"]
    costs = [r["totals"]["cost_usd"] for r in runs]
    durations = [r.get("wall_s") or r["totals"]["duration_s"] for r in runs]
    return {
        "runs": len(runs),
        "cost_usd": statistics.mean(costs),
        "duration_s": statistics.mean(durations),
        "noise": noise(costs),
        "costs": costs,
        "completed": sum(1 for r in runs if completed(r)),
        "rounds": [r["outcome"].get("verify_rounds") for r in runs],
        "probes_all": all(r["outcome"]["probes"]["passed"] == r["outcome"]["probes"]["total"] for r in runs),
        "units_ok": all(r["outcome"]["unit"]["ok"] for r in runs),
        "seeds_caught": result.get("seeds", {}).get("caught"),
        "false_fails": result.get("seeds", {}).get("false_fails"),
        "waiting": [r.get("waiting", {}).get("cost_usd", 0.0) for r in runs],
        "waiting_turns": [r.get("waiting", {}).get("messages", 0) for r in runs],
        "writing": [(r["outcome"].get("writing") or {}).get("count") for r in runs],
    }


def agent_stats(result, label):
    """Cost and calls of one agent type over all runs of a result, and its cost for each call."""
    per_run, counts, cost, calls = [], [], 0.0, 0
    for run in result["runs"]:
        run_cost = run_calls = 0
        for stage in run["stages"].values():
            agent = stage["agents"].get(label)
            if agent:
                run_cost += agent["cost_usd"]
                run_calls += agent["calls"]
        cost += run_cost
        calls += run_calls
        counts.append(run_calls)
        if run_calls:
            per_run.append(run_cost / run_calls)
    return {"cost": cost, "calls": calls, "per_call": cost / calls if calls else 0.0, "per_run": per_run,
            "counts": counts, "calls_per_run": calls / len(result["runs"]) if result["runs"] else 0.0}


def gate(baseline, candidate, min_gain=0.05, speed_limit=1.5, target=None, alpha=0.10, min_runs=5):
    """Decide if an edit stays. Effectiveness must not fall. Cost must fall by more than the noise.

    Without a target, the gate asks if the candidate runs cost clearly less than the baseline runs.
    It uses an exact permutation test, so that the spread between identical runs sets how much
    evidence it needs.

    A whole run varies a lot between identical runs, because the number of review rounds varies.
    For an edit that aims at one agent, `target` names the agent. The gate then judges the cost
    of each call of that agent, which varies much less, and it shows what that means for a whole
    run. A whole run must still not cost clearly more than before.
    """
    base, cand = summarise(baseline), summarise(candidate)
    reasons = []
    worse = []
    if base["completed"] == base["runs"] and cand["completed"] < cand["runs"]:
        worse.append("pdlc did not finish in %d of %d runs, and it finished in every baseline run"
                     % (cand["runs"] - cand["completed"], cand["runs"]))
    if base["probes_all"] and not cand["probes_all"]:
        worse.append("acceptance probes fail")
    if base["units_ok"] and not cand["units_ok"]:
        worse.append("the project's own checks fail")
    if base["seeds_caught"] is not None and cand["seeds_caught"] is not None:
        missed = sorted(set(base["seeds_caught"]) - set(cand["seeds_caught"]))
        if missed:
            worse.append("planted defects no longer caught: " + ", ".join(missed))
    if base["false_fails"] is not None and cand["false_fails"] is not None:
        extra = sorted(set(cand["false_fails"]) - set(base["false_fails"]))
        if extra:
            worse.append("clean change now fails review: " + ", ".join(extra))
    run_change = (cand["cost_usd"] - base["cost_usd"]) / base["cost_usd"] if base["cost_usd"] else 0.0
    slower = cand["duration_s"] / base["duration_s"] if base["duration_s"] else 1.0
    if slower > speed_limit:
        worse.append("%.0f%% slower, limit is %.0f%%" % ((slower - 1) * 100, (speed_limit - 1) * 100))
    detail = {}
    p_value = None
    if target == "waiting":
        before, after = base["waiting"], cand["waiting"]
        chance = permutation_p(before, after)
        p_value = chance
        saved = statistics.mean(before) - statistics.mean(after)
        share = saved / base["cost_usd"] if base["cost_usd"] else 0.0
        few = min(len(before), len(after)) < min_runs
        detail = {"target": "waiting", "per_run_before": statistics.mean(before),
                  "per_run_after": statistics.mean(after),
                  "turns_before": statistics.mean(base["waiting_turns"]),
                  "turns_after": statistics.mean(cand["waiting_turns"]),
                  "expected_run_saving": saved, "expected_run_saving_share": share}
        if run_change > 0 and (run_change > max(base["noise"], 0.25)
                               or permutation_p(cand["costs"], base["costs"]) <= alpha):
            worse.append("a whole run costs %.0f%% more, and that is not luck" % (run_change * 100))
        change = -share
        needed = min_gain
        if chance > alpha:
            change = 0.0
        gain_text = "waiting turns cost $%.2f -> $%.2f a run (%.1f -> %.1f turns), %.0f%% of a run less, and the chance that this is luck is %.0f%%" % (
            statistics.mean(before), statistics.mean(after), detail["turns_before"], detail["turns_after"],
            share * 100, chance * 100)
        none_text = "waiting turns cost $%.2f -> $%.2f a run, %.0f%% of a run less, and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
            statistics.mean(before), statistics.mean(after), share * 100, chance * 100, alpha * 100)
    elif target == "writing":
        before, after = base["writing"], cand["writing"]
        if not before or not after or None in before or None in after:
            missing = "baseline" if (not before or None in before) else "candidate"
            change, needed, few, p_value, detail = 0.0, min_gain, False, None, {}
            gain_text = none_text = ("the %s has no writing count, so the findings cannot be judged "
                                     "(run `recheck` on its folder)" % missing)
        else:
            chance = permutation_p(before, after)
            p_value = chance
            needed = min_gain
            few = min(len(before), len(after)) < min_runs
            mean_before, mean_after = statistics.mean(before), statistics.mean(after)
            change = (mean_after - mean_before) / mean_before if mean_before else 0.0
            detail = {"target": "writing", "findings_before": mean_before, "findings_after": mean_after}
            if run_change > max(base["noise"], 0.25) or (run_change > 0.10 and permutation_p(cand["costs"], base["costs"]) <= alpha):
                worse.append("a run costs %.0f%% more, and that is not luck" % (run_change * 100))
            if chance > alpha:
                change = 0.0
            gain_text = "writing findings fell from %.1f to %.1f a run (%.0f%% fewer), and the chance that this is luck is %.0f%%" % (
                mean_before, mean_after, -change * 100, chance * 100)
            none_text = "writing findings changed from %.1f to %.1f a run (%+.0f%%), and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
                mean_before, mean_after, change * 100, chance * 100, alpha * 100)
    elif target and target.startswith("calls:"):
        name = target[len("calls:"):]
        before, after = agent_stats(baseline, name), agent_stats(candidate, name)
        counts_before, counts_after = before["counts"], after["counts"]
        mean_before, mean_after = statistics.mean(counts_before), statistics.mean(counts_after)
        change = (mean_after - mean_before) / mean_before if mean_before else 0.0
        chance = permutation_p(counts_before, counts_after)
        p_value = chance
        needed = min_gain
        few = min(len(counts_before), len(counts_after)) < min_runs
        saved = before["per_call"] * (mean_before - mean_after)
        detail = {"target": target, "calls_before": mean_before, "calls_after": mean_after,
                  "per_call_before": before["per_call"], "expected_run_saving": saved,
                  "expected_run_saving_share": saved / base["cost_usd"] if base["cost_usd"] else 0.0}
        if run_change > 0 and (run_change > max(base["noise"], 0.25)
                               or permutation_p(cand["costs"], base["costs"]) <= alpha):
            worse.append("a whole run costs %.0f%% more, and that is not luck" % (run_change * 100))
        gain_text = "%s calls fell from %.2f to %.2f a run (%.0f%% fewer), and the chance that this is luck is %.0f%%" % (
            name, mean_before, mean_after, -change * 100, chance * 100)
        none_text = "%s calls changed from %.2f to %.2f a run (%+.0f%%), and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
            name, mean_before, mean_after, change * 100, chance * 100, alpha * 100)
        if chance > alpha:
            change = 0.0
    elif target:
        before, after = agent_stats(baseline, target), agent_stats(candidate, target)
        change = (after["per_call"] - before["per_call"]) / before["per_call"] if before["per_call"] else 0.0
        if not before["per_run"] or not after["per_run"]:
            missing = "baseline" if not before["per_run"] else "candidate"
            change, needed, few, p_value, detail = 0.0, min_gain, False, None, {}
            gain_text = none_text = "the %s has no %s call, so the cost of a call cannot be judged" % (missing, target)
        else:
            chance = permutation_p(before["per_run"], after["per_run"])
            p_value = chance
            needed = min_gain
            few = min(len(before["per_run"]), len(after["per_run"])) < min_runs
            saved = (before["per_call"] - after["per_call"]) * before["calls_per_run"]
            detail = {"target": target, "per_call_before": before["per_call"], "per_call_after": after["per_call"],
                      "calls_per_run": before["calls_per_run"], "expected_run_saving": saved,
                      "expected_run_saving_share": saved / base["cost_usd"] if base["cost_usd"] else 0.0}
            if run_change > 0 and (run_change > max(base["noise"], 0.25)
                                   or permutation_p(cand["costs"], base["costs"]) <= alpha):
                worse.append("a whole run costs %.0f%% more, and that is not luck" % (run_change * 100))
            gain_text = "each %s call costs %.0f%% less, and the chance that this is luck is %.0f%%" % (
                target, -change * 100, chance * 100)
            none_text = "each %s call changed %+.0f%%, and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
                target, change * 100, chance * 100, alpha * 100)
            if chance > alpha:
                change = 0.0
    else:
        change = run_change
        needed = min_gain
        few = min(len(base["costs"]), len(cand["costs"])) < min_runs
        chance = permutation_p(base["costs"], cand["costs"])
        p_value = chance
        if chance > alpha:
            change = 0.0
        gain_text = "cost fell %.0f%%, and the chance that this is luck is %.0f%%" % (-run_change * 100, chance * 100)
        none_text = "cost changed %+.0f%%, and the chance that this is luck is %.0f%% (it must be %.0f%% or less)" % (
            run_change * 100, chance * 100, alpha * 100)
    if worse:
        verdict = "REGRESSION -> revert"
        reasons = worse
    elif few and change <= -needed:
        verdict = "NEED MORE RUNS -> do not keep yet"
        reasons = ["the fall looks like %.0f%%, but %d runs are too few. Run at least %d on each side. Four runs that looked 25%% cheaper came back at +10%% with six more." % (
            -change * 100, min(len(base["costs"]), len(cand["costs"])), min_runs)]
    elif change <= -needed:
        verdict = "SAME OR BETTER -> keep"
        reasons = [gain_text]
    else:
        verdict = "NO GAIN -> revert"
        reasons = [none_text]
    return {"verdict": verdict, "reasons": reasons, "baseline": base, "candidate": cand, "cost_change": run_change,
            "target": detail, "p": p_value}


def command_gate(args):
    result = gate(json.loads(Path(args.baseline).read_text()), json.loads(Path(args.candidate).read_text()),
                  args.min_gain, args.speed_limit, args.target, min_runs=args.min_runs)
    base, cand = result["baseline"], result["candidate"]
    print("baseline   cost $%.2f  time %4.0fs  runs %d  noise %2.0f%%" % (base["cost_usd"], base["duration_s"], base["runs"], base["noise"] * 100))
    print("candidate  cost $%.2f  time %4.0fs  runs %d  noise %2.0f%%" % (cand["cost_usd"], cand["duration_s"], cand["runs"], cand["noise"] * 100))
    print("finished   %d of %d vs %d of %d runs   verify rounds %s vs %s" % (
        base["completed"], base["runs"], cand["completed"], cand["runs"], base["rounds"], cand["rounds"]))
    print("probes     %s vs %s" % (base["probes_all"], cand["probes_all"]))
    detail = result["target"]
    if detail and detail["target"] == "waiting":
        print("waiting    $%.2f -> $%.2f a run, %.1f -> %.1f turns, so about $%.2f (%.0f%%) less in a run" % (
            detail["per_run_before"], detail["per_run_after"], detail["turns_before"], detail["turns_after"],
            detail["expected_run_saving"], detail["expected_run_saving_share"] * 100))
    elif detail and detail["target"] == "writing":
        print("writing    %.1f -> %.1f findings a run, and a run costs %+.0f%%" % (
            detail["findings_before"], detail["findings_after"], result["cost_change"] * 100))
    elif detail and detail["target"].startswith("calls:"):
        print("%s  %.2f -> %.2f calls a run at $%.3f each, so about $%.2f (%.0f%%) less in a run" % (
            detail["target"], detail["calls_before"], detail["calls_after"],
            detail["per_call_before"], detail["expected_run_saving"],
            detail["expected_run_saving_share"] * 100))
    elif detail:
        print("%s  each call $%.3f -> $%.3f, %.1f calls a run, so about $%.2f (%.0f%%) less in a run" % (
            detail["target"], detail["per_call_before"], detail["per_call_after"], detail["calls_per_run"],
            detail["expected_run_saving"], detail["expected_run_saving_share"] * 100))
    if base["seeds_caught"] is not None and cand["seeds_caught"] is not None:
        print("defects    %d vs %d caught" % (len(base["seeds_caught"]), len(cand["seeds_caught"])))
    elif base["seeds_caught"] is not None:
        print("defects    not measured for the candidate")
    print("verdict    " + result["verdict"])
    for reason in result["reasons"]:
        print("           " + reason)
    return 0 if result["verdict"].startswith("SAME") else 1  # NEED MORE RUNS also exits 1


def command_recheck(args):
    """Read the outcome of each run again from its project folder, with the current checks."""
    folder = Path(args.folder)
    summary = json.loads((folder / "e2e.json").read_text())
    stage = summary.get("stage")
    snapshot = summary.get("snapshot", "r5")  # a result from before the snapshots has no name
    for number, run in enumerate(summary["runs"], 1):
        project = Path(run["project"])
        if not project.exists():
            print("run %d: the project folder is gone, so the outcome stays as it was" % number)
            continue
        if stage:
            entry = run["outcome"].get("entry") or entry_commit(project, stage_table(snapshot)[stage][0])
            run["outcome"] = stage_outcome(stage, check_stage(project, stage, entry, snapshot), entry)
        else:
            run["outcome"] = inspect_project(project)
        (folder / ("run%d.json" % number)).write_text(json.dumps(run, indent=1))
    (folder / "e2e.json").write_text(json.dumps(summary, indent=1))
    print("checked %d runs again" % len(summary["runs"]))


def command_reanalyse(args):
    """Read the saved event streams of a result folder again, with the current analysis."""
    folder = Path(args.folder)
    summary = json.loads((folder / "e2e.json").read_text())
    for number, run in enumerate(summary["runs"], 1):
        stream = folder / ("run%d.stream.jsonl" % number)
        items = [json.loads(line) for line in stream.read_text().splitlines() if line.strip()]
        fresh = analyse(items)
        for key in ("totals", "stages", "waiting"):
            run[key] = fresh[key]
        (folder / ("run%d.json" % number)).write_text(json.dumps(run, indent=1))
    (folder / "e2e.json").write_text(json.dumps(summary, indent=1))
    print("read %d runs again" % len(summary["runs"]))


# ---------------------------------------------------------------- planted defects

SEEDS = HERE / "seeds"


def apply_patch(project, patch):
    done = subprocess.run(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=project, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("cannot apply %s: %s" % (patch.name, done.stderr.strip()))


def build_seed_project(dest, plugin, seeded):
    """Rebuild the finished change of the first baseline run. With `seeded`, plant the defects."""
    spec = json.loads((SEEDS / "seeds.json").read_text())
    project = make_project(dest, plugin)
    apply_patch(project, SEEDS / "main.patch")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "Plan IN-0001: top option")
    git(project, "switch", "-q", "-c", spec["branch"])
    apply_patch(project, SEEDS / "change.patch")
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "Build CH-0001: add the --top option")
    if seeded:
        for edit in spec["edits"]:
            path = project / edit["file"]
            text = path.read_text()
            if edit["find"] not in text:
                raise RuntimeError("seed edit does not match %s" % edit["file"])
            path.write_text(text.replace(edit["find"], edit["replace"], 1))
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "Seed: planted defects")
    return project


def make_seed_packets(project, remits):
    done = subprocess.run([sys.executable, "pdlc/bin/make_packets.py", "CH-0001", *remits], cwd=project,
                          capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("make_packets failed: " + done.stdout + done.stderr)


def agent_model(plugin, name):
    """The model that an agent file asks for, or the benchmark model when it asks for none."""
    text = (Path(plugin) / "agents" / (name + ".md")).read_text()
    head = text.split("---")[1] if text.startswith("---") else ""
    found = re.search(r"^model:\s*(\S+)", head, re.M)
    return found.group(1) if found else MODEL


def parse_result(text):
    """Read a reviewer's result.md: the verdict and the text of the problems."""
    verdict = re.search(r"^Result:\s*(pass|fail)", text, re.M | re.I)
    problems = re.search(r"^Problems:(.*?)(?=^[A-Z][\w -]*:|\Z)", text, re.M | re.S)
    body = problems.group(1).strip() if problems else ""
    return {"verdict": verdict.group(1).lower() if verdict else "none",
            "problems": "" if body.lower() == "none" else body}


def final_reply(events):
    """The last message of a session: the text of its result event."""
    for item in reversed(events):
        if item["e"].get("type") == "result":
            return item["e"].get("result") or ""
    return ""


def score_seeds(spec, results):
    """results: remit -> parsed result of the seeded copy. A defect counts as caught when its
    reviewer fails the change and names the defect."""
    caught, missed = [], []
    for seed in spec["seeds"]:
        found = results.get(seed["remit"], {"verdict": "none", "problems": ""})
        hit = found["verdict"] == "fail" and any(re.search(p, found["problems"], re.I) for p in seed["patterns"])
        (caught if hit else missed).append(seed["id"])
    return caught, missed


def run_reviewer(project, remit, plugin, log_dir, model, timeout=900):
    packet = Path(project) / "pdlc" / "changes" / "CH-0001-top-option" / "review" / remit / "packet.md"
    prompt = "Review the packet at %s. Project root: %s." % (packet, project)
    events, wall, err = run_claude(prompt, project, plugin, Path(log_dir) / (remit + ".stream.jsonl"), timeout=timeout,
                                   budget_usd=3, extra=("--agent", "pdlc:reviewer", "--model", model))
    result = packet.parent / "result.md"
    if result.exists():
        parsed = parse_result(result.read_text())
        parsed["source"] = "file"
    else:
        parsed = parse_result(final_reply(events))
        parsed["source"] = "reply"
    cost = next((i["e"].get("total_cost_usd", 0) for i in events if i["e"].get("type") == "result"), 0)
    parsed.update({"cost_usd": round(cost, 4), "wall_s": wall})
    return parsed


def command_seeds(args):
    """Run the reviewers on the finished change with the planted defects, and on a clean copy."""
    from concurrent.futures import ThreadPoolExecutor

    plugin = Path(args.plugin).resolve()
    spec = json.loads((SEEDS / "seeds.json").read_text())
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    model = agent_model(plugin, "reviewer")
    remits = sorted({s["remit"] for s in spec["seeds"]})
    work = Path(tempfile.mkdtemp(prefix="pdlc-bench-seeds-"))
    jobs = {}
    for name, seeded, wanted in (("seeded", True, remits), ("clean", False, spec["control_remits"])):
        project = build_seed_project(work / name, plugin, seeded)
        make_seed_packets(project, wanted)
        (out_dir / name).mkdir(exist_ok=True)
        for remit in wanted:
            jobs[(name, remit)] = (project, remit)
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {key: pool.submit(run_reviewer, project, remit, plugin, out_dir / key[0], model, args.timeout)
                   for key, (project, remit) in jobs.items()}
        done = {key: future.result() for key, future in futures.items()}
    seeded = {remit: r for (name, remit), r in done.items() if name == "seeded"}
    clean = {remit: r for (name, remit), r in done.items() if name == "clean"}
    caught, missed = score_seeds(spec, seeded)
    false_fails = sorted(remit for remit, r in clean.items() if r["verdict"] == "fail")
    cost = round(sum(r["cost_usd"] for r in done.values()), 4)
    result = {"label": args.label, "reviewer_model": model, "caught": caught, "missed": missed,
              "false_fails": false_fails, "cost_usd": cost, "seeded": seeded, "clean": clean}
    (out_dir / "seeds.json").write_text(json.dumps(result, indent=1))
    print("model %s  caught %d/%d  missed %s  false fails %s  $%.2f" % (
        model, len(caught), len(spec["seeds"]), missed or "none", false_fails or "none", cost))
    return result


def command_rescore_seeds(args):
    """Read the reviewers' final replies again from the saved streams, and score the seeds again."""
    folder = HERE / "results" / args.label
    data = json.loads((folder / "seeds.json").read_text())
    for kind in ("seeded", "clean"):
        for remit, entry in data[kind].items():
            stream = folder / kind / (remit + ".stream.jsonl")
            if entry["verdict"] != "none" or not stream.exists():
                continue
            items = [json.loads(line) for line in stream.read_text().splitlines() if line.strip()]
            parsed = parse_result(final_reply(items))
            entry.update(verdict=parsed["verdict"], problems=parsed["problems"], source="reply")
    spec = json.loads((SEEDS / "seeds.json").read_text())
    caught, missed = score_seeds(spec, data["seeded"])
    false_fails = sorted(remit for remit, entry in data["clean"].items() if entry["verdict"] == "fail")
    data.update(caught=caught, missed=missed, false_fails=false_fails)
    (folder / "seeds.json").write_text(json.dumps(data, indent=1))
    print("%s  caught %d/%d  missed %s  false fails %s" % (
        args.label, len(caught), len(spec["seeds"]), missed or "none", false_fails or "none"))


def fmt_tokens(tokens):
    return "in %s  write %s  read %s  out %s" % tuple(
        "%dk" % round(tokens.get(k, 0) / 1000.0) if tokens.get(k, 0) >= 1000 else str(tokens.get(k, 0))
        for k in ("input", "cache_write", "cache_read", "output"))


def command_report(args):
    """Print each run of a result file: totals, then one line for each stage and agent."""
    result = json.loads(Path(args.result).read_text())
    for number, run in enumerate(result["runs"], 1):
        totals = run["totals"]
        print("run %d  $%.2f  %ss  turns %s  subagents %s  models %s" % (
            number, totals["cost_usd"], run.get("wall_s"), totals["turns"], totals["subagents"], totals["models"]))
        print("       " + fmt_tokens(totals["tokens"]))
        waiting = run.get("waiting")
        if waiting:
            print("       waiting turns %d  $%.3f" % (waiting["messages"], waiting["cost_usd"]))
        outcome = run["outcome"]
        print("       probes %s/%s  own checks %s (%s tests)  tip %s  dirty %s" % (
            outcome["probes"]["passed"], outcome["probes"]["total"], outcome["unit"]["ok"], outcome["unit"]["ran"],
            outcome.get("tip"), outcome.get("dirty")))
        for name, stage in sorted(run["stages"].items(), key=lambda kv: -kv[1]["cost_usd"]):
            share = stage["cost_usd"] / totals["cost_usd"] * 100 if totals["cost_usd"] else 0
            print("  %-9s $%.3f %3.0f%%  %5ss  msgs %-3d %s" % (name, stage["cost_usd"], share, stage.get("wall_s", "?"),
                                                           stage["messages"], fmt_tokens(stage["tokens"])))
            for label, agent in sorted(stage["agents"].items(), key=lambda kv: -kv[1]["cost_usd"]):
                print("      agent %-18s $%.3f  calls %d  %5ss  msgs %-3d" % (
                    label, agent["cost_usd"], agent["calls"], agent.get("wall_s", "?"), agent["messages"]))


def command_freeze(args):
    """Merge the runs of several e2e result files into one baseline file."""
    runs, commits, fixtures = [], set(), set()
    snapshots = set()
    for path in args.results:
        data = json.loads(Path(path).read_text())
        runs += data["runs"]
        if data.get("snapshot"):
            snapshots.add(data["snapshot"])
        commits.add(data["plugin_commit"])
        fixtures.add(data.get("fixture", "wordfreq"))
    baseline = {"label": args.label, "plugin_commit": ",".join(sorted(commits)), "model": MODEL, "effort": EFFORT,
                "fixture": ",".join(sorted(fixtures)), "runs": runs}
    if snapshots:
        baseline["snapshot"] = ",".join(sorted(snapshots))
    if args.seeds:
        seeds = json.loads(Path(args.seeds).read_text())
        baseline["seeds"] = {key: seeds[key] for key in ("reviewer_model", "caught", "missed", "false_fails", "cost_usd")}
    Path(args.out).write_text(json.dumps(baseline, indent=1))
    print("wrote %s with %d runs" % (args.out, len(runs)))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("e2e", "init-fixture"):
        p = sub.add_parser(name)
        p.add_argument("--plugin", default=str(DEFAULT_PLUGIN))
        p.add_argument("--timeout", type=int, default=3600)
        p.add_argument("--budget", type=float, default=20.0, help="stop a run at this many dollars")
        p.add_argument("--fixture", default="wordfreq", choices=sorted(FIXTURES),
                       help="the app to run pdlc on (bench/fixture-app, or a folder in bench/fixtures)")
        if name == "e2e":
            p.add_argument("--label", required=True)
            p.add_argument("--runs", type=int, default=1)
            p.add_argument("--intent", help="the intent to ship, in place of the intent of the fixture")
            p.add_argument("--out", default=str(HERE / "results"))
            p.add_argument("--forward", action="store_true",
                           help="stream the text of agents and the messages of nested agents. The split of the "
                                "cost then differs from runs without this flag")
    sd = sub.add_parser("seeds")
    sd.add_argument("--plugin", default=str(DEFAULT_PLUGIN))
    sd.add_argument("--label", required=True)
    sd.add_argument("--timeout", type=int, default=900)
    sd.add_argument("--out", default=str(HERE / "results"))
    rs = sub.add_parser("rescore-seeds")
    rs.add_argument("label")
    k = sub.add_parser("recheck")
    k.add_argument("folder")
    a = sub.add_parser("reanalyse")
    a.add_argument("folder")
    r = sub.add_parser("report")
    r.add_argument("result")
    f = sub.add_parser("freeze")
    f.add_argument("results", nargs="+")
    f.add_argument("--out", default=str(HERE / "baseline.json"))
    f.add_argument("--seeds", help="a seeds.json file to add to the result")
    f.add_argument("--label", default="baseline")
    g = sub.add_parser("gate")
    g.add_argument("baseline")
    g.add_argument("candidate")
    g.add_argument("--min-gain", type=float, default=0.05)
    g.add_argument("--speed-limit", type=float, default=1.5)
    g.add_argument("--min-runs", type=int, default=5, help="runs needed on each side to keep an edit by whole-run cost")
    g.add_argument("--target", help="an agent that the edit aims at, for example pdlc:reviewer; or waiting; or writing (the writing findings that a run leaves)")
    st = sub.add_parser("stage")
    st.add_argument("--stage", required=True, choices=sorted(REPLAY_STAGES))
    st.add_argument("--snapshot", default=DEFAULT_SNAPSHOT, choices=sorted(SNAPSHOTS),
                    help="the finished run to start from (default: %(default)s)")
    st.add_argument("--label", required=True)
    st.add_argument("--runs", type=int, default=6)
    st.add_argument("--plugin", default=str(DEFAULT_PLUGIN))
    st.add_argument("--out", default=str(HERE / "results"))
    st.add_argument("--timeout", type=int, default=1800)
    st.add_argument("--budget", type=float, default=6.0)
    rb = sub.add_parser("rebuild", help="build the app again from the specs alone, and score it")
    rb.add_argument("source", help="the result folder of an e2e run, or a project folder")
    rb.add_argument("--run", type=int, default=1)
    rb.add_argument("--ref", help="the branch to read (default: the tip of the e2e run)")
    rb.add_argument("--fixture", choices=sorted(FIXTURES), help="override the fixture in e2e.json")
    rb.add_argument("--keep", action="append", default=[], metavar="PATH",
                    help="keep this file in the clean copy (repeatable)")
    rb.add_argument("--label", help="default: rebuild-<label of the e2e run>")
    rb.add_argument("--out", default=str(HERE / "results"))
    rb.add_argument("--plugin", default=str(DEFAULT_PLUGIN), help="the plugin that the e2e run should have loaded")
    rb.add_argument("--budget", type=float, default=5.0)
    rb.add_argument("--timeout", type=int, default=1800)
    pr = sub.add_parser("prepare")
    pr.add_argument("--state", required=True, choices=PREPARE_STATES)
    pr.add_argument("--snapshot", default=DEFAULT_SNAPSHOT, choices=sorted(SNAPSHOTS),
                    help="the finished run to start from (default: %(default)s)")
    pr.add_argument("--plugin", default=str(DEFAULT_PLUGIN))
    pr.add_argument("--dest", required=True)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        command_prepare(args)
        return 0
    if args.command == "rebuild":
        args.label = args.label or "rebuild-" + Path(args.source).resolve().name
        try:
            command_rebuild(args)
        except RuntimeError as error:
            print("rebuild: %s" % error, file=sys.stderr)
            return 1
        return 0
    if args.command == "e2e":
        command_e2e(args)
        return 0
    if args.command == "init-fixture":
        command_init_fixture(args)
        return 0
    if args.command == "stage":
        command_stage(args)
        return 0
    if args.command == "seeds":
        command_seeds(args)
        return 0
    if args.command == "rescore-seeds":
        command_rescore_seeds(args)
        return 0
    if args.command == "recheck":
        command_recheck(args)
        return 0
    if args.command == "reanalyse":
        command_reanalyse(args)
        return 0
    if args.command == "report":
        command_report(args)
        return 0
    if args.command == "freeze":
        command_freeze(args)
        return 0
    return command_gate(args)


if __name__ == "__main__":
    sys.exit(main())
