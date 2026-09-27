# Vet Report: quiz

**Skill:** `quiz` · version `e6139c8b5903`
**Suite:** `evals/quiz/suite.json` · `bf0323ef8190`
**Run:** `20260927T102133Z` · 2 prompts × 3 runs · 6/6 runs usable · confidence normal
**Models:** skill runs on `sonnet` · judges on `sonnet`
**Agents:** preset `minimal` · waves of 1 · no overrides

This was a small test of the eval harness itself. Three runs per prompt is too few for
a settled grade, and the skill ran on a smaller model than usual. Read the numbers as
a first look, not a verdict on `/quiz`.

---

## Scores

| | Score | Meaning |
|---|---|---|
| Quality | 93.3 | Weighted share of the rubric met across all runs |
| Stability | 59.7 | How little the output changed between runs |
| **Overall** | **74.6 (C)** | √(quality × stability) |

Per-run quality: min 88 · median 93 · max 100

*(Grade bands: A ≥ 90 · B ≥ 80 · C ≥ 70 · D ≥ 60 · F below.)*

## How the grade settled

| Wave | Runs per prompt | Quality | Stability | Overall | Moved |
|---|---|---|---|---|---|
| 1 | 1 | 95 | - | - | - |
| 2 | 2 | 93.5 | 70.8 | 81.4 (B) | - |
| 3 | 3 | 93.3 | 61.1 | 75.5 (C) | -5.9 |

Not settled: the grade dropped 5.9 points at the last wave as the third run of each
prompt showed more drift. Quality held steady at about 93, so the movement is all
stability. More runs are needed before the grade can be trusted.

## Verdict

Quiz does what it says almost every time: the card format, the one-card-per-message
rule, the rhythm and the ending were met in every run, and quality sits at 93. What it
doesn't do is ask the same questions twice. The first question is stable (tone for
the email, "what's it for" for the tagline), but after that each run picked a
different set of follow-ups (2 to 4 of them), with different option labels, and one
run flipped the recommended tone. That single habit drives most of the low stability,
including the drift in the delivered work.

---

## Rubric items

| Item | Kind | Wt | Met | Stability, same prompt | Agreement | Stability, across prompts |
|---|---|---|---|---|---|---|
| R1 Card shape | structure | 2 | 100% | 100 · identical | 100% | 60 · minor drift |
| R2 Option lines: what/why/cost | structure | 2 | 83.3% | 62.5 · major drift | 66.7% | 25 · major drift |
| R3 Turn rhythm: hint + `[✓]` echo | structure | 2 | 100% | 100 · identical | 100% | 60 · minor drift |
| R4 Resolved view, confirm, summary | structure | 2 | 100% | 95 · equivalent | 100% | 60 · minor drift |
| R5 One card per message | behavior | 2 | 100% | 100 · identical | 100% | - |
| R6 One grounded `(recommended)` per card | behavior | 2 | 66.7% | 25 · major drift | 50% | - |
| R7 ≤ 7 questions, steady counter | behavior | 1 | 100% | 60 · minor drift | 66.7% | - |
| R8 Echo matches the reply | behavior | 2 | 91.7% | 62.5 · major drift | 83.4% | - |
| R9 No markdown or emoji in cards | behavior | 1 | 100% | 100 · identical | 100% | - |
| R10 Right questions, biggest first | outcome | 3 | 100% | 25 · major drift | 33.3% | - |
| R11 Realistic options, sensible default | outcome | 3 | 100% | 42.5 · major drift | 83.4% | - |
| R12 Summary and work reflect answers | outcome | 3 | 83.3% | 25 · major drift | 33.3% | - |

## Prompts

| Prompt | Axis | Quality | Stability | Usable runs |
|---|---|---|---|---|
| P01 a welcome email for new members of my climbing gym | typical | 97.3 | 64.6 | 3/3 |
| P02 a tagline | minimal | 89.3 | 57.6 | 3/3 |

---

## Where it falls short

### R6 One grounded `(recommended)` per card — met in 66.7% of runs

met 2 · partial 4 · missed 0 — every card carries exactly one tag, but the reason is
often generic rather than tied to the request.

> "because a single, concrete step converts far better than a list of options" — P01#2
> "A · a named product/app (recommended) — You've already got a specific product or app in mind" — P02#2 (a tag on the first card, before the user has said anything)

### R2 Option lines: what/why/cost — met in 83.3% of runs

met 4 · partial 2 · missed 0 — on the terse tagline prompt, some options are noun
phrases with no cost or trade-off.

> "A portfolio or bio-style line for a person or a one-off project — more voice-driven and idiosyncra…" — P02#3

### R12 Summary and work reflect answers — met in 83.3% of runs

met 4 · partial 2 · missed 0 — the delivered taglines sometimes break the choices just made.

> "Made with care, worth a look." (6 words after choosing 3-5) — P02#1

## Where it varies

### R10 Right questions, biggest first · P01 — major drift · 1 / 1 / 1 of 3

- 1 run (P01#1): tone, then call to action (2 questions)
- 1 run (P01#2): tone, then what to lead with, then what to close on (3 questions)
- 1 run (P01#3): tone, then what to lead with, then length and shape (3 questions)

Every run opens on tone and none re-asks the prompt, but the follow-up decisions
differ in kind each time.

### R10 Right questions, biggest first · P02 — major drift · 1 / 1 / 1 of 3

- 1 run (P02#1): subject, tone, length, focus (4 questions)
- 1 run (P02#2): subject, tone, emphasis (3 questions)
- 1 run (P02#3): subject, tone, length (3 questions)

### R11 Realistic options, sensible default · P01 — major drift · 2 / 1 of 3

- 2 runs (P01#1, P01#2): recommend "stoked & energetic" for the tone
- 1 run (P01#3): recommends "warm & personal" for the same question

A flipped default on the most load-bearing decision.

### R12 Summary and work reflect answers · P01 and P02 — major drift · 1 / 1 / 1 of 3

Each run's summary and work faithfully follow its own answers, but because the
questions differed, the work differs: one email centres on booking orientation, one
closes on the belay class, one is a short scannable list. This drift is downstream of
R10, not a separate fault.

### R6 One grounded `(recommended)` per card · P01 and P02 — major drift

Which cards get a request-specific reason changes from run to run (P01), and whether
the first card is tagged at all changes too (P02: untagged in 2 runs, tagged in 1).

### R8 Echo matches the reply · P02 — major drift · 2 / 1 of 3

- 2 runs (P02#1, P02#3): "you decide" is echoed with a `(via: you decide)` note
- 1 run (P02#2): the echo drops the note and shows only the chosen option

### R2 Option lines across prompts — major drift · 2 / 2 of 4

- P01 runs: every option names a cost or trade-off
- P02 runs: about half the options drop it, all of them on the first card

## What to fix

1. **Flow step 2 ("identifies all the questions that matter … most-load-bearing
   first")** — this is too loose to give the same questions twice. Make it a fixed
   procedure: before the first card, list the decisions in a set order (what it's
   for / audience → tone → scope or length → content focus → call to action), keep
   only those the prompt leaves open and that would change the work, then commit to
   that list and its count. → moves R10, R12, R7, R11
2. **Rules of the look #5 (`(recommended)`)** — say the reason must quote or point to
   something the user said, and that a card with nothing to go on (usually the first
   card on a terse prompt) gets no tag. → moves R6, R11
3. **Reply parsing ("you decide … defer to the option marked recommended")** — give the
   exact echo, e.g. `[✓] 02 tone → A · bold (you decided: recommended)`, so deferred
   replies are always marked the same way. → moves R8, R3
4. **Rules of the look #4 (option sentences)** — require every option sentence to end
   on its cost or trade-off, even on a first card with no context. → moves R2
5. **Final resolved view** — say it is always a fenced code block, as in the example;
   two of four runs used plain lines. → moves R4 across prompts

## Excluded runs and lost judges

None.

---

## Appendix

- Captures: `evals/quiz/runs/20260927T102133Z/outputs/` (one file per run: transcript + files written)
- Machine-readable twin: `results.json`, validating against `vet/references/results.schema.json`
- Eval cost: 13 agents, about 909k subagent tokens, 27 minutes on a 4-core machine (2 agents at a time)
