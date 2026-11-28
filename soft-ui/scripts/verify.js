#!/usr/bin/env node
// Load a soft-ui page in headless Chromium and report what went wrong.
// Usage: node verify.js PAGE.html [SHOT.png]
// Prints "check ok ..." or one "check error ..." line per problem. Exit 1 on any error.
const path = require("path");
let chromium;
try { ({ chromium } = require("playwright")); } catch (e) { console.log("check skipped: playwright is not installed"); process.exit(0); }

(async () => {
  const args = process.argv.slice(2), offline = args.includes("--offline");
  const [file, shot] = args.filter((a) => a !== "--offline");
  const url = "file://" + path.resolve(file);
  const browser = await chromium.launch();
  const problems = [];
  const warn = [];
  async function load(width, theme) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: theme });
    if (offline) await page.route(/^https?:\/\/(?!fonts\.)/, (r) => r.abort());   // an inline page must draw with no network
    page.on("pageerror", (e) => problems.push(`script error: ${String(e.message).split("\n")[0]}`));
    page.on("console", (m) => { if (m.type() === "error" && !/favicon|fonts\.g/.test(m.text())) warn.push(`console: ${m.text().slice(0, 200)}`); });
    page.on("requestfailed", (r) => { if (!/fonts\.g/.test(r.url()) && !offline) problems.push(`load failed: ${r.url()}`); });
    await page.goto(url, { waitUntil: "load", timeout: 45000 });
    try { await page.waitForFunction(() => window.__softui && window.__softui.done, null, { timeout: 30000 }); }
    catch (e) { problems.push("the page did not finish drawing in 30 s"); }
    return page;
  }
  const page = await load(1280, "light");
  const st = await page.evaluate(() => ({ errors: (window.__softui || {}).errors || [], nodes: (window.__softui || {}).nodes || 0,
    empty: [...document.querySelectorAll(".su-chart canvas")].filter((c) => !c.width).length,
    novalue: [...document.querySelectorAll(".su-stat-v.su-novalue")].map((e) => e.closest(".su-stat").querySelector(".su-stat-l").textContent) }));
  st.errors.forEach((e) => problems.push(e));
  if (st.novalue.length) problems.push(`stat tile(s) with no value: ${st.novalue.join(", ")}. Give value, or data with col and agg`);
  if (shot) await page.screenshot({ path: shot, fullPage: true });
  await page.close();
  for (const w of [768]) {   // tablet: the page must not scroll sideways either
    const tab = await load(w, "light");
    if (await tab.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)) problems.push(`page scrolls sideways at ${w}px`);
    await tab.close();
  }
  const phone = await load(390, "dark");
  const over = await phone.evaluate(() => {
    const W = document.documentElement.clientWidth;
    if (document.documentElement.scrollWidth <= W + 1) return null;
    const bad = [...document.querySelectorAll(".su-node, .su-leaf, .su-row > *, .su-grid > *")].filter((e) => e.getBoundingClientRect().right > W + 1)
      .map((e) => (e.className || e.tagName).toString().split(" ").slice(0, 2).join(".")).slice(0, 3);
    return `${document.documentElement.scrollWidth}px wide at ${W}px (${bad.join(", ") || "unknown element"})`;
  });
  if (over) problems.push("page scrolls sideways on a phone: " + over);
  const inner = await phone.evaluate(() => [...document.querySelectorAll(".su-tw, .su-gantt, .su-board, .su-heat, .su-diff-w")]
    .filter((e) => e.scrollWidth > e.clientWidth + 2).map((e) => { const n = e.closest(".su-node"); return n?.querySelector(".su-t")?.textContent || (n?.className.match(/su-c-(\w+)/) || [])[1] || "table"; }));
  if (inner.length) warn.push(`on a phone these scroll sideways inside their box: ${[...new Set(inner)].slice(0, 5).join(", ")}`);
  await phone.close();
  await browser.close();
  for (const w of [...new Set(warn)].slice(0, 5)) console.log("check warning " + w);
  if (problems.length) { [...new Set(problems)].forEach((p) => console.log("check error " + p)); process.exit(1); }
  console.log(`check ok · ${st.nodes} nodes drawn · no render errors · fits phone, tablet and desktop` + (offline ? " · draws with no network" : "") + (shot ? ` · screenshot ${shot}` : ""));
})().catch((e) => { console.log("check error " + e.message.split("\n")[0]); process.exit(1); });
