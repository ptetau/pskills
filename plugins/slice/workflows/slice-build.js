export const meta = {
  name: 'slice-build',
  description: 'Build one slice spec with the slice harness: red tests, then each slice, with a model for each job',
  whenToUse: 'After spec.md is ratified and interface.md is approved for a spec folder. Routing rules are in slice/models.md.',
  phases: [
    { title: 'Tests', detail: 'test writers (sonnet) write red tests for all slices; haiku runs the red checks' },
    { title: 'Build', detail: 'implementer (sonnet or opus by tier), reviewer (opus), script steps (haiku)' },
  ],
}

// args: { root, plugin, spec, slices: [{ id, tier: 'hard' | 'standard' }], writeTests: boolean }
const A = typeof args === 'string' ? JSON.parse(args) : args
const ROOT = A.root
const PLUGIN = A.plugin
const SPEC = A.spec
const S = `python3 ${PLUGIN}/bin/slice.py --root ${ROOT} --spec ${SPEC}`
const DIR = `${ROOT}/slice/${SPEC}`
// Spec 001 keeps its first file names. Each later spec puts its number in the name.
const NUM = SPEC.slice(0, 3)
const testFile = id => NUM === '001' ? `${id}Tests.cs` : `Spec${NUM}${id}Tests.cs`

const SH_SCHEMA = {
  type: 'object',
  properties: { exit_code: { type: 'integer' }, output: { type: 'string' } },
  required: ['exit_code', 'output'],
}
const REVIEW_SCHEMA = {
  type: 'object',
  properties: { code_major: { type: 'integer' }, tests_major: { type: 'integer' }, summary: { type: 'string' } },
  required: ['code_major', 'tests_major'],
}

// A script step. Haiku runs one command and returns its output. It judges nothing.
async function sh(command, label, phaseName) {
  // The command prints its own exit code, so the result does not depend on how the model reports it.
  const r = await agent(
    `Run this one bash command, once, from the folder ${ROOT}:\n\n( ${command} ); echo "EXIT_CODE=$?"\n\n` +
    `Return output (stdout and stderr together, exact, the last 9000 characters if it is longer; always keep the last line) ` +
    `and exit_code (the number on the EXIT_CODE line). Do not fix, explain or retry anything. Run no other command.`,
    { label: label, phase: phaseName, model: 'haiku', effort: 'low', schema: SH_SCHEMA })
  if (!r) return { exit_code: 99, output: 'the script step returned nothing' }
  const found = [...String(r.output).matchAll(/EXIT_CODE=(\d+)/g)].pop()
  return { exit_code: found ? Number(found[1]) : r.exit_code, output: r.output }
}

function role(name, id) {
  return `You are the slice ${name} agent of the slice plugin. Where your instructions say \${CLAUDE_PLUGIN_ROOT}, use ${PLUGIN}. ` +
    `Run slice.py as: ${S}\n` +
    `Project root: ${ROOT}. Spec folder: ${DIR}. Slice: ${id}.\n` +
    `The language reference is ${ROOT}/docs/language.md, with docs/diagnostics.md, docs/format.md, docs/tools.md and docs/examples/. ` +
    `The goal document is docs/rail-spec.md.\n`
}

// The review rule that the user chose on 2026-11-21 ("Converge + scope").
const REVIEW_RULE =
  `Round 1 reviews the whole slice. A later round checks only two things: that each finding of the earlier round is fixed, ` +
  `and that the fix broke nothing. A new finding of a later round that is not caused by the fix is a minor line. ` +
  `Slow compile time on an extreme input, and the exact boundary of a safety limit, are minor findings. ` +
  `A crash, a wrong result, an unmet requirement and a security hole of the interface.md floor stay major.\n`

function testWriter(id, extra, label) {
  return agent(role('test-writer', id) +
    `Write the tests of ${id} in ${ROOT}/tests/Rail.Tests/${testFile(id)} only. Use the helper that interface.md names. ` +
    `Do not run a build or a test command.\n` + extra,
    { label: label, phase: A.writeTests && extra.indexOf('review/') < 0 ? 'Tests' : 'Build', model: 'sonnet', effort: 'medium', agentType: 'slice:test-writer' })
}

function implementer(slice, rounds, extra) {
  const model = slice.tier === 'hard' || rounds >= 3 ? 'opus' : 'sonnet'
  return agent(role('implementer', slice.id) +
    `Never read or search ${ROOT}/tests. Never run dotnet test: run "${S} test ${slice.id}" for results, as often as you need. ` +
    `You can run "dotnet build src/Rail.Cli" to compile. Emitted code uses the templates of the section "Compiling to C#" of docs/rail-spec.md. ` +
    `Keep each command that a later slice owns failing with NotImplementedException("not implemented").\n` + extra,
    { label: `implement ${slice.id} (${model}, round ${rounds})`, phase: 'Build', model: model, effort: 'medium', agentType: 'slice:implementer' })
}

function reviewer(id, round) {
  return agent(role('reviewer', id) + REVIEW_RULE +
    `This is review round ${round}. Return code_major and tests_major: the number of open major lines in review/${id}.md and review/${id}.tests.md.`,
    { label: `review ${id} (opus, round ${round})`, phase: 'Build', model: 'opus', effort: 'high', schema: REVIEW_SCHEMA, agentType: 'slice:reviewer' })
}

// ---- Tests: every slice red before any build ----
if (A.writeTests) {
  phase('Tests')
  await parallel(A.slices.map(s => () => testWriter(s.id, '', `tests ${s.id} (sonnet)`)))

  const BUILD = `cd ${ROOT} && dotnet build tests/Rail.Tests --nologo -v q 2>&1 | grep -E "error|Build succeeded" | sort -u | head -40; test \${PIPESTATUS[0]} -eq 0`
  for (let i = 0; i < 4; i++) {
    const b = await sh(BUILD, `compile tests (${i + 1})`, 'Tests')
    if (b.exit_code === 0) break
    if (i === 3) return { stopped: 'interface', why: 'the tests do not compile', output: b.output }
    await agent(role('test-writer', 'all') +
      `The test project does not compile. Fix only the compile errors below, in the test files that they name. Keep each test's meaning.\n\n${b.output}`,
      { label: `fix test compile (${i + 1})`, phase: 'Tests', model: 'sonnet', effort: 'medium', agentType: 'slice:test-writer' })
  }
  for (const s of A.slices) {
    for (let i = 0; i < 4; i++) {
      const r = await sh(`${S} test ${s.id} --red`, `red check ${s.id}`, 'Tests')
      if (r.exit_code === 0) break
      if (i === 3) return { stopped: s.id, why: 'the tests are not red', output: r.output }
      await testWriter(s.id, `The red check of ${s.id} fails. Fix the tests that it names. A "does not reach the surface" test must call the surface before it asserts.\n\n${r.output}`, `fix red ${s.id} (${i + 1})`)
    }
  }
  const setRed = A.slices.map(s => `${S} set ${s.id} red`).join(' && ')
  const c = await sh(`${setRed} && ${S} commit interface`, 'commit interface', 'Tests')
  if (c.exit_code !== 0) return { stopped: 'interface', why: 'the interface commit was refused', output: c.output }
}

// ---- Build: one slice after the other ----
phase('Build')
const done = []
for (const slice of A.slices) {
  const id = slice.id
  let rounds = 0
  let stop = null

  // Run the implementer until the tests of the slice pass. Each run uses one test round.
  async function untilGreen(first, extra) {
    let r = first
    let note = extra
    while (r.exit_code !== 0) {
      const round = await sh(`${S} round ${id} test`, `round ${id}`, 'Build')
      if (round.exit_code !== 0) { stop = { why: 'no test round left', output: r.output }; return }
      rounds++
      await implementer(slice, rounds, `${note}\nThe last test results:\n\n${r.output}`)
      note = ''
      r = await sh(`${S} test ${id}`, `test ${id}`, 'Build')
    }
  }

  await untilGreen(await sh(`${S} set ${id} building && ${S} test ${id}`, `start ${id}`, 'Build'), '')

  let reviewRound = 0
  while (!stop) {
    const rr = await sh(`${S} set ${id} review && ${S} round ${id} review`, `review round ${id}`, 'Build')
    if (rr.exit_code !== 0) { stop = { why: 'no review round left', output: rr.output }; break }
    reviewRound++
    const rev = await reviewer(id, reviewRound)
    if (!rev) { stop = { why: 'the reviewer returned nothing', output: '' }; break }
    if (rev.tests_major > 0) {
      await testWriter(id, `Fix the open findings of ${DIR}/review/${id}.tests.md.`, `fix tests ${id} (sonnet)`)
      const ct = await sh(`${S} commit tests ${id}`, `commit tests ${id}`, 'Build')
      if (ct.exit_code !== 0) { stop = { why: 'the test fix was refused', output: ct.output }; break }
      await untilGreen(await sh(`${S} test ${id}`, `test ${id}`, 'Build'), 'The tests of the slice changed after a review finding.')
      if (stop) break
    }
    if (rev.code_major > 0) {
      const round = await sh(`${S} round ${id} test`, `round ${id}`, 'Build')
      if (round.exit_code !== 0) { stop = { why: 'no test round left for the review fix', output: round.output }; break }
      rounds++
      await implementer(slice, rounds, `Fix each open major finding of ${DIR}/review/${id}.md. Then make the tests pass again.`)
      await untilGreen(await sh(`${S} test ${id}`, `test ${id}`, 'Build'), 'A review fix broke a test.')
      if (stop) break
    }
    if (rev.tests_major === 0 && rev.code_major === 0) {
      const c = await sh(`${S} commit ${id}`, `commit ${id}`, 'Build')
      if (c.exit_code !== 0) stop = { why: 'the slice commit was refused', output: c.output }
      break
    }
  }
  if (stop) {
    await sh(`${S} set ${id} stopped --reason "${stop.why}"`, `stop ${id}`, 'Build')
    return { done: done, stopped: id, why: stop.why, output: stop.output }
  }
  done.push({ id: id, test_rounds: rounds, review_rounds: reviewRound })
  log(`${id} committed (test rounds ${rounds}, review rounds ${reviewRound})`)
}
return { done: done, stopped: null }
