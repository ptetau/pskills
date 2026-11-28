// Screenshot an HTML page, full height, at 1280 px. Usage: node shoot.js PAGE.html OUT.png
const { chromium } = require("playwright");
const path = require("path");
(async () => {
  const [file, out] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await p.goto("file://" + path.resolve(file), { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
  await p.waitForTimeout(2500);
  await p.screenshot({ path: out, fullPage: true });
  await b.close();
  console.log("saved " + out);
})();
