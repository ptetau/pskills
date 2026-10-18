#!/usr/bin/env python3
"""pdlc benchmark: run pdlc on a fixture app, measure tokens and time, and gate an edit.

Commands:
  run_bench.py init-fixture      run /pdlc:init once and keep its pdlc/ folder in the fixture
  run_bench.py e2e --label L     run the scripted intent through /pdlc:ship, one run
  run_bench.py gate BASELINE CANDIDATE
                                 compare two result files and print the verdict

A run uses `claude -p` with the plugin folder given by --plugin, in a throwaway copy of
bench/fixture-app. Nothing in the copy comes back into the repository.
"""
import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
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

# Files that init copies as they are. A run refreshes them from the plugin under test.
VERBATIM = [
    ("templates/README.md", "README.md"),
    ("templates", "templates"),
    ("ports", "ports"),
    ("adapters", "adapters"),
    ("bin", "bin"),
    ("reviews", "reviews"),
]

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


def sync_verbatim(project, plugin):
    """Copy the files that init copies as they are, from the plugin under test."""
    refs = Path(plugin) / "skills" / "init" / "references"
    for source, target in VERBATIM:
        src, dst = refs / source, Path(project) / "pdlc" / target
        if source == "templates/README.md":
            shutil.copyfile(src, dst)
            continue
        if source == "templates":
            for path in src.iterdir():
                if path.name not in ("README.md", "config.md"):
                    (dst).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, dst / path.name)
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))


def ensure_tools():
    """Install the visual review's npm packages once, into a cache that runs share."""
    if (TOOLS_CACHE / "node_modules" / "gifenc").exists():
        return TOOLS_CACHE
    TOOLS_CACHE.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1"}
    subprocess.run(["npm", "install", "--prefix", str(TOOLS_CACHE), "playwright", "gifenc", "pngjs"],
                   check=True, capture_output=True, env=env, timeout=300)
    return TOOLS_CACHE


def make_project(dest, plugin, with_pdlc=True):
    """A fresh git repository from the fixture. With pdlc, the pdlc folder is in place."""
    dest = Path(dest)
    shutil.copytree(FIXTURE, dest, ignore=shutil.ignore_patterns("__pycache__", "pdlc" if not with_pdlc else ""))
    if with_pdlc:
        sync_verbatim(dest, plugin)
        os.symlink(ensure_tools(), dest / "pdlc" / ".tools")
    git(dest, "init", "-q", "-b", "main")
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "Set up pdlc" if with_pdlc else "Seed")
    return dest


# ---------------------------------------------------------------- running claude


def claude_command(prompt, plugin, extra=()):
    return [
        "claude", "-p", prompt,
        "--model", MODEL, "--effort", EFFORT,
        "--plugin-dir", str(plugin),
        "--setting-sources", "project,local",
        "--strict-mcp-config",
        "--permission-mode", "auto",
        "--allowedTools", ALLOWED_TOOLS,
        "--output-format", "stream-json", "--verbose",
        "--no-session-persistence",
        *extra,
    ]


def run_claude(prompt, cwd, plugin, log_path, timeout=3600, budget_usd=None, extra=()):
    """Run one headless session. Write each event with its arrival time. Return the events."""
    command = claude_command(prompt, plugin, extra)
    if budget_usd:
        command += ["--max-budget-usd", str(budget_usd)]
    started = time.time()
    proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
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


STAGES = ("init", "intake", "ready", "change", "tests", "build", "show", "verify", "ship")
AGENT_STAGE = {"pdlc:recon": "intake", "pdlc:test-writer": "tests", "pdlc:builder": "build"}
SKILL_FILE = re.compile(r"skills/(%s)/SKILL\.md" % "|".join(STAGES))
WAITING_TOOLS = {"ReadNotifications", "Monitor", "TaskOutput"}
WORK_WORDS = ("git commit", "git add", "unittest", "pytest", "npm ", "node ",
              "record_gif", "make_packets", "check_merge", "record_merges", "sed -i", "<<",
              "python3 -")


def stage_name(skill):
    return skill.split(":")[-1] if skill else "ship"


def stage_from_call(name, args):
    """The stage that a top-level tool call starts, or None.

    The Skill tool names its stage. A read of one skill file also starts that stage. A
    command that reads several skill files at once reads ahead, so it starts no stage.
    """
    if name == "Skill":
        return stage_name(args.get("skill"))
    if name in ("Agent", "Task"):
        label = args.get("subagent_type")
        if label == "pdlc:reviewer":
            return "tests" if "/review/tests/" in (args.get("prompt") or "") else "verify"
        return AGENT_STAGE.get(label)
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
    stage_start = {}
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
                    started = stage_from_call(name, args)
                    if started:
                        stage = started
                        stage_start.setdefault(stage, t)
                        stage_end[stage] = t
                if name in ("Agent", "Task"):
                    label = args.get("subagent_type") or "general-purpose"
                    owner = AGENT_STAGE.get(label)
                    if label == "pdlc:reviewer":
                        owner = "tests" if "/review/tests/" in (args.get("prompt") or "") else "verify"
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
    stage_start.setdefault("ship", 0.0)

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

    names = sorted(stage_start, key=stage_start.get)
    for index, name in enumerate(names):
        if name not in stages:
            continue
        end = stage_start[names[index + 1]] if index + 1 < len(names) else stage_end.get(name, stage_start[name])
        stages[name]["wall_s"] = round(max(0.0, end - stage_start[name]), 1)
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


def inspect_project(project):
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
            match = re.search(r"^\**Status:?\**:?\s*(.+)$", text, re.M | re.I)
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
    out["unit"] = run_unit_checks(project)
    out["probes"] = run_probes(project)
    git(project, "checkout", "-q", "main")
    return out


# ---------------------------------------------------------------- the commands


def command_e2e(args):
    plugin = Path(args.plugin).resolve()
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = []
    for number in range(1, args.runs + 1):
        work = Path(tempfile.mkdtemp(prefix="pdlc-bench-"))
        project = make_project(work / "app", plugin)
        log = out_dir / ("run%d.stream.jsonl" % number)
        events, wall, err = run_claude("/pdlc:ship defaults " + INTENT, project, plugin, log,
                                       timeout=args.timeout, budget_usd=args.budget)
        analysis = analyse(events)
        analysis["wall_s"] = wall
        try:
            analysis["outcome"] = inspect_project(project)
        except Exception as error:  # keep the run: its stream and its cost are already paid for
            analysis["outcome"] = {"error": repr(error), "probes": {"passed": 0, "total": len(PROBES), "failed": []},
                                   "unit": {"ok": False, "ran": 0}}
        analysis["stderr"] = err[-500:]
        analysis["project"] = str(project)
        runs.append(analysis)
        (out_dir / ("run%d.json" % number)).write_text(json.dumps(analysis, indent=1))
        print("run %d: $%.2f, %ss, probes %s/%s" % (number, analysis["totals"]["cost_usd"], analysis["wall_s"],
              analysis["outcome"]["probes"]["passed"], analysis["outcome"]["probes"]["total"]))
    summary = {"label": args.label, "plugin_commit": git(plugin, "rev-parse", "--short", "HEAD").stdout.strip(),
               "model": MODEL, "effort": EFFORT, "runs": runs}
    (out_dir / "e2e.json").write_text(json.dumps(summary, indent=1))
    return summary


def command_init_fixture(args):
    plugin = Path(args.plugin).resolve()
    work = Path(tempfile.mkdtemp(prefix="pdlc-bench-init-"))
    project = make_project(work / "app", plugin, with_pdlc=False)
    log = work / "init.stream.jsonl"
    events, wall, err = run_claude("/pdlc:init defaults", project, plugin, log, timeout=args.timeout, budget_usd=args.budget)
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
    """A run is complete when pdlc proposed the change and the merge check passes on its branch."""
    checks = run["outcome"].get("merge_check") or {}
    return bool(checks) and all(lines and lines[0].startswith("ok") for lines in checks.values())


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
    for number, run in enumerate(summary["runs"], 1):
        project = Path(run["project"])
        if not project.exists():
            print("run %d: the project folder is gone, so the outcome stays as it was" % number)
            continue
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
    runs, commits = [], set()
    for path in args.results:
        data = json.loads(Path(path).read_text())
        runs += data["runs"]
        commits.add(data["plugin_commit"])
    baseline = {"label": args.label, "plugin_commit": ",".join(sorted(commits)), "model": MODEL, "effort": EFFORT, "runs": runs}
    if args.seeds:
        seeds = json.loads(Path(args.seeds).read_text())
        baseline["seeds"] = {key: seeds[key] for key in ("reviewer_model", "caught", "missed", "false_fails", "cost_usd")}
    Path(args.out).write_text(json.dumps(baseline, indent=1))
    print("wrote %s with %d runs" % (args.out, len(runs)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("e2e", "init-fixture"):
        p = sub.add_parser(name)
        p.add_argument("--plugin", default=str(DEFAULT_PLUGIN))
        p.add_argument("--timeout", type=int, default=3600)
        p.add_argument("--budget", type=float, default=20.0, help="stop a run at this many dollars")
        if name == "e2e":
            p.add_argument("--label", required=True)
            p.add_argument("--runs", type=int, default=1)
            p.add_argument("--out", default=str(HERE / "results"))
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
    g.add_argument("--target", help="an agent that the edit aims at, for example pdlc:reviewer")
    args = parser.parse_args(argv)
    if args.command == "e2e":
        command_e2e(args)
        return 0
    if args.command == "init-fixture":
        command_init_fixture(args)
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
