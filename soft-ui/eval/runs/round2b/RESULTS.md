# Results

Scores are 1 to 5. The judge did not score visual style. "Spec" is the size of the soft-ui spec. "Bespoke" is the HTML that the bespoke agent wrote.

| Report | Info | Components | Layout | Spirit | Verdict | Better for reader | Spec | Bespoke | Ratio |
|---|---|---|---|---|---|---|---|---|---|
| R11-pnl | 4 | 3 | 3 | 4 | close | bespoke | 4.6 KB | 27.0 KB | 5.9× |
| R17-options | 4 | 4 | 4 | 4 | close | bespoke | 2.4 KB | 24.7 KB | 10.4× |
| R18-business | 4 | 3 | 4 | 4 | close | bespoke | 4.9 KB | 23.5 KB | 4.8× |

**Mean over 3 reports:** information 4.0, components 3.3, layout 3.7, spirit 4.0. Verdicts: 3 close. Better for the reader: tool 0, bespoke 3, tie 0. The specs total 11.9 KB; the bespoke pages total 75.2 KB (6.3× more to write by hand).

## R11-pnl

**Judge:** Both pages answer the same four questions in roughly the same order: verdict, KPIs, profit build-up, account variances and monthly trend. B shows the budget inside the waterfall and adds a budget-to-actual bridge, explanations for each driver and a monthly P&L table, so the owner and the accountant can see why each variance happened. A only shows that the variances exist.

Only in the soft-ui page: Cost of sales KPI card (B has an operating expenses card instead); Separate variance-by-account table sorted by effect on profit, with section and adverse, favourable or on-budget verdict tags; Monthly revenue actual vs budget bar chart.

Only in the bespoke page: Budget shown as ghost bars beside the actuals in the revenue-to-net waterfall; Bridge from budgeted net profit to actual net profit, built from each account's variance, with the 4 small accounts grouped as Other; Annotated callouts that explain the Contractors, Print resale and Design fees/Marketing variances month by month (for example August and October contractor spikes); Inline variance bars in each row of the P&L statement; Cumulative net profit actual vs budget chart; Small multiples of monthly actual vs budget for the four accounts that move most; Month-by-month P&L table (revenue, cost of sales, gross profit, opex, net profit, each with its variance against budget); Net profit by month as bars coloured above or below budget, with values labelled; Headline stating that higher design fees and lower marketing recovered about $5,689.

**Soft-ui agent:** 2 render runs, 0 fixed lines, 0 error lines.

**Friction:** Both renders printed "check ok", with no "fixed" or "error" lines. The statement component did the hard part well. These were the problems:
(1) The callout cannot take values from the data. The headline numbers (net profit $55,637 against $75,900, and the Contractors and Print resale variances) are typed by hand into the callout. I computed them outside the tool, which goes against the "do not type numbers" rule.
(2) The stat with data+vs shows the raw column name in its sub line ("vs $75,900 net_b"). No prop sets a label for the comparison.
(3) To get section-signed totals (net profit, gross profit, revenue for the stats), I had to add a separate signed column for each section to the dataset with if/else expressions. A dataset step for "sign by section", or a statement-totals dataset, would be easier.
(4) A waterfall made from only the section subtotals (Revenue, Cost of sales, Gross profit, Operating expenses, Net profit) needs a separate grouped dataset with an ord column for the section order. The waterfall cannot read the statement's section/minus/subtotals config. At about 400px wide its x labels overlapped ("Gross profitOperating expenses"). I fixed this by changing the layout. The tool did not warn about the overlap.
(5) The table `good: {effect: up}` did not visibly colour the money-formatted effect column. Only the tone map on the verdict column gave colour. The variance column cannot be coloured by its effect on profit, as the statement does it, because cost lines need the reverse sign.
(6) fmt pct shows "-0%" for a tiny negative value (Insurance).
(7) There is no single bridge chart of the budget-to-actual net profit variance by account (budget net, then each account's effect, then actual net). A waterfall with a start bar would show it. I used a horizontal bar of effect on profit instead.
(8) No sparkline shows the monthly trend on the stat tiles without a typed list.

## R17-options

**Judge:** Both pages give the same verdict first ("serverless leads, but only just") and the same sections in the same order: ranking with a score heatmap, a cost line chart with a 12-month total bar, then pros and cons per option. A serves the CTO better because it shows how close the ranking is, with a stacked contribution bar, a gap tile and weight sliders that show which small weight changes flip the result, and it gives exact cost totals, growth rates and the crossover month that B leaves out.

Only in the soft-ui page: Table of month-12 cost for each option; Ranking table sorted by rank, with the criterion scores in line (A shows the score heatmap in a separate side-by-side table); Explicit note on the audience: 'For the CTO, decision due this week'.

Only in the bespoke page: KPI tiles: top score 3.70, gap to second 0.10, cheapest over 12 months $30.7k, fastest cost growth +158%; Stacked bar of weighted ranking that shows how much each criterion adds to each option's score; Interactive weight sliders with a sensitivity note on which weight changes flip the winner to VMs; 12-month cost total as a row in the comparison table, and exact 12-month totals with differences ($2,233 less than serverless, $26,759 less than K8s); A marker for the crossover month on the line chart, and direct labels on the lines; Cost growth percentages for each option (+158%, +71%, +24%, +38%); Caveat that the costs leave out staff time; Rank, score, 12-month cost, best criterion and weakest criterion on each pros and cons card.

**Soft-ui agent:** 2 render runs, 0 fixed lines, 0 error lines.

**Friction:** Both renders printed "check ok" and no "fixed" or "error" lines. The decision component matched the brief exactly. It read the scores map and the weights from the criteria file, and it printed the margin itself ("leads by 0.10 (2.8%)"). One problem: PaaS and VMs tie at 3.60, but the component ranks them 2 and 3 with no mark that they tie. I had to say so in the callout.

Things that were hard or missing:
(1) Pros and cons are lists inside each option. To show them, I had to explode pros and cons into two datasets, add a "kind" column to each, and union them. Then a board showed one column per option. That works, but it takes 3 datasets for a common need. A "list of strings" field in list or decision, for example `pros: pros, cons: cons` shown as bullets per option, would help.
(2) No step finds where two series cross. The callout and the chart notes say things like "VMs are cheapest from month 6 on". I had to work out those numbers by hand from the CSV, and my first draft said month 4, which was wrong. A crossover or "rank by month" helper, or chart marks from data, would stop this mistake.
(3) The decision table has no join to cost data. I could not put the 12-month cost total next to the weighted score in one table.
(4) In the row layout, the line chart (w: 2) next to a col with a chart and a table leaves a big empty space under the line chart. There is no way to make the cells the same height or to line them up.
(5) The decision shows the margin only for the leader against the runner-up. It does not show each option's distance from the leader.
(6) I could not tie a stated value, such as "0.1 of a weighted point", to the computed result, so the callout text is typed by hand.

## R18-business

**Judge:** B puts revenue, last year, and expenses on one chart with profit shaded, and adds a profit-by-month view, so the owner sees the health and the cost trend at a glance. B also labels each bar with its amount and share, and flags the data gaps; A puts the per-month numbers in a folded table and charts "Others" as the largest customer bar.

Only in the soft-ui page: Expenses this year as its own KPI ($565,493); Revenue last year (Jan-Nov) as its own KPI card; Bank, savings, owed to us, and we owe shown as separate KPI cards; Folded month-by-month table with revenue, last year, growth, expenses, profit, and margin each month; Separate revenue-vs-expenses grouped bar chart.

Only in the bespoke page: A KPI for total overdue invoices ($33,140, with $7,120 over 60 days); Profit-each-month bar chart that marks thin-margin months and shows the average; Net position line ($161,880) in a cash-position ledger; Overdue total row and a call-to-action note on who to chase; Percentage shares and amounts for each expense category and each customer; Data-quality footnotes (categories and customers do not add up to the monthly totals, no 2025 expenses, Kereru bucket); The note that costs are rising almost as fast as revenue.

**Soft-ui agent:** 4 render runs, 1 fixed lines, 0 error lines.

**Friction:** (1) The callout cannot reference computed values. A headline such as "revenue $662k, up 12.6%, profit $96.7k, cash = 2.4 months of expenses, $33.1k overdue" had to be computed outside the tool with a Python one-liner and typed in by hand. That conflicts with the rule "do not type numbers that the data holds". Chart notes such as "10 of 11 months" and "77% of expenses" have the same problem. A template form like {{sum monthly.revenue | money}} in callout and note would fix it. (2) The stat `vs` subline prints the raw column name ("vs $587,954 revenue_last_year"). I found no prop to label it. (3) The stats `cols` tiles use column names as labels, so I had to add a `rename` step on the dataset to get "Owed to us". A `labels` map on stats would be simpler. (4) Only a card can collapse. I first put `collapse` on a table, which was auto-fixed (dropped), and then wrapped the table in a card. (5) The data does not reconcile, and the page does not say so: expenses_by_category sums to $496.5k but the monthly expenses sum to $565.5k, and top_customers sums to $631.9k against $662.2k of revenue. A reconciliation or check step would help. (6) I wanted things I could not easily show: a derived cash-runway stat (cash / mean monthly expenses) computed from two datasets, a profit-margin line on the revenue/expense chart (a second axis or combo bar+line), and a mark on the ageing chart at the 60-day overdue boundary for a category axis. I also could not give stat tiles a sparkline from a data column (`spark` takes only a typed list). (7) Sorting by `days_overdue` puts the oldest debts first, which was right. My first title, "latest first", described that order wrongly; I fixed it to "most late first", which still reads awkwardly.

