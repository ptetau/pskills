export const meta = {
  name: 'vet',
  description: 'Run a skill repeatedly in isolated worktrees, grade each run against its rubric, and judge how much the runs differ, with a grade that settles wave by wave',
  whenToUse: 'Called by the /vet skill, which passes the suite, run settings and agent roles in args',
  phases: [
    { title: 'Run', detail: 'one agent per (prompt, repeat), each in its own git worktree, in waves' },
    { title: 'Grade', detail: 'rubric judges: one per run, or one per prompt per wave' },
    { title: 'Compare', detail: 'similarity judges place each wave of runs into groups; cross-prompt structure check at the end' },
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
//   wave:           repeats per prompt per wave (default 2); the grade is updated after each wave
//   settle:         { delta, patience, stop }       see "Settling" below
//   maxTurns:       assistant turns per run before stopping (default 12)
//   crossPerPrompt: runs per prompt shown to cross-prompt judges (default 2)
//   agents:         { preset, run, grade, compare, cross }, see "Agent roles" below
// }

const SKILL = args && args.skill
const SUITE = args && args.suite
if (!SKILL || !SUITE || !SUITE.rubric || !SUITE.rubric.length || !SUITE.prompts || !SUITE.prompts.length) {
  throw new Error('vet: args needs skill, suite.rubric and suite.prompts')
}
const RUBRIC = SUITE.rubric
const STRUCTURE = SUITE.structure || { summary: '', elements: [] }
const PROMPTS = SUITE.prompts
const R = Math.max(2, args.runs || 10)
const W = Math.max(1, Math.min(R, args.wave || 2))
const WAVES = Math.ceil(R / W)
const MAX_TURNS = args.maxTurns || 12
const CROSS_PER_PROMPT = args.crossPerPrompt || 2

// Settling: after every wave the running grade is recorded. It has settled once
// the overall score has moved no more than `delta` points in each of the last
// `patience` waves without changing letter. With `stop`, no new wave starts
// once it has settled.
const SETTLE = { delta: 2, patience: 2, stop: false, ...(args.settle || {}) }

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
//                  prompt one judge per prompt per wave
//   compare.batch: item   one judge per (prompt, rubric item) per wave
//                  prompt one judge per prompt per wave, covering every item
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
  if (c.effort && c.effort !== 'session' && !EFFORTS.includes(c.effort)) {
    throw new Error(`vet: agents.${role}.effort must be one of session, ${EFFORTS.join(', ')}`)
  }
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
const MERGED = AGENTS.compare.batch === 'merged'

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
    capture: { type: 'string', description: 'Absolute path of the capture file you wrote inside your working directory' },
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
const GRADE_SCHEMA = { type: 'object', properties: { captureOk: CAPTURE_OK, items: VERDICTS }, required: ['captureOk', 'items'] }
const GRADED_RUNS = {
  type: 'array',
  items: {
    type: 'object',
    properties: { label: { type: 'string', description: 'Run label, e.g. "P01#3"' }, captureOk: CAPTURE_OK, items: VERDICTS },
    required: ['label', 'captureOk', 'items'],
  },
}
const GRADE_BATCH_SCHEMA = { type: 'object', properties: { runs: GRADED_RUNS }, required: ['runs'] }

const CLASS = { type: 'string', enum: Object.keys(SIMILARITY) }
const REASON = { type: 'string', description: 'One or two sentences on what differs, or why nothing does' }

// Incremental placement: the judge puts each new run into an existing group or a
// new one, and classifies the item across all runs so far. The script keeps the groups.
const PLACED_ITEMS = {
  type: 'array',
  items: {
    type: 'object',
    properties: {
      item: { type: 'string', description: 'Rubric item id, e.g. "R3"' },
      place: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            run: { type: 'string', description: 'Run label, e.g. "P01#7"' },
            group: { type: 'string', description: 'An existing group id, or the id of a new group defined in newGroups' },
          },
          required: ['run', 'group'],
        },
      },
      newGroups: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id: { type: 'string', description: 'Starts with "new", e.g. "new1"' },
            description: { type: 'string', description: 'One line on how this group handles the item' },
          },
          required: ['id', 'description'],
        },
      },
      class: CLASS,
      reason: REASON,
    },
    required: ['item', 'place', 'newGroups', 'class', 'reason'],
  },
}
const PLACE_SCHEMA = { type: 'object', properties: { items: PLACED_ITEMS }, required: ['items'] }
const MERGED_SCHEMA = { type: 'object', properties: { runs: GRADED_RUNS, items: PLACED_ITEMS }, required: ['runs', 'items'] }

// Cross-prompt judgments are one-shot, so the judge draws the groups itself.
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
const SIM_SCHEMA = { type: 'object', properties: { groups: GROUPS, class: CLASS, reason: REASON }, required: ['groups', 'class', 'reason'] }
const SIM_BATCH_SCHEMA = {
  type: 'object',
  properties: {
    items: {
      type: 'array',
      items: {
        type: 'object',
        properties: { item: { type: 'string' }, groups: GROUPS, class: CLASS, reason: REASON },
        required: ['item', 'groups', 'class', 'reason'],
      },
    },
  },
  required: ['items'],
}

// ── Prompt text ─────────────────────────────────────────────────────────────

// Each run writes its capture inside its own worktree (isolated agents can't
// write outside it) and reports the absolute path. Judges read it from there;
// /vet copies the captures into evals/<skill>/runs/<runId>/outputs/ afterwards.
const pad2 = (n) => String(n).padStart(2, '0')
const labelOf = (p, r) => `${p.id}#${r}`
const captureName = (p, r) => `.vet-capture/${p.id}-r${pad2(r)}.md`
const CAPTURES = {}
const captureOfLabel = (label) => CAPTURES[label] || '(capture path not reported)'
const invocation = (p) => `/${SKILL.name} ${p.prompt}`.trim()
const captureList = (labels) => labels.map((l) => `- ${l}: ${captureOfLabel(l)}`).join('\n')
const uniq = (xs) => xs.filter((x, i) => xs.indexOf(x) === i)

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
- Stay inside your working directory: write every file there, scratch files included. Do not push, open pull requests, post comments, send messages, or change anything outside it.
- If the skill needs something you don't have (a running app, a connector, a binary), do what you can, say so where the skill would, and report status "blocked".
- Your messages must be exactly what the user would see. Never mention testing, grading or this setup in them.

When the run is over, write the capture file ${captureName(p, r)} inside your working directory, in this shape:

# ${labelOf(p, r)}
## Transcript
### assistant 1
<your first message, verbatim>
### user 1
<the reply you used, verbatim, with [fallback] if it was one>
### assistant 2
...and so on, alternating, until your last message.
## Files
For every file the run created or changed in your worktree (check git status, including untracked files, but leave out .vet-capture/ and your own scratch files): a "### <path>" heading, then the full content of a new file or the git diff of a changed one, inside a fence longer than any fence it contains. Write "None." if there were none.

Then return the structured result, with capture set to the capture file's absolute path.`

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

const GRADE_EACH = `Grade each run on its own, as if it were the only one. Don't compare runs while grading, and don't let one run's verdicts pull another's. Return one entry per run, using its label.`

const gradePrompt = (p, capture) => `You are grading one run of the Claude Code skill "${SKILL.name}" against a rubric. Judge only what the run produced, not what the skill promises.

Read the run's capture: ${capture}
It holds the transcript of the run and any files the run wrote.

${gradeContext(p)}

${GRADE_RULES}`

const gradeBatchPrompt = (p, labels) => `You are grading ${labels.length} runs of the Claude Code skill "${SKILL.name}" against a rubric. Every run got the same input. Judge only what each run produced, not what the skill promises.

Captures (each holds one run's transcript and any files it wrote):
${captureList(labels)}

${gradeContext(p)}

${GRADE_EACH}

${GRADE_RULES}`

const CLASSES = `   identical: every run handles it the same way, near word for word.
   equivalent: every run lands on the same substance and choices, in different words.
   minor_drift: the same approach throughout, but details differ (a point added or dropped, a different order, different examples).
   major_drift: some runs differ materially in content or approach, or the item is present in some runs and absent in others.
   contradictory: runs reach incompatible outcomes (opposite choices, conflicting conclusions).
When torn between two classes, choose the less similar one.`

const SIM_STEPS = `1. Group the runs so that runs in one group handle the item the same way: the same content, choices and structure, though the wording may differ. Put every run in exactly one group, using its label. Describe each group in one line.
2. Classify the item across all the runs:
${CLASSES}`

const PLACE_STEPS = `For each item, place every run listed under "place":
- Put it in an existing group if it handles the item the same way as that group's example run: the same content, choices and structure, though the wording may differ.
- Otherwise put it in a new group. Define each new group under newGroups with an id starting with "new" (new1, new2, ...) and a one-line description. Runs placed in the same new group must match each other.
- When torn between an existing group and a new one, choose the new one.
Then classify the item across ALL runs so far, counting the groups as they stand after your placements:
${CLASSES}
Judge each item on its own; don't let one item's class pull another's. Answer every listed item.`

const SAME_INPUT = (p) =>
  `Every run below got the same input, ${JSON.stringify(invocation(p))}, with the same scripted replies. Any difference between them comes from the skill.`
const CROSS_INPUT =
  'The runs below got DIFFERENT inputs, so their content will differ. Ignore content. Compare only the shape each item describes: sections, their order, formats, turn pattern, file layout.'

const groupLine = (g) => `${g.id} (${g.runs.length} run${g.runs.length === 1 ? '' : 's'}, example ${g.runs[0]}): ${g.description}`
const jobText = (j) =>
  [
    itemText(j.item),
    j.groups.length ? `   existing groups:\n${j.groups.map((g) => `     ${groupLine(g)}`).join('\n')}` : '   existing groups: none yet',
    `   place: ${j.unplaced.join(', ')}`,
  ].join('\n')
const exampleLabels = (jobs) => uniq(jobs.flatMap((j) => j.groups.map((g) => g.runs[0])))

const placePrompt = (p, jobs, k) => {
  const examples = exampleLabels(jobs)
  const fresh = uniq(jobs.flatMap((j) => j.unplaced)).filter((l) => !examples.includes(l))
  return `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across repeated runs, wave ${k} of up to ${WAVES}. You judge sameness, not quality: ten identical wrong answers are "identical".

${SAME_INPUT(p)}

Captures to read (each once):
${examples.length ? `Example runs of the existing groups:\n${captureList(examples)}\n` : ''}Runs to place:
${captureList(fresh)}

Rubric items:
${jobs.map(jobText).join('\n')}

${PLACE_STEPS}`
}

const mergedPrompt = (p, newLabels, jobs, k) => {
  const examples = exampleLabels(jobs).filter((l) => !newLabels.includes(l))
  const pending = uniq(jobs.flatMap((j) => j.unplaced)).filter((l) => !newLabels.includes(l) && !examples.includes(l))
  return `You are grading ${newLabels.length} new run(s) of the Claude Code skill "${SKILL.name}" against a rubric, then checking how consistently it behaves across all runs so far (wave ${k} of up to ${WAVES}). Every run got the same input.

Runs to grade and place:
${captureList(newLabels)}
${examples.length || pending.length ? `Earlier runs, for comparison only (don't grade them):\n${captureList(examples.concat(pending))}\n` : ''}
${gradeContext(p)}

Part 1, grading. Grade only the runs to grade. ${GRADE_EACH}

${GRADE_RULES}

Part 2, sameness. Only after grading: place the runs below, leaving out any run whose capture is not ok. You judge sameness, not quality: ten identical wrong answers are "identical".

Rubric items:
${jobs.map(jobText).join('\n')}

${PLACE_STEPS}`
}

const simPrompt = (item, labels, scope) => `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across runs, for ONE rubric item. You judge sameness, not quality: ten identical wrong answers are "identical".

${scope}

Rubric item:
${itemText(item)}

Captures (read each one and look only at the part relevant to this item):
${captureList(labels)}

${SIM_STEPS}`

const simBatchPrompt = (jobs, scope) => {
  const pool = uniq(jobs.flatMap((j) => j.labels))
  return `You are checking how consistently the Claude Code skill "${SKILL.name}" behaves across runs, for EACH rubric item below. You judge sameness, not quality: ten identical wrong answers are "identical".

${scope}

Captures (read each one once):
${captureList(pool)}

Rubric items:
${jobs.map((j) => itemText(j.item) + (j.labels.length === pool.length ? '' : `\n   compare only: ${j.labels.join(', ')}`)).join('\n')}

For each item, looking only at the part of each output relevant to that item:
${SIM_STEPS}
Judge each item on its own; don't let one item's class pull another's. Answer every item, in rubric order.`
}

// ── State ───────────────────────────────────────────────────────────────────

const lostJudges = []
const S = Object.fromEntries(
  PROMPTS.map((p) => [p.id, { p, recs: [], groups: {}, nextGroup: {}, classHist: {}, waveDone: 0, finished: false }]),
)
const repsOfWave = (k) => Array.from({ length: Math.min(R, k * W) - (k - 1) * W }, (_, i) => (k - 1) * W + i + 1)
const baseOf = (p, r) => ({ prompt: p.id, repeat: r, label: labelOf(p, r), capture: null })
const withGrade = (rec, grade, lostReason) => {
  if (!grade) return { ...rec, excluded: lostReason }
  if (!grade.captureOk) return { ...rec, grade, excluded: 'capture missing or not verbatim' }
  return { ...rec, grade }
}
const verdictOf = (g, id) => {
  const hit = g.grade && g.grade.items.find((x) => x.id === id)
  return hit ? hit.verdict : null
}
const usableOf = (st) => st.recs.filter((x) => !x.excluded)
const applicable = (runs) => RUBRIC.filter((item) => runs.some((g) => verdictOf(g, item.id) !== 'n/a'))

// Jobs: for each item, the groups so far and the usable runs not yet placed in them.
const jobsFor = (st, labels, items) =>
  items
    .map((item) => {
      const groups = st.groups[item.id] || []
      const placed = new Set(groups.flatMap((g) => g.runs))
      return { item, groups, unplaced: labels.filter((l) => !placed.has(l)) }
    })
    .filter((j) => j.unplaced.length)

function applyPlacement(st, job, ans, k, label) {
  const tag = `${label}/${job.item.id}`
  if (!ans || !(ans.class in SIMILARITY)) {
    lostJudges.push(tag)
    log(`${tag}: no answer; its runs are offered again next wave`)
    return
  }
  const groups = (st.groups[job.item.id] = st.groups[job.item.id] || [])
  const rename = {}
  for (const g of ans.newGroups || []) {
    if (rename[g.id]) continue
    st.nextGroup[job.item.id] = (st.nextGroup[job.item.id] || 0) + 1
    rename[g.id] = `g${st.nextGroup[job.item.id]}`
    groups.push({ id: rename[g.id], description: g.description, runs: [] })
  }
  const allowed = new Set(job.unplaced)
  const done = new Set()
  for (const a of ans.place || []) {
    const g = groups.find((x) => x.id === (rename[a.group] || a.group))
    if (!g || !allowed.has(a.run) || done.has(a.run)) continue
    g.runs.push(a.run)
    done.add(a.run)
  }
  st.groups[job.item.id] = groups.filter((g) => g.runs.length)
  st.classHist[job.item.id] = (st.classHist[job.item.id] || []).concat({ wave: k, class: ans.class, reason: ans.reason })
  if (done.size < job.unplaced.length) {
    log(`${tag}: ${job.unplaced.length - done.size} run(s) not placed; offered again next wave`)
  }
}

// ── Run, grade, compare one wave ────────────────────────────────────────────

async function runOne(p, r) {
  const base = baseOf(p, r)
  const run = await agent(
    runPrompt(p, r),
    optsFor('run', { label: `run:${base.label}`, phase: 'Run', isolation: 'worktree', schema: RUN_SCHEMA }),
  ).catch(() => null)
  if (!run) return { ...base, excluded: 'run agent died' }
  if (!run.capture || !run.capture.startsWith('/')) return { ...base, run, excluded: 'capture path not reported' }
  CAPTURES[base.label] = run.capture
  base.capture = run.capture
  if (AGENTS.grade.batch !== 'run') return { ...base, run }
  const grade = await agent(
    gradePrompt(p, base.capture),
    optsFor('grade', { label: `grade:${base.label}`, phase: 'Grade', schema: GRADE_SCHEMA }),
  ).catch(() => null)
  return withGrade({ ...base, run }, grade, 'grader died')
}

const startWave = (p, k) =>
  parallel(repsOfWave(k).map((r) => () => runOne(p, r))).then((xs) =>
    xs.map((x, i) => x || { ...baseOf(p, repsOfWave(k)[i]), excluded: 'lost' }),
  )

async function judgeWave(p, k, recs) {
  const st = S[p.id]
  if (AGENTS.grade.batch === 'prompt') {
    const alive = recs.filter((x) => !x.excluded).map((x) => x.label)
    if (alive.length) {
      const label = `${MERGED ? 'judge' : 'grade'}:${p.id}@w${k}`
      const jobs = MERGED ? jobsFor(st, usableOf(st).map((x) => x.label).concat(alive), RUBRIC) : null
      const out = await agent(
        MERGED ? mergedPrompt(p, alive, jobs, k) : gradeBatchPrompt(p, alive),
        optsFor('grade', { label, phase: 'Grade', schema: MERGED ? MERGED_SCHEMA : GRADE_BATCH_SCHEMA }),
      ).catch(() => null)
      const byLabel = new Map(((out && out.runs) || []).map((g) => [g.label, g]))
      recs = recs.map((x) => (x.excluded ? x : withGrade(x, byLabel.get(x.label) || null, out ? 'grader skipped this run' : 'grader died')))
      if (MERGED) {
        const usable = new Set(usableOf(st).concat(recs.filter((x) => !x.excluded)).map((x) => x.label))
        const answers = new Map(((out && out.items) || []).map((a) => [a.item, a]))
        for (const job of jobs) {
          const unplaced = job.unplaced.filter((l) => usable.has(l))
          if (unplaced.length) applyPlacement(st, { ...job, unplaced }, answers.get(job.item.id) || null, k, label)
        }
      }
    }
  }
  st.recs.push(...recs)
  if (MERGED) return

  const usable = usableOf(st)
  if (usable.length < 2) return
  const jobs = jobsFor(st, usable.map((x) => x.label), applicable(usable))
  if (!jobs.length) return
  if (AGENTS.compare.batch === 'prompt') {
    const label = `compare:${p.id}@w${k}`
    const out = await agent(placePrompt(p, jobs, k), optsFor('compare', { label, phase: 'Compare', schema: PLACE_SCHEMA })).catch(() => null)
    const answers = new Map(((out && out.items) || []).map((a) => [a.item, a]))
    for (const job of jobs) applyPlacement(st, job, answers.get(job.item.id) || null, k, label)
  } else {
    await parallel(
      jobs.map((job) => async () => {
        const label = `compare:${p.id}@w${k}`
        const out = await agent(
          placePrompt(p, [job], k),
          optsFor('compare', { label: `${label}/${job.item.id}`, phase: 'Compare', schema: PLACE_SCHEMA }),
        ).catch(() => null)
        applyPlacement(st, job, out && (out.items || []).find((a) => a.item === job.item.id), k, label)
      }),
    )
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
const qualityPairs = (g) =>
  RUBRIC.map((i) => [WEIGHT[i.id], VERDICT[verdictOf(g, i.id)]]).filter(([, v]) => v !== undefined)
const similarityPairs = (list) => list.filter((s) => s.item in WEIGHT).map((s) => [WEIGHT[s.item], SIMILARITY[s.class]])

// The within-prompt judgments as of wave k (all waves when k is null): the latest
// class per applicable item, for prompts with at least two usable runs by then.
function withinAt(k) {
  const out = []
  for (const pr of PROMPTS) {
    const st = S[pr.id]
    const runs = usableOf(st).filter((g) => k === null || g.repeat <= k * W)
    if (runs.length < 2) continue
    for (const item of applicable(runs)) {
      const hist = (st.classHist[item.id] || []).filter((h) => k === null || h.wave <= k)
      if (!hist.length) continue
      const last = hist[hist.length - 1]
      out.push({ scope: pr.id, item: item.id, class: last.class, reason: last.reason })
    }
  }
  return out
}

function scoresAt(k, cross) {
  const runs = PROMPTS.flatMap((pr) => usableOf(S[pr.id]).filter((g) => k === null || g.repeat <= k * W))
  const sims = withinAt(k).concat(cross || [])
  const quality = pct(wmean(runs.flatMap(qualityPairs)))
  const stability = pct(wmean(similarityPairs(sims)))
  const overall = quality === null || stability === null ? null : round1(Math.sqrt(quality * stability))
  return { usable: runs.length, quality, stability, overall, grade: letter(overall) }
}

// ── Settling ────────────────────────────────────────────────────────────────

const trajectory = []
let settledAt = null
const checkpointWaiters = []
const waitForCheckpoint = (k) =>
  trajectory.length >= k ? Promise.resolve() : new Promise((resolve) => checkpointWaiters.push({ k, resolve }))

function isSettled() {
  const n = trajectory.length
  if (n <= SETTLE.patience) return false
  const recent = trajectory.slice(n - SETTLE.patience - 1)
  if (recent.some((t) => t.overall === null)) return false
  const sameLetter = recent.every((t) => t.grade === recent[0].grade)
  const small = recent.slice(1).every((t, i) => Math.abs(t.overall - recent[i].overall) <= SETTLE.delta)
  return sameLetter && small
}

function recordCheckpoint(k) {
  const s = scoresAt(k, null)
  const prev = trajectory[trajectory.length - 1]
  const moved = prev && prev.overall !== null && s.overall !== null ? round1(s.overall - prev.overall) : null
  trajectory.push({ wave: k, runsPerPrompt: Math.min(R, k * W), ...s, moved })
  const settled = isSettled()
  if (settled && settledAt === null) settledAt = k
  if (!settled) settledAt = null
  const fmt = (x) => (x === null ? '-' : x)
  log(
    `wave ${k}/${WAVES} (${Math.min(R, k * W)} of ${R} runs per prompt): quality ${fmt(s.quality)} · stability ${fmt(s.stability)} · ` +
      `overall ${fmt(s.overall)} (${s.grade || '-'})${moved === null ? '' : ` · moved ${moved >= 0 ? '+' : ''}${moved}`} · ${settled ? 'settled' : 'settling'}`,
  )
}

function bumpCheckpoints() {
  const sts = PROMPTS.map((pr) => S[pr.id])
  const furthest = Math.max(...sts.map((st) => st.waveDone))
  const reached = Math.min(...sts.map((st) => (st.finished ? furthest : st.waveDone)))
  while (trajectory.length < reached) recordCheckpoint(trajectory.length + 1)
  for (const w of checkpointWaiters.filter((x) => x.k <= trajectory.length)) w.resolve()
}

async function promptLoop(p) {
  const st = S[p.id]
  try {
    let pending = startWave(p, 1)
    for (let k = 1; k <= WAVES; k++) {
      const recs = await pending
      // Queue this wave's judges before the next wave's runs, so the grade keeps up.
      const judging = judgeWave(p, k, recs)
      if (k < WAVES && !SETTLE.stop) pending = startWave(p, k + 1)
      await judging
      st.waveDone = k
      bumpCheckpoints()
      if (k < WAVES && SETTLE.stop) {
        await waitForCheckpoint(k)
        if (settledAt !== null) break
        pending = startWave(p, k + 1)
      }
    }
  } catch (e) {
    log(`${p.id}: stopped after an error in wave ${st.waveDone + 1}`)
  } finally {
    st.finished = true
    bumpCheckpoints()
  }
}

const structureItems = RUBRIC.filter((i) => i.kind === 'structure')
const M = PROMPTS.length
const estimate =
  M * R +
  (AGENTS.grade.batch === 'run' ? M * R : M * WAVES) +
  ({ item: M * RUBRIC.length * WAVES, prompt: M * WAVES, merged: 0 })[AGENTS.compare.batch] +
  (structureItems.length ? (AGENTS.cross.batch === 'item' ? structureItems.length : 1) : 0)
log(
  `vet ${SKILL.name}: preset ${PRESET}, ${M} prompts x ${R} runs in waves of ${W} (${WAVES} waves), ` +
    `${RUBRIC.length} rubric items, up to ${estimate} agents${SETTLE.stop ? '; stops early once the grade settles' : ''}`,
)
log('The grade is recorded after each wave. Up to min(16, CPU cores - 2) agents run at once; the rest queue.')

await parallel(PROMPTS.map((p) => () => promptLoop(p)))

if (settledAt !== null && SETTLE.stop && trajectory.length < WAVES) {
  log(`stopped early: the grade settled at wave ${settledAt}`)
}

// ── Cross-prompt structure check (once, at the end) ─────────────────────────

const crossRunsFor = (item) =>
  PROMPTS.flatMap((pr) =>
    usableOf(S[pr.id])
      .filter((g) => verdictOf(g, item.id) !== 'n/a')
      .sort((a, b) => a.repeat - b.repeat)
      .slice(0, CROSS_PER_PROMPT),
  )
const crossJobs = structureItems
  .map((item) => ({ item, runs: crossRunsFor(item) }))
  .filter((j) => new Set(j.runs.map((g) => g.prompt)).size > 1)
  .map((j) => ({ ...j, labels: j.runs.map((g) => g.label) }))
if (crossJobs.length < structureItems.length) {
  log(`cross-prompt check: ${structureItems.length - crossJobs.length} structure item(s) skipped; they have usable runs from fewer than two prompts`)
}

function collectCross(list, jobs, label) {
  const byItem = new Map((list || []).map((s) => [s.item, s]))
  const out = []
  for (const j of jobs) {
    const s = byItem.get(j.item.id)
    if (!s || !(s.class in SIMILARITY)) {
      lostJudges.push(`${label}/${j.item.id}`)
      continue
    }
    out.push({ scope: 'cross', item: j.item.id, class: s.class, groups: s.groups, reason: s.reason })
  }
  if (!list) log(`${label}: judge died; cross-prompt items are left out of stability`)
  return out
}

let cross = []
if (crossJobs.length && AGENTS.cross.batch === 'all') {
  const out = await agent(simBatchPrompt(crossJobs, CROSS_INPUT), optsFor('cross', { label: 'compare:cross', phase: 'Compare', schema: SIM_BATCH_SCHEMA })).catch(() => null)
  cross = collectCross(out && out.items, crossJobs, 'compare:cross')
} else if (crossJobs.length) {
  const outs = await parallel(
    crossJobs.map((j) => () =>
      agent(simPrompt(j.item, j.labels, CROSS_INPUT), optsFor('cross', { label: `compare:cross/${j.item.id}`, phase: 'Compare', schema: SIM_SCHEMA }))
        .catch(() => null)
        .then((s) => collectCross(s ? [{ item: j.item.id, ...s }] : null, [j], 'compare:cross')),
    ),
  )
  cross = outs.filter(Boolean).flat()
}

// ── Tallies: count how each judgment split the runs ─────────────────────────
// Counted here, not by the judge. A judgment whose groups don't place every
// compared run exactly once is flagged, and its tally is taken over the runs placed.

const tallyOf = (groups, expected) => {
  const seen = groups.flatMap((g) => g.runs)
  const counts = groups.map((g) => g.runs.length).sort((a, b) => b - a)
  const placed = seen.length
  const clean = placed === expected.length && new Set(seen).size === placed && seen.every((l) => expected.includes(l))
  return {
    counts,
    agreement: placed ? Math.round((1000 * counts[0]) / placed) / 10 : null,
    split: `${counts.join(' / ')} of ${placed}`,
    clean,
  }
}

const within = withinAt(null).map((s) => {
  const groups = (S[s.scope].groups[s.item] || []).map((g) => ({ runs: g.runs.slice(), description: g.description }))
  return { ...s, groups, tally: tallyOf(groups, usableOf(S[s.scope]).map((g) => g.label)) }
})
const crossTallied = cross.map((s) => {
  const job = crossJobs.find((j) => j.item.id === s.item)
  return { ...s, tally: tallyOf(s.groups, job ? job.labels : []) }
})
const allSimilarity = within.concat(crossTallied)
const untidy = allSimilarity.filter((s) => !s.tally.clean)
if (untidy.length) {
  log(`${untidy.length} judgment(s) didn't place every run exactly once: ${untidy.map((s) => `${s.scope}/${s.item}`).join(', ')}`)
}

// ── Final scores ────────────────────────────────────────────────────────────

const allRuns = PROMPTS.flatMap((pr) => S[pr.id].recs.slice().sort((a, b) => a.repeat - b.repeat))
const usableRuns = allRuns.filter((g) => !g.excluded)
const final = scoresAt(null, crossTallied)
log(
  `final: quality ${final.quality} · stability ${final.stability} (with cross-prompt) · overall ${final.overall} (${final.grade}) · ` +
    `${settledAt !== null ? `settled at wave ${settledAt}` : 'not settled'}`,
)

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
const runQualities = runs.filter((x) => x.quality !== null).map((x) => x.quality).sort((a, b) => a - b)
const median = (xs) => (xs.length ? (xs.length % 2 ? xs[(xs.length - 1) / 2] : round1((xs[xs.length / 2 - 1] + xs[xs.length / 2]) / 2)) : null)

const items = RUBRIC.map((i) => {
  const values = usableRuns.map((g) => VERDICT[verdictOf(g, i.id)]).filter((v) => v !== undefined)
  const mine = within.filter((s) => s.item === i.id)
  const crossHit = crossTallied.find((s) => s.item === i.id)
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

const prompts = PROMPTS.map((pr) => {
  const mine = usableOf(S[pr.id])
  return {
    id: pr.id,
    usableRuns: mine.length,
    quality: pct(wmean(mine.flatMap(qualityPairs))),
    stability: pct(wmean(similarityPairs(within.filter((s) => s.scope === pr.id)))),
  }
})

const effectiveAgents = { preset: PRESET }
for (const role of ['run', 'grade', 'compare', 'cross']) {
  const c = AGENTS[role]
  effectiveAgents[role] = { model: c.model || 'session', effort: c.effort || 'session' }
  if (c.agentType) effectiveAgents[role].agentType = c.agentType
  if (c.batch) effectiveAgents[role].batch = c.batch
}
const usableShare = allRuns.length ? usableRuns.length / allRuns.length : 0

return {
  config: {
    prompts: PROMPTS.map((p) => p.id),
    runs: R,
    wave: W,
    maxTurns: MAX_TURNS,
    crossPerPrompt: CROSS_PER_PROMPT,
    agents: effectiveAgents,
    agentEstimate: estimate,
  },
  scores: {
    quality: final.quality,
    stability: final.stability,
    overall: final.overall,
    grade: final.grade,
    confidence: usableShare >= 0.8 ? 'normal' : 'low',
    usableRuns: usableRuns.length,
    totalRuns: allRuns.length,
  },
  settle: {
    settled: settledAt !== null,
    settledAt,
    delta: SETTLE.delta,
    patience: SETTLE.patience,
    stopWhenSettled: !!SETTLE.stop,
    wavesRun: trajectory.length,
  },
  trajectory,
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
