// Browser test of a rendered page. Run: node test_page_browser.js [PAGE.html]
// It needs puppeteer-core (set NODE_PATH to its folder) and a Chromium file (set CHROME_PATH).
// If either is missing, the test says so and exits with 0. The page must be the page of
// examples/summit-welcome.quiz.json, because the test knows its question and option IDs.
let puppeteer;
try { puppeteer = require('puppeteer-core'); } catch (e) { console.log('skipped: puppeteer-core is not installed'); process.exit(0); }
const path = require('path');
const fs = require('fs');
const CHROME = process.env.CHROME_PATH || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
if (!fs.existsSync(CHROME)) { console.log('skipped: no Chromium at ' + CHROME); process.exit(0); }
const PAGE = path.resolve(process.argv[2] || path.join(__dirname, '..', 'examples', 'summit-welcome.quiz.html'));
const assert = require('assert');
(async () => {
  const b = await puppeteer.launch({ executablePath: CHROME, args: ['--no-sandbox','--disable-gpu'] });
  const p = await b.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.evaluateOnNewDocument(() => {
    window.__sent = null;
    window.claude = { use: async (n) => n === 'db' ? { doc: (path) => ({ set: async (d) => { window.__sent = { path, d }; } }) } : null };
  });
  await p.setViewport({ width: 1280, height: 900 });
  await p.goto('file://' + PAGE, { waitUntil: 'load' });
  await new Promise(r => setTimeout(r, 400));
  // send button appears when db exists, disabled until complete
  assert.strictEqual(await p.$eval('#send', e => e.hidden), false, 'send visible');
  assert.strictEqual(await p.$eval('#send', e => e.disabled), true, 'send disabled at start');
  // answer: tone=warm (2nd), layout via label, palette third, booking defer, extras two boxes
  await p.click('#q-tone .opt:nth-of-type(2) .mat');
  await p.click('#q-layout .opt:nth-of-type(3) label.body');
  await p.click('#q-palette .opt:nth-of-type(3) .mat');
  await p.click('[data-defer="booking"]');
  await p.click('#q-extras .opt:nth-of-type(1) label.body');
  await p.click('#q-extras .opt:nth-of-type(4) .mat');
  await p.type('#note-layout', 'Use the club photo.');
  // switching tone selection replaces, does not add
  await p.click('#q-tone .opt:nth-of-type(1) .mat');
  const pl = await p.evaluate(() => window.__quiz.payload());
  assert.strictEqual(pl.summary.total, 5);
  assert.strictEqual(pl.summary.answered, 5);
  assert.strictEqual(pl.summary.deferred, 1);
  assert.strictEqual(pl.summary.withNotes, 1);
  const by = Object.fromEntries(pl.answers.map(a => [a.id, a]));
  assert.strictEqual(by.tone.choice.id, 'stoked');
  assert.strictEqual(by.layout.choice.id, 'split');
  assert.strictEqual(by.layout.note, 'Use the club photo.');
  assert.strictEqual(by.palette.choice.id, 'sky-rope');
  assert.strictEqual(by.booking.deferred, true);
  assert.strictEqual(by.booking.choice.id, 'pick-day');   // no recommendation, so the first option
  assert.strictEqual(by.booking.decidedBy, 'first option');
  assert.strictEqual(by.tone.decidedBy, null);
  assert.deepStrictEqual(by.extras.choices.map(c => c.id), ['hours', 'gear']);
  assert.strictEqual(by.extras.choice, null);
  // selecting an option after deferral clears the deferral
  await p.click('#q-booking .opt:nth-of-type(3) label.body');
  const pl2 = await p.evaluate(() => window.__quiz.payload());
  assert.strictEqual(pl2.answers.find(a => a.id === 'booking').deferred, false);
  assert.strictEqual(pl2.answers.find(a => a.id === 'booking').choice.id, 'reply');
  // send writes quiz/answers
  assert.strictEqual(await p.$eval('#send', e => e.disabled), false, 'send enabled when done');
  await p.click('#send');
  await new Promise(r => setTimeout(r, 200));
  const sent = await p.evaluate(() => window.__sent);
  assert.strictEqual(sent.path, 'quiz/answers');
  assert.strictEqual(sent.d.summary.answered, 5);
  // state survives a reload
  await p.reload({ waitUntil: 'load' });
  await new Promise(r => setTimeout(r, 300));
  const pl3 = await p.evaluate(() => window.__quiz.payload());
  assert.strictEqual(pl3.summary.answered, 5);
  // reset clears
  await p.click('#reset');
  const pl4 = await p.evaluate(() => window.__quiz.payload());
  assert.strictEqual(pl4.summary.answered, 0);
  assert.strictEqual(await p.$eval('#copy', e => e.disabled), true);
  // copy fallback: clipboard blocked in file mode -> text box opens
  await p.click('#q-tone .opt:nth-of-type(1) .mat');
  for (const id of ['layout','palette','booking','extras']) await p.click('#q-' + id + ' .opt:nth-of-type(1) label.body');
  await p.evaluate(() => { Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('blocked')) }, configurable: true }); });
  await p.click('#copy');
  await new Promise(r => setTimeout(r, 200));
  assert.strictEqual(await p.$eval('#raw', e => e.open), true, 'raw text opens when copy is blocked');
  const raw = await p.$eval('#rawtext', e => e.value);
  assert.strictEqual(JSON.parse(raw).summary.answered, 5);
  console.log(errs.length ? 'PAGE ERRORS: ' + errs.join('; ') : 'behaviour OK, no page errors');
  await b.close();
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
