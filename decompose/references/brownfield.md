# Subsystem mode: designing inside an established codebase

In a new system, volatility is a judgment. In an existing one, it has left tracks in the
git history. Code that changes often, and code that keeps changing together, tells you
where the volatility is and where the current walls leak. This file covers how to measure
that, how to read it, and how to attach a new subsystem without disturbing the host.

## Why history is good evidence

- Change history predicts defects better than code metrics. Graves et al. (2000): the
  number of times code has changed is a better indicator of faults than its length.
  Nagappan and Ball (2005): relative churn separated fault-prone binaries from the rest
  with 89% accuracy. Rahman and Devanbu (2013): process metrics beat code metrics.
- Change coupling predicts defects too. D'Ambros, Lanza and Robbes (2009) found it
  correlates with defects more strongly than complexity metrics do. Cataldo et al. (2009)
  found logical dependencies explained most of the variance in fault proneness.
- Tornhill calls change coupling a "hidden, implicit dependency": a change to one module
  leads to a predictable change in the other. Coupling is not bad in itself. Coupling
  *inside* a component is cohesion. Surprising coupling *across* components is the design
  problem.

## Step 1 — Measure

Run the bundled script from the repo root:

```
python <skill-dir>/scripts/volatility.py --path <area> --depth <n> --since "12 months ago"
```

| Option | Use |
|--------|-----|
| `--path src` | Analyse one subtree. Components are the directories below it. |
| `--depth 2` | How many directory levels make a component. Pick the level where the host's modules live. |
| `--since "2 years ago"` | Longer window for slow-moving code; shorter (`"3 months ago"`) to see the current trend. |
| `--first-parent` | Count each merged PR as one change. Use it when the team makes many small commits per PR, which otherwise hides coupling. |
| `--exclude 'glob'` | Drop more noise, such as a generated client or a fixtures folder. |
| `--json` | Machine-readable output. |

The script already drops merge commits, whitespace-only changes, commits listed in
`.git-blame-ignore-revs`, lockfiles, vendored and built paths, and files marked
`linguist-generated` or `linguist-vendored`. It follows renames. It leaves commits that
touch more than 30 files out of coupling, as code-maat does. It warns on a shallow clone.

If Python is not available, the same signals come from plain git:

```
git log --no-merges --since="12 months ago" --format=format: --name-only | sort | uniq -c | sort -rn | head -30
git log --oneline -- <hotspot file>          # what kind of change keeps happening
```

## Step 2 — Read the report

**Component volatility.** Read commits, months active, and days since change together.

| Pattern | Meaning |
|---------|---------|
| Many commits, many months active, changed recently | Steady volatility. A strong wall candidate. |
| Many commits in one or two months | A one-off burst (a migration, a launch). Weak evidence. Check the messages. |
| Few commits, long since changed | Stable. Leave it alone even if it is ugly: low change means low cost. |
| Many authors | Coordination cost. Check the ownership boundary (Conway's law, below). |

**Change coupling.** Degree is shared commits divided by the average commits of the
pair. Thresholds follow code-maat: pairs need at least 5 commits on average, 5 shared
commits, and 30% degree to be listed.

| Pair | Meaning |
|------|---------|
| Two files in the same component | Usually cohesion. Fine. |
| Code and its test | Expected. Fine. |
| Two components, high degree | One volatility smeared across both. Either merge them or give the shared volatility its own wall. |
| New subsystem's future area and a host hotspot | The subsystem will drag that hotspot along. Put an abstraction between them. |

**Hotspots** are files that are both frequently changed and large. They are where the
host's volatility currently lives, usually unwalled.

**Name the kind of change.** Numbers show *where*; commit messages show *what*. Read
`git log --oneline -- <file>` for the top hotspots and coupled pairs, and sort the
messages:

| Messages look like | The volatility is | Wall type |
|--------------------|-------------------|-----------|
| "add step", "reorder", "skip X when Y" | the sequence | Manager |
| "change rate", "new rule", "fix rounding", "new discount" | an activity or rule | Engine |
| "switch to vendor X", "migrate table", "new API version" | access to a resource | ResourceAccess |
| "new screen", "new endpoint", "mobile" | the caller | Client |

**Distrust the data a little.** A squash-merge repo shows PR-sized changesets (more
coupling). A many-small-commits repo shows less. `--since` uses committer dates, which
rebases reset. The numbers nominate volatilities; the reasoning in Phase 2 decides.

## Step 3 — Map the host onto the taxonomy

Before designing new walls, label what already exists, even if the host uses different
names:

- Where do workflows live (the order of steps)? That code is acting as a Manager.
- Where do business rules live? Acting as Engines. Are they in one place or scattered?
- Where does code talk to databases and vendors? Acting as ResourceAccess. Do vendor
  types leak past it?
- What calls the system? The Clients.

Mark tangles: a rule duplicated in two places, a controller that is also a workflow and
a rule engine, a vendor SDK type used across the codebase. Hotspots are usually tangles.

The host's structure is a given. Redesign only what the subsystem needs, plus the seam.

## Step 4 — Choose the seam

Feathers: "A seam is a place where you can alter behavior in your program without
editing in that place." Every seam has an **enabling point**, where you choose which
behavior runs: a dependency-injection binding, a factory, a config value, a feature flag.

- Attach the subsystem at a seam with an explicit enabling point.
- Prefer adding new code beside the host over editing hotspots in place. Feathers' *sprout*
  and *wrap* techniques: put new behavior in a new class or method and call it from one
  line in the host.
- Never make the new subsystem depend directly on a host hotspot. Depend on an
  abstraction over it.

## Step 5 — Protect the new walls from the host

**Anti-corruption layer** (Evans): "create an isolating layer to provide your system with
functionality of the upstream system in terms of your own domain model." It talks to the
host through the host's existing interface and translates in one or both directions.

- Host types never cross it. The subsystem's contract uses its own shapes.
- It is a ResourceAccess-style component: it hides the host as a volatile resource.
- If the host area is a big ball of mud, draw a boundary around it and don't try to model
  inside it (Evans).

Other relationships from Evans' context map, when an ACL is too heavy:

| Relationship | Use when |
|--------------|----------|
| Conformist | The host's model is good enough; just adopt it. |
| Open-host service + published language | Many consumers need the subsystem; publish one documented protocol. |
| Separate ways | The integration costs more than it returns. |

**Hyrum's law**: "all observable behaviors of your system will be depended on by
somebody." The host's implicit behavior at the seam (ordering, error text, nulls,
timing) is part of the contract. Pin it with characterization tests before redirecting
any calls.

## Step 6 — Plan the migration

Every step must leave the system releasable.

**Branch by abstraction** (Hammant; Fowler), for replacing behavior inside the host:

1. Put an abstraction in front of the existing behavior and route one caller through it.
2. Move every caller onto the abstraction, adding tests as you go.
3. Build the new implementation behind the same abstraction. Switch callers over one at
   a time, behind a flag. Compare old and new side by side where you can.
4. Delete the old implementation, and the abstraction if it has no further use.

**Strangler fig** (Fowler), for growing a new system around an old one: start with small
additions, built on top of but separate from the legacy code. Grow them until the old
code can be removed. Useful moves: *event interception* (route some state changes to the
new component) and *asset capture* (move one asset at a time, keeping the option to move
it back).

Label any code that exists only for the migration as **transitional architecture**, and
schedule its deletion.

Feathers' legacy change algorithm, for each step that edits host code: identify change
points, find test points, break dependencies, write tests, then make the change.

## Step 7 — Check ownership

Conway (1968): organizations "are constrained to produce designs which are copies of the
communication structures of these organizations." Team Topologies lists **change cadence**
as a natural place to split a system, alongside business domain, regulation, risk,
performance isolation, technology, and user personas.

- One team should own each new wall. If a wall is split across teams, it will leak
  along the team line.
- If the measured coupling crosses a team boundary, move the wall or raise it with the
  people who own the teams.

## Step 8 — Define success as a measurement

Write the check into the design doc, for example: "Six months after the switch-over,
re-run `volatility.py`. Coupling between `cart` and `checkout` is below 30%. Changes to
promotions touch only `PricingEngine` and `PromotionsAccess`." If the numbers don't move,
the wall leaks and the design needs another look.

## Rules for subsystem mode

1. Measure before you decompose. Evidence nominates, reasoning decides.
2. Don't put a wall between two components with coupling of 30% or more unless the wall
   exists to absorb that coupling (behind an abstraction or ACL).
3. Enter the host only through seams with explicit enabling points.
4. The subsystem owns its anti-corruption layer. Host types never cross it.
5. Characterize the host's behavior at the seam before cutting.
6. Stay releasable at every step. Delete transitional code on schedule.
7. Keep volatile new code out of stable old packages, and don't depend directly on host
   hotspots.
8. Leave stable ugly code alone.
9. Align each wall with one owning team.
10. Define success as a number you will re-measure.
