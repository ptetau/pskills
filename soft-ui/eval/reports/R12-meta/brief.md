# R12 · Meta-analysis of a sleep intervention

`studies.json` holds 9 randomised trials of a cognitive behavioural therapy for insomnia
(CBT-I) against usual care. Each study gives the mean difference in sleep onset time
(minutes; negative is better), its 95% confidence interval, the sample size, the weight
in the pooled model, the year, and the risk of bias. `pooled.json` holds the pooled
random-effects result and the heterogeneity statistics. `outcomes.csv` holds the raw
sleep-onset minutes for each participant in the largest trial, by arm.

Reader: a clinical researcher who writes the discussion section. They need the pooled
effect and its certainty, how each study compares, whether the studies agree, whether
the high-bias studies drive the result, and how the outcome is distributed in the
largest trial.
