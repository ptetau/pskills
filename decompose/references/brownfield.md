# Subsystem mode: designing inside an established codebase

In a new system, volatility is a judgement. In an existing system, volatility left tracks
in the git history. Some code changes frequently. Other code changes together again and
again. Together, these two signals show where the volatility is and where the current
walls leak. This file tells you how to measure and read these signals, and how to attach a
new subsystem and not disturb the host.

## Why history is good evidence

- Change history predicts defects better than code metrics do. Graves and others (2000):
  the number of times that code changed is a better indicator of faults than the length
  of the code. Nagappan and Ball (2005): *relative* churn (normalised by size and time
  span) separated fault-prone binaries from the other binaries with 89% accuracy. But
  absolute churn was a poor predictor. Rahman and Devanbu (2013): process metrics are
  better than code metrics.
- `volatility.py` reports raw commit counts and churn. Read these numbers against the file
  size and the length of the window. Do not read them as absolute scores.
- Change coupling also predicts defects. D'Ambros, Lanza and Robbes (2009) found that
  change coupling correlates with defects more strongly than complexity metrics do.
  Cataldo and others (2009) found that logical dependencies explained most of the variance
  in fault proneness.
- Tornhill calls change coupling a "hidden, implicit dependency": a change to one module
  causes a predictable change in the other module. Coupling is not bad in itself. Coupling
  *inside* a component is cohesion. Unexpected coupling *across* components is the design
  problem.

## Step 1 — Measure

Run the bundled script from the root of the repository:

```
python <skill-dir>/scripts/volatility.py --path <area> --depth <n> --since "12 months ago"
```

| Option | Use |
|--------|-----|
| `--path src` | Analyse one subtree. The components are the directories below the subtree. |
| `--depth 2` | The number of directory levels that make a component. Select the level where the modules of the host are. |
| `--since "2 years ago"` | A longer window for code that changes slowly. A shorter window (`"3 months ago"`) shows the current trend. |
| `--first-parent` | Count each merged PR as one change. Use this option when the team makes many small commits for each PR. Without this option, the small commits hide coupling. |
| `--exclude 'glob'` | Remove more noise, for example a generated client or a fixtures folder. |
| `--json` | Machine-readable output. |

The script already removes these items:

- Merge commits.
- Changes to whitespace only.
- Commits that `.git-blame-ignore-revs` lists.
- Lockfiles, and vendored and built paths.
- Files marked `linguist-generated` or `linguist-vendored`.

The script follows renames. The script does not use a commit that touches more than 30
files for coupling, as code-maat does. The script gives a warning on a shallow clone.

If Python is not available, get the same signals from plain git:

```
git log --no-merges --since="12 months ago" --format=format: --name-only | sort | uniq -c | sort -rn | head -30
git log --oneline -- <hotspot file>          # what kind of change keeps happening
```

## Step 2 — Read the report

**Component volatility.** Read these three numbers together: commits, months active, and
days since change.

| Pattern | Meaning |
|---------|---------|
| Many commits, many months active, changed recently | Steady volatility. A strong wall candidate. |
| Many commits in one or two months | A one-off burst (a migration, a launch). Weak evidence. Read the commit messages. |
| Few commits, a long time since a change | Stable. Leave this code alone, even if the code is ugly. Low change means low cost. |
| Many authors | Coordination cost. Examine the ownership boundary (Conway's law, in Step 7). |

**Change coupling.** The degree is the number of shared commits, divided by the average
number of commits of the two items in the pair. The thresholds come from code-maat. The
report lists a pair only when the pair passes all three thresholds:

- At least 5 commits on average.
- At least 5 shared commits.
- A degree of at least 30%.

These thresholds are noise floors to *list* a pair. The thresholds are not verdicts.
Tornhill adjusts the thresholds for each codebase ("I usually have to tweak and
experiment"), and usually ignores coupling below 30%.

Coupling in itself is not good and not bad. The important question is whether the
coupling is expected.

| Pair | Meaning |
|------|---------|
| Two files in the same component | Usually cohesion. Correct. |
| Code and its test | Expected. Correct. |
| Two components, high degree | One volatility in both components. Merge the two components, or give the shared volatility its own wall. |
| The future area of the new subsystem, and a host hotspot | The subsystem will change together with that hotspot. Put an abstraction between the two. |

**Hotspots** are files that change frequently and are also large. The hotspots show where
the volatility of the host lives now. Usually, this volatility has no wall.

**Name the kind of change.** The numbers show *where*. The commit messages show *what*.
Read `git log --oneline -- <file>` for the top hotspots and the coupled pairs. Then sort
the messages:

| Messages look like | The volatility is | Wall type |
|--------------------|-------------------|-----------|
| "add step", "reorder", "skip X when Y" | the sequence | Manager |
| "change rate", "new rule", "fix rounding", "new discount" | an activity or rule | Engine |
| "switch to vendor X", "migrate table", "new API version" | access to a resource | ResourceAccess |
| "new screen", "new endpoint", "mobile" | the caller | Client |

**Do not fully trust the data.** A repository with squash merges shows changesets the size
of a PR (more coupling). A repository with many small commits shows less coupling.
`--since` uses committer dates, and a rebase resets these dates. The numbers nominate
volatilities. The reasoning in Phase 2 decides.

## Step 3 — Map the host onto the taxonomy

Before you design new walls, label the parts that already exist, also if the host uses
different names:

- Where are the workflows (the order of steps)? That code acts as a Manager.
- Where are the business rules? That code acts as Engines. Are the rules in one place, or
  in many places?
- Where does code talk to databases and vendors? That code acts as ResourceAccess. Do
  vendor types leak past that code?
- What calls the system? These callers are the Clients.

Mark the tangles. Examples of tangles:

- A rule that is duplicated in two places.
- A controller that is also a workflow and a rule engine.
- A vendor SDK type that is used across the codebase.

Hotspots are usually tangles.

Accept the structure of the host as it is. Redesign only what the subsystem needs, plus
the seam.

## Step 4 — Choose the seam

Feathers: "A seam is a place where you can alter behavior in your program without editing
in that place." Each seam has an **enabling point**, where you select the behaviour that
runs. Examples are a dependency-injection binding, a factory, a config value, and a
feature flag.

- Attach the subsystem at a seam with an explicit enabling point.
- Try to add new code beside the host, not to edit hotspots in place. Feathers'
  *sprout* and *wrap* techniques: put new behaviour in a new class or method. Then call
  that class or method from one line in the host.
- Do not make the new subsystem depend directly on a host hotspot. Make the subsystem
  depend on an abstraction over the hotspot.

## Step 5 — Protect the new walls from the host

The correct pattern depends on which side is downstream. The downstream side is the side
that consumes the model of the other side.

**The subsystem calls the host: anti-corruption layer** (Evans). "As a downstream client,
create an isolating layer to provide your system with functionality of the upstream system
in terms of your own domain model." The anti-corruption layer talks to the host through
the existing interface of the host, and translates. In the terms of this skill, the layer
is a ResourceAccess component over the host. The layer hides the host as a volatile
resource.

**The host calls the subsystem: open-host service** (Evans). The subsystem publishes one
API in its own terms (a published language). Now the host is the downstream side. The
translator that changes host types into subsystem types is on the host side of the seam.
In the terms of Evans, that translator is the anti-corruption layer of the host. Keep the
translator thin, and keep the translator in the seam.

In the two patterns, host types do not cross into the subsystem.

- If the host area is a big ball of mud, draw a boundary around the area. Do not try to
  model inside the boundary (Evans).

When an ACL (anti-corruption layer) is too heavy, use a different relationship from the
context map of Evans:

| Relationship | Use when |
|--------------|----------|
| Conformist | The model of the host is sufficiently good. Use the model as it is. |
| Open-host service + published language | Many consumers need the subsystem. Publish one documented protocol. |
| Separate ways | The integration costs more than it returns. |

**Hyrum's law**: "all observable behaviors of your system will be depended on by
somebody." The implicit behaviour of the host at the seam (ordering, error text, nulls,
timing) is part of the contract. Before you redirect a call, pin this behaviour with
characterisation tests.

## Step 6 — Plan the migration

Each step must keep the system releasable.

**Branch by abstraction** (Hammant, and Fowler) replaces behaviour inside the host:

1. Put an abstraction in front of the existing behaviour. Route one caller through the
   abstraction.
2. Move each caller onto the abstraction. Add tests as you move the callers.
3. Build the new implementation behind the same abstraction. Move the callers to the new
   implementation one at a time, behind a flag. Where you can, compare the old and the
   new implementation side by side.
4. Delete the old implementation. If the abstraction has no more use, delete the
   abstraction too.

**Strangler fig** (Fowler) grows a new system around an old system. Start with small
additions. Build the additions on top of the legacy code, but separate from the legacy
code. Make the additions larger until you can remove the old code. Two moves are useful:

- *Event interception*: route some state changes to the new component.
- *Asset capture*: move one asset at a time, and keep the option to move the asset back.

If code exists only for the migration, label that code as **transitional architecture**.
Schedule the deletion of that code.

For each step that edits host code, use the legacy change algorithm of Feathers:

1. Identify change points.
2. Find test points.
3. Break dependencies.
4. Write tests.
5. Make the change.

## Step 7 — Check ownership

Conway (1968): organisations "are constrained to produce designs which are copies of the
communication structures of these organizations." Team Topologies gives **change cadence**
as a natural place to split a system. The other natural places in that list are business
domain, regulatory compliance, team location, risk, performance isolation, technology, and
user personas.

- Try to have one team own each new wall. If two or more teams share a wall, the wall
  will leak along the team line.
- If the measured coupling crosses a team boundary, move the wall. Or, discuss the
  coupling with the persons who own the teams.

## Step 8 — Define success as a measurement

Write the check into the design doc. Measure only the period after the switch-over.
Compare this period with a window of the same length before the switch-over. A long
window contains mostly commits from before the change. Thus, a long window reports the old
coupling. Tornhill recommends a window of two or three months for recent trends. For
example:

```
python volatility.py --path shop --since 2026-01-01 --until 2026-04-01   # before
python volatility.py --path shop --since 2026-05-01                      # after
```

"Three months after the switch-over, the coupling between `cart` and `checkout` is much
lower than its old 62% (the bar that the skill recommends: out of the report, below the
30% floor). Changes to promotions touch only `PricingEngine` and `PromotionsAccess`." If
the numbers do not change, the wall leaks, and the design needs another look.

## Rules for subsystem mode

1. Measure before you decompose. The evidence nominates, and the reasoning decides.
2. Treat each pair that the report lists (30% or more, the default floor of code-maat) as
   a question that the design must answer. Do not put a wall between such a pair, with one
   exception. The exception is a wall that exists to absorb that coupling, behind an
   abstraction or a translation layer. (The 30% figure is a heuristic of this skill, from
   the default of a tool. The figure is not a law.)
3. Enter the host only through seams with explicit enabling points.
4. Do not let host types cross into the subsystem. Use an anti-corruption layer where the
   subsystem calls the host. Use an open-host service where the host calls the subsystem.
5. Before you cut, characterise the behaviour of the host at the seam.
6. Keep the system releasable at each step. Delete transitional code on schedule.
7. Keep volatile new code out of stable old packages. Do not depend directly on host
   hotspots.
8. Do not change code that is stable and ugly.
9. Align each wall with one owning team.
10. Define success as a number that you will measure again.
