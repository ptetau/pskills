#!/usr/bin/env node
// pdlc visual review: plays a short script and records it as a GIF plus PNG frames.
//
// Usage: node pdlc/bin/record_gif.mjs <script.json> <out-dir>
//
// The script is JSON:
// {
//   "kind": "web" | "terminal",
//   "title": "CH-0001 · Spanish greeting",
//   "base_url": "http://localhost:3000",       (web only)
//   "start": "node server.js",                 (optional: started first, stopped after)
//   "width": 1000, "height": 640,              (optional)
//   "steps": [
//     { "caption": "JOB-x.R1 · Given …, when …, then …", "goto": "/" },
//     { "type": ["#title", "buy milk"] }, { "press": "Enter" }, { "click": "#add" },
//     { "wait": 500 },
//     { "caption": "CAP-x.R2 · …", "run": "node src/cli.js Ana --lang es" }   (terminal)
//   ]
// }
//
// Every step makes one frame. A caption stays until the next step sets a new one.
// A terminal shows each command's output and errors in order, and scrolls like a real
// one: every frame shows the newest lines.
//
// A frame must show what its caption claims. The recording fails, naming the step, when:
//   - a frame is blank: almost every pixel is one colour;
//   - a step that should change the screen doesn't. That is a click, typing or a key press
//     that leaves the page as it was, or a command that prints nothing.
// After a click, typing or a key press, the recorder waits up to 5 s for the page to change
// and settle. Then the frame shows the result, not the page before it. A step whose
// acceptance line says nothing changes sets "unchanged": true. If a check fails, the
// recorder writes no review.gif.
// Needs playwright, gifenc and pngjs. It looks for them in pdlc/.tools, then globally.

import { createRequire } from "node:module";
import { execSync, spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const [scriptPath, outDir] = process.argv.slice(2);
if (!scriptPath || !outDir) {
  console.error("usage: node record_gif.mjs <script.json> <out-dir>");
  process.exit(1);
}

function load(name) {
  const roots = [path.resolve("pdlc/.tools/node_modules")];
  try { roots.push(execSync("npm root -g", { encoding: "utf8" }).trim()); } catch {}
  for (const root of roots) {
    try { return createRequire(path.join(root, "noop.js"))(name); } catch {}
  }
  console.error(`missing ${name}: run  npm install --prefix pdlc/.tools playwright gifenc pngjs`);
  process.exit(1);
}

const { chromium } = load("playwright");
const { GIFEncoder, quantize, applyPalette } = load("gifenc");
const { PNG } = load("pngjs");

const script = JSON.parse(fs.readFileSync(scriptPath, "utf8"));
const width = script.width || 1000;
const height = script.height || 640;
const escape = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);

const banner = (title, caption, n, total) => `
  <div id="pdlc-banner" style="position:fixed;left:0;right:0;top:0;z-index:2147483647;
    font:14px/1.4 system-ui,sans-serif;background:#111827;color:#f9fafb;padding:8px 14px;
    display:flex;justify-content:space-between;gap:16px;box-shadow:0 1px 4px #0006">
    <span><b>${escape(caption || "")}</b></span>
    <span style="opacity:.7;white-space:nowrap">${escape(title || "")} · ${n}/${total}</span>
  </div>`;

const terminalPage = (lines) => `<!doctype html><meta charset="utf-8">
  <body style="margin:0;background:#0b0f14;color:#d1d5db;font:15px/1.5 ui-monospace,Menlo,monospace">
  <pre style="margin:0;padding:52px 18px 18px;white-space:pre-wrap">${lines.join("\n")}</pre></body>`;

const SETTLE_MS = 5000;

// What the page shows, without the caption bar, for the frame checks.
const look = (page) => page.screenshot({ animations: "disabled", caret: "hide" });

// Waits until the page differs from `before` (when given) and stops changing, or 5 s pass.
async function settle(page, before) {
  const end = Date.now() + SETTLE_MS;
  let last = await look(page);
  while (Date.now() < end) {
    await page.waitForTimeout(150);
    const next = await look(page);
    if ((!before || !next.equals(before)) && next.equals(last)) return next;
    last = next;
  }
  return last;
}

// True when fewer than 1 pixel in 10,000 differs clearly from the most common colour.
function isBlank(png) {
  const { data, width: w, height: h } = PNG.sync.read(png);
  const counts = new Map();
  for (let i = 0; i < data.length; i += 4) {
    const key = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2];
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  let top = 0;
  let most = 0;
  for (const [key, n] of counts) if (n > most) { most = n; top = key; }
  const [r, g, b] = [top >> 16, (top >> 8) & 255, top & 255];
  let ink = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (Math.abs(data[i] - r) + Math.abs(data[i + 1] - g) + Math.abs(data[i + 2] - b) > 48) ink++;
  }
  return ink * 10000 < w * h;
}

// "step 3 · click "#go" · JOB-x.R1 · …": how a problem names its step.
function stepName(step, n, caption) {
  const kinds = ["run", "click", "type", "press", "goto"];
  const kind = kinds.find((k) => step[k] !== undefined);
  const what = kind ? `${kind} ${JSON.stringify(kind === "type" ? step.type[0] : step[kind])}`
    : "caption only";
  return `step ${n} · ${what}${caption ? ` · ${caption}` : ""}`;
}

async function waitForUrl(url, ms = 20000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try { await fetch(url); return; } catch { await new Promise((r) => setTimeout(r, 300)); }
  }
  throw new Error(`app did not start at ${url}`);
}

async function launch() {
  try { return await chromium.launch(); } catch (first) {
    const dir = process.env.PLAYWRIGHT_BROWSERS_PATH || "/opt/pw-browsers";
    const guess = path.join(dir, "chromium");
    if (fs.existsSync(guess)) return chromium.launch({ executablePath: guess });
    throw first;
  }
}

// Start from an empty frames folder and no GIF, so nothing from an earlier recording
// lingers and reaches the reviewers.
fs.rmSync(path.join(outDir, "frames"), { recursive: true, force: true });
fs.rmSync(path.join(outDir, "review.gif"), { force: true });
fs.mkdirSync(path.join(outDir, "frames"), { recursive: true });
let app;
let browser;
const frames = [];
const lines = [];
const problems = [];
let caption = "";

try {
  if (script.start) {
    app = spawn(script.start, { shell: true, stdio: "ignore", detached: true });
    if (script.base_url) await waitForUrl(script.base_url);
  }
  browser = await launch();
  const page = await browser.newPage({ viewport: { width, height } });
  const steps = script.steps || [];
  for (const [i, step] of steps.entries()) {
    if (step.caption) caption = step.caption;
    const label = stepName(step, i + 1, caption);
    let view;
    if (script.kind === "terminal") {
      if (step.run) {
        let out;
        // Errors go to the same stream, so a warning from a command that succeeds still shows.
        const command = `{ ${step.run}\n} 2>&1`;
        try { out = execSync(command, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }); }
        catch (e) { out = (e.stdout || "") + (e.stderr || ""); }
        lines.push(`<span style="color:#34d399">$</span> ${escape(step.run)}`, escape(out.trimEnd()));
        if (!out.trim() && !step.unchanged) {
          problems.push(`${label}: the command printed nothing, so its frame shows no result. ` +
            "Show its effect (print it, or run a command that reads it), or join it to the next step.");
        }
      }
      await page.setContent(terminalPage(lines));
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      if (step.wait) await page.waitForTimeout(step.wait);
      view = await look(page);
    } else {
      await page.evaluate(() => document.getElementById("pdlc-banner")?.remove());
      if (step.goto) await page.goto(new URL(step.goto, script.base_url).href);
      const acts = step.click !== undefined || step.type !== undefined || step.press !== undefined;
      const before = acts && !step.unchanged ? await look(page) : null;
      if (step.click) {
        await page.click(step.click);
        await page.mouse.move(0, 0); // so a hover style doesn't pass for a change
      }
      if (step.type) await page.fill(step.type[0], step.type[1]);
      if (step.press) await page.keyboard.press(step.press);
      if (step.wait) await page.waitForTimeout(step.wait);
      view = await settle(page, before);
      if (before && view.equals(before)) {
        problems.push(`${label}: the screen did not change within ${SETTLE_MS / 1000} s, so its ` +
          "frame would show the page before the step. Check the selector and what the step " +
          'should show. Only if its acceptance line says nothing changes, set "unchanged": true.');
      }
    }
    if (isBlank(view)) {
      problems.push(`${label}: the frame is blank (almost all one colour). Show what the ` +
        "caption claims: the page or output it describes.");
    }
    await page.evaluate(({ html }) => {
      document.getElementById("pdlc-banner")?.remove();
      document.body.insertAdjacentHTML("beforeend", html);
    }, { html: banner(script.title, caption, i + 1, steps.length) });
    const shot = await page.screenshot();
    const name = path.join(outDir, "frames", String(i + 1).padStart(2, "0") + ".png");
    fs.writeFileSync(name, shot);
    frames.push(shot);
  }
} finally {
  if (browser) await browser.close();
  if (app) try { process.kill(-app.pid); } catch {}
}

if (problems.length) {
  for (const problem of problems) console.error(`record_gif: ${problem}`);
  console.error(`record_gif: ${problems.length} frame problem(s). No review.gif was written; ` +
    "the frames are left for you to look at. Fix the script and record again.");
  process.exit(1);
}

const gif = GIFEncoder();
frames.forEach((buffer, i) => {
  const { data, width: w, height: h } = PNG.sync.read(buffer);
  const palette = quantize(data, 256);
  gif.writeFrame(applyPalette(data, palette), w, h, {
    palette, delay: i === frames.length - 1 ? 3000 : 1400,
  });
});
gif.finish();
fs.writeFileSync(path.join(outDir, "review.gif"), gif.bytes());
console.log(`wrote ${path.join(outDir, "review.gif")} and ${frames.length} frames`);
