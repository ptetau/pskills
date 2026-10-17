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


def stage_name(skill):
    return skill.split(":")[-1] if skill else "ship"


def analyse(items):
    """Split a run into stages. Return totals and one entry per stage.

    A stage starts when the top-level session calls the Skill tool. Messages from an agent
    that the session started count toward the stage that was active, under the agent's name.
    """
    messages = {}
    order = []
    stage = "ship"
    stage_start = {}
    stage_end = {}
    agent_of = {}
    agent_span = {}
    result = {}
    for item in items:
        event, t = item["e"], item["t"]
        kind = event.get("type")
        if kind == "result":
            result = event
            continue
        if kind == "assistant":
            message = event.get("message", {})
            parent = event.get("parent_tool_use_id")
            for block in message.get("content", []):
                if block.get("type") != "tool_use":
                    continue
                name, args = block.get("name"), block.get("input") or {}
                if parent is None and name == "Skill":
                    stage = stage_name(args.get("skill"))
                    stage_start.setdefault(stage, t)
                    stage_end[stage] = t
                if name in ("Agent", "Task"):
                    label = args.get("subagent_type") or "general-purpose"
                    agent_of[block["id"]] = (stage, label)
                    agent_span[block["id"]] = [t, t]
            key = message.get("id") or "m%d" % len(order)
            if key not in messages:
                order.append(key)
            messages[key] = {"usage": message.get("usage") or {}, "model": message.get("model"),
                             "stage": stage, "parent": parent, "t": t}
            stage_end[stage] = t
        elif kind == "user":
            for block in (event.get("message", {}).get("content") or []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    span = agent_span.get(block.get("tool_use_id"))
                    if span:
                        span[1] = t
    stage_start.setdefault("ship", 0.0)

    per_model_weight = {}
    for key in order:
        entry = messages[key]
        per_model_weight[entry["model"]] = per_model_weight.get(entry["model"], 0) + message_weight(entry["usage"])
    model_cost = {model: info.get("costUSD", 0.0) for model, info in (result.get("modelUsage") or {}).items()}

    stages = {}
    for key in order:
        entry = messages[key]
        label = "session"
        if entry["parent"] in agent_of:
            stage_of, label = agent_of[entry["parent"]]
            entry["stage"] = stage_of
        data = stages.setdefault(entry["stage"], {"tokens": {}, "cost_usd": 0.0, "messages": 0, "agents": {}})
        share = 0.0
        weight = per_model_weight.get(entry["model"]) or 0
        if weight:
            share = model_cost.get(entry["model"], 0.0) * message_weight(entry["usage"]) / weight
        add_tokens(data["tokens"], tokens_of(entry["usage"]))
        data["cost_usd"] += share
        data["messages"] += 1
        if label != "session":
            agent = data["agents"].setdefault(label, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
            add_tokens(agent["tokens"], tokens_of(entry["usage"]))
            agent["cost_usd"] += share
            agent["messages"] += 1
    for tool_id, (stage_of, label) in agent_of.items():
        data = stages.setdefault(stage_of, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "agents": {}})
        agent = data["agents"].setdefault(label, {"tokens": {}, "cost_usd": 0.0, "messages": 0, "calls": 0})
        agent["calls"] += 1
        start, end = agent_span[tool_id]
        agent["wall_s"] = round(agent.get("wall_s", 0) + (end - start), 1)

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

    totals = {"tokens": {}, "cost_usd": round(result.get("total_cost_usd", 0.0), 4),
              "duration_s": round(result.get("duration_ms", 0) / 1000.0, 1),
              "turns": result.get("num_turns"), "is_error": result.get("is_error"),
              "terminal_reason": result.get("terminal_reason"),
              "subagents": (result.get("subagent_stats") or {}).get("spawned")}
    for info in (result.get("modelUsage") or {}).values():
        add_tokens(totals["tokens"], {"input": info.get("inputTokens", 0), "cache_write": info.get("cacheCreationInputTokens", 0),
                                      "cache_read": info.get("cacheReadInputTokens", 0), "output": info.get("outputTokens", 0)})
    totals["models"] = {m: round(i.get("costUSD", 0.0), 4) for m, i in (result.get("modelUsage") or {}).items()}
    return {"totals": totals, "stages": stages}


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
    """Run the intent's acceptance probes against the code in `project` as it is checked out."""
    sample = Path(project) / ".bench-sample.txt"
    sample.write_text(SAMPLE)
    passed, failed = 0, []
    for name, args, code, out, err in PROBES:
        for ordering in ([args + [str(sample)], [str(sample)] + args] if args else [[str(sample)]]):
            try:
                proc = subprocess.run([sys.executable, "-m", "wordfreq", *ordering], cwd=project,
                                      capture_output=True, text=True, timeout=20)
            except subprocess.TimeoutExpired:
                failed.append(name + " (timeout)")
                break
            good = proc.returncode == code and proc.stdout == out and (err is None or proc.stderr == err)
            if not good:
                failed.append(name)
                break
        else:
            passed += 1
    sample.unlink()
    return {"passed": passed, "total": len(PROBES), "failed": failed}


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
        "probes_all": all(r["outcome"]["probes"]["passed"] == r["outcome"]["probes"]["total"] for r in runs),
        "units_ok": all(r["outcome"]["unit"]["ok"] for r in runs),
        "seeds_caught": result.get("seeds", {}).get("caught"),
    }


def gate(baseline, candidate, min_gain=0.05, speed_limit=1.5):
    """Decide if an edit stays. Effectiveness must not fall. Cost must fall by more than the noise."""
    base, cand = summarise(baseline), summarise(candidate)
    reasons = []
    worse = []
    if base["probes_all"] and not cand["probes_all"]:
        worse.append("acceptance probes fail")
    if base["units_ok"] and not cand["units_ok"]:
        worse.append("the project's own checks fail")
    if base["seeds_caught"] is not None and cand["seeds_caught"] is not None:
        missed = sorted(set(base["seeds_caught"]) - set(cand["seeds_caught"]))
        if missed:
            worse.append("planted defects no longer caught: " + ", ".join(missed))
    change = (cand["cost_usd"] - base["cost_usd"]) / base["cost_usd"] if base["cost_usd"] else 0.0
    needed = max(min_gain, base["noise"], cand["noise"])
    slower = cand["duration_s"] / base["duration_s"] if base["duration_s"] else 1.0
    if slower > speed_limit:
        worse.append("%.0f%% slower, limit is %.0f%%" % ((slower - 1) * 100, (speed_limit - 1) * 100))
    if worse:
        verdict = "REGRESSION -> revert"
        reasons = worse
    elif change <= -needed:
        verdict = "SAME OR BETTER -> keep"
        reasons = ["cost fell %.0f%%, more than the %.0f%% needed" % (-change * 100, needed * 100)]
    else:
        verdict = "NO GAIN -> revert"
        reasons = ["cost changed %+.0f%%, and %.0f%% fall was needed" % (change * 100, needed * 100)]
    return {"verdict": verdict, "reasons": reasons, "baseline": base, "candidate": cand, "cost_change": change}


def command_gate(args):
    result = gate(json.loads(Path(args.baseline).read_text()), json.loads(Path(args.candidate).read_text()),
                  args.min_gain, args.speed_limit)
    base, cand = result["baseline"], result["candidate"]
    print("baseline   cost $%.2f  time %4.0fs  runs %d  noise %2.0f%%" % (base["cost_usd"], base["duration_s"], base["runs"], base["noise"] * 100))
    print("candidate  cost $%.2f  time %4.0fs  runs %d  noise %2.0f%%" % (cand["cost_usd"], cand["duration_s"], cand["runs"], cand["noise"] * 100))
    print("probes     %s vs %s" % (base["probes_all"], cand["probes_all"]))
    if base["seeds_caught"] is not None:
        print("defects    %d vs %d caught" % (len(base["seeds_caught"]), len(cand["seeds_caught"] or [])))
    print("verdict    " + result["verdict"])
    for reason in result["reasons"]:
        print("           " + reason)
    return 0 if result["verdict"].startswith("SAME") else 1


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
    baseline = {"label": "baseline", "plugin_commit": ",".join(sorted(commits)), "model": MODEL, "effort": EFFORT, "runs": runs}
    for extra in ("seeds",):
        for path in args.results:
            data = json.loads(Path(path).read_text())
            if extra in data:
                baseline[extra] = data[extra]
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
    r = sub.add_parser("report")
    r.add_argument("result")
    f = sub.add_parser("freeze")
    f.add_argument("results", nargs="+")
    f.add_argument("--out", default=str(HERE / "baseline.json"))
    g = sub.add_parser("gate")
    g.add_argument("baseline")
    g.add_argument("candidate")
    g.add_argument("--min-gain", type=float, default=0.05)
    g.add_argument("--speed-limit", type=float, default=1.5)
    args = parser.parse_args(argv)
    if args.command == "e2e":
        command_e2e(args)
        return 0
    if args.command == "init-fixture":
        command_init_fixture(args)
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
