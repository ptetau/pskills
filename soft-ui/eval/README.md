# soft-ui comparison

This folder tests one claim: a page from soft-ui lands in the same place as a page that
an agent builds by hand. "The same place" means the same information, the same kinds of
components, a similar layout, and the same emphasis for the reader. Visual style is a
separate problem, and the judge does not score it.

## Method

For each report:

1. A bespoke agent reads the brief and the data, and writes an HTML page by hand. The
   agent cannot read soft-ui.
2. A soft-ui agent reads the same brief and data, and writes a spec for soft-ui.
3. A judge takes a screenshot of each page. The judge does not know which page came from
   which agent. Pages A and B change places from one report to the next.
4. The judge scores information, components, layout, and spirit from 1 to 5. The judge
   also lists what only one page shows, and says which page serves the reader better.

Each build agent also reports its size of work. The bespoke agent reports the characters
that it wrote. The soft-ui agent reports the size of its spec, its render runs, and each
"fixed" and "error" line. The soft-ui agent also reports friction: anything that it could
not show.

## The 10 reports

| ID | Report | Reader |
|---|---|---|
| R1 | Probe findings | Tech lead before triage |
| R2 | Vet scorecard | Skill author who decides to merge |
| R3 | Design summary | Engineers who review the design |
| R4 | pdlc dashboard | Project owner at the start of the day |
| R5 | Pull request review | PR author |
| R6 | Test run | Engineer on call |
| R7 | Git volatility | Architect |
| R8 | Latency regression | Release manager |
| R9 | Migration plan | Engineering manager |
| R10 | Dependency audit | Security lead |

Each folder in `reports/` holds `brief.md` and the data. `shoot.js` takes a full-page
screenshot. The results of each run are in `runs/<run>/`, with a `RESULTS.md` summary.
