#!/usr/bin/env python3
"""Write RESULTS.md for a comparison run from the workflow result files.

Usage: python3 summarise.py RUN_DIR RESULT.json [RESULT.json ...]
Each RESULT.json is the list that the comparison workflow returns.
"""

import json
import sys
from pathlib import Path


def main(argv):
    run = Path(argv[0])
    rows = []
    for f in argv[1:]:
        d = json.loads(Path(f).read_text())
        rows += d["result"] if isinstance(d, dict) else d
    rows.sort(key=lambda r: int(r["report"].split("-")[0][1:]))
    out = ["# Results", "", "Scores are 1 to 5. The judge did not score visual style. "
           "\"Spec\" is the size of the soft-ui spec. \"Bespoke\" is the HTML that the bespoke agent wrote.", "",
           "| Report | Info | Components | Layout | Spirit | Verdict | Better for reader | Spec | Bespoke | Ratio |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    tot = {k: 0 for k in ("information", "components", "layout", "spirit")}
    verdicts, better, n = {}, {"tool": 0, "bespoke": 0, "tie": 0}, 0
    spec_sum = bes_sum = 0
    for r in rows:
        if "judge" not in r or not r["judge"]:
            out.append(f"| {r['report']} | – | – | – | – | {r.get('error', 'no judge')} | – | – | – | – |")
            continue
        j, n = r["judge"], n + 1
        for k in tot:
            tot[k] += j[k]
        verdicts[j["verdict"]] = verdicts.get(j["verdict"], 0) + 1
        b = j["better_for_reader"]
        who = "tie" if b == "tie" else (r["a"] if b == "A" else ("bespoke" if r["a"] == "tool" else "tool"))
        better[who] += 1
        spec, bes = r["tool"]["spec_chars"], r["bespoke"]["authored_chars"]
        spec_sum, bes_sum = spec_sum + spec, bes_sum + bes
        out.append(f"| {r['report']} | {j['information']} | {j['components']} | {j['layout']} | {j['spirit']} | "
                   f"{j['verdict']} | {who} | {spec / 1000:.1f} KB | {bes / 1000:.1f} KB | {bes / max(spec, 1):.1f}× |")
    if n:
        out += ["", f"**Mean over {n} reports:** " + ", ".join(f"{k} {v / n:.1f}" for k, v in tot.items())
                + f". Verdicts: " + ", ".join(f"{v} {k}" for k, v in sorted(verdicts.items()))
                + f". Better for the reader: tool {better['tool']}, bespoke {better['bespoke']}, tie {better['tie']}."
                + f" The specs total {spec_sum / 1000:.1f} KB; the bespoke pages total {bes_sum / 1000:.1f} KB"
                + f" ({bes_sum / max(spec_sum, 1):.1f}× more to write by hand).", ""]
    for r in rows:
        if not r.get("judge"):
            continue
        j = r["judge"]
        tool_side, bes_side = ("a_only", "b_only") if r["a"] == "tool" else ("b_only", "a_only")
        out += [f"## {r['report']}", "", f"**Judge:** {j['why']}", "",
                "Only in the soft-ui page: " + "; ".join(j[tool_side]) + ".", "",
                "Only in the bespoke page: " + "; ".join(j[bes_side]) + ".", "",
                f"**Soft-ui agent:** {r['tool']['render_runs']} render runs, "
                f"{len(r['tool']['fixed_lines'])} fixed lines, {len(r['tool']['error_lines'])} error lines.", "",
                f"**Friction:** {r['tool']['friction']}", ""]
    (run / "RESULTS.md").write_text("\n".join(out) + "\n")
    print(f"wrote {run / 'RESULTS.md'}")


if __name__ == "__main__":
    main(sys.argv[1:])
