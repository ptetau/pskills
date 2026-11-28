# Plans

This folder holds the plans for changes to this repository. A plan in this folder is
open. A plan that is done or superseded is in `archive/`.

To make a plan, run `/quiz-plan`. To run a plan, run `/quiz-plan-execute`.

## Open

| Plan | State | What it does |
|---|---|---|
| [tidy-up.plan.md](tidy-up.plan.md) | open | Gives the repository one front door, one place for plans, and smaller eval and bench data. |
| [soft-ui-80ms.plan.md](soft-ui-80ms.plan.md) | draft | Rewrites soft-ui in Go. A page builds in 80 ms, and is drawn in 80 ms on a desktop and on a phone. |

## Archive

| Plan | State | What it did | Pull request |
|---|---|---|---|
| [archive/build-probe-skill.plan.md](archive/build-probe-skill.plan.md) | done | Built the `probe` skill. | none: direct commits |
| [archive/build-pdlc-v1.plan.md](archive/build-pdlc-v1.plan.md) | superseded | Built pdlc version 1 (17 of 20 steps). Later pdlc versions replaced it. | none in the git log |
| [archive/harden-pdlc.plan.md](archive/harden-pdlc.plan.md) | done | Hardened pdlc by building sample apps with it. | #7 (harden pdlc by building sample apps) |
| [archive/pdlc-speed.plan.md](archive/pdlc-speed.plan.md) | done | Made pdlc faster and cheaper, in rounds, with a benchmark. Rounds 3 to 7 are kept. | #12 (add the benchmark), then #13 to #16 |
| [archive/align.plan.md](archive/align.plan.md) | done | Aligned decompose, blueprint, and pdlc with shared words and a hand-off. | #19 (the plan), #20 (the change) |
| [archive/pdlc-declarative-map.md](archive/pdlc-declarative-map.md) | done | A rule map from the old pdlc skill text (0.3.0) to the declarative text (0.4.0). | #21 (pdlc 0.4.0) |
| [archive/slice-harness.plan.md](archive/slice-harness.plan.md) | done | Built the `slice` plugin. | #28, #29, #30, #31 |

The state of `align.plan.md` in its own header says "Proposal". Pull request #20 built it.
