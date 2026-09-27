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
// Needs playwright, gifenc and pngjs. They are looked up in pdlc/.tools, then globally.

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

// Start from an empty frames folder, so frames from an earlier, longer recording don't
// linger and reach the reviewers.
fs.rmSync(path.join(outDir, "frames"), { recursive: true, force: true });
fs.mkdirSync(path.join(outDir, "frames"), { recursive: true });
let app;
let browser;
const frames = [];
const lines = [];
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
    if (script.kind === "terminal") {
      if (step.run) {
        let out;
        try { out = execSync(step.run, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }); }
        catch (e) { out = (e.stdout || "") + (e.stderr || ""); }
        lines.push(`<span style="color:#34d399">$</span> ${escape(step.run)}`, escape(out.trimEnd()));
      }
      await page.setContent(terminalPage(lines));
    } else {
      if (step.goto) await page.goto(new URL(step.goto, script.base_url).href);
      if (step.click) await page.click(step.click);
      if (step.type) await page.fill(step.type[0], step.type[1]);
      if (step.press) await page.keyboard.press(step.press);
    }
    if (step.wait) await page.waitForTimeout(step.wait);
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
