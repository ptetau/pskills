#!/usr/bin/env python3
"""Run one pdlc experiment from a spec file. A cheap model can run it.

Commands:
  run_experiment.py check SPEC   check the spec and the edits on a scratch copy. It calls no model.
  run_experiment.py start SPEC   start the experiment in the background
  run_experiment.py wait SPEC    wait up to --seconds for the experiment. Run it again until it says DONE.
  run_experiment.py run SPEC     run the experiment in this process

A spec is a JSON file:
  id                 lower-case words with hyphens, for example "r3-foreground-agents"
  hypothesis         one sentence
  lever              the lever that the edit pulls
  edits              a list of {"file", "find", "replace"}. A file is a path inside plugins/pdlc.
                     Each "find" text must occur exactly once in its file.
  runs               how many end-to-end runs (default 6)
  seeds              true to also run the planted-defect check (use it when reviewers can change)
  target             an agent for the gate's agent mode, or null for whole-run cost
  baseline           the result file to compare with (default bench/baseline.json)
  gate               optional: min_gain, alpha, min_runs, speed_limit
  budget_usd_per_run stop a run at this many dollars (default 8)

The results go to bench/results/<id>/: spec.json, applied.diff, check.txt, result.json, gate.txt,
gate.json, status.json, and DONE when the experiment has finished. Each run is in
bench/results/<id>-<n>/.
"""
import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import run_bench

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
PLUGIN = REPO / "plugins" / "pdlc"
RESULTS = HERE / "results"
CHECK_WRITING = PLUGIN / "skills" / "init" / "references" / "bin" / "check_writing.py"


class SpecError(Exception):
    pass


def load_spec(path):
    """Read a spec and fill in the defaults. Raise SpecError for anything that is wrong."""
    spec = json.loads(Path(path).read_text())
    problems = []
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(spec.get("id", ""))):
        problems.append('"id" must be lower-case words with hyphens')
    for key in ("hypothesis", "lever"):
        if not str(spec.get(key, "")).strip():
            problems.append('"%s" is missing' % key)
    edits = spec.get("edits")
    if not isinstance(edits, list) or not edits:
        problems.append('"edits" must be a list with at least one edit')
    else:
        for number, edit in enumerate(edits, 1):
            for key in ("file", "find", "replace"):
                if not isinstance(edit.get(key), str) or (key != "replace" and not edit[key]):
                    problems.append('edit %d: "%s" is missing' % (number, key))
            if isinstance(edit.get("find"), str) and edit.get("find") == edit.get("replace"):
                problems.append("edit %d: find and replace are the same" % number)
    spec.setdefault("runs", 6)
    spec.setdefault("seeds", False)
    spec.setdefault("target", None)
    spec.setdefault("baseline", "bench/baseline.json")
    spec.setdefault("gate", {})
    spec.setdefault("budget_usd_per_run", 8)
    if not isinstance(spec["runs"], int) or spec["runs"] < 1:
        problems.append('"runs" must be a whole number of at least 1')
    if problems:
        raise SpecError("; ".join(problems))
    return spec


def apply_edits(spec, plugin=PLUGIN):
    """Copy the plugin to a scratch folder, apply the edits, and return the new plugin folder."""
    scratch = Path(tempfile.mkdtemp(prefix="pdlc-exp-%s-" % spec["id"])) / "pdlc"
    shutil.copytree(plugin, scratch, ignore=shutil.ignore_patterns("__pycache__"))
    for number, edit in enumerate(spec["edits"], 1):
        path = scratch / edit["file"]
        if not path.is_file():
            raise SpecError("edit %d: there is no file %s in the plugin" % (number, edit["file"]))
        text = path.read_text()
        found = text.count(edit["find"])
        if found != 1:
            raise SpecError("edit %d: the find text occurs %d times in %s, and it must occur once" % (number, found, edit["file"]))
        path.write_text(text.replace(edit["find"], edit["replace"], 1))
    return scratch


def writing_findings(path):
    done = subprocess.run([sys.executable, str(CHECK_WRITING), str(path)], capture_output=True, text=True)
    return len([line for line in done.stdout.splitlines() if " · " in line])


def check(spec, plugin=PLUGIN, run_tests=True):
    """Apply the edits to a scratch copy and test it. Return (scratch folder, report text)."""
    scratch = apply_edits(spec, plugin)
    lines = ["edits apply: %d" % len(spec["edits"])]
    for file in sorted({e["file"] for e in spec["edits"]}):
        if file.endswith(".md"):
            before, after = writing_findings(Path(plugin) / file), writing_findings(scratch / file)
            lines.append("writing check %s: %d findings before, %d after%s" % (
                file, before, after, "  <- NEW FINDINGS" if after > before else ""))
    diff = subprocess.run(["diff", "-ru", "-x", "__pycache__", str(plugin), str(scratch)], capture_output=True, text=True).stdout
    diff = diff.replace(str(plugin), "a").replace(str(scratch), "b")  # stable paths, so the diff does not change between runs
    if run_tests:
        done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=scratch, capture_output=True, text=True)
        tail = (done.stderr.strip().splitlines() or ["no output"])[-1]
        lines.append("plugin tests: %s" % ("OK" if done.returncode == 0 else "FAILED"))
        lines.append("  " + tail)
        if done.returncode:
            lines.append(done.stderr[-1500:])
    return scratch, "\n".join(lines), diff


def out_dir(spec):
    folder = RESULTS / spec["id"]
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def write_status(folder, **fields):
    """Update status.json. It keeps the fields that an earlier call wrote, such as the process id."""
    path = folder / "status.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    path.write_text(json.dumps({**current, **fields, "at": time.strftime("%H:%M:%S")}, indent=1))


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except (OSError, TypeError):
        return False
    return True


def runner_command(spec_path):
    """The command that runs an experiment in the background. The spec path is absolute, because
    the runner starts in another folder."""
    return [sys.executable, str(Path(__file__).resolve()), "run", str(Path(spec_path).resolve())]


def command_check(args):
    spec = load_spec(args.spec)
    scratch, report, diff = check(spec)
    folder = out_dir(spec)
    (folder / "spec.json").write_text(json.dumps(spec, indent=1))
    (folder / "applied.diff").write_text(diff)
    (folder / "check.txt").write_text(report + "\n")
    print(report)
    print("applied.diff has %d lines" % len(diff.splitlines()))
    return 1 if "FAILED" in report or "NEW FINDINGS" in report else 0


def command_run(args):
    spec = load_spec(args.spec)
    folder = out_dir(spec)
    (folder / "DONE").unlink(missing_ok=True)
    write_status(folder, state="checking")
    scratch, report, diff = check(spec)
    (folder / "spec.json").write_text(json.dumps(spec, indent=1))
    (folder / "applied.diff").write_text(diff)
    (folder / "check.txt").write_text(report + "\n")
    if "FAILED" in report:
        (folder / "DONE").write_text("CHECK FAILED\n" + report)
        write_status(folder, state="done", verdict="CHECK FAILED")
        return 1
    labels = ["%s-%d" % (spec["id"], n) for n in range(1, spec["runs"] + 1)]
    write_status(folder, state="running", runs=labels)

    def one(label):
        ns = Namespace(plugin=str(scratch), label=label, runs=1, out=str(RESULTS), timeout=2400, budget=spec["budget_usd_per_run"])
        try:
            run_bench.command_e2e(ns)
        except Exception as error:  # keep the others going
            print("run %s failed: %r" % (label, error))

    with ThreadPoolExecutor(max_workers=len(labels) + 1) as pool:
        jobs = [pool.submit(one, label) for label in labels]
        seeds_job = None
        if spec["seeds"]:
            ns = Namespace(plugin=str(scratch), label="%s-seeds" % spec["id"], timeout=900, out=str(RESULTS))
            seeds_job = pool.submit(run_bench.command_seeds, ns)
        for job in jobs:
            job.result()
        if seeds_job:
            seeds_job.result()
    finished = [l for l in labels if (RESULTS / l / "e2e.json").exists()]
    if not finished:
        (folder / "DONE").write_text("NO RUNS FINISHED\n")
        write_status(folder, state="done", verdict="NO RUNS FINISHED")
        return 1
    freeze = Namespace(results=[str(RESULTS / l / "e2e.json") for l in finished], out=str(folder / "result.json"), label=spec["id"],
                       seeds=str(RESULTS / ("%s-seeds" % spec["id"]) / "seeds.json") if spec["seeds"] else None)
    run_bench.command_freeze(freeze)
    options = {"min_gain": 0.05, "speed_limit": 1.5, "alpha": 0.10, "min_runs": 5, **spec["gate"]}
    baseline = json.loads((REPO / spec["baseline"]).read_text())
    candidate = json.loads((folder / "result.json").read_text())
    verdict = run_bench.gate(baseline, candidate, options["min_gain"], options["speed_limit"], spec["target"], options["alpha"], options["min_runs"])
    gate_args = Namespace(baseline=str(REPO / spec["baseline"]), candidate=str(folder / "result.json"), min_gain=options["min_gain"],
                          speed_limit=options["speed_limit"], target=spec["target"], min_runs=options["min_runs"])
    text = io.StringIO()
    with contextlib.redirect_stdout(text):
        run_bench.command_gate(gate_args)
    (folder / "gate.txt").write_text(text.getvalue())
    (folder / "gate.json").write_text(json.dumps(verdict, indent=1, default=str))
    note = "" if len(finished) == len(labels) else "\n%d of %d runs did not finish" % (len(labels) - len(finished), len(labels))
    (folder / "DONE").write_text(verdict["verdict"] + note + "\n")
    write_status(folder, state="done", verdict=verdict["verdict"], finished=len(finished), runs=len(labels))
    return 0


def command_start(args):
    spec = load_spec(args.spec)
    folder = out_dir(spec)
    (folder / "DONE").unlink(missing_ok=True)
    log = open(folder / "run.log", "w")
    proc = subprocess.Popen(runner_command(args.spec), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, cwd=str(HERE))
    write_status(folder, state="starting", pid=proc.pid)
    print("started %s (process %d). Log: %s" % (spec["id"], proc.pid, folder / "run.log"))
    return 0


def command_wait(args):
    spec = load_spec(args.spec)
    folder = out_dir(spec)
    end = time.time() + args.seconds
    while time.time() < end:
        if (folder / "DONE").exists():
            print("DONE: " + (folder / "DONE").read_text().strip())
            for name in ("check.txt", "gate.txt"):
                if (folder / name).exists():
                    print("--- " + name)
                    print((folder / name).read_text().rstrip())
            return 0
        status = json.loads((folder / "status.json").read_text()) if (folder / "status.json").exists() else {}
        if status.get("pid") and not process_alive(status["pid"]) and not (folder / "DONE").exists():
            log = folder / "run.log"
            tail = "\n".join(log.read_text().splitlines()[-12:]) if log.exists() else "no log"
            print("FAILED: the runner stopped before it finished. The end of %s:\n%s" % (log, tail))
            return 1
        time.sleep(10)
    done = len([n for n in range(1, spec["runs"] + 1) if (RESULTS / ("%s-%d" % (spec["id"], n)) / "e2e.json").exists()])
    status = json.loads((folder / "status.json").read_text()) if (folder / "status.json").exists() else {}
    print("RUNNING: %d of %d runs finished. State: %s. Run this command again." % (done, spec["runs"], status.get("state", "unknown")))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "start", "run", "wait"):
        p = sub.add_parser(name)
        p.add_argument("spec")
        if name == "wait":
            p.add_argument("--seconds", type=int, default=540)
    args = parser.parse_args(argv)
    try:
        return {"check": command_check, "start": command_start, "run": command_run, "wait": command_wait}[args.command](args)
    except SpecError as error:
        print("SPEC ERROR: %s" % error)
        return 2


if __name__ == "__main__":
    sys.exit(main())
