#!/usr/bin/env python3
"""Compare two /vet results: the original skill (baseline) and the rewritten skill (candidate).

The two results must come from the same suite (suiteSha256), the same prompts, runs, wave
size, agent roles, and models. If they do not, the script says so and stops: scores from
different settings are not comparable.

The candidate fails if one of these conditions is true:
  - The overall score is more than --overall points lower (default 5).
  - The pass rate of a weight-3 rubric item is more than --item points lower (default 20).
  - Fewer runs are usable than in the baseline. A usable run is a run that executed the skill.

These thresholds are defaults, not measured judge noise. To measure the noise for a skill,
run /vet on the baseline two times and compare the two results with this script.

Usage:
  python compare_vet.py BASELINE/results.json CANDIDATE/results.json
  python compare_vet.py BASELINE/results.json CANDIDATE/results.json --json
Exit code: 0 pass, 1 fail, 2 not comparable.
"""

import argparse
import json
import sys

SAME = [("suiteSha256",), ("config", "prompts"), ("config", "runs"), ("config", "wave"),
        ("config", "agents"), ("config", "sessionModel")]


def get(d, path):
    for k in path:
        d = (d or {}).get(k)
    return d


def compare(base, cand, overall_tol=5.0, item_tol=20.0):
    out = {"comparable": True, "differences": [], "failures": [], "warnings": [], "rows": []}
    for path in SAME:
        if get(base, path) != get(cand, path):
            out["differences"].append("%s: baseline %r, candidate %r" % (".".join(path), get(base, path), get(cand, path)))
    if out["differences"]:
        out["comparable"] = False
        return out
    bs, cs = base["scores"], cand["scores"]
    for key in ("quality", "stability", "overall"):
        out["rows"].append({"measure": key, "baseline": bs[key], "candidate": cs[key], "change": round(cs[key] - bs[key], 1)})
    if cs["overall"] < bs["overall"] - overall_tol:
        out["failures"].append("overall score fell %.1f points (more than %.0f)" % (bs["overall"] - cs["overall"], overall_tol))
    for key in ("quality", "stability"):
        if cs[key] < bs[key] - overall_tol:
            out["warnings"].append("%s fell %.1f points" % (key, bs[key] - cs[key]))
    if cs.get("usableRuns", 0) < bs.get("usableRuns", 0):
        out["failures"].append("usable runs fell from %d to %d" % (bs["usableRuns"], cs["usableRuns"]))
    for conf, who in ((bs.get("confidence"), "baseline"), (cs.get("confidence"), "candidate")):
        if conf == "low":
            out["warnings"].append("%s confidence is low (under 80%% of runs usable)" % who)
    citems = {i["id"]: i for i in cand.get("items", [])}
    for bi in base.get("items", []):
        ci = citems.get(bi["id"])
        if ci is None or bi.get("passRate") is None or ci.get("passRate") is None:
            continue
        change = round(ci["passRate"] - bi["passRate"], 1)
        out["rows"].append({"measure": "%s (weight %s) %s" % (bi["id"], bi["weight"], bi["criterion"][:50]),
                            "baseline": bi["passRate"], "candidate": ci["passRate"], "change": change})
        if bi.get("weight") == 3 and change < -item_tol:
            out["failures"].append("%s (%s) pass rate fell %.0f points" % (bi["id"], bi["criterion"][:50], -change))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("baseline")
    p.add_argument("candidate")
    p.add_argument("--overall", type=float, default=5.0, help="points the overall score can fall (default 5)")
    p.add_argument("--item", type=float, default=20.0, help="points a weight-3 item can fall (default 20)")
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(argv)
    with open(opts.baseline) as f:
        base = json.load(f)
    with open(opts.candidate) as f:
        cand = json.load(f)
    out = compare(base, cand, opts.overall, opts.item)
    if opts.json:
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif not out["comparable"]:
        print("NOT COMPARABLE: the two results use different settings.")
        for d in out["differences"]:
            print("  - " + d)
    else:
        print("%-62s %9s %9s %7s" % ("Measure", "Baseline", "Candidate", "Change"))
        for r in out["rows"]:
            print("%-62s %9.1f %9.1f %+7.1f" % (r["measure"][:62], r["baseline"], r["candidate"], r["change"]))
        for w in out["warnings"]:
            print("WARN  " + w)
        for f in out["failures"]:
            print("FAIL  " + f)
        print("REGRESSION" if out["failures"] else "NO REGRESSION")
    sys.exit(2 if not out["comparable"] else 1 if out["failures"] else 0)


if __name__ == "__main__":
    main()
