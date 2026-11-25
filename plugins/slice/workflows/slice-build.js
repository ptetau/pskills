export const meta = {
  name: 'slice-build',
  description: 'Build one slice spec with the slice harness: implement each slice, write acceptance tests after, then review code and tests',
  whenToUse: 'After spec.md is ratified and domain.md is mapped for a spec folder. Routing rules are in slice/models.md.',
  phases: [
    { title: 'Build', detail: 'implementer (sonnet or opus by tier), test-writer (sonnet), reviewer (opus), script steps (haiku)' },
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
    `The language reference is ${ROOT}/docs/language.md, with docs/diagnostics.md, docs/format.md, docs/tools.md, docs/guide.md and docs/examples/. ` +
    `The goal document is docs/rail-spec.md.\n`
}

// The review rule that the user chose on 2026-11-21 ("Converge + scope").
const REVIEW_RULE =
  `Round 1 reviews the whole slice. A later round checks only two things: that each finding of the earlier round is fixed, ` +
  `and that the fix broke nothing. A new finding of a later round that is not caused by the fix is a minor line. ` +
  `Slow compile time on an extreme input, and the exact boundary of a safety limit, are minor findings. ` +
  `A crash, a wrong result, an unmet requirement and a security hole stay major.\n`

function testWriter(id, extra, label) {
  return agent(role('test-writer', id) +
    `Write the acceptance tests of ${id} in ${ROOT}/tests/Rail.Tests/${testFile(id)} only against the public boundary from spec.md and domain.md. ` +
    `Do not run a build or a test command. Use only the programs of the acceptance lines. Do not invent a Rail program: ` +
    `you cannot compile one, and a program that does not compile makes a test that no code can pass.\n` + extra,
    { label: label, phase: 'Build', model: 'sonnet', effort: 'medium', agentType: 'slice:test-writer' })
}

function implementer(slice, rounds, extra) {
  const model = slice.tier === 'hard' || rounds >= 3 ? 'opus' : 'sonnet'
  return agent(role('implementer', slice.id) +
    `Never read or search ${ROOT}/tests. Never run dotnet test: run "${S} test ${slice.id}" for results, as often as you need. ` +
    `You can run "dotnet build src/Rail.Cli" to compile. Emitted code uses the templates of the section "Compiling to C#" of docs/rail-spec.md. ` +
    `You may write and run unit tests in any configured unit tests folder.` +
    `If a test cannot pass because what it expects conflicts with the language reference or with an earlier spec ` +
    `(for example it expects exit code 0 where the reference says 1), do not spend rounds on it: write no workaround, ` +
    `and end your reply with one line of the form "IMPOSSIBLE TEST: <test name>: <why>". Write that line only for such a test, never to say that there is none.\n` + extra,
    { label: `implement ${slice.id} (${model}, round ${rounds})`, phase: 'Build', model: model, effort: 'medium', agentType: 'slice:implementer' })
}

function reviewer(id, round) {
  return agent(role('reviewer', id) + REVIEW_RULE +
    `This is review round ${round}. Return code_major and tests_major: the number of open major lines in review/${id}.md and review/${id}.tests.md.`,
    { label: `review ${id} (opus, round ${round})`, phase: 'Build', model: 'opus', effort: 'high', schema: REVIEW_SCHEMA, agentType: 'slice:reviewer' })
}

// ---- Build: one slice after the other (implement -> test-writer -> reviewer -> fix loop -> commit) ----
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
      if (round.exit_code !== 0) { stop = { why: 'no test round left', output: r.output }; return r }
      rounds++
      const said = await implementer(slice, rounds, `${note}\nThe last test results:\n\n${r.output}`)
      if (/IMPOSSIBLE TEST:\s*`?test_/.test(String(said || ''))) {
        stop = { why: 'the implementer reports a test that cannot pass', output: String(said).slice(-1500) }
        return r
      }
      note = ''
      r = await sh(`${S} test ${id}`, `test ${id}`, 'Build')
    }
    return r
  }

  await sh(`${S} set ${id} building`, `start ${id}`, 'Build')
  await implementer(slice, 0, 'Build this slice from spec.md and domain.md.')

  await testWriter(id, '', `tests ${id} (sonnet)`)
  const BUILD = `cd ${ROOT} && dotnet build tests/Rail.Tests --nologo -v q 2>&1 | grep -E "error|Build succeeded" | sort -u | head -40; test \${PIPESTATUS[0]} -eq 0`
  for (let i = 0; i < 4; i++) {
    const b = await sh(BUILD, `compile tests ${id} (${i + 1})`, 'Build')
    if (b.exit_code === 0) break
    if (i === 3) { stop = { why: 'the tests do not compile', output: b.output }; break }
    await testWriter(id, `The test project does not compile. Fix only the compile errors below, in the test files that they name. Keep each test's meaning.\n\n${b.output}`, `fix test compile ${id} (${i + 1})`)
  }

  let r = stop ? null : await sh(`${S} test ${id}`, `test ${id}`, 'Build')
  let reviewRound = 0
  while (!stop) {
    const rr = await sh(`${S} set ${id} review && ${S} round ${id} review`, `review round ${id}`, 'Build')
    if (rr.exit_code !== 0) { stop = { why: 'no review round left', output: rr.output }; break }
    reviewRound++
    const rev = await reviewer(id, reviewRound)
    if (!rev) { stop = { why: 'the reviewer returned nothing', output: '' }; break }
    if (rev.tests_major > 0) {
      await testWriter(id, `Fix the open findings of ${DIR}/review/${id}.tests.md.`, `fix tests ${id} (sonnet)`)
      r = await sh(`${S} test ${id}`, `test ${id}`, 'Build')
    }
    if (rev.code_major > 0 || (r && r.exit_code !== 0)) {
      const round = await sh(`${S} round ${id} test`, `round ${id}`, 'Build')
      if (round.exit_code !== 0) { stop = { why: 'no test round left', output: r ? r.output : '' }; break }
      rounds++
      const fixNote = rev.code_major > 0
        ? `Fix each open major finding of ${DIR}/review/${id}.md. Then make the acceptance tests pass.\n\n${r ? r.output : ''}`
        : `The acceptance tests of ${id} fail.\n\n${r ? r.output : ''}`
      const said = await implementer(slice, rounds, fixNote)
      if (/IMPOSSIBLE TEST:\s*`?test_/.test(String(said || ''))) {
        stop = { why: 'the implementer reports a test that cannot pass', output: String(said).slice(-1500) }
        break
      }
      r = await untilGreen(await sh(`${S} test ${id}`, `test ${id}`, 'Build'), 'Fix the failing acceptance tests.')
      if (stop) break
    }
    if (rev.tests_major === 0 && rev.code_major === 0 && r && r.exit_code === 0) {
      const c = await sh(`${S} commit ${id} --summary "Implements and verifies ${id} (${slice.tier} tier)."`, `commit ${id}`, 'Build')
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
