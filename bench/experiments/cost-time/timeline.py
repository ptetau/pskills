#!/usr/bin/env python3
"""Split saved bench runs into where the time and the cost go.

Usage: timeline.py RESULTS_DIR

RESULTS_DIR holds one folder for each run (for example v040-1/run1.stream.jsonl), as
`run_bench.py e2e --runs 1` writes them. The script writes RESULTS_DIR/timeline.json and prints
a summary for each label (the part of the folder name before the last dash).

The stream gives each message its output tokens at the start of the message, so it holds almost
no output tokens. The script estimates the output of each message from its text, its tool input
and the thinking tokens before it. Then it scales the estimates to the total that the CLI reports.
"""
import collections
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import run_bench as rb  # noqa: E402

BASE_CONTEXT = 37400   # the tokens that each new session starts with
REREAD = 10000         # the tokens that a fresh stage session reads again


def tool_kind(name, args):
    """A short name for a tool call, with Bash commands put in groups."""
    if name in ("Agent", "Task"):
        return "agent:" + (args.get("subagent_type") or "general")
    if name != "Bash":
        return name
    c = (args.get("command") or "").strip()
    for word, kind in (("record_gif", "gif"), ("check_writing", "writing check"), ("check_merge", "merge check"),
                       ("make_packets", "pdlc script"), ("record_merges", "pdlc script")):
        if word in c:
            return kind
    if re.search(r"unittest|pytest", c):
        return "checks"
    if re.match(r"(cd [^&;]+&&\s*)?git\b", c):
        return "git"
    return "other tool"


def read_run(path):
    """One run: the main-session time of each stage by part, and each message with its cost weight."""
    stage, pending, result = "ship", 0, {}
    msgs, calls, events = {}, {}, []
    for line in open(path):
        item = json.loads(line)
        e, t = item["e"], item["t"]
        kind = e.get("type")
        if kind == "result":
            result = e
        elif kind == "system" and e.get("subtype") == "thinking_tokens":
            pending += e.get("estimated_tokens_delta", 0)
        elif kind == "assistant":
            m, parent = e["message"], e.get("parent_tool_use_id")
            for b in m.get("content", []):
                if b.get("type") == "tool_use" and b["id"] not in calls:
                    args = b.get("input") or {}
                    if parent is None:
                        stage = rb.stage_from_call(b["name"], args, stage) or stage
                    owner = rb.agent_stage(args.get("subagent_type"), args.get("prompt"), stage) \
                        if b["name"] in ("Agent", "Task") else None
                    calls[b["id"]] = {"stage": owner or stage, "kind": tool_kind(b["name"], args),
                                      "main": parent is None}
            if m["id"] not in msgs:
                u = m.get("usage") or {}
                msgs[m["id"]] = {"main": parent is None, "usage": u, "out": 0.0, "writing": False,
                                 "stage": stage if parent is None else calls.get(parent, {}).get("stage", stage),
                                 "context": sum(u.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens",
                                                                      "cache_read_input_tokens"))}
                if parent is None:
                    events.append((t, "model", m["id"]))
            rec = msgs[m["id"]]
            rec["out"] += pending
            pending = 0
            for b in m.get("content", []):
                if b.get("type") == "text":
                    rec["out"] += len(b["text"]) / 4
                elif b.get("type") == "tool_use":
                    rec["out"] += len(json.dumps(b.get("input"))) / 4
                    rec["writing"] |= rec["main"] and "check_writing" in json.dumps(b.get("input"))
        elif kind == "user" and e.get("parent_tool_use_id") is None:
            for b in (e.get("message", {}).get("content") or []):
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                    events.append((t, "tool", b["tool_use_id"]))
    # Each gap between two main-session events goes to the model, or to the tool whose result ends it.
    time = collections.defaultdict(collections.Counter)
    events.sort()
    for (t0, _, _), (t1, kind, ref) in zip(events, events[1:]):
        if kind == "model":
            time[msgs[ref]["stage"]]["model"] += t1 - t0
        else:
            time[calls[ref]["stage"]][calls[ref]["kind"]] += t1 - t0
    # The weight of each message, with its estimated output scaled to the reported total.
    reported = sum(v.get("outputTokens", 0) for v in result.get("modelUsage", {}).values())
    estimated = sum(r["out"] for r in msgs.values()) or 1
    for r in msgs.values():
        u = r["usage"]
        r["weight"] = (rb.message_weight(u) - u.get("output_tokens", 0) * rb.PRICE["output"]
                       + r["out"] * reported / estimated * rb.PRICE["output"])
    return {"time": time, "msgs": msgs, "cost": result.get("total_cost_usd", 0.0),
            "wall": events[-1][0] if events else 0.0}


def summarise(run):
    """The numbers of one run that the analysis uses."""
    msgs = run["msgs"].values()
    total = sum(r["weight"] for r in msgs) or 1
    start = {}
    for r in msgs:
        if r["main"]:
            start.setdefault(r["stage"], r["context"])
    saved = sum(max(0, r["context"] - (BASE_CONTEXT + REREAD + r["context"] - start[r["stage"]])) * rb.PRICE["cache_read"]
                for r in msgs if r["main"] and r["stage"] != "ship")
    stages = collections.defaultdict(float)
    for r in msgs:
        stages[r["stage"]] += r["weight"] / total * run["cost"]
    main = [r for r in msgs if r["main"]]
    return {"cost": run["cost"], "wall_s": run["wall"],
            "main_share": sum(r["weight"] for r in main) / total,
            "main_turns": len(main),
            "main_context": statistics.mean(r["context"] for r in main) if main else 0,
            "writing_turns": sum(1 for r in main if r["writing"]),
            "writing_share": sum(r["weight"] for r in main if r["writing"]) / total,
            "fresh_stage_saving": saved / total,
            "stage_cost": dict(stages),
            "stage_time": {k: dict(v) for k, v in run["time"].items()}}


def main(results):
    folder = Path(results)
    runs = {}
    for d in sorted(folder.iterdir()):
        log = d / "run1.stream.jsonl"
        if d.is_dir() and log.is_file():
            runs[d.name] = summarise(read_run(log))
    (folder / "timeline.json").write_text(json.dumps(runs, indent=1))
    labels = sorted({name.rsplit("-", 1)[0] for name in runs})
    for label in labels:
        group = [v for k, v in runs.items() if k.rsplit("-", 1)[0] == label]
        mean = lambda key: statistics.mean(v[key] for v in group)  # noqa: E731
        print("%s (%d runs): cost $%.2f, main session %.0f%%, %.1f main turns, context %.0f tokens a turn"
              % (label, len(group), mean("cost"), 100 * mean("main_share"), mean("main_turns"), mean("main_context")))
        print("  writing-check turns %.1f a run (%.0f%% of the cost), fresh session for each stage saves %.0f%%"
              % (mean("writing_turns"), 100 * mean("writing_share"), 100 * mean("fresh_stage_saving")))
    print("wrote", folder / "timeline.json")


if __name__ == "__main__":
    main(sys.argv[1])
