export const meta = {
  name: 'vet',
  description: 'Run a skill repeatedly in isolated worktrees, grade each run against its rubric, and judge how much the runs differ',
  whenToUse: 'Called by the /vet skill, which passes the suite and run settings in args',
  phases: [
    { title: 'Run', detail: 'one agent per (prompt, repeat), each in its own git worktree' },
    { title: 'Grade', detail: 'one rubric judge per run' },
    { title: 'Compare', detail: 'one similarity judge per (prompt, rubric item), plus cross-prompt structure checks' },
  ],
}

// This script is fixed on purpose. The evaluator should vary as little as the
// skills it scores, so /vet runs this same file every time instead of writing
// a new script per eval.
//
// args: {
//   skill:          { name, dir, file }             absolute paths in the main checkout
//   suite:          { structure, rubric, prompts }  prompts already cut to this run's selection
//   runs:           repeats per prompt (default 10, minimum 2)
//   maxTurns:       assistant turns per run before stopping (default 12)
//   crossPerPrompt: runs per prompt shown to each cross-prompt judge (default 2)
//   outDir:         absolute directory the capture files go in
// }

const SKILL = args && args.skill
const SUITE = args && args.suite
const OUT = args && args.outDir
if (!SKILL || !SUITE || !SUITE.rubric || !SUITE.rubric.length || !SUITE.prompts || !SUITE.prompts.length || !OUT) {
  throw new Error('vet: args needs skill, suite.rubric, suite.prompts and outDir')
}
const RUBRIC = SUITE.rubric
const STRUCTURE = SUITE.structure || { summary: '', elements: [] }
const PROMPTS = SUITE.prompts
const R = Math.max(2, args.runs || 10)
const MAX_TURNS = args.maxTurns || 12
const CROSS_PER_PROMPT = args.crossPerPrompt || 2

// Values behind the scores. n/a verdicts are left out of quality entirely.
const VERDICT = { met: 1, partial: 0.5, missed: 0 }
const SIMILARITY = { identical: 1, equivalent: 0.9, minor_drift: 0.6, major_drift: 0.25, contradictory: 0 }
const WEIGHT = Object.fromEntries(RUBRIC.map((i) => [i.id, i.weight || 1]))

// ── Schemas each agent must return ──────────────────────────────────────────

const RUN_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['completed', 'blocked', 'error'] },
    capture: { type: 'string', description: 'Absolute path of the capture file you wrote' },
    assistantTurns: { type: 'integer' },
    fallbackReplies: { type: 'integer', description: 'How many user replies were [fallback]' },
    filesWritten: { type: 'array', items: { type: 'string' } },
    note: { type: 'string', description: 'One line on what blocked or broke the run; empty if nothing did' },
  },
  required: ['status', 'capture', 'assistantTurns', 'fallbackReplies', 'filesWritten', 'note'],
}

const GRADE_SCHEMA = {
  type: 'object',
  properties: {
    captureOk: { type: 'boolean', description: 'False if the capture is missing, empty, or summarised instead of verbatim' },
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          verdict: { type: 'string', enum: ['met', 'partial', 'missed', 'n/a'] },
          evidence: { type: 'string', description: 'Shortest verbatim quote that proves the verdict, or "absent"' },
        },
        required: ['id', 'verdict', 'evidence'],
      },
    },
  },
  required: ['captureOk', 'items'],
}

const SIM_SCHEMA = {
  type: 'object',
  properties: {
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          runs: { type: 'array', items: { type: 'string' }, description: 'Run labels, e.g. "P01#3"' },
          description: { type: 'string', description: 'One line on how this group handles the item' },
        },
        required: ['runs', 'description'],
      },
    },
    class: { type: 'string', enum: Object.keys(SIMILARITY) },
    reason: { type: 'string', description: 'One or two sentences on what differs, or why nothing does' },
  },
  required: ['groups', 'class', 'reason'],
}

// ── Prompt text ─────────────────────────────────────────────────────────────

const pad2 = (n) => String(n).padStart(2, '0')
const labelOf = (p, r) => `${p.id}#${r}`
const captureOf = (p, r) => `${OUT}/${p.id}-r${pad2(r)}.md`
const invocation = (p) => `/${SKILL.name} ${p.prompt}`.trim()

const repliesText = (p) =>
  p.replies && p.replies.length
    ? p.replies.map((x, i) => `${i + 1}. ${x}`).join('\n')
    : '(none; this skill is not expected to ask anything)'

const structureText = () =>
  [STRUCTURE.summary, ...(STRUCTURE.elements || []).map((e) => `${e.id} ${e.description}`)].filter(Boolean).join('\n')

const itemText = (i) =>
  [
    `${i.id} [${i.kind}, weight ${i.weight || 1}] ${i.criterion}`,
    `   pass: ${i.pass}`,
    `   partial: ${i.partial || 'partly satisfies the pass description'}`,
    `   applies when: ${i.appliesWhen || 'always'}`,
  ].join('\n')

// The part of this prompt that shapes the skill's behaviour is identical for
// every repeat of a prompt. Only the capture path at the end differs.
const runPrompt = (p, r) => `You are running a Claude Code skill for a user, inside a scratch git worktree (your working directory).

Skill: ${SKILL.name}
Instructions: ${SKILL.file}
Read that file first, then any files it points to (resolve relative paths against ${SKILL.dir}). Follow it exactly as if the harness had just loaded it for you. Do not invoke it through the Skill tool. Do not read anything under an evals/ directory.

The user's message is:
${invocation(p)}

The user is not live. Their replies are scripted, in order:
${repliesText(p)}

Whenever the skill would end its turn and wait for the user (a question, a choice, a confirmation, including anything it would ask through an interactive tool), write that message exactly as you would show it, then take the next scripted reply as the user's answer and carry on. If the scripted replies run out and the skill still needs an answer, answer as the user by picking the option marked recommended, or "you decide" if none is, and mark that reply [fallback]. Stop when the skill's work is done, or after ${MAX_TURNS} assistant turns.

Rules:
- Stay inside your working directory. Do not push, open pull requests, post comments, send messages, or change anything outside it, except the capture file below.
- If the skill needs something you don't have (a running app, a connector, a binary), do what you can, say so where the skill would, and report status "blocked".
- Your messages must be exactly what the user would see. Never mention testing, grading or this setup in them.

When the run is over, write the capture file ${captureOf(p, r)} in this shape:

# ${labelOf(p, r)}
## Transcript
### assistant 1
<your first message, verbatim>
### user 1
<the reply you used, verbatim, with [fallback] if it was one>
### assistant 2
...and so on, alternating, until your last message.
## Files
For every file the run created or changed in your worktree (check git status, including untracked files): a "### <path>" heading, then the full content of a new file or the git diff of a changed one, inside a fence longer than any fence it contains. Write "None." if there were none.

Then return the structured result.`

const gradePrompt = (p, capture) => `You are grading one run of the Claude Code skill "${SKILL.name}" against a rubric. Judge only what the run produced, not what the skill promises.

Read the run's capture: ${capture}
It holds the transcript of the run and any files the run wrote.

The run was given:
${invocation(p)}
Scripted user replies, in order: ${JSON.stringify(p.replies || [])}

Expected output structure:
${structureText()}

Rubric:
${RUBRIC.map(itemText).join('\n')}

Give every rubric item one verdict, in rubric order:
- met: the pass description holds in full.
- partial: the partial description holds, or the item is only partly satisfied.
- missed: absent or wrong.
- n/a: only when the item's "applies when" condition is false for this run.
Evidence is the shortest verbatim quote from the capture that proves the verdict, or "absent".
When torn between two verdicts, choose the lower one.
Set captureOk to false if the capture is missing, empty, or a summary rather than the verbatim messages.`

const SAME_INPUT = (p) =>
  `Every run below got the same input, ${JSON.stringify(invocation(p))}, with the same scripted replies. Any difference between them comes from the skill.`
const CROSS_INPUT =
  'The runs below got DIFFERENT inputs, so their content will differ. Ignore content. Compare only the shape this item describes: sections, their order, formats, turn pattern, file layout.'

const simPrompt = (item, runs, scope) => `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across runs, for ONE rubric item. You judge sameness, not quality: ten identical wrong answers are "identical".

${scope}

Rubric item:
${itemText(item)}

Captures (read each one and look only at the part relevant to this item):
${runs.map((x) => `- ${x.label}: ${x.capture}`).join('\n')}

1. Group the runs so that runs in one group handle this item the same way: the same content, choices and structure, though the wording may differ. Put every run in exactly one group, using its label. Describe each group in one line.
2. Classify the item across all the runs:
   identical: every run handles it the same way, near word for word.
   equivalent: every run lands on the same substance and choices, in different words.
   minor_drift: the same approach throughout, but details differ (a point added or dropped, a different order, different examples).
   major_drift: some runs differ materially in content or approach, or the item is present in some runs and absent in others.
   contradictory: runs reach incompatible outcomes (opposite choices, conflicting conclusions).
When torn between two classes, choose the less similar one.`

// ── Run, grade, compare ─────────────────────────────────────────────────────

async function runAndGrade(p, r) {
  const base = { prompt: p.id, repeat: r, label: labelOf(p, r), capture: captureOf(p, r) }
  const run = await agent(runPrompt(p, r), {
    label: `run:${base.label}`,
    phase: 'Run',
    isolation: 'worktree',
    schema: RUN_SCHEMA,
  })
  if (!run) return { ...base, excluded: 'run agent died' }
  const grade = await agent(gradePrompt(p, base.capture), {
    label: `grade:${base.label}`,
    phase: 'Grade',
    schema: GRADE_SCHEMA,
  })
  if (!grade) return { ...base, run, excluded: 'grader died' }
  if (!grade.captureOk) return { ...base, run, grade, excluded: 'capture missing or not verbatim' }
  return { ...base, run, grade }
}

const verdictOf = (g, id) => {
  const hit = g.grade.items.find((x) => x.id === id)
  return hit ? hit.verdict : null
}

const lostJudges = []
async function compareOne(item, runs, scope, scopeLabel) {
  const label = `compare:${scopeLabel}/${item.id}`
  const s = await agent(simPrompt(item, runs, scope), { label, phase: 'Compare', schema: SIM_SCHEMA }).catch(() => null)
  if (!s) {
    lostJudges.push(label)
    log(`${label}: judge died; this item/scope is left out of stability`)
    return null
  }
  return { scope: scopeLabel, item: item.id, class: s.class, groups: s.groups, reason: s.reason }
}

const reps = Array.from({ length: R }, (_, i) => i + 1)
const structureItems = RUBRIC.filter((i) => i.kind === 'structure')
log(
  `vet ${SKILL.name}: ${PROMPTS.length} prompts x ${R} runs = ${PROMPTS.length * R} runs, ` +
    `${RUBRIC.length} rubric items, up to ${PROMPTS.length * R * 2 + PROMPTS.length * RUBRIC.length + structureItems.length} agents`,
)

const perPrompt = await pipeline(
  PROMPTS,
  // Stage 1: run and grade every repeat of this prompt. This waits for all
  // repeats of one prompt (not all prompts): the similarity judges need them together.
  (p) =>
    parallel(reps.map((r) => () => runAndGrade(p, r))).then((xs) =>
      xs.map((x, i) => x || { prompt: p.id, repeat: reps[i], label: labelOf(p, reps[i]), capture: captureOf(p, reps[i]), excluded: 'lost' }),
    ),
  // Stage 2: one similarity judge per rubric item across this prompt's usable runs.
  async (graded, p) => {
    const usable = graded.filter((g) => !g.excluded)
    if (usable.length < 2) {
      log(`${p.id}: ${usable.length} usable runs, too few to compare; skipping its similarity judges`)
      return { prompt: p.id, graded, similarity: [] }
    }
    // An item that is n/a in every run has nothing to compare.
    const items = RUBRIC.filter((item) => usable.some((g) => verdictOf(g, item.id) !== 'n/a'))
    const similarity = await parallel(items.map((item) => () => compareOne(item, usable, SAME_INPUT(p), p.id)))
    return { prompt: p.id, graded, similarity: similarity.filter(Boolean) }
  },
)

const byPrompt = perPrompt.map(
  (x, i) =>
    x || {
      prompt: PROMPTS[i].id,
      graded: reps.map((r) => ({ prompt: PROMPTS[i].id, repeat: r, label: labelOf(PROMPTS[i], r), capture: captureOf(PROMPTS[i], r), excluded: 'lost' })),
      similarity: [],
    },
)
const allRuns = byPrompt.flatMap((x) => x.graded)
const usableRuns = allRuns.filter((g) => !g.excluded)

// Cross-prompt: structure items only, on the first few usable runs of each prompt
// where the item applies. This needs every prompt's runs, so it waits for the pipeline.
const crossRunsFor = (item) =>
  byPrompt.flatMap((x) => x.graded.filter((g) => !g.excluded && verdictOf(g, item.id) !== 'n/a').slice(0, CROSS_PER_PROMPT))
const crossJobs = structureItems
  .map((item) => ({ item, runs: crossRunsFor(item) }))
  .filter((j) => new Set(j.runs.map((g) => g.prompt)).size > 1)
if (crossJobs.length < structureItems.length) {
  log(`cross-prompt check: ${structureItems.length - crossJobs.length} structure item(s) skipped; they have usable runs from fewer than two prompts`)
}
const cross = (await parallel(crossJobs.map(({ item, runs }) => () => compareOne(item, runs, CROSS_INPUT, 'cross')))).filter(Boolean)

// ── Scores (plain arithmetic, no judge involved) ────────────────────────────

const round1 = (x) => (x === null ? null : Math.round(x * 10) / 10)
const wmean = (pairs) => {
  const w = pairs.reduce((s, [wt]) => s + wt, 0)
  return w ? pairs.reduce((s, [wt, v]) => s + wt * v, 0) / w : null
}
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null)
const pct = (x) => (x === null ? null : round1(100 * x))
const letter = (x) => (x === null ? null : x >= 90 ? 'A' : x >= 80 ? 'B' : x >= 70 ? 'C' : x >= 60 ? 'D' : 'F')

// (weight, value) pairs for one run's applicable verdicts
const qualityPairs = (g) =>
  RUBRIC.map((i) => [WEIGHT[i.id], VERDICT[verdictOf(g, i.id)]]).filter(([, v]) => v !== undefined)
const similarityPairs = (list) => list.filter((s) => s.item in WEIGHT).map((s) => [WEIGHT[s.item], SIMILARITY[s.class]])

const runs = allRuns.map((g) => ({
  label: g.label,
  prompt: g.prompt,
  repeat: g.repeat,
  capture: g.capture,
  status: g.run ? g.run.status : null,
  note: g.run ? g.run.note : '',
  quality: g.excluded ? null : pct(wmean(qualityPairs(g))),
  verdicts: g.grade ? g.grade.items : [],
  excluded: g.excluded || null,
}))

const within = byPrompt.flatMap((x) => x.similarity)
const allSimilarity = within.concat(cross)

const quality = pct(wmean(usableRuns.flatMap(qualityPairs)))
const stability = pct(wmean(similarityPairs(allSimilarity)))
const overall = quality === null || stability === null ? null : round1(Math.sqrt(quality * stability))

const runQualities = runs.filter((x) => x.quality !== null).map((x) => x.quality).sort((a, b) => a - b)
const median = (xs) => (xs.length ? (xs.length % 2 ? xs[(xs.length - 1) / 2] : round1((xs[xs.length / 2 - 1] + xs[xs.length / 2]) / 2)) : null)

const items = RUBRIC.map((i) => {
  const values = usableRuns.map((g) => VERDICT[verdictOf(g, i.id)]).filter((v) => v !== undefined)
  const mine = within.filter((s) => s.item === i.id)
  const crossHit = cross.find((s) => s.item === i.id)
  return {
    id: i.id,
    kind: i.kind,
    weight: WEIGHT[i.id],
    criterion: i.criterion,
    passRate: pct(mean(values)),
    stabilityWithin: pct(mean(mine.map((s) => SIMILARITY[s.class]))),
    classesWithin: Object.fromEntries(mine.map((s) => [s.scope, s.class])),
    stabilityCross: crossHit ? pct(SIMILARITY[crossHit.class]) : null,
    classCross: crossHit ? crossHit.class : null,
  }
})

const prompts = byPrompt.map((x) => {
  const mine = x.graded.filter((g) => !g.excluded)
  return {
    id: x.prompt,
    usableRuns: mine.length,
    quality: pct(wmean(mine.flatMap(qualityPairs))),
    stability: pct(wmean(similarityPairs(x.similarity))),
  }
})

const usableShare = allRuns.length ? usableRuns.length / allRuns.length : 0

return {
  config: { prompts: PROMPTS.map((p) => p.id), runs: R, maxTurns: MAX_TURNS, crossPerPrompt: CROSS_PER_PROMPT },
  scores: {
    quality,
    stability,
    overall,
    grade: letter(overall),
    confidence: usableShare >= 0.8 ? 'normal' : 'low',
    usableRuns: usableRuns.length,
    totalRuns: allRuns.length,
  },
  qualitySpread: {
    min: runQualities.length ? runQualities[0] : null,
    median: median(runQualities),
    max: runQualities.length ? runQualities[runQualities.length - 1] : null,
  },
  items,
  prompts,
  runs,
  similarity: allSimilarity,
  excluded: runs.filter((x) => x.excluded).map((x) => ({ label: x.label, reason: x.excluded })),
  lostJudges,
}
