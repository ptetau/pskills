# Results

Scores are 1 to 5. The judge did not score visual style. "Spec" is the size of the soft-ui spec. "Bespoke" is the HTML that the bespoke agent wrote.

| Report | Info | Components | Layout | Spirit | Verdict | Better for reader | Spec | Bespoke | Ratio |
|---|---|---|---|---|---|---|---|---|---|
| R1-probe | 5 | 5 | 4 | 4 | close | bespoke | 1.0 KB | 11.9 KB | 12.2× |
| R2-vet | 4 | 4 | 4 | 4 | close | bespoke | 1.9 KB | 10.9 KB | 5.7× |
| R3-design | 4 | 4 | 4 | 4 | close | bespoke | 3.4 KB | 19.3 KB | 5.7× |
| R4-pdlc | 4 | 4 | 4 | 4 | close | bespoke | 1.7 KB | 10.7 KB | 6.5× |
| R5-pr | 5 | 5 | 4 | 5 | same place | bespoke | 1.0 KB | 11.4 KB | 11.2× |
| R6-tests | 4 | 4 | 4 | 4 | close | bespoke | 1.7 KB | 10.4 KB | 6.3× |
| R7-churn | 4 | 4 | 4 | 3 | close | bespoke | 2.3 KB | 12.9 KB | 5.7× |
| R8-latency | 4 | 4 | 4 | 4 | close | bespoke | 1.9 KB | 11.4 KB | 5.9× |
| R9-migration | 4 | 4 | 4 | 3 | close | bespoke | 1.5 KB | 15.6 KB | 10.7× |
| R10-deps | 4 | 4 | 4 | 4 | close | bespoke | 0.8 KB | 10.9 KB | 13.4× |

**Mean over 10 reports:** information 4.2, components 4.2, layout 4.0, spirit 3.9. Verdicts: 9 close, 1 same place. Better for the reader: tool 0, bespoke 10, tie 0. The specs total 17.1 KB; the bespoke pages total 125.5 KB (7.3× more to write by hand).

## R1-probe

**Judge:** Both pages give the same facts in the same order: severity stat tiles, a flow-by-kind heatmap coloured by worst severity, a stacked bar chart by flow, chip filters, and a findings table that expands to show repro steps and evidence. B serves a tech lead who has 5 minutes better: its summary states the hot spot first, and its table puts the two criticals at the top, but A's table puts them at the bottom.

Only in the soft-ui page: Run facts in a separate key-value panel (app, commit, start time, minutes, flows probed, probes, raw findings, verified); B puts the same facts in one subtitle line; A free-text search box in the top filter panel and a second search box above the table; A second set of filter dropdowns (severity, flow, dimension) on the table, which repeats the chip filter bar; Findings by flow as a vertical stacked bar chart.

Only in the bespoke page: A written summary callout at the top: 2 critical, 5 high, checkout is the hot spot with both criticals, and 3 security issues span checkout, cart and account; Heatmap cells that filter the list when you click them; A 'Clear filters' link and a 'Showing N of 14' count beside the table; Table sorted with the worst first (critical, then high, medium, low); A's table shows low first and the criticals last, although its spec asked for '-severity'; Findings by flow as a horizontal stacked bar chart.

**Soft-ui agent:** 1 render runs, 0 fixed lines, 0 error lines.

**Friction:** The spec rendered with "check ok" on the first run, and no "fixed" or "error" lines. Five points were unclear or missing:
1. Catalog: the catalog does not say whether `sort: -severity` on a table uses severity rank (critical > high > medium > low) or alphabetical order. I assumed rank and could not confirm it without opening the page or reading the scripts.
2. Data paths: the catalog does not say how a relative data path resolves. The brief told me that paths resolve from the folder of the spec, and I needed that to write ../../../reports/R1-probe/findings.json.
3. kv list values: `kv` with a list value (flows_probed) has no documented display, such as comma-joined text or chips.
4. Run summary: I wanted a run-funnel line (31 raw findings, then 14 verified, from 25 probes) as one compact visual, but I found no funnel or ratio component. A meter (verified out of raw) could do part of it, but it would need inline values when a file holds the data.
5. Expanded rows: `expand` on a table shows repro and evidence, but I could not set a per-column fmt for the expanded fields. For example, I wanted evidence as code and repro as a numbered list with its newlines kept. I also could not tell whether a clicked heatmap cell (flow x dimension) filters on both axes or on one axis.

## R2-vet

**Judge:** Both pages give the same verdict, KPIs, convergence lines, rubric table and run facts in nearly the same order. A serves the skill author better because it plots each delta against its spread, says plainly when the scores settled, and gives a reasoned merge call, while B gives a different merge call with no reasoning, shows the spread only as table numbers, and colours the deltas the wrong way round.

Only in the soft-ui page: Recommendation is 'Fix those two before you merge', which is a different merge call from A; Items-unchanged tile (2: R2, R7); Separate grouped bar chart of absolute baseline and candidate scores per item; Separate diverging bar chart of the change per item, sorted by delta; Table sorted with the regressions first, with an inline bar for the candidate score; Spread shown only as two table columns, not in a chart and not tied to the regressions; Delta colours are inverted in the table: negative values are green and positive values are red, which works against the emphasis on the regressions.

Only in the bespoke page: Recommendation is 'merge, after a look at R4 and R8', with the reasoning that both drops are smaller than the run-to-run spread and may be noise; Subtitle states the run size: 12 prompts x 4 runs x 6 waves; Dumbbell chart shows baseline-to-candidate movement per item with the +/- spread bars, so you can see each change against its noise; States that the scores settled from wave 3, and that candidate quality moved less than 0.012 over waves 3 to 6; Regressed rows are highlighted and tagged REG in the table and in the chart; Items-improved tile names the two biggest gains (R3 +0.12, R6 +0.15).

**Soft-ui agent:** 1 render runs, 0 fixed lines, 0 error lines.

**Friction:** The first render printed "check ok". Five things were hard or missing.
1. Summary tiles from the final wave: no data-driven way to get them. I wanted quality and stability at wave 6, with the delta from the baseline. That needs a filter to the last row and a pivot by version, and the stat `where` and `agg` options do not do this. I typed the values (0.853, +0.052 and so on) by hand, so they are not tied to the data.
2. Improved, unchanged and regressed counts: none of the expression, `where` or `by` options can derive a status column from delta. I typed the counts and the item lists by hand. A conditional computed column, for example `status: "delta > 0 ? 'improved' : ..."`, would fix this. It would also allow `stats: {by: status}` and a tone column in the table.
3. Regression flags: the table cannot mark R4 and R8 (the rows in run.json `regressions`) as bad from a second dataset. A tone map works only on a value in the same row, and the delta of R8 is -0.04, not a category.
4. Column labels: the table shows raw names such as baseline_spread. I could rename them with {key, label}, but that makes the spec longer.
5. Delta-only chart: I was not sure if a negative bar gets a bad colour, or if sort: -y works with fmt: delta.
I could not check the look by eye. I did not open the page.

## R3-design

**Judge:** Page A gives the reviewers the full use-case flow with numbered steps they can see, and contracts that show where each one is used. Page A also reports the retry exception honestly as an open question, but Page B names a second component that the data does not give. Page B puts the exception first, which helps, but it hides the steps in a tab and turns the contracts into a reference graph that says less about where each type is used.

Only in the soft-ui page: A warning banner at the top that puts the retry-with-backoff exception first; The retry banner names ChannelAccess as the second component, but design.json gives only a count of 2, so B made up that detail; A data-contract class diagram with reference edges (DeliveryResult to Message to Event) in place of four type cards; A 'Changes per component' bar chart beside the change table; The components table groups rows by kind and folds each group; The change table is sorted by components touched, so the exception is the first row; A separate 'changes simulated: 7' KPI tile.

Only in the bespoke page: The 9 numbered use-case steps are visible below the sequence diagram, and the arrows carry matching step numbers (B keeps the steps in a folded 'Steps' tab); Where each data contract is used or returned (for example 'returned by PreferenceEngine.decide'); A 'Changes' count for each component inside the components table; A discussion note that 'Move user prefs to a new service' lands in UserDirectory, which the design rates low volatility; States plainly that the design does not name the second component touched by the retry change; A legend for component kind and volatility, and a note that every call goes one way, down the layers.

**Soft-ui agent:** 3 render runs, 0 fixed lines, 2 error lines.

**Friction:** 1) The `data: {d: design.json}` form registers only the top-level arrays (d.components, d.calls, d.contracts, d.change_simulation). It does not register arrays nested inside an object, such as core_use_case.steps. Writing `d.core_use_case.steps` failed with a misleading "data file not found" error, and the error gave no hint about the `file.json#a.b` form. Guessing `design.json#core_use_case.steps` worked. 2) A string array turns into rows with one column named `value`, and the catalog does not say so. The steps table has no step number column, and I found no "numbered list from data" option. 3) No component draws a sequence diagram from data. The steps are prose, so I wrote the Mermaid sequenceDiagram by hand, which copies the data into the spec. 4) No component draws a class or type diagram from data. Contracts hold `fields` arrays, and I was not sure how a table shows an array cell. So I wrote a Mermaid classDiagram by hand, which also copies the data. A `classes` or `types` component that takes {type, fields[]} rows would avoid this. 5) The tone map key for a numeric column (components_touched: {1: good, 2: warn}) went through without an error or fix line, but nothing confirms that integer keys match. 6) The stats tiles are hand-typed counts. stats `by` can count rows, but no tile shows the row count of a dataset, such as the number of components, and no tile counts rows matching a condition, such as "lands in one place, 6 / 7". 7) A small cost: the subtitle had a colon in it, and YAML failed until I quoted it. The hint was clear. 8) I did not view the page visually. I trusted "check ok", so the graph's box-by-kind layout with TD direction and the 3:2 width split are not checked by eye. The bespoke.html was not opened.

## R4-pdlc

**Judge:** B serves the owner's morning job better: it puts everything that waits for the owner in one list, ties the questions to the pipeline cards, and shows intent progress with titles and a percent. A has the same core views (KPIs, kanban, stacked intent bars, question list) and adds a filterable table, but its stuck banner mislabels slow changes as stuck, and its intent chart shows only IDs, with stages out of pipeline order.

Only in the soft-ui page: A full table of all 12 changes, grouped by intent, with stage and owner filters and days-in-stage bars; A separate Intents table (id, title, status); A 'changes in flight 12' KPI and an 'intents 3 (2 building, 1 ready)' KPI; A red alert banner that says CH-0029 is stuck, and also calls CH-0021 and CH-0024 stuck for 8 to 9 days in verify (the data marks them not stuck); An empty DONE column in the pipeline; Question dates as absolute dates (2026-11-26).

Only in the bespoke page: One 'Waits for you' list that merges the stuck change, the 3 questions, and the 2 changes owned by you ('your turn', with the next action); A 'Slow movers (7+ days in stage)' table with 4 changes, including CH-0026 Dark mode tokens; KPIs for 'changes 7+ days in stage' (4) and 'ready to show / merge' (2); Question badges (Q-31, Q-32, Q-33) and 'you' badges on the pipeline cards, which tie questions to changes; Intent progress rows with intent titles, status, change, stuck and question counts, and a percent complete; Stage-ordered segments in the intent bars, labelled inline; Relative question ages ('asked 2 days ago').

**Soft-ui agent:** 2 render runs, 2 fixed lines, 0 error lines.

**Friction:** Disclosure: after rendering I opened shot.png in the output folder to check my page. It turned out to show the bespoke page ("ledger · pdlc board"), not mine. I did not change the spec after I saw it, but the comparison for this run may not be fully blind. The render does not say where its own screenshot goes, or whether it makes one. A render flag that writes a screenshot to a named path would stop this mix-up.

Gaps:
(1) No join across datasets. The question list cannot show the title or stage of each question's change, and the board cannot badge a change that has an open question. I put the change id on each question as a badge instead.
(2) No derived per-intent "progress %". A stacked horizontal bar by stage is the closest. A meter per intent would need values that I work out by hand.
(3) No easy way to show "aging" rows (7+ days in stage) as a tone or a highlight. I put them in the callout text and sorted the table by days_in_stage.
(4) The stat tile values (stuck, questions, owned by you) are hand counts. stats by: works on one column, but not on a filter such as owner == you or stuck == true. Each tile needs a where: plus a count.
(5) I was not sure that the board tone {stuck: {true: bad}} matches a JSON boolean. render gave no warning, but I could not check the result without a screenshot of my own page.
(6) A combined "waits for you" list (stuck changes, questions, and changes owned by you in one feed) is not possible from three datasets without a union.

## R5-pr

**Judge:** The two pages give the same verdict, severity counts, files table with change bars, findings ranked most serious first, and diff with each finding inline at its line, so the author takes away the same thing in the same order. B serves the author slightly better: it puts findings beside the files and tags each file with its finding IDs, while A repeats the PR metadata in a panel and the comment text in a wide table.

Only in the soft-ui page: Separate 'Pull request' key-value panel (author, base, head, commits, verdict); Full comment text for each finding in the findings table (B shows only title and file:line there); File status column (modified/added) as text; Severity counts as separate HIGH/MEDIUM/LOW stat tiles; Split (side-by-side) diff view.

Only in the bespoke page: Total lines changed stat (+34 -4) and a Commits stat tile; Per-file finding chips (C1, C2...) in the files table and on each diff file header, linking findings to files; Gutter markers on the exact lines that carry a finding; Full hunk ranges (@@ -1,24 +1,30 @@); Verdict as a badge in the header with the summary as a quote, not a coloured callout; Unified diff view.

**Soft-ui agent:** 3 render runs, 0 fixed lines, 0 error lines.

**Friction:** All three renders printed "check ok", but the check missed two layout and sorting problems. I found both only by taking my own headless Chrome screenshot.

(1) The table sort direction for severity is reversed. "sort: -severity" put low first and high last, and "sort: severity" put high first. The severity rank is ascending from most serious, but neither the catalog nor explain says so. An agent that writes "-severity" for "most serious first" gets the wrong order with no warning.

(2) In a three-child row (kv, chart, table), the files table was clipped. It needed a horizontal scroll, so the added and removed columns were hidden. "check ok" and "fits a 400px phone" did not flag this overflow at desktop width. I removed the chart and gave the table w: 2. The chart only repeated the table's inline bars.

(3) The inline bars for "added" and "removed" are both blue. There is no green/red (good/bad) colouring for diff counts, and the table has no clear prop for a bar colour per column.

(4) The data paths resolve from the spec folder, so the spec points at ../../../reports/R5-pr/. That is correct but clumsy. At first I copied the data next to the spec, then removed the copies.

(5) To show the verdict as a callout, I had to type the summary text from pr.json into the spec by hand. callout cannot read a field from a dataset (for example pr.summary), and kv cannot give the verdict a tone.

(6) The SKILL says that render loads the page in a browser, but it gives the agent no screenshot or a way to look at the page. I had to find google-chrome myself to check the layout.

Everything in the brief is shown: the verdict, files changed and by how much, the full diff, and each finding inline at its line, plus a severity-sorted findings table. A small wish: each finding in the findings table could link to its note in the diff.

## R6-tests

**Judge:** Both pages follow the brief's order: verdict callout, KPIs, suite timing, then failed and flaky tests. A serves the on-call engineer better: each failed row shows its error and file:line, and the callout names the fix. In B, every failure card is folded, so the reader must click seven cards to see any error, and the slowest tests come after the failures.

Only in the soft-ui page: Three separate bar charts: total time by suite, mean test time by suite, and a stacked chart of results by suite; Failed tests grouped under suite headings with counts; Total-time KPI and total-tests KPI as cards; Slowest-tests table shows the status of each test, has inline bars, and is paged over all 271 tests; All-tests table folded by default, grouped by suite.

Only in the bespoke page: Pass rate KPI (97.3%) and a stacked status bar under the KPIs; Root-cause callout tells the reader what to fix (price.total expired-code handling) and shows the two-line call path; One suite table holds total time, test count, mean time and fail/flaky counts per suite, with inline bars; Error message and failing test file:line shown inline on each failed row, with the stack trace one click away; Duration of each failed test; Note below the slowest tests that 2 search tests take a third of the suite time; All-tests table opens by default with a name search box and filters for suite and status.

**Soft-ui agent:** 1 render runs, 0 fixed lines, 0 error lines.

**Friction:** The first render printed "check ok", with no fixed or error lines. Five things were hard or missing.
1. Data is not joined. The tool cannot join failures.json (error and trace) to results.csv (status, ms, retries). The failed-tests list therefore has no duration or retry count, and the flaky tests have no errors to show. The flaky table shows only suite, test, ms and retries.
2. The summary is typed by hand. The page cannot compute the "build failed" verdict or the shared root cause (all 7 traces end in app/cart/price.py:52, ValueError('code expired')). I checked the data with Python and then wrote the callout text and the subtitle counts myself. A "group by error" or "group by last trace line" option, or a derived column for the list, would make the common cause visible without hand-written text.
3. Top-N is not clear. `limit` on a table means "rows per page", so the "Slowest tests" table pages through all rows. It does not show only the top 10. A top-N option for tables, like `limit` on chart, would help.
4. Totals are raw. The "Total time" stat sums ms and shows it in ms. The fmt `s` is not available on stat, so the large number is not converted to seconds.
5. Paths are long. Data paths from the output folder need `../../../reports/...`, which was easy to get right but verbose. No other confusion: catalog plus explain was enough to write the spec in one pass.

## R7-churn

**Judge:** B answers the architect's three questions directly: a co-change correlation matrix shows which files change together, and the bars, heatmap and table all carry the same wall assignment. A has the same core views (KPIs, callout, ranked bars, file-by-week heatmap, daily commits, hot-spot table), but it uses the heatmap as a stand-in for co-change, adds a noisy line chart and a very long detail table, and reaches a different and weaker wall recommendation.

Only in the soft-ui page: Multi-series line chart of lines changed each week for each file (10 overlapping lines); Weekly detail table, grouped by file and filterable, with the lines and commits for each file in each week; KPI note '84 days with commits'; KPI 'Top 2 files share 50%' (B reports 77% in 4 files instead); Heatmap used as the 'change together' view, with column totals for each week; Recommendation of one Engine wall for the tax and discount rules, with invoice.py as the Manager that calls it.

Only in the bespoke page: Pairwise correlation matrix of weekly churn: a real 'which files change together' view with values such as invoice/models 0.75 and invoice/emails 0.72; Recommendation of two walls: a Rules engine (vat, discount, tax) and an Invoice workflow (invoice with models and emails), plus 'leave the other 6 files as they are'; Bars coloured by wall assignment (rules engine, invoice workflow, calm), with the commit count on each label; Heatmap peak W41-W42 marked, with values printed on the hottest cells; Daily commits chart with the busy period (29 Sep to 19 Oct) shaded and the peak day (19 Oct, 14 commits) called out; 'Active weeks' column (for example 12/12) and a named wall for each file in the hot-spot table; Share of lines held by the rules files (63%).

**Soft-ui agent:** 2 render runs, 1 fixed lines, 0 error lines.

**Friction:** The table cannot aggregate. I wanted a hot-spot table with one row per file (total lines, total commits, share of churn). To get it, I computed the totals by hand and put them inline as a CSV dataset. The spec repeats derived numbers, and they do not follow filters. A table option such as `agg`, or computed data with group-by (for example `data: {file: churn.csv, group: file, sum: [lines, commits]}`), would remove that step. The stat tiles have the same problem: total lines (5681), the top-2 share (50%) and the peak week (890) are numbers I worked out myself. I could have computed total lines with stat data+agg, but no option gives a share of the total or the max of a group sum. There is also no co-change component. The brief asks which files "change together", and the data has no file-pair co-commit counts. So I used a file x week heatmap as a stand-in. A co-change matrix (file x file, from shared weeks or commits) would show coupling directly. The line chart with 10 file series is probably busy. A 'top N series, others grouped' option would help. Data paths had to climb out of the run folder (../../../reports/R7-churn/). That worked, but it was not obvious from the docs that a path with .. is allowed. The only fix was a comma inside an unquoted flow-map value, and the "Next time" hint made it clear.

## R8-latency

**Judge:** Both pages give the same verdict first, then the same four headline numbers, the daily trend against the SLO, and the endpoints ranked by change, so the release manager takes away the same story. B serves the reader slightly better because it marks the release on the trend chart and states for each endpoint whether it now breaks the 300 ms SLO, which A leaves the reader to infer from a separate bar chart.

Only in the soft-ui page: A separate horizontal bar chart of p95 before and after per endpoint, with an SLO line, beside the daily line chart; A folded 'Daily data' panel with the raw table of 20 daily rows (p50, p95, requests); A stat card 'Endpoints regressed: 3 of 8 with p95 +10% or more'; An inline bar on the change % column of the endpoint table.

Only in the bespoke page: A vertical release marker at 2026-11-20 and a shaded after-release region on the daily line chart; Before and after mean p95 lines (259 ms and 340 ms) drawn on the line chart; A per-endpoint SLO status column (Now breaks SLO, Over SLO worse, OK); A stat card 'Endpoints over SLO: 3/8, before 1/8 (checkout)'; The callout and footnote say GET /v1/search crossed the SLO and POST /v1/checkout was already over it before 3.14; Absolute ms deltas (+81 ms, +13 ms) in the stat cards; Before/after bars with an SLO line inline in each endpoint table row, in place of a separate chart.

**Soft-ui agent:** 3 render runs, 0 fixed lines, 0 error lines.

**Friction:** 1) I wanted a vertical marker on the daily line chart at the release date (2026-11-20). I tried `mark: [{x: 2026-11-20, label: "3.14"}]`. Render dropped it with no warning: no "fixed" line and no "error" line, and it still printed check ok. `explain chart` lists only `{y: ...}` marks, so I removed it and put the release date in a note. A before/after shaded band or an x mark would make the step change clearer. 2) The headline numbers (the 10-day before/after means of p95 and p50, the % change, the days over SLO, and the count of regressed endpoints) are hand-computed and typed as literal stat values. stat takes data+agg+col, but I found no clear way to split the rows at the release date. `where` with a date comparison is not documented, and computed columns have no if/else to add a before/after period column, so I did not use them. 3) Chart series take their legend names from the raw column names. To get "before/after" in place of "p95_before/p95_after", I added alias computed columns (`before: "p95_before"`). A per-series label prop would be cleaner. 4) Table tones match exact values only. I could not tone the p95-after cells over the 300 ms SLO, or the regressions over 10%, with a threshold rule, so the SLO breach per endpoint shows only through the dashed SLO line on the bar chart. 5) On the horizontal bar chart, the SLO mark label sits on top of the first bar and is hard to read (styling). 6) No fixed lines or error lines came out in any of the 3 runs. Run 2 was a re-render to get a screenshot with --shot, after Playwright was not importable from plain Python. Run 3 was after the edits above. Each run printed check ok.

## R9-migration

**Judge:** A is better for the engineering manager because it shows the schedule problems they must act on: the S4/S5 overlap, the zero-slack critical path into the holiday freeze, and Ana as the main owner risk. B has the same facts and the same section order. But its dependencies sit apart from the timeline, it reduces owners to step counts, and its risk heatmap has unordered axes and no risk IDs, so the reader has to find the problems alone.

Only in the soft-ui page: Separate left-to-right dependency graph, grouped by phase, with the critical path as a caption; Bar chart of step count per owner (counts only, no step names on it); Gantt rows grouped under phase headers; Steps table grouped by phase, folds by group, and has an owner filter; Risks table sorted by impact; Start and finish as separate KPI tiles, with the reads-switch tile marked 'before holiday freeze'; Risk heatmap with unordered axes (high/medium columns; medium/high/low rows) and a count legend instead of risk IDs.

Only in the bespoke page: Callout that S5 (turn on dual writes) starts 16 Dec, before its dependency S4 (backfill history) ends 19 Dec, with a red dashed overlap arrow in the Gantt; Critical path drawn on the Gantt bars (outlined) and given as a KPI tile; Holiday gap (24 Dec - 5 Jan) shaded on the timeline; Dependency arrows drawn inside the Gantt itself, not as a separate graph; Owner and dates on each Gantt row label; Owner cards that list each person's step names and days of work, plus a note that Ana owns 4 of the 6 critical-path steps; Risk numbers placed on a full 3x3 likelihood-by-impact matrix with ordered axes; Days column and phase badges in the steps table.

**Soft-ui agent:** 2 render runs, 0 fixed lines, 0 error lines.

**Friction:** 1) The dependencies are stored as an "after" array in each step of plan.json. The graph component needs a from/to edge list, and no data form expands an array column into edges. So I typed the 7 edges into the spec by hand as CSV. That copies data the skill says to reference by path. A "graph: {data: plan, id: id, deps: after}" form, or an explode/unnest option in data, would fix this. 2) The graph nodes show only the IDs (S1..S8). I found no prop that uses a nodes column (step) as the node label, so the reader must map IDs to names in the steps table. 3) I had to work out and type the summary tiles myself: the step count, the start date, the reads-switch date, the finish date, and the high-impact risk count. stat agg/col might compute min and max dates, but the catalog does not say whether agg works on dates. 4) I could not compute a critical path or a slack/duration column. Computed columns do not seem to support date arithmetic, so I wrote the critical path as a note by hand. 5) I could not mark the holiday-freeze window or the 2-week dual-write period after S7 on the gantt. Only one 'today' line is available, with no ranges or milestones. 6) The risk heatmap uses likelihood and impact strings. I could not set the axis order (low, medium, high), so the order may be alphabetical. 7) I could not check the visual result (node labels, phase boxes, axis order) without opening the HTML. render reports only that each node drew.

## R10-deps

**Judge:** Both pages give the same core structure: severity KPI tiles, a table of packages with severity, versions, issue and path, and a dependency tree beside the table. B serves the security lead better because its severity-coloured tree and its 'upgrade by entry point' list group the fixes by parent package, which plans the upgrades directly, while A's plain tree does not even show which nodes are vulnerable.

Only in the soft-ui page: Facet filter by dependency path (axios > follow-redirects, direct, eslint > semver, and so on) and a free-text search box; Table rows grouped under collapsible severity headers with counts; Separate installed and fixed_in columns (B merges them into one 'installed -> fixed' column); Per-node child counts in the dependency tree.

Only in the bespoke page: Subtitle summary: 2 direct, 7 transitive, through 6 top-level dependencies; Stacked severity proportion bar under the KPI tiles; Dependency tree nodes coloured by severity with installed versions, plus a legend that separates vulnerable nodes from non-vulnerable parents (A's tree shows axios only as a folder and does not mark it vulnerable); 'Upgrade by entry point' ranked list: the packages grouped by top-level parent, with the worst severity and the fix versions for each group; Path shown as a breadcrumb that starts at web, with a DIRECT badge for direct packages.

**Soft-ui agent:** 1 render runs, 0 fixed lines, 0 error lines.

**Friction:** Rendered first time with "check ok". There were five things I could not do well. (1) tree.txt uses "a > b > c" lines and is not a supported data file type. I had to copy its 9 paths into the spec by hand as a tree `paths` list, which breaks the rule "do not copy data into the spec". A `.txt` path-list loader, or a `sep: " > "` option on tree, would fix this. (2) The tree cannot put severity badges on each leaf, because those come from vulns.json and the tree paths come from inline text. A join between a path column and a data column, or a computed column that builds "web/" + path, would show severity on the tree. (3) I wanted a stat that splits direct from transitive packages. A computed column with a string condition (path == "direct") could give it, but the docs show only arithmetic expressions. (4) `sort: severity` and `group: severity` do not say if they use severity rank (critical > high > medium > low) or alphabetical order. stats `by` has an `order` prop, but table group has none. (5) A graph from the edge list would also work, but it needs a from/to edge list that the data does not have. I did not look at the page visually.

