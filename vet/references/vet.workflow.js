export const meta = {
  name: 'vet',
  description: 'Run a skill repeatedly in isolated worktrees, grade each run against its rubric, and judge how much the runs differ',
  whenToUse: 'Called by the /vet skill, which passes the suite, run settings and agent roles in args',
  phases: [
    { title: 'Run', detail: 'one agent per (prompt, repeat), each in its own git worktree' },
    { title: 'Grade', detail: 'rubric judges: one per run, or one per prompt' },
    { title: 'Compare', detail: 'similarity judges per prompt (or per item), plus cross-prompt structure checks' },
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
//   crossPerPrompt: runs per prompt shown to cross-prompt judges (default 2)
//   outDir:         absolute directory the capture files go in
//   agents:         { preset, run, grade, compare, cross }, see "Agent roles" below
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

// ── Agent roles ─────────────────────────────────────────────────────────────
// Four roles: run (executes the skill), grade (rubric judge), compare
// (similarity across repeats of one prompt), cross (structure across prompts).
// Each role takes model ("session" = inherit), effort, agentType, and the judges
// take batch, which sets how much work one agent does:
//   grade.batch:   run    one judge per run
//                  prompt one judge grades every run of a prompt
//   compare.batch: item   one judge per (prompt, rubric item)
//                  prompt one judge per prompt compares every item
//                  merged the per-prompt grade judge also compares (needs grade.batch prompt)
//   cross.batch:   item   one judge per structure item
//                  all    one judge for every structure item
// A preset fills in batch; anything set explicitly wins.

const PRESETS = {
  thorough: { grade: { batch: 'run' }, compare: { batch: 'item' }, cross: { batch: 'item' } },
  lean: { grade: { batch: 'prompt' }, compare: { batch: 'prompt' }, cross: { batch: 'all' } },
  minimal: { grade: { batch: 'prompt' }, compare: { batch: 'merged' }, cross: { batch: 'all' } },
}
const BATCH = { grade: ['run', 'prompt'], compare: ['item', 'prompt', 'merged'], cross: ['item', 'all'] }
const EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max']
const ROLE_KEYS = ['model', 'effort', 'agentType', 'batch']

const AGENTS_IN = args.agents || {}
const PRESET = AGENTS_IN.preset || 'lean'
if (!PRESETS[PRESET]) throw new Error(`vet: unknown preset "${PRESET}"; use one of ${Object.keys(PRESETS).join(', ')}`)
const AGENTS = {}
for (const role of ['run', 'grade', 'compare', 'cross']) {
  const c = { ...(PRESETS[PRESET][role] || {}), ...(AGENTS_IN[role] || {}) }
  for (const k of Object.keys(c)) {
    if (!ROLE_KEYS.includes(k)) throw new Error(`vet: agents.${role}.${k} is not a setting; use ${ROLE_KEYS.join(', ')}`)
  }
  if (c.effort && !EFFORTS.includes(c.effort)) throw new Error(`vet: agents.${role}.effort must be one of ${EFFORTS.join(', ')}`)
  if (c.batch !== undefined && !(BATCH[role] || []).includes(c.batch)) {
    throw new Error(`vet: agents.${role}.batch "${c.batch}" is not allowed; use ${(BATCH[role] || ['(none)']).join(', ')}`)
  }
  if (c.model === 'session') delete c.model
  if (c.effort === 'session') delete c.effort
  AGENTS[role] = c
}
if (AGENTS.compare.batch === 'merged' && AGENTS.grade.batch !== 'prompt') {
  log('compare.batch "merged" needs grade.batch "prompt"; using that')
  AGENTS.grade.batch = 'prompt'
}

const optsFor = (role, opts) => {
  const c = AGENTS[role]
  const o = { ...opts }
  if (c.model) o.model = c.model
  if (c.effort) o.effort = c.effort
  if (c.agentType) o.agentType = c.agentType
  return o
}

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

const VERDICTS = {
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
}
const CAPTURE_OK = { type: 'boolean', description: 'False if the capture is missing, empty, or summarised instead of verbatim' }

const GRADE_SCHEMA = {
  type: 'object',
  properties: { captureOk: CAPTURE_OK, items: VERDICTS },
  required: ['captureOk', 'items'],
}

const GRADED_RUNS = {
  type: 'array',
  items: {
    type: 'object',
    properties: { label: { type: 'string', description: 'Run label, e.g. "P01#3"' }, captureOk: CAPTURE_OK, items: VERDICTS },
    required: ['label', 'captureOk', 'items'],
  },
}

const GROUPS = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      runs: { type: 'array', items: { type: 'string' }, description: 'Run labels, e.g. "P01#3"' },
      description: { type: 'string', description: 'One line on how this group handles the item' },
    },
    required: ['runs', 'description'],
  },
}
const CLASS = { type: 'string', enum: Object.keys(SIMILARITY) }
const REASON = { type: 'string', description: 'One or two sentences on what differs, or why nothing does' }

const SIM_SCHEMA = {
  type: 'object',
  properties: { groups: GROUPS, class: CLASS, reason: REASON },
  required: ['groups', 'class', 'reason'],
}

const COMPARED_ITEMS = {
  type: 'array',
  items: {
    type: 'object',
    properties: { item: { type: 'string', description: 'Rubric item id, e.g. "R3"' }, groups: GROUPS, class: CLASS, reason: REASON },
    required: ['item', 'groups', 'class', 'reason'],
  },
}

const GRADE_BATCH_SCHEMA = { type: 'object', properties: { runs: GRADED_RUNS }, required: ['runs'] }
const SIM_BATCH_SCHEMA = { type: 'object', properties: { items: COMPARED_ITEMS }, required: ['items'] }
const MERGED_SCHEMA = { type: 'object', properties: { runs: GRADED_RUNS, items: COMPARED_ITEMS }, required: ['runs', 'items'] }

// ── Prompt text ─────────────────────────────────────────────────────────────

const pad2 = (n) => String(n).padStart(2, '0')
const labelOf = (p, r) => `${p.id}#${r}`
const captureOf = (p, r) => `${OUT}/${p.id}-r${pad2(r)}.md`
const invocation = (p) => `/${SKILL.name} ${p.prompt}`.trim()
const captureList = (runs) => runs.map((x) => `- ${x.label}: ${x.capture}`).join('\n')

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

const gradeContext = (p) => `The run was given:
${invocation(p)}
Scripted user replies, in order: ${JSON.stringify(p.replies || [])}

Expected output structure:
${structureText()}

Rubric:
${RUBRIC.map(itemText).join('\n')}`

const GRADE_RULES = `Give every rubric item one verdict, in rubric order:
- met: the pass description holds in full.
- partial: the partial description holds, or the item is only partly satisfied.
- missed: absent or wrong.
- n/a: only when the item's "applies when" condition is false for this run.
Evidence is the shortest verbatim quote from the capture that proves the verdict, or "absent".
When torn between two verdicts, choose the lower one.
Set captureOk to false if the capture is missing, empty, or a summary rather than the verbatim messages.`

const gradePrompt = (p, capture) => `You are grading one run of the Claude Code skill "${SKILL.name}" against a rubric. Judge only what the run produced, not what the skill promises.

Read the run's capture: ${capture}
It holds the transcript of the run and any files the run wrote.

${gradeContext(p)}

${GRADE_RULES}`

const GRADE_EACH = `Grade each run on its own, as if it were the only one. Don't compare runs while grading, and don't let one run's verdicts pull another's. Return one entry per run, using its label.`

const gradeBatchPrompt = (p, runs) => `You are grading ${runs.length} runs of the Claude Code skill "${SKILL.name}" against a rubric. Every run got the same input. Judge only what each run produced, not what the skill promises.

Captures (each holds one run's transcript and any files it wrote):
${captureList(runs)}

${gradeContext(p)}

${GRADE_EACH}

${GRADE_RULES}`

const SIM_STEPS = `1. Group the runs so that runs in one group handle the item the same way: the same content, choices and structure, though the wording may differ. Put every run in exactly one group, using its label. Describe each group in one line.
2. Classify the item across all the runs:
   identical: every run handles it the same way, near word for word.
   equivalent: every run lands on the same substance and choices, in different words.
   minor_drift: the same approach throughout, but details differ (a point added or dropped, a different order, different examples).
   major_drift: some runs differ materially in content or approach, or the item is present in some runs and absent in others.
   contradictory: runs reach incompatible outcomes (opposite choices, conflicting conclusions).
When torn between two classes, choose the less similar one.`

const SAME_INPUT = (p) =>
  `Every run below got the same input, ${JSON.stringify(invocation(p))}, with the same scripted replies. Any difference between them comes from the skill.`
const CROSS_INPUT =
  'The runs below got DIFFERENT inputs, so their content will differ. Ignore content. Compare only the shape each item describes: sections, their order, formats, turn pattern, file layout.'

const simPrompt = (item, runs, scope) => `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across runs, for ONE rubric item. You judge sameness, not quality: ten identical wrong answers are "identical".

${scope}

Rubric item:
${itemText(item)}

Captures (read each one and look only at the part relevant to this item):
${captureList(runs)}

${SIM_STEPS}`

// jobs: [{ item, runs }]. Runs may differ per item (cross-prompt skips runs where an item is n/a).
const uniqueRuns = (runs) => runs.filter((x, i) => runs.findIndex((y) => y.label === x.label) === i)
const simJobsText = (jobs) => {
  const pool = uniqueRuns(jobs.flatMap((j) => j.runs))
  return jobs
    .map((j) => itemText(j.item) + (j.runs.length === pool.length ? '' : `\n   compare only: ${j.runs.map((x) => x.label).join(', ')}`))
    .join('\n')
}

const simBatchPrompt = (jobs, scope) => `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across runs, for EACH rubric item below. You judge sameness, not quality: ten identical wrong answers are "identical".

${scope}

Captures (read each one once):
${captureList(uniqueRuns(jobs.flatMap((j) => j.runs)))}

Rubric items:
${simJobsText(jobs)}

For each item, looking only at the part of each output relevant to that item:
${SIM_STEPS}
Judge each item on its own; don't let one item's class pull another's. Answer every item, in rubric order.`

const mergedPrompt = (p, runs, items) => `You are grading ${runs.length} runs of the Claude Code skill "${SKILL.name}" against a rubric, then checking how consistently it behaved across them. Every run got the same input.

Captures (each holds one run's transcript and any files it wrote; read each one once):
${captureList(runs)}

${gradeContext(p)}

Part 1, grading. ${GRADE_EACH}

${GRADE_RULES}

Part 2, sameness. Only after grading every run: for each of these rubric items, ${items.map((i) => i.id).join(', ')}, compare the runs whose capture is ok. You judge sameness, not quality: ten identical wrong answers are "identical". For each item, looking only at the part of each output relevant to it:
${SIM_STEPS}
Answer every listed item, in rubric order.`

// ── Run, grade, compare ─────────────────────────────────────────────────────

const lostJudges = []
const baseOf = (p, r) => ({ prompt: p.id, repeat: r, label: labelOf(p, r), capture: captureOf(p, r) })
const withGrade = (rec, grade, lostReason) => {
  if (!grade) return { ...rec, excluded: lostReason }
  if (!grade.captureOk) return { ...rec, grade, excluded: 'capture missing or not verbatim' }
  return { ...rec, grade }
}
const verdictOf = (g, id) => {
  const hit = g.grade.items.find((x) => x.id === id)
  return hit ? hit.verdict : null
}

async function runOne(p, r) {
  const base = baseOf(p, r)
  const run = await agent(
    runPrompt(p, r),
    optsFor('run', { label: `run:${base.label}`, phase: 'Run', isolation: 'worktree', schema: RUN_SCHEMA }),
  ).catch(() => null)
  if (!run) return { ...base, excluded: 'run agent died' }
  if (AGENTS.grade.batch !== 'run') return { ...base, run }
  const grade = await agent(
    gradePrompt(p, base.capture),
    optsFor('grade', { label: `grade:${base.label}`, phase: 'Grade', schema: GRADE_SCHEMA }),
  ).catch(() => null)
  return withGrade({ ...base, run }, grade, 'grader died')
}

// Keep a judge's answer for each expected item; anything missing is logged, never scored.
function collect(list, items, scope, label) {
  const byItem = new Map((list || []).map((s) => [s.item, s]))
  const out = []
  for (const item of items) {
    const s = byItem.get(item.id)
    if (!s || !(s.class in SIMILARITY)) {
      lostJudges.push(`${label}/${item.id}`)
      continue
    }
    out.push({ scope, item: item.id, class: s.class, groups: s.groups, reason: s.reason })
  }
  if (!list) log(`${label}: judge died; its items are left out of stability`)
  else if (out.length < items.length) log(`${label}: ${items.length - out.length} item(s) missing from the answer; left out of stability`)
  return out
}

async function compareOne(role, item, runs, scope, scopeLabel) {
  const label = `compare:${scopeLabel}/${item.id}`
  const s = await agent(simPrompt(item, runs, scope), optsFor(role, { label, phase: 'Compare', schema: SIM_SCHEMA })).catch(() => null)
  return collect(s ? [{ item: item.id, ...s }] : null, [item], scopeLabel, label)
}

async function compareBatch(role, jobs, scope, scopeLabel) {
  const label = `compare:${scopeLabel}`
  const out = await agent(simBatchPrompt(jobs, scope), optsFor(role, { label, phase: 'Compare', schema: SIM_BATCH_SCHEMA })).catch(() => null)
  return collect(out && out.items, jobs.map((j) => j.item), scopeLabel, label)
}

// Stage 1 for one prompt: every repeat, then its grading (per run, or one judge for all).
async function runAndGrade(p) {
  let recs = (await parallel(reps.map((r) => () => runOne(p, r)))).map((x, i) => x || { ...baseOf(p, reps[i]), excluded: 'lost' })
  let merged = null
  if (AGENTS.grade.batch === 'prompt') {
    const alive = recs.filter((x) => !x.excluded)
    if (alive.length) {
      const merging = AGENTS.compare.batch === 'merged'
      const label = `${merging ? 'judge' : 'grade'}:${p.id}`
      const out = await agent(
        merging ? mergedPrompt(p, alive, RUBRIC) : gradeBatchPrompt(p, alive),
        optsFor('grade', { label, phase: 'Grade', schema: merging ? MERGED_SCHEMA : GRADE_BATCH_SCHEMA }),
      ).catch(() => null)
      const byLabel = new Map(((out && out.runs) || []).map((g) => [g.label, g]))
      recs = recs.map((x) => (x.excluded ? x : withGrade(x, byLabel.get(x.label) || null, out ? 'grader skipped this run' : 'grader died')))
      if (merging) merged = { label, items: out ? out.items : null }
    }
  }
  log(`${p.id}: ${recs.filter((x) => !x.excluded).length}/${R} runs usable`)
  return { recs, merged }
}

// Stage 2 for one prompt: similarity across its usable runs.
async function compareRuns({ recs, merged }, p) {
  const usable = recs.filter((x) => !x.excluded)
  if (usable.length < 2) {
    log(`${p.id}: ${usable.length} usable runs, too few to compare; skipping its similarity judges`)
    return { prompt: p.id, graded: recs, similarity: [] }
  }
  // An item that is n/a in every run has nothing to compare.
  const items = RUBRIC.filter((item) => usable.some((g) => verdictOf(g, item.id) !== 'n/a'))
  let similarity
  if (AGENTS.compare.batch === 'merged') {
    similarity = collect(merged && merged.items, items, p.id, merged ? merged.label : `judge:${p.id}`)
  } else if (AGENTS.compare.batch === 'prompt') {
    similarity = await compareBatch('compare', items.map((item) => ({ item, runs: usable })), SAME_INPUT(p), p.id)
  } else {
    similarity = (await parallel(items.map((item) => () => compareOne('compare', item, usable, SAME_INPUT(p), p.id)))).filter(Boolean).flat()
  }
  return { prompt: p.id, graded: recs, similarity }
}

const reps = Array.from({ length: R }, (_, i) => i + 1)
const structureItems = RUBRIC.filter((i) => i.kind === 'structure')
const M = PROMPTS.length
const estimate =
  M * R +
  (AGENTS.grade.batch === 'run' ? M * R : M) +
  ({ item: M * RUBRIC.length, prompt: M, merged: 0 })[AGENTS.compare.batch] +
  (structureItems.length ? (AGENTS.cross.batch === 'item' ? structureItems.length : 1) : 0)
log(`vet ${SKILL.name}: preset ${PRESET}, ${M} prompts x ${R} runs = ${M * R} runs, ${RUBRIC.length} rubric items, up to ${estimate} agents`)
log('Runs, grades and comparisons overlap. The Workflow runtime runs up to 16 agents at once (fewer on small machines) and queues the rest.')

const perPrompt = await pipeline(PROMPTS, runAndGrade, compareRuns)

const byPrompt = perPrompt.map(
  (x, i) =>
    x || {
      prompt: PROMPTS[i].id,
      graded: reps.map((r) => ({ ...baseOf(PROMPTS[i], r), excluded: 'lost' })),
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
let cross = []
if (crossJobs.length && AGENTS.cross.batch === 'all') {
  cross = await compareBatch('cross', crossJobs, CROSS_INPUT, 'cross')
} else if (crossJobs.length) {
  cross = (await parallel(crossJobs.map(({ item, runs }) => () => compareOne('cross', item, runs, CROSS_INPUT, 'cross')))).filter(Boolean).flat()
}

// ── Tallies: count how each judgment split the runs ─────────────────────────
// Counted here, not by the judge. A judgment whose groups don't place every
// compared run exactly once is flagged, and its tally is taken over the runs it did place.

const expectedRuns = (s) => {
  if (s.scope === 'cross') {
    const job = crossJobs.find((j) => j.item.id === s.item)
    return job ? job.runs.map((x) => x.label) : []
  }
  const pp = byPrompt.find((x) => x.prompt === s.scope)
  return pp ? pp.graded.filter((g) => !g.excluded).map((g) => g.label) : []
}
const tallyOf = (s) => {
  const expected = expectedRuns(s)
  const seen = s.groups.flatMap((g) => g.runs)
  const counts = s.groups.map((g) => g.runs.length).sort((a, b) => b - a)
  const placed = seen.length
  const clean = placed === expected.length && new Set(seen).size === placed && seen.every((l) => expected.includes(l))
  return {
    counts,
    agreement: placed ? Math.round((1000 * counts[0]) / placed) / 10 : null,
    split: `${counts.join(' / ')} of ${placed}`,
    clean,
  }
}

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
const allSimilarity = within.concat(cross).map((s) => ({ ...s, tally: tallyOf(s) }))
const untidy = allSimilarity.filter((s) => !s.tally.clean)
if (untidy.length) {
  log(`${untidy.length} judgment(s) didn't place every run exactly once: ${untidy.map((s) => `${s.scope}/${s.item}`).join(', ')}`)
}

const quality = pct(wmean(usableRuns.flatMap(qualityPairs)))
const stability = pct(wmean(similarityPairs(allSimilarity)))
const overall = quality === null || stability === null ? null : round1(Math.sqrt(quality * stability))

const runQualities = runs.filter((x) => x.quality !== null).map((x) => x.quality).sort((a, b) => a - b)
const median = (xs) => (xs.length ? (xs.length % 2 ? xs[(xs.length - 1) / 2] : round1((xs[xs.length / 2 - 1] + xs[xs.length / 2]) / 2)) : null)

const items = RUBRIC.map((i) => {
  const values = usableRuns.map((g) => VERDICT[verdictOf(g, i.id)]).filter((v) => v !== undefined)
  const mine = allSimilarity.filter((s) => s.item === i.id && s.scope !== 'cross')
  const crossHit = allSimilarity.find((s) => s.item === i.id && s.scope === 'cross')
  return {
    id: i.id,
    kind: i.kind,
    weight: WEIGHT[i.id],
    criterion: i.criterion,
    passRate: pct(mean(values)),
    stabilityWithin: pct(mean(mine.map((s) => SIMILARITY[s.class]))),
    classesWithin: Object.fromEntries(mine.map((s) => [s.scope, s.class])),
    agreementWithin: round1(mean(mine.map((s) => s.tally.agreement).filter((x) => x !== null))),
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
const effectiveAgents = { preset: PRESET }
for (const role of ['run', 'grade', 'compare', 'cross']) {
  const c = AGENTS[role]
  effectiveAgents[role] = { model: c.model || 'session', effort: c.effort || 'session' }
  if (c.agentType) effectiveAgents[role].agentType = c.agentType
  if (c.batch) effectiveAgents[role].batch = c.batch
}

return {
  config: {
    prompts: PROMPTS.map((p) => p.id),
    runs: R,
    maxTurns: MAX_TURNS,
    crossPerPrompt: CROSS_PER_PROMPT,
    agents: effectiveAgents,
    agentEstimate: estimate,
  },
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
