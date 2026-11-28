/* soft-ui runtime: draws the checked plan in #su-plan into #su-root. No build step. */
(function () {
  "use strict";
  const PLAN = JSON.parse(document.getElementById("su-plan").textContent);
  const DS = PLAN.data || {};
  const ST = (window.__softui = { done: false, errors: [], nodes: 0 });
  const FILT = {};           // dataset -> {f: {col: Set}, q: ""}
  const SUBS = {};           // dataset -> [rerender]
  const LIVE = [];           // rerender on theme change (charts, diagrams)
  const PENDING = [];        // diagrams waiting to be visible
  const WAIT = [];           // promises the done flag waits for
  let uid = 0;

  // ---- helpers --------------------------------------------------------------------
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      const v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v;
      else if (k === "style" && typeof v === "object") { for (const sk in v) { if (v[sk] == null) continue; if (sk.startsWith("--")) el.style.setProperty(sk, v[sk]); else el.style[sk] = v[sk]; } }
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else if (k.startsWith("--")) el.style.setProperty(k, v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    return el;
  }
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const isNum = (v) => typeof v === "number" && isFinite(v);
  const arr = (v) => (v == null ? [] : Array.isArray(v) ? v : [v]);
  const colKey = (c) => (typeof c === "object" ? c.key : c);

  function inline(s) {
    const codes = [];
    s = String(s).replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
    s = esc(s)
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
      .replace(/(^|[\s(])_([^_\s][^_]*)_/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\(((?:https?:\/\/|#)[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => "<code>" + esc(codes[+i]) + "</code>");
  }
  function md(src) {
    const out = [], lines = String(src == null ? "" : src).replace(/\r/g, "").split("\n");
    let para = [], list = null, code = null;
    const flushP = () => { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } };
    const flushL = () => { if (list) { out.push(`<${list.t}>` + list.items.map((i) => "<li>" + inline(i) + "</li>").join("") + `</${list.t}>`); list = null; } };
    for (const ln of lines) {
      if (code) { if (/^\s*```/.test(ln)) { out.push('<pre class="su-pre su-wrap"><code>' + esc(code.join("\n")) + "</code></pre>"); code = null; } else code.push(ln); continue; }
      if (/^\s*```/.test(ln)) { flushP(); flushL(); code = []; continue; }
      let m;
      if (!ln.trim()) { flushP(); flushL(); continue; }
      if ((m = ln.match(/^(#{1,4})\s+(.*)/))) { flushP(); flushL(); out.push(`<h${Math.min(4, m[1].length + 2)}>` + inline(m[2]) + `</h${Math.min(4, m[1].length + 2)}>`); continue; }
      if ((m = ln.match(/^\s*([-*+]|\d+[.)])\s+(.*)/))) {
        flushP(); const t = /\d/.test(m[1]) ? "ol" : "ul";
        if (!list || list.t !== t) { flushL(); list = { t, items: [] }; }
        list.items.push(m[2].replace(/^\[( |x)\]\s*/i, (_, x) => (x.trim() ? "☑ " : "☐ "))); continue;
      }
      if ((m = ln.match(/^>\s?(.*)/))) { flushP(); flushL(); out.push('<p style="color:var(--muted)">' + inline(m[1]) + "</p>"); continue; }
      if (list && /^\s{2,}\S/.test(ln)) { list.items[list.items.length - 1] += " " + ln.trim(); continue; }
      flushL(); para.push(ln.trim());
    }
    if (code) out.push('<pre class="su-pre"><code>' + esc(code.join("\n")) + "</code></pre>");
    flushP(); flushL();
    return out.join("");
  }

  const TONE_SYN = { red: "bad", danger: "bad", error: "bad", critical: "bad", fail: "bad", green: "good", success: "good", ok: "good", pass: "good",
    yellow: "warn", amber: "warn", orange: "warn", warning: "warn", blue: "info", grey: "neutral", gray: "neutral", muted: "neutral", none: "neutral" };
  const normTone = (t) => { if (!t) return null; t = String(t).toLowerCase(); t = TONE_SYN[t] || t; return ["good", "warn", "bad", "info", "neutral"].includes(t) ? t : null; };
  const AUTO = { critical: "bad", blocker: "bad", high: "bad", severe: "bad", fail: "bad", failed: "bad", failing: "bad", error: "bad", broken: "bad", blocked: "bad", late: "bad", red: "bad", vulnerable: "bad", regressed: "bad", regression: "bad",
    medium: "warn", moderate: "warn", warn: "warn", warning: "warn", flaky: "warn", stuck: "warn", "at-risk": "warn", "at risk": "warn", skipped: "warn", pending: "warn", partial: "warn", amber: "warn", review: "warn",
    low: "info", minor: "info", info: "info", "in progress": "info", "in-progress": "info", building: "info", running: "info",
    pass: "good", passed: "good", passing: "good", ok: "good", done: "good", success: "good", fixed: "good", green: "good", merged: "good", shipped: "good", improved: "good", resolved: "good", verified: "good" };
  const SEV = ["critical", "blocker", "high", "severe", "major", "error", "fail", "failed", "medium", "moderate", "warn", "warning", "low", "minor", "info", "none"];
  const sevRank = (v) => SEV.indexOf(String(v).toLowerCase());
  function cmp(a, b) {
    if (a == null && b == null) return 0; if (a == null) return 1; if (b == null) return -1;
    const ra = sevRank(a), rb = sevRank(b);
    if (ra >= 0 && rb >= 0) return rb - ra;   // as values: critical > high > medium > low
    if (isNum(a) && isNum(b)) return a - b;
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  }
  const allSev = (xs) => xs.length > 0 && xs.every((v) => v == null || v === "—" || sevRank(v) >= 0);
  const worstFirst = (a, b) => -cmp(a, b);   // lists of groups, chips, series: worst first
  function autoTone(ds, col) {
    const d = DS[ds]; if (!d || !col) return false;
    const vals = new Set(d.rows.map((r) => r[col]).filter((v) => v != null).map((v) => String(v).toLowerCase()));
    return vals.size > 0 && vals.size <= 12 && [...vals].every((v) => v in AUTO);
  }
  function mapTone(m, v) {
    // Exact value first, then thresholds such as ">300", ">=0.1", "<0".
    if (!m || v == null) return null;
    const t = m[v] ?? m[String(v)] ?? m[String(v).toLowerCase()];
    if (t) return normTone(t);
    const n = +v;
    for (const k in m) {
      const mm = String(k).match(/^\s*(>=|<=|>|<|!=)\s*(-?[\d.]+)\s*$/);
      if (mm && isFinite(n) && ({ ">=": n >= +mm[2], "<=": n <= +mm[2], ">": n > +mm[2], "<": n < +mm[2], "!=": n !== +mm[2] })[mm[1]]) return normTone(m[k]);
    }
    return null;
  }
  function toneOf(p, row, ds, cols) {
    if (p.tone && typeof p.tone === "object") for (const c in p.tone) {
      const m = p.tone[c], v = row[c];
      if (m && typeof m === "object" && v != null) { const t = mapTone(m, v); if (t) return t; }
    }
    for (const c of arr(cols)) if (autoTone(ds, c)) return normTone(AUTO[String(row[c]).toLowerCase()]);
    return null;
  }
  function cellTone(p, ds, col, v) {
    if (v == null) return null;
    const m = p.tone && p.tone[col];
    if (m) return mapTone(m, v);
    if (autoTone(ds, col)) return normTone(AUTO[String(v).toLowerCase()]);
    return null;
  }
  function badge(text, tone, title) { return h("span", { class: "su-badge" + (tone ? " su-t-" + tone : ""), title }, text); }

  function fmt(v, f, t) {
    if (v == null || v === "") return "";
    if (Array.isArray(v)) return v.join(", ");
    if (typeof v === "object") return JSON.stringify(v);
    const n = typeof v === "number" ? v : (typeof v === "string" && /^[+-]?\d+(\.\d+)?$/.test(v) ? +v : NaN);
    switch (f) {
      case "int": return isNaN(n) ? String(v) : Math.round(n).toLocaleString("en");
      case "num": return isNaN(n) ? String(v) : n.toLocaleString("en", { maximumFractionDigits: 2 });
      case "pct": return isNaN(n) ? String(v) : n.toLocaleString("en", { maximumFractionDigits: 1 }) + "%";
      case "ratio": return isNaN(n) ? String(v) : (n * 100).toLocaleString("en", { maximumFractionDigits: 1 }) + "%";
      case "ms": return isNaN(n) ? String(v) : n >= 1000 ? (n / 1000).toLocaleString("en", { maximumFractionDigits: 2 }) + " s" : Math.round(n * 10) / 10 + " ms";
      case "s": return isNaN(n) ? String(v) : n >= 120 ? (n / 60).toFixed(1) + " min" : n.toLocaleString("en", { maximumFractionDigits: 2 }) + " s";
      case "bytes": { if (isNaN(n)) return String(v); const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0, x = n; while (x >= 1024 && i < 4) { x /= 1024; i++; } return x.toLocaleString("en", { maximumFractionDigits: 1 }) + " " + u[i]; }
      case "money": { if (isNaN(n)) return String(v); const a = Math.abs(n), cur = PLAN.currency || "$";
        const sym = /^[A-Z]{3}$/.test(cur) ? ({ NZD: "$", USD: "$", AUD: "$", CAD: "$", EUR: "€", GBP: "£", JPY: "¥" }[cur] || cur + " ") : cur;
        return (n < 0 ? "−" : "") + sym + a.toLocaleString("en", { minimumFractionDigits: a < 100 && !Number.isInteger(a) ? 2 : 0, maximumFractionDigits: a < 100 ? 2 : 0 }); }
      case "k": return isNaN(n) ? String(v) : Math.abs(n) >= 1e6 ? (n / 1e6).toFixed(1) + "M" : Math.abs(n) >= 1e3 ? (n / 1e3).toFixed(1) + "k" : String(n);
      case "date": return String(v).slice(0, 10);
      case "time": return String(v).replace("T", " ").slice(0, 16);
      case "delta": return isNaN(n) ? String(v) : (n > 0 ? "+" : n < 0 ? "−" : "") + Math.abs(n).toLocaleString("en", { maximumFractionDigits: 2 });
      default:
        if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString("en") : v.toLocaleString("en", { maximumFractionDigits: 2 });
        if (typeof v === "boolean") return v ? "yes" : "no";
        if (t === "date" && /T\d/.test(v)) return String(v).replace("T", " ").slice(0, 16);
        return String(v);
    }
  }
  function fmtCell(v, f, t, good) {
    if (f === "md") return h("span", { class: "su-md", html: inline(v ?? "") });
    if (f === "code") return v == null ? "" : h("code", { class: "su-code-inline" }, String(v));
    if (f === "delta") {
      const s = fmt(v, f, t); const n = parseFloat(String(v));
      if (!good || !n) return s;
      const ok = (n > 0) === (good === "up");
      return h("span", { style: { color: ok ? "var(--good-ink)" : "var(--bad-ink)" } }, s);
    }
    return fmt(v, f, t);
  }

  // ---- data -----------------------------------------------------------------------
  function matchWhere(row, where) {
    for (const k in where) {
      const want = where[k], v = row[k];
      if (v == null && !(typeof want === "string" && want.startsWith("!="))) return false;
      if (Array.isArray(want)) { if (!want.map(String).includes(String(v))) return false; }
      else if (typeof want === "string" && /^(>=|<=|>|<|!=)/.test(want)) {
        const m = want.match(/^(>=|<=|>|<|!=)\s*(.*)$/), x = isNum(v) ? +m[2] : m[2];
        if (!({ ">=": v >= x, "<=": v <= x, ">": v > x, "<": v < x, "!=": String(v) !== String(m[2]) })[m[1]]) return false;
      } else if (String(v) !== String(want)) return false;
    }
    return true;
  }
  function rowsFor(p, own) {
    const d = DS[p.data]; if (!d) return [];
    let rows = d.rows;
    if (p.where) rows = rows.filter((r) => matchWhere(r, p.where));
    const f = FILT[p.data];
    if (f) {
      for (const c in f.f) if (f.f[c].size && !(own && own.includes(c))) rows = rows.filter((r) => f.f[c].has(String(r[c])));
      if (f.q) { const q = f.q.toLowerCase(); rows = rows.filter((r) => Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(q))); }
    }
    return rows;
  }
  const typeOf = (ds, c) => (DS[ds] && DS[ds].types[c]) || "str";
  const uniq = (rows, c) => { const s = new Map(); for (const r of rows) { const v = r[c]; if (v != null && !s.has(String(v))) s.set(String(v), v); } return [...s.values()]; };
  function subscribe(ds, fn) { (SUBS[ds] = SUBS[ds] || []).push(fn); }
  const fstate = (ds) => (FILT[ds] = FILT[ds] || { f: {}, q: "" });
  function picked(ds, col) { const f = FILT[ds]; return f && f.f[col] && f.f[col].size ? f.f[col] : null; }
  function toggleFilter(ds, pairs) {
    // Click on a mark: select its value(s); click the same mark again to clear.
    const f = fstate(ds);
    const same = pairs.every(([c, v]) => f.f[c] && f.f[c].size === 1 && f.f[c].has(String(v)));
    for (const [c, v] of pairs) f.f[c] = new Set(same ? [] : [String(v)]);
    notify(ds);
  }
  function notify(ds) { for (const fn of SUBS[ds] || []) fn(); }
  function groupBy(rows, col) {
    const m = new Map();
    for (const r of rows) { const k = r[col] == null ? "—" : String(r[col]); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    const keys = [...m.keys()];
    if (allSev(keys)) keys.sort(worstFirst);
    return keys.map((k) => [k, m.get(k)]);
  }
  function localControls(p, ds, onChange) {
    // Local filter dropdowns and a search box for one table or list.
    const st = { f: {}, q: "" };
    let cols = p.filter === true ? (DS[ds].cols.filter((c) => typeOf(ds, c) === "str" && uniq(DS[ds].rows, c).length > 1 && uniq(DS[ds].rows, c).length <= 12)) : arr(p.filter).map(colKey);
    if (!cols.length && !p.search) return { el: null, apply: (r) => r };
    const bar = h("div", { class: "su-ctl" });
    if (p.search) bar.append(h("input", { type: "search", placeholder: "Search…", "aria-label": "Search", id: "su-q" + ++uid, oninput: (e) => { st.q = e.target.value.toLowerCase(); onChange(); } }));
    for (const c of cols) {
      const vals = uniq(DS[ds].rows, c); vals.sort(allSev(vals) ? worstFirst : cmp);
      const sel = h("select", { "aria-label": c, id: "su-f" + ++uid, onchange: (e) => { st.f[c] = e.target.value; onChange(); } },
        h("option", { value: "" }, `${c}: all`), vals.map((v) => h("option", { value: String(v) }, String(v))));
      bar.append(sel);
    }
    return { el: bar, apply: (rows) => rows.filter((r) => Object.entries(st.f).every(([c, v]) => !v || String(r[c]) === v) && (!st.q || Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(st.q)))) };
  }

  // ---- components -----------------------------------------------------------------
  const C = {};
  const BOXED = new Set(["chart", "heatmap", "gantt", "tree", "kv", "checklist", "timeline", "meter", "diagram", "graph", "filter", "box", "treemap", "sankey", "er", "classes"]);

  C.text = (p, el) => { el.className += " su-md"; el.innerHTML = md(p.md); };
  C.callout = (p, el) => {
    const t = normTone(p.tone) || "info";
    const icon = { good: "✓", warn: "!", bad: "✕", info: "i", neutral: "•" }[t];
    el.append(h("div", { class: "su-callout su-t-" + t, role: t === "bad" || t === "warn" ? "alert" : "note" },
      h("span", { class: "su-callout-i", "aria-hidden": "true" }, icon), h("div", { class: "su-callout-b su-md", html: md(p.text) })));
  };
  C.kv = (p, el) => {
    const dl = h("dl", { class: "su-kv", "--kvc": p.cols || 1 });
    let pairs = p.pairs || {};
    if (p.data && DS[p.data]) {
      const rows = DS[p.data].rows, cols = DS[p.data].cols;
      pairs = cols.length === 2 && cols[0] === "key" ? Object.fromEntries(rows.map((r) => [r.key, r.value])) : (rows[0] || {});
      if (p.keys) pairs = Object.fromEntries(arr(p.keys).filter((k) => k in pairs).map((k) => [k, pairs[k]]));
    }
    for (const k in pairs) dl.append(h("dt", null, k), h("dd", { html: inline(fmt(pairs[k])) }));
    el.append(dl);
  };
  C.meter = (p, el) => {
    const max = p.max || 100, pct = Math.max(0, Math.min(100, (p.value / max) * 100));
    const t = normTone(p.tone);
    el.append(h("div", { class: "su-meter" + (t ? " su-t-" + t : "") },
      h("div", { class: "su-meter-l" }, h("span", null, p.label || ""), h("span", null, `${fmt(p.value)} / ${fmt(max)}`)),
      h("div", { class: "su-meter-t", role: "meter", "aria-valuenow": p.value, "aria-valuemax": max, "aria-label": p.label || "progress" },
        h("div", { class: "su-meter-f", style: { width: pct + "%" } }))));
  };
  function spark(vals) {
    vals = arr(vals).map(Number).filter(isFinite); if (vals.length < 2) return null;
    const W = 120, H = 30, lo = Math.min(...vals), hi = Math.max(...vals), sp = hi - lo || 1;
    const pts = vals.map((v, i) => [(i / (vals.length - 1)) * (W - 4) + 2, H - 3 - ((v - lo) / sp) * (H - 6)]);
    const d = pts.map((q, i) => (i ? "L" : "M") + q[0].toFixed(1) + " " + q[1].toFixed(1)).join("");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("preserveAspectRatio", "none"); svg.setAttribute("class", "su-spark");
    svg.innerHTML = `<path class="a" d="${d}L${pts[pts.length - 1][0]} ${H}L${pts[0][0]} ${H}Z"/><path class="l" d="${d}" vector-effect="non-scaling-stroke"/>`;
    const last = pts[pts.length - 1];
    const dot = h("i", { style: { position: "absolute" } });
    return [svg, last, dot];
  }
  function statEl(p) {
    const t = normTone(p.tone);
    const box = h("div", { class: "su-stat" + (t ? " su-tone su-t-" + t : "") });
    box.append(h("div", { class: "su-stat-l" }, p.label ?? ""));
    const v = h("div", { class: "su-stat-v" + (p.value == null || p.value === "" ? " su-novalue" : "") }, typeof p.value === "number" ? fmt(p.value, p.fmt) : String(p.value ?? "—"));
    if (p.unit) v.append(h("span", { class: "su-stat-u" }, p.unit));
    if (p.delta != null && p.delta !== "") {
      const s = String(p.delta), n = parseFloat(s.replace(/[^\d.+-]/g, "")), up = s.trim().startsWith("-") || s.trim().startsWith("−") ? false : n > 0 ? true : n < 0 ? false : null;
      const good = (p.good || "up") === "up";
      const cls = up == null ? "" : up ? (good ? "su-up-good" : "su-up-bad") : (good ? "su-down-bad" : "su-down-good");
      const txt = (isNum(p.delta) && p.delta > 0 ? "+" : "") + s.replace(/^-/, "−");
      v.append(h("span", { class: "su-stat-d " + cls }, (up == null ? "" : up ? "▲ " : "▼ ") + txt.replace(/^[+−]/, "")));
    }
    box.append(v);
    if (p.sub) box.append(h("div", { class: "su-stat-s" }, p.sub));
    const sp = spark(p.spark); if (sp) box.append(sp[0]);
    return box;
  }
  function aggValue(p, col) {
    const rows = rowsFor(p), agg = p.agg || (col || p.col ? "sum" : "count"), c = col || p.col;
    if (agg === "count" && !col) return rows.length;
    const v = rows.map((r) => +r[c]).filter(isFinite);
    if (!v.length) return null;
    return agg === "sum" ? v.reduce((a, b) => a + b, 0) : agg === "mean" ? v.reduce((a, b) => a + b, 0) / v.length : agg === "min" ? Math.min(...v) : Math.max(...v);
  }
  function liveStat(p) {
    // A stat whose value comes from data: agg of col, optional `of` (n / total) and `vs` (delta against a column).
    if (!p.data) return p;
    const v = aggValue(p);
    const of = p.of ? (p.of === true ? rowsFor({ ...p, where: null }).length : p.of) : null;
    const out = { ...p, value: v, unit: of != null ? `/ ${fmt(of)}` : p.unit, sub: p.sub ?? (of ? `${Math.round((100 * v) / (of || 1))}%` : null) };
    if (p.vs) {
      const b = aggValue(p, p.vs), d = v - b, good = (p.good || "up") === "up";
      out.delta = (d >= 0 ? "+" : "-") + fmt(Math.abs(d), p.fmt) + (b ? ` (${(d >= 0 ? "+" : "-") + Math.abs((100 * d) / b).toFixed(1)}%)` : "");
      out.sub = p.sub ?? `vs ${fmt(b, p.fmt)} ${p.vs_label || String(p.vs).replace(/_/g, " ")}`;
      if (!p.tone && d) out.tone = (d > 0) === good ? "good" : "bad";
    }
    return out;
  }
  C.stat = (p, el) => {
    if (!p.data) { el.append(statEl(p)); return; }
    const draw = () => el.replaceChildren(statEl(liveStat(p)));
    draw(); subscribe(p.data, draw);
  };
  C.stats = (p, el) => {
    const grid = h("div", { class: "su-stats" });
    const draw = () => {
      grid.innerHTML = "";
      let items = arr(p.items);
      if (p.data && p.by && !p.cols) {
        const rows = rowsFor(p, [p.by]), groups = groupBy(rows, p.by);
        const order = p.order ? arr(p.order).map(String) : groups.map((g) => g[0]);
        const m = new Map(groups);
        items = (p.total ? [{ label: p.total === true ? "Total" : p.total, value: rows.length }] : [])
          .concat(order.map((k) => ({ label: k, value: (m.get(k) || []).length, tone: cellTone(p, p.data, p.by, k) || undefined, _pick: k })));
      } else if (p.data && !p.cols) {
        const rows = rowsFor(p), d = DS[p.data];
        const lc = p.label || d.cols.find((c) => typeOf(p.data, c) === "str") || d.cols[0];
        const vc = p.value || d.cols.find((c) => typeOf(p.data, c) === "num") || d.cols[1];
        items = rows.map((r) => ({ label: r[lc], value: r[vc], tone: p.tone ? r[p.tone] : null, delta: r.delta, unit: r.unit, sub: r.sub, good: r.good }));
      }
      if (p.data && p.cols) items = arr(p.cols).map((c) => { c = colKey(c); return { label: (p.labels && p.labels[c]) || c, value: aggValue(p, c) }; });
      items = items.map((it) => (it && typeof it === "object" ? liveStat({ fmt: p.fmt, ...it }) : it));
      const sel = p.by && picked(p.data, p.by);
      for (const it of items) {
        const t = statEl(typeof it === "object" ? it : { label: "", value: it });
        if (it && it._pick != null) {
          t.classList.add("su-click"); t.tabIndex = 0; t.setAttribute("role", "button");
          if (sel && !sel.has(String(it._pick))) t.classList.add("su-dim");
          const go = () => toggleFilter(p.data, [[p.by, it._pick]]);
          t.addEventListener("click", go); t.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
        }
        grid.append(t);
      }
    };
    draw(); if (p.data) subscribe(p.data, draw);
    for (const ds2 of new Set(arr(p.items).map((it) => it && it.data).filter(Boolean))) subscribe(ds2, draw);
    el.append(grid);
  };

  function headCell(c, ds, p, sortState, redraw) {
    const key = colKey(c), label = (typeof c === "object" && c.label) || key;
    const th = h("th", { scope: "col", class: typeOf(ds, key) === "num" ? "su-num" : "" }, label);
    if (sortState.k === key) th.setAttribute("aria-sort", sortState.d > 0 ? "ascending" : "descending");
    th.addEventListener("click", () => { sortState.d = sortState.k === key ? -sortState.d : (typeOf(ds, key) === "num" ? -1 : 1); sortState.k = key; redraw(); });
    return th;
  }
  C.table = (p, el) => {
    const ds = p.data, d = DS[ds];
    const cols = (p.cols && p.cols.length ? p.cols : d.cols.filter((c) => c !== p.group)).map((c) => (typeof c === "object" ? c : { key: c }))
      .map((c) => (p.labels && p.labels[c.key] && !c.label ? { ...c, label: p.labels[c.key] } : c));
    const sort = { k: null, d: 1 };
    if (p.sort) { sort.k = p.sort.replace(/^-/, ""); sort.d = p.sort.startsWith("-") ? -1 : 1; }
    const shut = new Set();
    let page = 0;
    const wrap = h("div", { class: "su-tw" + (p.h ? " su-scroll" : ""), style: p.h ? { maxHeight: p.h + "px" } : null });
    // A table with more than four columns that does not fit its box becomes one card per row.
    const fit = () => {
      if (cols.length <= 4 || p.stack === false || !wrap.clientWidth) return;
      wrap.classList.remove("su-stacked");
      if (wrap.scrollWidth > wrap.clientWidth + 2) wrap.classList.add("su-stacked");
    };
    let lastW = 0;
    new ResizeObserver(() => { const w = wrap.parentElement ? wrap.parentElement.clientWidth : 0; if (w !== lastW) { lastW = w; fit(); } }).observe(el);
    const ctl = localControls(p, ds, () => { page = 0; draw(); });
    if (ctl.el) el.append(ctl.el);
    el.append(wrap);
    const bars = new Set(arr(p.bar).map(colKey));
    const expand = arr(p.expand).map(colKey), open = new Set();
    if (expand.length) {
      const btn = h("button", { class: "su-btn", type: "button" }, "Expand all");
      btn.addEventListener("click", () => { const all = open.size === 0; if (all) rowsFor(p).forEach((r) => open.add(r)); else open.clear(); btn.textContent = all ? "Collapse all" : "Expand all"; draw(); });
      (ctl.el || el.insertBefore(h("div", { class: "su-ctl" }), wrap)).append(btn);
    }
    function draw() {
      let rows = ctl.apply(rowsFor(p)).slice();
      if (sort.k) rows.sort((a, b) => sort.d * cmp(a[sort.k], b[sort.k]) || 0);
      if (p.top) rows = rows.slice(0, p.top);
      const max = {}; for (const b of bars) max[b] = Math.max(1e-9, ...rows.map((r) => Math.abs(+r[b] || 0)));
      const total = rows.length;
      const lim = p.limit && !p.group ? p.limit : 0;
      if (lim) rows = rows.slice(page * lim, page * lim + lim);
      const t = h("table", { class: "su-table" + (p.dense ? " su-dense" : "") });
      const tr = h("tr"); for (const c of cols) tr.append(headCell(c, ds, p, sort, draw));
      t.append(h("thead", null, tr));
      const tb = h("tbody");
      const short = new Set(cols.map((c) => c.key).filter((k) => rows.slice(0, 50).every((r) => r[k] == null || String(r[k]).length <= 12)));
      const rowEl = (r) => {
        const row = h("tr", expand.length ? { class: "su-xrow" + (open.has(r) ? " su-open" : ""), onclick: () => { open.has(r) ? open.delete(r) : open.add(r); draw(); } } : null);
        for (const c of cols) {
          const k = c.key, ty = typeOf(ds, k), f = c.fmt || (p.fmt && p.fmt[k]), v = r[k];
          const td = h("td", { class: (ty === "num" ? "su-num" : "") + (ty === "date" ? " su-mono" : "") + (short.has(k) ? " su-nw" : ""), "data-label": c.label || k });
          const tone = cellTone(p, ds, k, v);
          if (bars.has(k) && isNum(+v)) td.append(h("div", { class: "su-cellbar" }, h("i", { style: { width: Math.round((Math.abs(+v) / max[k]) * 80) + "px" } }), h("span", null, fmt(v, f, ty))));
          else if (tone) td.append(badge(fmt(v, f, ty), tone));
          else { const x = fmtCell(v, f, ty, p.good && p.good[k]); td.append(x); }
          row.append(td);
        }
        if (!expand.length || !open.has(r)) return row;
        const det = h("div", { class: "su-xdet" });
        for (const k of expand) {
          const v = r[k]; if (v == null || v === "") continue;
          det.append(h("div", { class: "su-xk" }, k));
          det.append(/\n/.test(String(v)) || (p.fmt && p.fmt[k] === "code") ? codeEl({ src: String(v) }) : h("div", { class: "su-md", html: md(String(v)) }));
        }
        return [row, h("tr", { class: "su-xtr" }, h("td", { colspan: cols.length }, det))];
      };
      if (p.group) {
        let gs = groupBy(rows, p.group);
        if (p.order) { const o = arr(p.order).map(String); gs = gs.sort((a, b) => (o.indexOf(a[0]) + 1 || 1e9) - (o.indexOf(b[0]) + 1 || 1e9)); }
        for (const [k, rs] of gs) {
          const tone = cellTone(p, ds, p.group, k);
          const g = h("tr", { class: "su-grp" + (shut.has(k) ? " su-shut" : ""), onclick: () => { shut.has(k) ? shut.delete(k) : shut.add(k); draw(); } },
            h("td", { colspan: cols.length }, tone ? badge(k, tone) : k, " ", h("span", { class: "su-count" }, rs.length)));
          tb.append(g);
          if (!shut.has(k)) rs.forEach((r) => tb.append(...[rowEl(r)].flat()));
        }
      } else rows.forEach((r) => tb.append(...[rowEl(r)].flat()));
      if (!total) tb.append(h("tr", null, h("td", { colspan: cols.length, class: "su-empty" }, "No rows match.")));
      t.append(tb);
      wrap.replaceChildren(t);
      requestAnimationFrame(fit);
      if (lim && total > lim) {
        const pages = Math.ceil(total / lim);
        wrap.append(h("div", { class: "su-pager" }, h("span", null, `${page * lim + 1}–${Math.min(total, page * lim + lim)} of ${total}`),
          h("span", null, h("button", { class: "su-btn", disabled: page === 0, onclick: () => { page--; draw(); } }, "Prev"), " ",
            h("button", { class: "su-btn", disabled: page >= pages - 1, onclick: () => { page++; draw(); } }, "Next"))));
      }
    }
    draw(); subscribe(ds, draw);
  };

  function itemEl(p, ds, r, cls) {
    const tone = toneOf(p, r, ds, arr(p.badges).concat(p.group ? [p.group] : []));
    const badges = h("span", { class: "su-badges" }, arr(p.badges).map((b) => { b = colKey(b); return r[b] == null || r[b] === "" ? null : badge(fmt(r[b], p.fmt && p.fmt[b], typeOf(ds, b)), cellTone(p, ds, b, r[b]), b); }));
    const head = h("div", { class: "su-item-h" }, h("span", { html: inline(r[p.head] ?? "") }), badges);
    const parts = [];
    if (p.body && r[p.body] != null) parts.push(h("div", { class: "su-item-b su-md", html: md(r[p.body]) }));
    if (p.code && r[p.code] != null) parts.push(codeEl({ src: String(r[p.code]), lang: p.lang }));
    const st = tone ? { "--tone": `var(--${tone})` } : null;
    if (p.collapse && parts.length) return h("details", { class: cls + (tone ? " su-t-" + tone : ""), style: st }, h("summary", null, head), parts);
    return h("div", { class: cls + (tone ? " su-t-" + tone : ""), style: st }, head, parts);
  }
  C.list = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-list" });
    const ctl = localControls(p, ds, () => draw());
    if (ctl.el) el.append(ctl.el);
    el.append(box);
    function draw() {
      const rows = ctl.apply(rowsFor(p));
      box.replaceChildren();
      if (!rows.length) box.append(h("div", { class: "su-empty" }, "No items match."));
      if (p.group) for (const [k, rs] of groupBy(rows, p.group)) {
        const t = cellTone(p, ds, p.group, k);
        box.append(h("div", { class: "su-gh" }, t ? h("span", { class: "su-dot su-t-" + t }) : null, k, h("span", { class: "su-count" }, rs.length)));
        rs.forEach((r) => box.append(itemEl(p, ds, r, "su-item")));
      } else rows.forEach((r) => box.append(itemEl(p, ds, r, "su-item")));
    }
    draw(); subscribe(ds, draw);
  };
  C.board = (p, el) => {
    const ds = p.data, board = h("div", { class: "su-board" });
    el.append(board);
    function draw() {
      const rows = rowsFor(p);
      const lanes = p.order ? arr(p.order).map(String) : uniq(DS[ds].rows, p.by).map(String);
      for (const v of uniq(rows, p.by).map(String)) if (!lanes.includes(v)) lanes.push(v);
      board.replaceChildren();
      for (const lane of lanes) {
        const rs = rows.filter((r) => String(r[p.by]) === lane);
        const col = h("div", { class: "su-lane" }, h("div", { class: "su-lane-h" }, h("span", null, lane), h("span", { class: "su-count" }, rs.length)));
        for (const r of rs) {
          const tone = toneOf(p, r, ds, arr(p.badges));
          col.append(h("div", { class: "su-bcard" + (tone ? " su-t-" + tone : ""), style: tone ? { "--tone": `var(--${tone})` } : null },
            h("b", { html: inline(r[p.head] ?? "") }),
            p.body && r[p.body] ? h("div", { class: "su-md", style: { marginBottom: "4px", color: "var(--muted)" }, html: inline(r[p.body]) }) : null,
            h("div", { class: "su-badges" }, arr(p.badges).map((b) => { b = colKey(b); return r[b] == null ? null : badge(fmt(r[b]), cellTone(p, ds, b, r[b]), b); }))));
        }
        if (!rs.length) col.append(h("div", { class: "su-empty" }, "Empty"));
        board.append(col);
      }
    }
    draw(); subscribe(ds, draw);
  };
  C.checklist = (p, el) => {
    let items = arr(p.items).map((it) => {
      if (typeof it === "object") return { text: it.text ?? it.label ?? it.name ?? "", done: !!(it.done ?? it.checked) };
      const m = String(it).match(/^\s*\[( |x|X|✓)?\]\s*(.*)$/);
      return m ? { text: m[2], done: !!(m[1] && m[1].trim()) } : { text: String(it), done: false };
    });
    if (p.data) items = rowsFor(p).map((r) => ({ text: r[p.text || "text"], done: ["true", "yes", "done", "1", "x"].includes(String(r[p.done || "done"]).toLowerCase()) }));
    const n = items.filter((i) => i.done).length;
    el.append(h("ul", { class: "su-check" }, items.map((i) => h("li", { class: i.done ? "su-done" : "" }, h("i", { "aria-hidden": "true" }, i.done ? "✓" : ""), h("span", { html: inline(i.text) }), h("span", { class: "su-visually-hidden", style: { display: "none" } }, i.done ? " (done)" : "")))));
    el.append(h("div", { class: "su-note" }, `${n} of ${items.length} done`));
  };
  C.timeline = (p, el) => {
    const ds = p.data, ol = h("ol", { class: "su-tl" }); el.append(ol);
    const draw = () => {
      ol.replaceChildren();
      for (const r of rowsFor(p).slice().sort((a, b) => cmp(a[p.at], b[p.at]))) {
        const tone = toneOf(p, r, ds, arr(p.badges));
        ol.append(h("li", { style: tone ? { "--tone": `var(--${tone})` } : null }, h("time", null, fmt(r[p.at], null, typeOf(ds, p.at))),
          h("span", { html: inline(r[p.text] ?? "") }),
          h("span", { class: "su-badges" }, arr(p.badges).map((b) => { b = colKey(b); return r[b] == null ? null : badge(fmt(r[b]), cellTone(p, ds, b, r[b]), b); }))));
      }
    };
    draw(); subscribe(ds, draw);
  };
  const DAY = 86400000;
  const toTime = (v) => (isNum(v) ? v : Date.parse(String(v).length === 10 ? v + "T00:00:00Z" : v));
  C.gantt = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-gantt" }); el.append(box);
    const draw = () => {
      const rows = rowsFor(p).map((r) => {
        const s = toTime(r[p.start]); let e = p.end ? toTime(r[p.end]) : NaN;
        if (isNaN(e) && p.days) e = s + (+r[p.days] || 1) * DAY;
        if (isNaN(e)) e = s + DAY;
        return { r, s, e };
      }).filter((x) => !isNaN(x.s));
      box.replaceChildren();
      if (!rows.length) { box.append(h("div", { class: "su-empty" }, "No tasks with a start date.")); return; }
      let lo = Math.min(...rows.map((x) => x.s)), hi = Math.max(...rows.map((x) => x.e));
      const today = p.today ? toTime(p.today) : NaN;
      if (!isNaN(today)) { lo = Math.min(lo, today); hi = Math.max(hi, today); }
      const span = hi - lo || DAY, pos = (t) => ((t - lo) / span) * 100;
      const inner = h("div", { class: "su-gantt-in" });
      const cap = Math.max(3, Math.floor(((box.clientWidth || 600) * 0.66) / 64));
      const days = span / DAY, step = [1, 2, 7, 14, 30, 61, 91, 182, 365].find((s) => days / s <= cap) || 365;
      const ticks = h("div", { class: "su-g-ticks" });
      for (let t = lo; t <= hi; t += step * DAY) ticks.append(h("span", { style: { left: pos(t) + "%" } }, shortDate(new Date(t).toISOString().slice(0, 10), [])));
      inner.append(h("div", { class: "su-g-axis" }, h("div"), ticks));
      const groups = p.group ? groupBy(rows.map((x) => ({ ...x.r, __x: x })), p.group).map(([k, rs]) => [k, rs.map((r) => r.__x)]) : [[null, rows]];
      for (const [g, xs] of groups) {
        if (g != null) inner.append(h("div", { class: "su-g-row su-g-grp" }, h("div", { class: "su-g-name" }, g), h("div")));
        for (const x of xs) {
          const tone = toneOf(p, x.r, ds, []);
          const track = h("div", { class: "su-g-track" }, h("div", { class: "su-g-bar", style: { left: pos(x.s) + "%", width: Math.max(0.6, pos(x.e) - pos(x.s)) + "%", ...(tone ? { "--tone": `var(--${tone})` } : {}) },
            title: `${x.r[p.task]}: ${new Date(x.s).toISOString().slice(0, 10)} → ${new Date(x.e).toISOString().slice(0, 10)}` }));
          if (!isNaN(today)) track.append(h("div", { class: "su-g-today", style: { left: pos(today) + "%" } }));
          inner.append(h("div", { class: "su-g-row" }, h("div", { class: "su-g-name", title: x.r[p.task] }, x.r[p.task] ?? ""), track));
        }
      }
      box.append(inner);
    };
    draw(); subscribe(ds, draw);
    let lastW = 0; new ResizeObserver(() => { const w = box.clientWidth; if (Math.abs(w - lastW) > 60) { lastW = w; draw(); } }).observe(box);
  };
  C.tree = (p, el) => {
    const ds = p.data;
    const draw = () => {
      const root = { kids: new Map(), row: null };
      const pc = p.path || (p.data && DS[p.data].cols.includes("path") ? "path" : "value");
      const items = p.data ? rowsFor(p).map((r) => [String(r[pc] ?? ""), r]) : arr(p.paths).map((s) => [String(s), null]);
      const sep = p.sep || (items.some(([x]) => x.includes(" > ")) ? ">" : "/");
      for (const [path, r] of items) {
        let n = root;
        for (const part of path.split(sep).map((x) => x.trim()).filter(Boolean)) { if (!n.kids.has(part)) n.kids.set(part, { kids: new Map(), row: null }); n = n.kids.get(part); }
        n.row = r || n.row;
      }
      const ul = (n, depth) => {
        const list = h("ul");
        const entries = [...n.kids.entries()].sort((a, b) => (b[1].kids.size > 0) - (a[1].kids.size > 0) || a[0].localeCompare(b[0]));
        for (let [name, k] of entries) {
          while (sep === "/" && k.kids.size === 1 && !k.row && [...k.kids.values()][0].kids.size) { const [n2, k2] = [...k.kids.entries()][0]; name += "/" + n2; k = k2; }
          if (k.kids.size) list.append(h("li", null, h("details", { open: depth < (p.open ?? 2) }, h("summary", null, name + (sep === "/" ? "/" : ""), h("span", { class: "su-count" }, " " + countLeaves(k))), ul(k, depth + 1))));
          else {
            const r = k.row, tone = r ? toneOf(p, r, ds, arr(p.badges)) : null;
            list.append(h("li", null, h("div", { class: "su-leafrow" }, tone ? h("span", { class: "su-dot su-t-" + tone }) : null, h("span", null, name),
              r ? h("span", { class: "su-badges" }, arr(p.badges).map((b) => { b = colKey(b); return r[b] == null || r[b] === "" ? null : badge(fmt(r[b]), cellTone(p, ds, b, r[b]), b); })) : null)));
          }
        }
        return list;
      };
      el.replaceChildren(h("div", { class: "su-tree" }, ul(root, 0)));
    };
    const countLeaves = (n) => (n.kids.size ? [...n.kids.values()].reduce((a, k) => a + countLeaves(k), 0) : 1);
    draw(); if (ds) subscribe(ds, draw);
  };
  C.filter = (p, el) => {
    const ds = p.data, f = fstate(ds);
    const box = h("div", { class: "su-filter" });
    const count = h("span", { class: "su-count" });
    const chipEls = [];
    const upd = () => {
      count.textContent = `${rowsFor(p).length} of ${DS[ds].rows.length} rows`;
      for (const { b, c, v, n } of chipEls) {
        const on = !!(f.f[c] && f.f[c].has(String(v)));
        b.setAttribute("aria-pressed", on);
        n.textContent = rowsFor(p, [c]).filter((r) => String(r[c]) === String(v)).length;
      }
    };
    if (p.search !== false) box.append(h("div", { class: "su-ctl", style: { marginBottom: 0 } }, h("input", { type: "search", placeholder: "Search…", "aria-label": "Search", id: "su-s" + ++uid, oninput: (e) => { f.q = e.target.value; notify(ds); } }), count));
    for (const c0 of arr(p.fields)) {
      const c = colKey(c0); f.f[c] = f.f[c] || new Set();
      const row = h("div", { class: "su-filter-row" }, h("b", null, c));
      const chips = h("div", { class: "su-chips" });
      const chipVals = uniq(DS[ds].rows, c); chipVals.sort(allSev(chipVals) ? worstFirst : cmp);
      for (const v of chipVals) {
        const t = cellTone(p, ds, c, v);
        const n = h("span", { class: "su-chip-n" });
        const b = h("button", { class: "su-chip", "aria-pressed": "false", type: "button" }, t ? h("span", { class: "su-dot su-t-" + t, style: { marginRight: "5px" } }) : null, String(v), n);
        b.addEventListener("click", () => { const s = f.f[c] = f.f[c] || new Set(), k = String(v); s.has(k) ? s.delete(k) : s.add(k); notify(ds); });
        chips.append(b); chipEls.push({ b, c, v, n });
      }
      row.append(chips); box.append(row);
    }
    el.append(box); upd(); subscribe(ds, upd);
  };

  // ---- finance, statistics, structure ----------------------------------------------
  C.statement = (p, el) => {
    const ds = p.data, vals = arr(p.values).map(colKey), minus = new Set(arr(p.minus).map(String)), f = p.fmt || "money";
    const wrap = h("div", { class: "su-tw" }); el.append(wrap);
    const draw = () => {
      const rows = rowsFor(p), secs = new Map();
      for (const r of rows) {
        const sec = String(r[p.section] ?? "—"), ln = String(r[p.line] ?? "—");
        if (!secs.has(sec)) secs.set(sec, new Map());
        const m = secs.get(sec); if (!m.has(ln)) m.set(ln, vals.map(() => 0));
        const a = m.get(ln); vals.forEach((v, i) => (a[i] += +r[v] || 0));
      }
      const order = p.order ? arr(p.order).map(String).filter((x) => secs.has(x)).concat([...secs.keys()].filter((x) => !arr(p.order).map(String).includes(x))) : [...secs.keys()];
      const variance = p.variance !== false && vals.length === 2;
      const t = h("table", { class: "su-table su-stmt", style: { "--nc": vals.length + (p.variance !== false && vals.length === 2 ? 1 : 0) } });
      const head = h("tr", null, h("th", null, ""), vals.map((v) => h("th", { class: "su-num" }, (p.labels && p.labels[v]) || v)),
        variance ? [h("th", { class: "su-num" }, "Variance"), h("th", { class: "su-num" }, "%")] : null);
      t.append(h("thead", null, head));
      const tb = h("tbody"), run = vals.map(() => 0);
      const cells = (a, sign, strong) => {
        const out = a.map((x) => h("td", { class: "su-num" + (strong ? " su-strong" : "") }, fmt(x, f)));
        if (variance) {
          const d = a[0] - a[1], pc = a[1] ? (100 * d) / Math.abs(a[1]) : null, good = sign * d >= 0;
          const col = Math.abs(d) < 1e-9 ? "" : good ? "var(--good-ink)" : "var(--bad-ink)";
          out.push(h("td", { class: "su-num", style: { color: col } }, (d > 0 ? "+" : d < 0 ? "−" : "") + fmt(Math.abs(d), f)),
            h("td", { class: "su-num", style: { color: col } }, pc == null ? "" : (pc > 0 ? "+" : pc < 0 ? "−" : "") + Math.abs(pc).toFixed(1) + "%"));
        }
        return out;
      };
      const subs = arr(p.subtotals);
      for (const sec of order) {
        const sign = minus.has(sec) ? -1 : 1, lines = secs.get(sec), tot = vals.map(() => 0);
        tb.append(h("tr", { class: "su-stmt-sec" }, h("td", { colspan: 1 + vals.length + (variance ? 2 : 0) }, sec)));
        for (const [ln, a] of lines) { a.forEach((x, i) => (tot[i] += x)); tb.append(h("tr", null, h("td", { class: "su-stmt-line" }, ln), cells(a, sign))); }
        tb.append(h("tr", { class: "su-stmt-tot" }, h("td", null, "Total " + sec.toLowerCase()), cells(tot, sign, true)));
        tot.forEach((x, i) => (run[i] += sign * x));
        for (const st of subs.filter((x) => String(x.after) === sec)) tb.append(h("tr", { class: "su-stmt-sub" }, h("td", null, st.label), cells(run.slice(), 1, true)));
      }
      t.append(tb); wrap.replaceChildren(t);
    };
    draw(); subscribe(ds, draw);
  };

  function quart(v) {
    const q = (p) => { const i = (v.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i); return v[lo] + (v[hi] - v[lo]) * (i - lo); };
    return { q1: q(0.25), med: q(0.5), q3: q(0.75) };
  }
  const svgEl = (w, hgt, inner, cls) => { const s2 = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s2.setAttribute("viewBox", `0 0 ${w} ${hgt}`); s2.setAttribute("width", "100%"); s2.setAttribute("class", cls || ""); s2.innerHTML = inner; return s2; };
  function niceTicks(lo, hi, n) {
    const raw = (hi - lo) / (n || 5) || 1, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((k) => k >= raw);
    const out = []; for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(+t.toFixed(10)); return out;
  }
  C.box = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-box" }); el.append(box);
    const draw = () => {
      const rows = rowsFor(p), groups = p.by ? groupBy(rows, p.by) : [[p.y, rows]];
      const stats = groups.map(([g, rs]) => {
        const v = rs.map((r) => +r[p.y]).filter(isFinite).sort((a, b) => a - b); if (!v.length) return null;
        const { q1, med, q3 } = quart(v), iqr = q3 - q1, lo = v.find((x) => x >= q1 - 1.5 * iqr), hi = [...v].reverse().find((x) => x <= q3 + 1.5 * iqr);
        return { g, v, q1, med, q3, lo, hi, mean: v.reduce((a, b) => a + b, 0) / v.length, out: v.filter((x) => x < lo || x > hi) };
      }).filter(Boolean);
      if (!stats.length) { box.replaceChildren(h("div", { class: "su-empty" }, "No numeric values.")); return; }
      const all = stats.flatMap((s2) => s2.v), mn = Math.min(...all), mx = Math.max(...all), ticks = niceTicks(mn, mx, 6);
      const lo = Math.min(mn, ticks[0]), hi = Math.max(mx, ticks[ticks.length - 1]);
      const W = 640, L = 120, R = 16, RH = 44, H = stats.length * RH + 28, X = (x) => L + ((x - lo) / (hi - lo || 1)) * (W - L - R);
      let g = ticks.map((t) => `<line x1="${X(t)}" x2="${X(t)}" y1="4" y2="${H - 22}" class="gr"/><text x="${X(t)}" y="${H - 6}" class="tk" text-anchor="middle">${esc(fmt(t, p.fmt))}</text>`).join("");
      const ser = SER();
      stats.forEach((s2, i) => {
        const y = 10 + i * RH, c = ser[i % 8], m = y + 14;
        g += `<text x="${L - 10}" y="${m + 4}" class="lb" text-anchor="end">${esc(s2.g)}</text>
          <line x1="${X(s2.lo)}" x2="${X(s2.hi)}" y1="${m}" y2="${m}" class="wh"/><line x1="${X(s2.lo)}" x2="${X(s2.lo)}" y1="${m - 7}" y2="${m + 7}" class="wh"/><line x1="${X(s2.hi)}" x2="${X(s2.hi)}" y1="${m - 7}" y2="${m + 7}" class="wh"/>
          <rect x="${X(s2.q1)}" y="${y}" width="${Math.max(1, X(s2.q3) - X(s2.q1))}" height="28" rx="3" fill="${c}" fill-opacity=".22" stroke="${c}" stroke-width="1.5"><title>${esc(s2.g)}: n ${s2.v.length}, median ${fmt(s2.med)}, IQR ${fmt(s2.q1)}–${fmt(s2.q3)}, mean ${fmt(s2.mean)}</title></rect>
          <line x1="${X(s2.med)}" x2="${X(s2.med)}" y1="${y}" y2="${y + 28}" stroke="${c}" stroke-width="2.5"/>` +
          (p.mean !== false ? `<path d="M${X(s2.mean)} ${m - 4}l4 4-4 4-4-4z" class="mn"/>` : "") +
          s2.out.map((o) => `<circle cx="${X(o)}" cy="${m}" r="2.5" fill="none" stroke="${c}"/>`).join("");
      });
      box.replaceChildren(svgEl(W, H, g, "su-svgplot"), h("div", { class: "su-note" }, `Box = quartiles, line = median, ◆ = mean, whiskers = 1.5 × IQR, ○ = outliers. n = ${stats.map((s2) => `${s2.g} ${s2.v.length}`).join(", ")}.`));
    };
    draw(); subscribe(ds, draw);
  };

  C.forest = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-forest" }); el.append(box);
    const draw = () => {
      const rows = rowsFor(p).filter((r) => isFinite(+r[p.est]));
      const pool = p.pooled && isFinite(+p.pooled.est) ? p.pooled : null;
      const tr = (x) => (p.log ? Math.log(x) : x);
      const all = rows.flatMap((r) => [+r[p.lo], +r[p.hi]]).concat(pool ? [+pool.lo, +pool.hi] : []).concat([p.null ?? (p.log ? 1 : 0)]).filter(isFinite);
      let lo = tr(Math.min(...all)), hi = tr(Math.max(...all)); const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
      const W = 360, X = (x) => 8 + ((tr(x) - lo) / (hi - lo)) * (W - 16), nul = p.null ?? (p.log ? 1 : 0);
      const wmax = p.weight ? Math.max(...rows.map((r) => +r[p.weight] || 0)) || 1 : 1;
      const t = h("table", { class: "su-ftable" });
      t.append(h("thead", null, h("tr", null, h("th", null, p.label), p.group ? h("th", null, p.group) : null, h("th", { class: "su-fplot" }, ""), h("th", { class: "su-num" }, `${p.est} [95% CI]`), p.weight ? h("th", { class: "su-num" }, p.weight) : null)));
      const tb = h("tbody");
      const rowSvg = (e, l, u, size, diamond, tone) => {
        const c = tone ? css("--" + tone) : css("--fg");
        let g = `<line x1="${X(nul)}" x2="${X(nul)}" y1="0" y2="26" class="nl"/>`;
        if (diamond) g += `<path d="M${X(l)} 13L${X(e)} 4L${X(u)} 13L${X(e)} 22Z" fill="${css("--accent")}"/>`;
        else g += `<line x1="${X(l)}" x2="${X(u)}" y1="13" y2="13" stroke="${c}" stroke-width="1.6"/><rect x="${X(e) - size / 2}" y="${13 - size / 2}" width="${size}" height="${size}" fill="${c}"/>`;
        return svgEl(W, 26, g, "su-fsvg");
      };
      for (const r of rows) {
        const tone = p.group ? cellTone(p, ds, p.group, r[p.group]) : null;
        const size = p.weight ? 5 + 9 * Math.sqrt((+r[p.weight] || 0) / wmax) : 8;
        tb.append(h("tr", null, h("td", null, r[p.label]), p.group ? h("td", null, badge(String(r[p.group]), tone)) : null,
          h("td", { class: "su-fplot" }, rowSvg(+r[p.est], +r[p.lo], +r[p.hi], size, false, tone)),
          h("td", { class: "su-num su-mono" }, `${fmt(+r[p.est], p.fmt)} [${fmt(+r[p.lo], p.fmt)}, ${fmt(+r[p.hi], p.fmt)}]`),
          p.weight ? h("td", { class: "su-num" }, fmt(r[p.weight])) : null));
      }
      if (pool) tb.append(h("tr", { class: "su-fpool" }, h("td", null, pool.label || "Pooled"), p.group ? h("td") : null,
        h("td", { class: "su-fplot" }, rowSvg(+pool.est, +pool.lo, +pool.hi, 0, true)),
        h("td", { class: "su-num su-mono" }, `${fmt(+pool.est, p.fmt)} [${fmt(+pool.lo, p.fmt)}, ${fmt(+pool.hi, p.fmt)}]`), p.weight ? h("td", { class: "su-num" }, "100") : null));
      const ticks = niceTicks(p.log ? Math.exp(lo) : lo, p.log ? Math.exp(hi) : hi, 5);
      const ax = ticks.map((k) => `<line x1="${X(k)}" x2="${X(k)}" y1="0" y2="4" class="gr"/><text x="${X(k)}" y="15" text-anchor="middle" class="tk">${esc(fmt(k, p.fmt))}</text>`).join("");
      tb.append(h("tr", { class: "su-faxis" }, h("td"), p.group ? h("td") : null, h("td", { class: "su-fplot" }, svgEl(W, 20, ax, "su-fsvg"),
        p.left || p.right ? h("div", { class: "su-fsides" }, h("span", null, p.left ? "← " + p.left : ""), h("span", null, p.right ? p.right + " →" : "")) : null), h("td"), p.weight ? h("td") : null));
      t.append(tb); box.replaceChildren(h("div", { class: "su-tw" }, t));
    };
    draw(); subscribe(ds, draw);
  };

  function squarify(items, x, y, w, hgt) {
    // items: [{v, ...}] sorted desc; returns [{...item, x, y, w, h}]
    const out = [], total = items.reduce((a, b) => a + b.v, 0) || 1;
    let rest = items.slice(), X0 = x, Y0 = y, W0 = w, H0 = hgt, sum = total;
    while (rest.length) {
      const horiz = W0 >= H0, side = horiz ? H0 : W0, area = W0 * H0;
      let row = [rest[0]], best = Infinity;
      const worst = (r) => { const s2 = r.reduce((a, b) => a + b.v, 0) * area / sum, mx = Math.max(...r.map((q) => q.v * area / sum)), mn = Math.min(...r.map((q) => q.v * area / sum)); return Math.max((side * side * mx) / (s2 * s2), (s2 * s2) / (side * side * mn)); };
      best = worst(row);
      for (let i = 1; i < rest.length; i++) { const cand = rest.slice(0, i + 1), wv = worst(cand); if (wv > best) break; row = cand; best = wv; }
      const rs = row.reduce((a, b) => a + b.v, 0), thick = (rs / sum) * (horiz ? W0 : H0);
      let off = 0;
      for (const it of row) { const len = (it.v / rs) * side; out.push(horiz ? { ...it, x: X0, y: Y0 + off, w: thick, h: len } : { ...it, x: X0 + off, y: Y0, w: len, h: thick }); off += len; }
      if (horiz) { X0 += thick; W0 -= thick; } else { Y0 += thick; H0 -= thick; }
      sum -= rs; rest = rest.slice(row.length);
    }
    return out;
  }
  C.treemap = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-tmap", style: { height: (p.height || 420) + "px" } }); el.append(box);
    const lab = p.label || DS[ds].cols.find((c) => typeOf(ds, c) === "str" && c !== p.group);
    const draw = () => {
      const rows = rowsFor(p).filter((r) => +r[p.size] > 0), W = box.clientWidth || 800, Hh = p.height || 420;
      const cvals = p.color ? rows.map((r) => +r[p.color]).filter(isFinite) : [], cmax = cvals.length ? Math.max(...cvals) : 1;
      const groups = p.group ? groupBy(rows, p.group).map(([g, rs]) => ({ g, rs, v: rs.reduce((a, r) => a + +r[p.size], 0) })).sort((a, b) => b.v - a.v) : [{ g: null, rs: rows, v: rows.reduce((a, r) => a + +r[p.size], 0) }];
      const ser = SER(); box.replaceChildren();
      squarify(groups, 0, 0, W, Hh).forEach((G, gi) => {
        const top = p.group ? 18 : 0, gEl = h("div", { class: "su-tm-g", style: { left: G.x + "px", top: G.y + "px", width: G.w + "px", height: G.h + "px" } });
        if (p.group) gEl.append(h("div", { class: "su-tm-gh", title: `${G.g}: ${fmt(G.v, p.fmt)}` }, `${G.g} · ${fmt(G.v, p.fmt)}`));
        const kids = G.rs.map((r) => ({ v: +r[p.size], r })).sort((a, b) => b.v - a.v);
        squarify(kids, 1, top, Math.max(0, G.w - 2), Math.max(0, G.h - top - 1)).forEach((c) => {
          const t = p.color && isFinite(+c.r[p.color]) ? +c.r[p.color] / (cmax || 1) : null;
          const bg = t != null ? `color-mix(in oklab, var(--seq-hi) ${Math.round(8 + 80 * t)}%, var(--surface))` : `color-mix(in oklab, ${ser[gi % 8]} 28%, var(--surface))`;
          const name = String(c.r[lab] ?? "").split("/").pop();
          gEl.append(h("div", { class: "su-tm-c" + (t != null && t > 0.6 ? " su-hi" : ""), style: { left: c.x + "px", top: c.y + "px", width: Math.max(0, c.w - 1) + "px", height: Math.max(0, c.h - 1) + "px", background: bg },
            title: `${c.r[lab]}: ${fmt(c.v, p.fmt)}${p.color ? ` · ${p.color} ${fmt(c.r[p.color])}` : ""}` }, c.w > 46 && c.h > 18 ? name : ""));
        });
        box.append(gEl);
      });
      if (p.color) el.querySelector(".su-tm-legend")?.remove(), el.append(h("div", { class: "su-scale su-tm-legend" }, h("span", null, "size = " + p.size), h("span", null, "· colour = " + p.color + ": 0"),
        h("i", { style: { background: "linear-gradient(90deg, color-mix(in oklab, var(--seq-hi) 8%, var(--surface)), var(--seq-hi))" } }), h("span", null, fmt(cmax))));
    };
    requestAnimationFrame(draw); subscribe(ds, draw); new ResizeObserver(() => draw()).observe(box);
  };

  C.decision = (p, el) => {
    const ds = p.data, rows = rowsFor(p), max = p.max || 5;
    const crit = p.criteria ? arr(p.criteria).map(String) : p.scores ? Object.keys(rows[0]?.[p.scores] || {}) : [];
    const W = p.weights || {}, wsum = crit.reduce((a, c) => a + (+W[c] || (W[c] == null ? 1 : 0)), 0) || 1;
    const sc = (r, c) => +(p.scores ? (r[p.scores] || {})[c] : r[c]);
    const res = rows.map((r) => ({ r, name: r[p.option], total: crit.reduce((a, c) => a + (isFinite(sc(r, c)) ? sc(r, c) : 0) * (W[c] == null ? 1 : +W[c]), 0) / wsum })).sort((a, b) => b.total - a.total);
    const t = h("table", { class: "su-table su-dec" });
    t.append(h("thead", null, h("tr", null, h("th", null, "Rank"), h("th", null, p.option), crit.map((c) => h("th", { class: "su-num" }, c, h("div", { class: "su-count" }, W[c] != null ? `× ${fmt(+W[c])}` : ""))), h("th", { class: "su-num" }, "Weighted"))));
    const tb = h("tbody");
    res.forEach((x, i) => {
      tb.append(h("tr", { class: i === 0 ? "su-win" : "" }, h("td", null, i === 0 ? badge("1st", "good") : String(i + 1)), h("td", { class: "su-strong" }, x.name),
        crit.map((c) => { const v = sc(x.r, c), tt = isFinite(v) ? v / max : 0; return h("td", { class: "su-num su-dcell", style: { background: `color-mix(in oklab, var(--seq-hi) ${Math.round(6 + 60 * tt)}%, var(--surface))`, color: tt > 0.7 ? "var(--surface)" : "" } }, isFinite(v) ? fmt(v) : "—"); }),
        h("td", { class: "su-num" }, h("div", { class: "su-cellbar" }, h("i", { style: { width: Math.round((x.total / max) * 90) + "px", background: i === 0 ? "var(--good)" : "var(--s1)" } }), h("span", { class: "su-strong" }, x.total.toFixed(2))))));
    });
    t.append(tb);
    const gap = res.length > 1 ? res[0].total - res[1].total : null;
    el.append(h("div", { class: "su-tw" }, t), gap != null ? h("div", { class: "su-note" }, `${res[0].name} leads ${res[1].name} by ${gap.toFixed(2)} (${((100 * gap) / (res[1].total || 1)).toFixed(1)}%). Scores 1–${max}; higher is better.`) : null);
  };

  C.truth = (p, el) => {
    const rows = p.rows || rowsFor(p), cols = p.cols || (p.data ? DS[p.data].cols : []);
    const outs = p.exprs ? Object.keys(p.exprs) : cols.slice(-1), ins = cols.filter((c) => !outs.includes(c));
    const hi = p.highlight || null; let only = !!p.only;
    const wrap = h("div"); el.append(wrap);
    const draw = () => {
      const t = h("table", { class: "su-table su-truth" });
      t.append(h("thead", null, h("tr", null, ins.map((c) => h("th", { class: "su-tin" }, c)), outs.map((c) => h("th", { class: "su-tout", title: p.exprs ? p.exprs[c] : "" }, c)))));
      const tb = h("tbody");
      for (const r of rows) {
        const hot = hi && +r[hi] === 1; if (only && !hot) continue;
        tb.append(h("tr", { class: hot ? "su-hot" : "" }, ins.map((c) => h("td", { class: "su-b su-b" + (+r[c] ? 1 : 0) }, +r[c] ? "1" : "0")),
          outs.map((c) => h("td", { class: "su-b su-o su-b" + (+r[c] ? 1 : 0) }, +r[c] ? "1" : "0"))));
      }
      t.append(tb);
      const n = hi ? rows.filter((r) => +r[hi] === 1).length : 0;
      const ctl = hi ? h("div", { class: "su-ctl" }, h("label", null, h("input", { type: "checkbox", id: "su-only" + ++uid, checked: only, onchange: (e) => { only = e.target.checked; draw(); } }), `Only rows where ${hi} = 1 (${n} of ${rows.length})`)) : null;
      wrap.replaceChildren(...[ctl, h("div", { class: "su-tw" }, t), p.exprs ? h("dl", { class: "su-kv su-exprs" }, Object.entries(p.exprs).flatMap(([k, v]) => [h("dt", null, k), h("dd", null, h("code", { class: "su-code-inline" }, v))])) : null].filter(Boolean));
    };
    draw();
  };

  // ---- charts ---------------------------------------------------------------------
  const SER = () => [1, 2, 3, 4, 5, 6, 7, 8].map((i) => css("--s" + i));
  const SEV_VAR = { critical: "--bad", blocker: "--bad", severe: "--bad", high: "--serious", major: "--serious", error: "--bad", fail: "--bad", failed: "--bad",
    medium: "--warn", moderate: "--warn", warn: "--warn", warning: "--warn", flaky: "--warn", skipped: "--neutral", low: "--info", minor: "--info", info: "--info",
    pass: "--good", passed: "--good", ok: "--good", done: "--good", good: "--good", bad: "--bad", neutral: "--neutral" };
  function seriesColors(p, labels) {
    // Severity-like series values take status colours, so a chart agrees with the badges.
    const ser = SER();
    const tmap = p.tone && p.series && p.tone[p.series];
    if (tmap || labels.every((l) => SEV_VAR[String(l).toLowerCase()])) {
      const tv = { bad: "--bad", warn: "--warn", info: "--info", good: "--good", neutral: "--neutral" };
      return labels.map((l, i) => { const t = tmap && normTone(tmap[l]); return css(t ? tv[t] : SEV_VAR[String(l).toLowerCase()] || "--s" + (i % 8 + 1)); });
    }
    return labels.map((_, i) => ser[i % 8]);
  }
  const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function shortDate(k, keys) {
    // 2026-05-31 → 31 May; 2026-06 → Jun 26; add the year only when the axis spans years.
    const s2 = String(k), m = s2.match(/^(\d{4})-(\d{2})(?:-(\d{2}))?/); if (!m) return s2;
    const years = new Set(keys.map((x) => String(x).slice(0, 4))).size > 1;
    if (!m[3]) return `${MON[+m[2] - 1]} ${m[1].slice(2)}`;
    return `${+m[3]} ${MON[+m[2] - 1]}` + (years ? ` ${m[1].slice(2)}` : "");
  }
  function chartModel(p) {
    const ds = p.data, rows = rowsFor(p, [p.x]), x = p.x, ys = arr(p.y).map(colKey), agg = p.agg && p.agg !== "none" ? p.agg : null;
    const xt = typeOf(ds, x);
    let keys = uniq(rows, x);
    if (xt === "date" || xt === "num" || p.sort === "x") keys.sort(cmp);
    const sdom = p.series ? uniq(DS[ds].rows, p.series).map(String) : null; // full data: colours stay put when filtered
    if (sdom && allSev(sdom)) sdom.sort(worstFirst);
    const reduce = (rs, y) => {
      if (agg === "count" || !y) return rs.length;
      const v = rs.map((r) => +r[y]).filter(isFinite);
      if (!v.length) return null;
      if (agg === "sum") return v.reduce((a, b) => a + b, 0);
      if (agg === "mean") return v.reduce((a, b) => a + b, 0) / v.length;
      if (agg === "min") return Math.min(...v);
      if (agg === "max") return Math.max(...v);
      return v[0];
    };
    const byX = new Map(keys.map((k) => [String(k), []]));
    for (const r of rows) { const k = String(r[x]); if (byX.has(k)) byX.get(k).push(r); }
    let sets;
    if (sdom) {
      const y = ys[0];
      sets = sdom.map((s, i) => ({ label: s, idx: i, data: keys.map((k) => { const rs = byX.get(String(k)).filter((r) => String(r[p.series]) === s); return rs.length ? reduce(rs, y) : (agg === "count" ? 0 : null); }) }));
    } else if (ys.length) sets = ys.map((y, i) => ({ label: y, idx: i, data: keys.map((k) => reduce(byX.get(String(k)), y)) }));
    else sets = [{ label: "count", idx: 0, data: keys.map((k) => byX.get(String(k)).length) }];
    if (p.sort === "y" || p.sort === "-y") {
      const tot = keys.map((k, i) => [k, sets.reduce((a, s) => a + (+s.data[i] || 0), 0), i]);
      tot.sort((a, b) => (p.sort === "y" ? a[1] - b[1] : b[1] - a[1]));
      keys = tot.map((t) => t[0]); sets.forEach((s) => (s.data = tot.map((t) => s.data[t[2]])));
    }
    if (p.limit) { keys = keys.slice(0, p.limit); sets.forEach((s) => (s.data = s.data.slice(0, p.limit))); }
    const datey = xt === "date" || (keys.length && keys.every((k) => /^\d{4}-\d{2}(-\d{2})?$/.test(String(k))));
    return { labels: keys.map((k) => (datey ? shortDate(k, keys) : fmt(k, null, xt))), keys, sets, xt };
  }
  const refLines = {
    id: "suRef",
    afterDatasetsDraw(chart, _a, opts) {
      const marks = opts.marks || [], bands = opts.bands || [], keys = (opts.keys || []).map(String);
      if (!marks.length && !bands.length) return;
      const { ctx, chartArea: a } = chart, horiz = chart.options.indexAxis === "y";
      const sc = horiz ? chart.scales.x : chart.scales.y, cat = horiz ? chart.scales.y : chart.scales.x;
      const linear = cat.type === "linear";
      const catPx = (x) => { if (linear) return cat.getPixelForValue(+x); const i = keys.indexOf(String(x)); if (i >= 0) return cat.getPixelForValue(i);
        // between two keys (e.g. a date not in the data): place by order
        const j = keys.findIndex((k) => k > String(x)); return j <= 0 ? (j === 0 ? cat.getPixelForValue(0) : null) : (cat.getPixelForValue(j - 1) + cat.getPixelForValue(j)) / 2; };
      ctx.save(); ctx.font = "11px " + css("--mono");
      for (const b of bands) {
        if (Array.isArray(b.x) || Array.isArray(b.y)) {   // value box, e.g. a scatter quadrant: {x: [300, null], y: [8, null]}
          const xs = b.x || [null, null], ys = b.y || [null, null];
          const x1 = xs[0] == null ? a.left : catPx(xs[0]), x2 = xs[1] == null ? a.right : catPx(xs[1]);
          const y1 = ys[1] == null ? a.top : sc.getPixelForValue(+ys[1]), y2 = ys[0] == null ? a.bottom : sc.getPixelForValue(+ys[0]);
          ctx.fillStyle = css("--warn") + "22"; ctx.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
          if (b.label) { ctx.fillStyle = css("--muted"); ctx.textAlign = "left"; ctx.fillText(b.label, Math.min(x1, x2) + 4, Math.min(y1, y2) + 12); }
          continue;
        }
        const p1 = catPx(b.from), p2 = catPx(b.to ?? keys[keys.length - 1]); if (p1 == null || p2 == null) continue;
        ctx.fillStyle = css("--accent") + "14";
        if (horiz) ctx.fillRect(a.left, Math.min(p1, p2), a.right - a.left, Math.abs(p2 - p1)); else ctx.fillRect(Math.min(p1, p2), a.top, Math.abs(p2 - p1), a.bottom - a.top);
        if (b.label) { ctx.fillStyle = css("--muted"); ctx.textAlign = "left"; ctx.fillText(b.label, horiz ? a.left + 4 : Math.min(p1, p2) + 4, horiz ? Math.min(p1, p2) + 12 : a.top + 12); }
      }
      ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5; ctx.strokeStyle = css("--bad"); ctx.fillStyle = css("--muted");
      for (const m of marks) {
        if (m.x != null && m.y == null) {
          const px = catPx(m.x); if (px == null) continue;
          ctx.beginPath(); if (horiz) { ctx.moveTo(a.left, px); ctx.lineTo(a.right, px); } else { ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); } ctx.stroke();
          if (m.label) { ctx.textAlign = "left"; ctx.fillText(m.label, horiz ? a.left + 4 : px + 4, horiz ? px - 4 : a.top + 24); }
          continue;
        }
        const v = m.y ?? m.value; if (v == null) continue;
        const px = sc.getPixelForValue(+v);
        ctx.beginPath();
        if (horiz) { ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); } else { ctx.moveTo(a.left, px); ctx.lineTo(a.right, px); }
        ctx.stroke();
        if (m.label) { ctx.textAlign = horiz ? "left" : "right"; ctx.fillText(m.label, horiz ? px + 4 : a.right - 4, horiz ? a.top + 10 : px - 4); }
      }
      ctx.restore();
    },
  };
  function histModel(p) {
    const rows = rowsFor(p), x = p.x, vals = rows.map((r) => +r[x]).filter(isFinite);
    if (!vals.length) return { labels: [], keys: [], sets: [] };
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const n = p.bins || Math.max(5, Math.min(30, Math.ceil(Math.log2(vals.length) + 1)));
    const raw = (hi - lo) / n || 1, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((k) => k >= raw);
    const start = Math.floor(lo / step) * step, nb = Math.max(1, Math.ceil((hi - start) / step + 1e-9));
    const keys = Array.from({ length: nb }, (_, i) => start + i * step);
    const labels = keys.map((k) => `${fmt(k, p.fmt)}–${fmt(k + step, p.fmt)}`);
    const groups = p.series ? uniq(DS[p.data].rows, p.series).map(String) : [null];
    const sets = groups.map((g, gi) => {
      const counts = new Array(nb).fill(0);
      for (const r of rows) { if (g != null && String(r[p.series]) !== g) continue; const v = +r[x]; if (!isFinite(v)) continue; counts[Math.min(nb - 1, Math.floor((v - start) / step))]++; }
      return { label: g ?? "count", idx: gi, data: counts };
    });
    return { labels, keys, sets };
  }
  function linreg(pts) {
    const n = pts.length; if (n < 3) return null;
    const mx = pts.reduce((a, q) => a + q.x, 0) / n, my = pts.reduce((a, q) => a + q.y, 0) / n;
    let sxy = 0, sxx = 0, syy = 0; for (const q of pts) { sxy += (q.x - mx) * (q.y - my); sxx += (q.x - mx) ** 2; syy += (q.y - my) ** 2; }
    if (!sxx) return null;
    const b = sxy / sxx, a = my - b * mx, r2 = syy ? (sxy * sxy) / (sxx * syy) : 0;
    return { a, b, r2 };
  }
  C.chart = (p, el) => {
    const box = h("div", { class: "su-chart", style: { "--ch": (p.height || 260) + "px" } });
    const cv = h("canvas", { role: "img", "aria-label": (p.title || "chart") + ": " + p.kind + " of " + arr(p.y).map(colKey).join(", ") + " by " + p.x });
    box.append(cv); el.append(box);
    let chart = null;
    const draw = () => {
      if (!window.Chart) { el.replaceChildren(h("div", { class: "su-err" }, "Chart.js did not load (no network?).")); return; }
      if (chart) chart.destroy();
      const kind0 = p.kind || "bar";
      const m = kind0 === "hist" ? histModel(p) : chartModel(p), kind = kind0 === "hist" ? "bar" : kind0;
      const ser = seriesColors(p, kind === "donut" ? m.labels : m.sets.map((x) => x.label));
      const fg = css("--muted"), grid = css("--line"), font = css("--chart-font") || css("--font");
      const yRight = css("--su-yaxis") === "right", barR = css("--su-bar-radius") === "" ? 4 : parseFloat(css("--su-bar-radius")), axisC = css("--axis") || css("--line-2");
      const single = m.sets.length === 1;
      const sel = picked(p.data, p.x);
      const dim = (c, i) => (sel && !sel.has(String(m.keys[i])) ? c + "40" : c);
      const datasets = m.sets.map((s) => {
        const c = ser[s.idx] || ser[s.idx % 8];
        const base = { label: (p.labels && p.labels[s.label]) || s.label, data: s.data, borderColor: c, backgroundColor: c };
        if (kind === "line" || kind === "area") return { ...base, borderWidth: 2, pointRadius: m.labels.length > 40 ? 0 : 2.5, pointHoverRadius: 5, tension: 0.25, fill: kind === "area" ? (p.stack ? "stack" : "origin") : false, backgroundColor: kind === "area" ? c + (p.stack ? "cc" : "33") : c, spanGaps: true };
        if (kind === "scatter") {
          const rows = rowsFor(p), y = arr(p.y).map(colKey)[0];
          const pts = rows.filter((r) => (!p.series || String(r[p.series]) === s.label) && isFinite(+r[p.x]) && isFinite(+r[y])).map((r) => ({ x: +r[p.x], y: +r[y] }));
          return { ...base, label: p.series ? base.label : (p.labels && p.labels[y]) || y, data: pts, pointRadius: 4, pointHoverRadius: 6, backgroundColor: c + "b3" };
        }
        if (kind === "waterfall") {
          let cum = 0; const fl = [], cols = [], labs = [];
          const subs = arr(p.subtotals);
          s.data.forEach((v, i) => {
            const a = cum; cum += +v || 0; fl.push([a, cum]); cols.push(css(+v >= 0 ? "--good" : "--bad")); labs.push(m.labels[i]);
            for (const st of subs.filter((x) => String(x.after) === String(m.keys[i]))) { fl.push([0, cum]); cols.push(css("--s1")); labs.push(st.label || "Subtotal"); }
          });
          if (p.total) { fl.push([0, cum]); cols.push(css("--s1")); labs.push(p.total); }
          m.wlabels = labs;
          return { ...base, data: fl, backgroundColor: cols, borderRadius: 3, borderSkipped: false, maxBarThickness: 46, borderWidth: 0 };
        }
        if (kind === "donut") return { ...base, backgroundColor: ser, borderColor: css("--surface"), borderWidth: 2 };
        return { ...base, backgroundColor: sel ? m.keys.map((_, i) => dim(c, i)) : c, borderRadius: barR, borderSkipped: "start", maxBarThickness: 38, borderWidth: 0 };
      });
      if (kind === "waterfall" && m.wlabels) m.labels = m.wlabels;
      if (kind === "scatter" && p.trend) {
        for (const d of datasets.slice()) {
          const lr = linreg(d.data); if (!lr) continue;
          const xs = d.data.map((q) => q.x), x0 = Math.min(...xs), x1 = Math.max(...xs);
          datasets.push({ type: "line", label: `${d.label} trend (r² ${lr.r2.toFixed(2)})`, data: [{ x: x0, y: lr.a + lr.b * x0 }, { x: x1, y: lr.a + lr.b * x1 }],
            borderColor: d.borderColor, borderDash: [6, 4], borderWidth: 1.5, pointRadius: 0, fill: false });
        }
      }
      const narrow = box.clientWidth < 520;
      const tick = (v) => fmt(v, p.fmt);
      const vAxis = { beginAtZero: p.zero !== false, stacked: !!p.stack, grid: { color: grid, drawTicks: false }, border: { display: false }, ticks: { color: fg, padding: 6, callback: tick, maxTicksLimit: narrow ? 4 : 6, maxRotation: 0, font: { size: narrow ? 10.5 : 12 }, precision: m.sets.every((s) => s.data.every((v) => v == null || Number.isInteger(v))) ? 0 : undefined } };
      const cAxis = { stacked: !!p.stack, grid: { display: false }, border: { color: axisC, width: yRight ? 1.5 : 1 },
        ticks: { color: fg, autoSkip: true, autoSkipPadding: 6, maxRotation: narrow ? 50 : 40, minRotation: 0, font: { size: narrow ? 10.5 : 12 } } };
      const horiz = !!p.horizontal && kind === "bar";
      const cfg = {
        type: kind === "area" ? "line" : kind === "donut" ? "doughnut" : kind === "waterfall" ? "bar" : kind,
        data: { labels: m.labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false, indexAxis: horiz ? "y" : "x",
          interaction: { mode: kind === "scatter" || kind === "donut" ? "nearest" : "index", intersect: kind === "scatter" || kind === "donut" },
          plugins: {
            legend: { display: (!single || kind === "donut" || (kind === "scatter" && p.trend)) && kind !== "waterfall", position: kind === "donut" && !narrow ? "right" : "top", align: "start", labels: { color: css("--fg") || fg, boxWidth: 10, boxHeight: 10, useBorderRadius: true, borderRadius: barR ? 2 : 0, font: { family: font, size: narrow ? 11 : 12.5 }, padding: narrow ? 8 : 12 } },
            tooltip: { callbacks: { label: (c) => {
              if (kind === "waterfall") { const r = c.raw; return ` ${fmt(r[1] - r[0], p.fmt)} → ${fmt(r[1], p.fmt)}`; }
              if (kind === "scatter") return ` ${c.dataset.label}: (${fmt(c.parsed.x)}, ${fmt(c.parsed.y, p.fmt)})`;
              return ` ${c.dataset.label}: ${fmt(c.parsed && typeof c.parsed === "object" ? (horiz ? c.parsed.x : c.parsed.y) : c.parsed, p.fmt)}`; } } },
            suRef: { marks: arr(p.mark), bands: arr(p.band), keys: m.keys },
          },
          scales: kind === "donut" ? {} : horiz ? { x: { ...vAxis, position: yRight ? "top" : "bottom" }, y: cAxis }
            : { x: kind === "scatter" ? { ...vAxis, type: "linear", beginAtZero: false, title: { display: true, text: (p.labels && p.labels[p.x]) || p.x, color: fg } } : { ...cAxis, ...(kind0 === "hist" ? { title: { display: true, text: p.x, color: fg } } : {}) },
                y: { ...(kind === "scatter" ? { ...vAxis, beginAtZero: false, title: { display: true, text: (p.labels && p.labels[arr(p.y).map(colKey)[0]]) || arr(p.y).map(colKey)[0], color: fg } } : vAxis), position: yRight ? "right" : "left" } },
          cutout: kind === "donut" ? "62%" : undefined,
          onClick: kind === "bar" || kind === "donut" ? (e, els) => { if (els.length) toggleFilter(p.data, [[p.x, m.keys[els[0].index]]]); } : undefined,
          onHover: kind === "bar" || kind === "donut" ? (e, els) => { e.native.target.style.cursor = els.length ? "pointer" : "default"; } : undefined,
        },
        plugins: [refLines],
      };
      Chart.defaults.font.family = font; Chart.defaults.color = fg;
      chart = new Chart(cv, cfg);
    };
    draw(); subscribe(p.data, draw); LIVE.push(draw);
    let wasNarrow = box.clientWidth < 520;
    new ResizeObserver(() => { const n2 = box.clientWidth < 520; if (n2 !== wasNarrow) { wasNarrow = n2; draw(); } }).observe(box);
  };

  C.heatmap = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-heat" }); el.append(box);
    const draw = () => {
      const rows = rowsFor(p, [p.x, p.y]), xt = typeOf(ds, p.x);
      const worst = new Map();
      if (p.worst) for (const r of rows) {
        const k = r[p.y] + "\u0001" + r[p.x], rank = sevRank(r[p.worst]);
        if (rank >= 0 && (!worst.has(k) || rank < sevRank(worst.get(k)))) worst.set(k, r[p.worst]);
      }
      const selX = picked(ds, p.x), selY = picked(ds, p.y);
      const xs = uniq(rows, p.x); if (xt === "date" || xt === "num" || allSev(xs)) xs.sort(cmp);
      if (p.xorder) { const o = arr(p.xorder).map(String); xs.sort((a, b) => (o.indexOf(String(a)) + 1 || 1e9) - (o.indexOf(String(b)) + 1 || 1e9)); }
      const cell = new Map(), tot = new Map();
      for (const r of rows) {
        const k = r[p.y] + "\u0001" + r[p.x]; if (!cell.has(k)) cell.set(k, []);
        cell.get(k).push(p.v ? +r[p.v] : 1);
      }
      const val = (a) => !a ? null : p.agg === "mean" ? a.reduce((s, b) => s + b, 0) / a.length : p.agg === "max" ? Math.max(...a) : p.agg === "count" ? a.length : a.reduce((s, b) => s + b, 0);
      const ys = uniq(rows, p.y);
      for (const y of ys) tot.set(y, xs.reduce((s, x) => s + (val(cell.get(y + "\u0001" + x)) || 0), 0));
      if (p.yorder) { const o = arr(p.yorder).map(String); ys.sort((a, b) => (o.indexOf(String(a)) + 1 || 1e9) - (o.indexOf(String(b)) + 1 || 1e9)); }
      else if (allSev(ys)) ys.sort(worstFirst);
      else if (typeOf(ds, p.y) !== "date") ys.sort((a, b) => tot.get(b) - tot.get(a)); else ys.sort(cmp);
      const all = [...cell.values()].map(val).filter(isNum);
      const lo = Math.min(0, ...all), hi = Math.max(...all, 0), amax = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
      const color = (v) => {
        if (v == null) return "var(--sunk)";
        if (p.scale === "div") { const t = Math.abs(v) / amax; return `color-mix(in oklab, var(${v < 0 ? "--div-lo" : "--div-hi"}) ${Math.round(8 + 82 * t)}%, var(--surface))`; }
        const t = hi === lo ? 1 : (v - lo) / (hi - lo); return `color-mix(in oklab, var(--seq-hi) ${Math.round(6 + 90 * t)}%, var(--surface))`;
      };
      const t = h("table", { role: "grid" });
      t.append(h("thead", null, h("tr", null, h("th"), xs.map((x) => h("th", null, fmt(x, null, xt))), p.totals ? h("th", null, "Total") : null)));
      const tb = h("tbody");
      for (const y of ys) {
        const tr = h("tr", null, h("th", { class: "su-y", title: y }, y));
        for (const x of xs) {
          const k = y + "\u0001" + x, v = val(cell.get(k)), tt = v == null ? 0 : p.scale === "div" ? Math.abs(v) / amax : (v - lo) / (hi - lo || 1);
          const wv = worst.get(k), wt = wv != null ? normTone(AUTO[String(wv).toLowerCase()]) : null;
          const bg = wt ? `color-mix(in oklab, var(--${wt}) ${Math.round(22 + 60 * tt)}%, var(--surface))` : color(v);
          const on = (!selX || selX.has(String(x))) && (!selY || selY.has(String(y)));
          const td = h("td", { style: { background: bg, opacity: on ? 1 : 0.3, cursor: v == null ? "" : "pointer" }, class: (tt > 0.55 && p.scale !== "div" && !wt) || (wt && tt > 0.6) ? "su-hi" : "",
            title: `${y} · ${fmt(x, null, xt)}: ${v == null ? "—" : fmt(v, p.fmt)}` + (wv != null ? ` · worst: ${wv}` : "") }, (p.labels || p.worst) && v != null ? fmt(v, p.fmt) : "");
          if (v != null) td.addEventListener("click", () => toggleFilter(ds, [[p.x, x], [p.y, y]]));
          tr.append(td);
        }
        if (p.totals) tr.append(h("th", { class: "su-tot" }, fmt(tot.get(y), p.fmt)));
        tb.append(tr);
      }
      if (p.totals) tb.append(h("tr", null, h("th", { class: "su-y" }, "Total"), xs.map((x) => h("th", { class: "su-tot" }, fmt(ys.reduce((s, y) => s + (val(cell.get(y + "\u0001" + x)) || 0), 0), p.fmt))),
        h("th", { class: "su-tot" }, fmt([...tot.values()].reduce((a, b) => a + b, 0), p.fmt))));
      t.append(tb);
      const scale = p.worst ? h("div", { class: "su-scale" }, ["critical", "high", "medium", "low"].map((k) => h("span", { style: { display: "inline-flex", gap: "5px", alignItems: "center" } }, h("span", { class: "su-dot su-t-" + normTone(AUTO[k]) }), k)), h("span", null, `· colour = worst ${p.worst}; darker = more rows`))
        : h("div", { class: "su-scale" }, h("span", null, fmt(p.scale === "div" ? -amax : lo, p.fmt)),
        h("i", { style: { background: p.scale === "div" ? "linear-gradient(90deg, var(--div-lo), var(--surface), var(--div-hi))" : "linear-gradient(90deg, color-mix(in oklab, var(--seq-hi) 6%, var(--surface)), var(--seq-hi))" } }),
        h("span", null, fmt(p.scale === "div" ? amax : hi, p.fmt)), p.v ? h("span", null, `${p.agg || "sum"} of ${p.v}`) : h("span", null, "rows"),
        p.worst ? h("span", null, `· colour = worst ${p.worst}`) : null);
      box.replaceChildren(t, scale);
    };
    draw(); subscribe(ds, draw);
  };

  // ---- code and diff --------------------------------------------------------------
  function hl(code, lang) {
    if (window.hljs && lang && hljs.getLanguage(lang)) { try { return hljs.highlight(code, { language: lang, ignoreIllegals: true }).value; } catch (e) { /* plain */ } }
    return esc(code);
  }
  function splitHtmlLines(html) {
    // Split highlighted HTML into lines, and close and reopen spans at each line end.
    const out = []; let open = [], cur = "";
    const re = /(<span[^>]*>)|(<\/span>)|(\n)|([^<\n]+|<)/g; let m;
    while ((m = re.exec(html))) {
      if (m[1]) { open.push(m[1]); cur += m[1]; }
      else if (m[2]) { open.pop(); cur += m[2]; }
      else if (m[3]) { cur += "</span>".repeat(open.length); out.push(cur); cur = open.join(""); }
      else cur += m[4];
    }
    out.push(cur); return out;
  }
  function codeEl(p) {
    const lines = splitHtmlLines(hl(String(p.src ?? ""), p.lang));
    const marks = new Set(arr(p.mark).map(Number)), start = p.start || 1;
    const pre = h("pre", { class: "su-pre" + (p.wrap ? " su-wrap" : "") });
    const code = h("code");
    code.innerHTML = lines.map((l, i) => `<span class="su-ln${marks.has(start + i) ? " su-mark" : ""}" data-n="${start + i}">${l || " "}</span>`).join("");
    pre.append(code); return pre;
  }
  function noteRow(n, span) {
    const t = normTone(AUTO[String(n.sev ?? "").toLowerCase()] || n.sev) || "info";
    const card = h("div", { class: "su-cnote su-t-" + t, style: { "--tone": `var(--${t})` } },
      h("div", { class: "su-cnote-h" }, n.id != null ? h("span", { class: "su-count" }, String(n.id)) : null, n.sev ? badge(String(n.sev), t) : null, n.head ? h("b", { html: inline(n.head) }) : null),
      n.text ? h("div", { class: "su-md", html: md(n.text) }) : null);
    return span ? h("tr", { class: "su-ntr" }, h("td", { colspan: span }, card)) : card;
  }
  C.code = (p, el) => {
    const pre = codeEl(p);
    if (p.notes) {
      const by = new Map(); for (const n of p.notes) { const k = +n.line; if (!by.has(k)) by.set(k, []); by.get(k).push(n); }
      const code = pre.querySelector("code");
      for (const ln of [...code.children]) { const ns = by.get(+ln.dataset.n); if (ns) { ln.classList.add("su-mark"); ns.forEach((n) => ln.after(noteRow(n))); } }
    }
    el.append(pre);
  };
  function intraline(a, b) {
    let i = 0; while (i < a.length && i < b.length && a[i] === b[i]) i++;
    let j = 0; while (j < a.length - i && j < b.length - i && a[a.length - 1 - j] === b[b.length - 1 - j]) j++;
    const mk = (s) => esc(s.slice(0, i)) + (s.length - j > i ? "<mark>" + esc(s.slice(i, s.length - j)) + "</mark>" : "") + esc(s.slice(s.length - j));
    if (i + j < Math.min(a.length, b.length) * 0.3) return [esc(a), esc(b)];
    return [mk(a), mk(b)];
  }
  C.diff = (p, el) => {
    const wantSplit = (p.mode || "split") === "split";
    const draw = (narrow) => { el.replaceChildren(); drawDiff(p, el, wantSplit && !narrow); };
    let narrow = null;
    new ResizeObserver(() => { const n2 = el.clientWidth < 720; if (n2 !== narrow) { narrow = n2; draw(n2); } }).observe(el);
    draw(false);
  };
  function drawDiff(p, el, split) {
    const notesFor = (f) => {
      const m = new Map();
      for (const n of arr(p.notes)) {
        if (n.file && !(f.new && (f.new === n.file || f.new.endsWith("/" + n.file) || String(n.file).endsWith(f.new))) && !(f.old && f.old === n.file)) continue;
        if (!n.file && arr(p.files).length > 1) continue;
        const k = +n.line; if (!m.has(k)) m.set(k, []); m.get(k).push(n);
      }
      return m;
    };
    for (const f of arr(p.files)) {
      const lang = p.lang || f.lang;
      const NOTES = notesFor(f), used = new Set(), tb = h("tbody");
      const after = (num) => { if (num == null || !NOTES.has(num) || used.has(num)) return; used.add(num); NOTES.get(num).forEach((n) => tb.append(noteRow(n, split ? 6 : 4))); };
      const name = f.new && f.old && f.new !== f.old ? `${f.old} → ${f.new}` : f.new || f.old || "file";
      const box = h("div", { class: "su-diff" }, h("div", { class: "su-diff-h" }, h("span", null, name), h("span", { class: "a" }, "+" + f.add), h("span", { class: "d" }, "−" + f.del),
        !f.old ? badge("new", "good") : !f.new ? badge("deleted", "bad") : null, NOTES.size ? h("span", { class: "su-count" }, `${[...NOTES.values()].flat().length} notes`) : null));
      const t = h("table", { class: "su-dt" + (split ? " split" : "") });
      t.append(h("colgroup", null, split ? [h("col", { style: { width: "5ch" } }), h("col", { style: { width: "2ch" } }), h("col", { class: "code" }), h("col", { style: { width: "5ch" } }), h("col", { style: { width: "2ch" } }), h("col", { class: "code" })]
        : [h("col", { style: { width: "5ch" } }), h("col", { style: { width: "5ch" } }), h("col", { style: { width: "2ch" } }), h("col")]));
      const td = (cls, html) => h("td", { class: cls, html });
      for (const hk of f.hunks) {
        const first = hk.lines[0] || [];
        tb.append(h("tr", { class: "hk" }, h("td", { colspan: split ? 6 : 4 }, `@@ ${first[1] ?? first[2] ?? ""} ${hk.head || ""}`)));
        const L = hk.lines;
        for (let i = 0; i < L.length;) {
          if (L[i][0] === "c") {
            const code = hl(L[i][3], lang);
            tb.append(split ? h("tr", null, td("n", L[i][1]), td("m", ""), td("", code), td("n", L[i][2]), td("m", ""), td("", code))
              : h("tr", null, td("n", L[i][1]), td("n", L[i][2]), td("m", ""), td("", code)));
            after(L[i][2]); i++; continue;
          }
          const dels = [], adds = [];
          while (i < L.length && L[i][0] === "d") dels.push(L[i++]);
          while (i < L.length && L[i][0] === "a") adds.push(L[i++]);
          const n = Math.max(dels.length, adds.length);
          for (let k = 0; k < n; k++) {
            const d = dels[k], a = adds[k];
            let dh = d ? hl(d[3], lang) : "", ah = a ? hl(a[3], lang) : "";
            if (d && a) [dh, ah] = intraline(d[3], a[3]);
            if (split) { tb.append(h("tr", null, d ? [td("n del", d[1]), td("m del", "−"), td("del", dh)] : [td("n emp", ""), td("m emp", ""), td("emp", "")],
              a ? [td("n add", a[2]), td("m add", "+"), td("add", ah)] : [td("n emp", ""), td("m emp", ""), td("emp", "")])); if (a) after(a[2]); }
          }
          if (!split) {
            dels.forEach((d, k) => tb.append(h("tr", null, td("n del", d[1]), td("n del", ""), td("m del", "−"), td("del", adds[k] ? intraline(d[3], adds[k][3])[0] : hl(d[3], lang)))));
            adds.forEach((a, k) => { tb.append(h("tr", null, td("n add", ""), td("n add", a[2]), td("m add", "+"), td("add", dels[k] ? intraline(dels[k][3], a[3])[1] : hl(a[3], lang)))); after(a[2]); });
          }
        }
      }
      t.append(tb);
      const left = [...NOTES.keys()].filter((k) => !used.has(k));
      box.append(h("div", { class: "su-diff-w" }, t));
      if (left.length) box.append(h("div", { class: "su-cnotes" }, h("div", { class: "su-gh" }, "Notes on lines outside the diff"), left.flatMap((k) => NOTES.get(k).map((n) => noteRow({ ...n, head: `L${k} · ${n.head || ""}` })))));
      el.append(box);
    }
    if (!arr(p.files).length) el.append(h("div", { class: "su-empty" }, "No changes."));
  };

  // ---- diagrams -------------------------------------------------------------------
  let mermaidReady = false;
  function mermaidInit() {
    if (!window.mermaid) return false;
    const dark = matchMedia("(prefers-color-scheme: dark)").matches && document.documentElement.dataset.theme !== "light" || document.documentElement.dataset.theme === "dark";
    mermaid.initialize({
      startOnLoad: false, securityLevel: "strict", theme: "base", fontFamily: css("--font"),
      themeVariables: { darkMode: dark, background: css("--surface"), primaryColor: css("--sunk"), primaryBorderColor: css("--line-2"), primaryTextColor: css("--fg"),
        secondaryColor: css("--surface"), tertiaryColor: css("--bg"), lineColor: css("--muted"), textColor: css("--fg"), fontSize: "13px",
        clusterBkg: css("--bg"), clusterBorder: css("--line-2"), noteBkgColor: css("--sunk"), noteTextColor: css("--fg"), noteBorderColor: css("--line-2"),
        actorBkg: css("--sunk"), actorBorder: css("--line-2"), actorTextColor: css("--fg"), signalColor: css("--fg"), signalTextColor: css("--fg"),
        labelBoxBkgColor: css("--sunk"), labelBoxBorderColor: css("--line-2"), labelTextColor: css("--fg"), loopTextColor: css("--fg"), activationBkgColor: css("--line"),
        edgeLabelBackground: css("--surface"), classText: css("--fg") },
      flowchart: { htmlLabels: true, curve: "basis" }, sequence: { useMaxWidth: true },
      themeCSS: `.node rect, .node polygon { rx: ${css("--su-node-radius") || 6}; ry: ${css("--su-node-radius") || 6}; }`,
    });
    mermaidReady = true; return true;
  }
  async function drawDiagram(job) {
    const { el, src, path } = job;
    if (!window.mermaid) { el.replaceChildren(h("div", { class: "su-err" }, "Mermaid did not load (no network?).")); return; }
    if (!mermaidReady) mermaidInit();
    const id = "su-m" + ++uid;
    try {
      const { svg } = await mermaid.render(id, src);
      el.classList.remove("su-pending"); el.innerHTML = svg;
    } catch (e) {
      document.getElementById("d" + id)?.remove(); document.getElementById(id)?.remove();
      const msg = String(e && e.message || e).split("\n").slice(0, 6).join("\n");
      ST.errors.push(`${path}: Mermaid error: ${msg}`);
      el.classList.remove("su-pending");
      el.replaceChildren(h("div", { class: "su-err" }, `Diagram error at ${path}:\n${msg}`), h("pre", { class: "su-pre su-wrap" }, h("code", null, src)));
    }
  }
  const visible = (el) => !!(el.offsetParent || el.getClientRects().length);
  function flushPending() {
    for (let i = PENDING.length - 1; i >= 0; i--) if (visible(PENDING[i].el)) { const j = PENDING.splice(i, 1)[0]; WAIT.push(drawDiagram(j)); }
  }
  C.diagram = (p, el, n, path) => {
    const box = h("div", { class: "su-diagram su-pending" }, "Drawing diagram…"); el.append(box);
    if (p.legend && p.legend.length) el.append(h("div", { class: "su-legend", style: { marginTop: "8px" } }, p.legend.map((l) => h("span", null, h("i", { style: { background: `var(--${l.tone})` } }), l.label))));
    if (p.cyclelist && p.cyclelist.length) el.append(h("div", { class: "su-note" }, `Cycles (red edges): ${p.cyclelist.map((c) => c.join(" → ")).join("; ")}`));
    const job = { el: box, src: p.src, path };
    PENDING.push(job);
    LIVE.push(() => { if (!PENDING.includes(job)) { mermaidReady = false; PENDING.push(job); } });
  };
  C.graph = C.diagram; C.sankey = C.diagram; C.er = C.diagram; C.classes = C.diagram;

  // ---- layout ---------------------------------------------------------------------
  function kidsInto(container, kids, path) { kids.forEach((k, i) => container.append(node(k, `${path}[${i}]`))); return container; }
  const L = {};
  L.row = (n, path) => {
    const el = h("div", { class: `su-row su-gap-${n.p.gap || "m"}` + (n.p.align ? " su-al-" + n.p.align : ""), "--min": (n.p.min || 240) + "px" });
    n.kids.forEach((k, i) => { const c = node(k, `${path}[${i}]`); if (k.p.w) c.style.setProperty("--w", k.p.w); el.append(c); });
    return titled(n, el);
  };
  L.col = (n, path) => titled(n, kidsInto(h("div", { class: `su-col su-gap-${n.p.gap || "m"}` }), n.kids, path));
  L.grid = (n, path) => {
    const el = h("div", { class: `su-grid su-gap-${n.p.gap || "m"}`, "--min": (n.p.min || 260) + "px", style: n.p.cols ? { gridTemplateColumns: `repeat(${n.p.cols}, minmax(0, 1fr))` } : null });
    n.kids.forEach((k, i) => { const c = node(k, `${path}[${i}]`); if (k.p.span) c.style.setProperty("--span", k.p.span); el.append(c); });
    return titled(n, el);
  };
  L.section = (n, path) => h("section", { class: "su-section su-node", id: n.p.id }, n.p.title ? h("h2", null, n.p.title) : null, kidsInto(h("div", { class: "su-flow", style: { gap: "var(--gap-m)" } }), n.kids, path), noteEl(n));
  L.card = (n, path) => {
    const t = normTone(n.p.tone);
    const head = n.p.title ? h(n.p.collapse ? "summary" : "div", { class: "su-card-h" }, n.p.title, countOf(n)) : (n.p.collapse ? h("summary", { class: "su-card-h" }, "Details") : null);
    const body = kidsInto(h("div", { class: "su-card-b" }), n.kids, path);
    const el = h(n.p.collapse ? "details" : "div", { class: "su-card su-node" + (t ? " su-tone su-t-" + t : ""), id: n.p.id, open: n.p.collapse ? n.p.open === true : null }, head, body, noteEl(n, true));
    if (n.p.collapse) el.addEventListener("toggle", flushPending);
    return el;
  };
  function countOf(n) {
    const k = n.kids && n.kids[0];
    if (n.kids.length === 1 && k.p.data && DS[k.p.data] && ["table", "list", "board", "timeline"].includes(k.c)) return h("span", { class: "su-count" }, rowsForStatic(k));
    return null;
  }
  const rowsForStatic = (k) => rowsFor(k.p).length;
  L.tabs = (n, path) => {
    const bar = h("div", { class: "su-tabs-bar", role: "tablist" }), wrap = h("div", { class: "su-node su-tabs", id: n.p.id });
    const panels = [];
    n.kids.forEach((k, i) => {
      const label = k.p.title || `Tab ${i + 1}`;
      const kk = { ...k, p: { ...k.p, title: null } };
      const panel = h("div", { class: "su-panel", role: "tabpanel", hidden: i !== 0 }, node(kk, `${path}[${i}]`));
      const b = h("button", { class: "su-tab", role: "tab", type: "button", "aria-selected": i === 0 ? "true" : "false", id: `su-tab${++uid}` }, label, countOf({ kids: [k] }));
      b.addEventListener("click", () => {
        bar.querySelectorAll(".su-tab").forEach((x) => x.setAttribute("aria-selected", "false")); b.setAttribute("aria-selected", "true");
        panels.forEach((pp) => (pp.hidden = pp !== panel)); flushPending(); window.dispatchEvent(new Event("resize"));
      });
      bar.append(b); panels.push(panel);
    });
    if (n.p.title) wrap.append(h("h3", { class: "su-t" }, n.p.title));
    wrap.append(bar, ...panels, noteEl(n) || "");
    return wrap;
  };
  L.compare = (n, path) => {
    if ((n.p.mode || "side") === "side") {
      const el = h("div", { class: "su-compare", style: { "--n": Math.min(n.kids.length, 4) } });
      n.kids.forEach((k, i) => el.append(node(k, `${path}[${i}]`)));
      return titled(n, el);
    }
    const bar = h("div", { class: "su-seg", role: "tablist" }), panels = [];
    n.kids.forEach((k, i) => {
      const kk = { ...k, p: { ...k.p, title: null } };
      const panel = h("div", { class: "su-panel", hidden: i !== 0 }, node(kk, `${path}[${i}]`));
      const b = h("button", { type: "button", role: "tab", "aria-selected": i === 0 ? "true" : "false" }, k.p.title || `View ${i + 1}`);
      b.addEventListener("click", () => { bar.querySelectorAll("button").forEach((x) => x.setAttribute("aria-selected", "false")); b.setAttribute("aria-selected", "true"); panels.forEach((q) => (q.hidden = q !== panel)); flushPending(); window.dispatchEvent(new Event("resize")); });
      bar.append(b); panels.push(panel);
    });
    return titled(n, h("div", { class: "su-col su-gap-s" }, bar, ...panels));
  };
  L.sidebar = (n, path) => {
    const side = kidsInto(h("aside", { class: "su-side-a" }), n.p.side || [], path + ".side");
    const main = kidsInto(h("div", { class: "su-side-m" }), n.p.main || [], path + ".main");
    return titled(n, h("div", { class: "su-side su-at-" + (n.p.at || "left"), "--side-w": (n.p.width || 300) + "px" }, side, main));
  };
  L.float = (n, path) => {
    const body = kidsInto(h("div", { class: "su-float-b" }), n.kids, path);
    const el = h("div", { class: "su-float su-at-" + (n.p.at || "br"), "--fw": (n.p.width || 320) + "px", role: "complementary", "aria-label": n.p.title || "panel" });
    const btn = h("button", { class: "su-btn", type: "button", "aria-expanded": "true" }, "Hide");
    btn.addEventListener("click", () => { const min = el.classList.toggle("su-min"); btn.textContent = min ? "Show" : "Hide"; btn.setAttribute("aria-expanded", String(!min)); });
    el.append(h("div", { class: "su-float-h" }, h("span", null, n.p.title || ""), btn), body);
    return el;
  };
  function noteEl(n, pad) { return n.p.note ? h("div", { class: "su-note su-md", style: pad ? { padding: "0 16px 12px" } : null, html: md(n.p.note) }) : null; }
  function titled(n, el) {
    if (!n.p.title && !n.p.note && !n.p.id) return el;
    return h("div", { class: "su-node", id: n.p.id }, n.p.title ? h("h3", { class: "su-t" }, n.p.title) : null, el, noteEl(n));
  }

  function node(n, path) {
    ST.nodes++;
    try {
      if (L[n.c]) return L[n.c](n, path);
      const fn = C[n.c];
      if (!fn) throw new Error(`unknown component "${n.c}"`);
      const body = h("div", { class: "su-body" + (BOXED.has(n.c) ? " su-leaf" : ""), style: n.p.h ? { maxHeight: n.p.h + "px", overflow: "auto" } : null });
      const wrap = h("div", { class: "su-node su-c-" + n.c, id: n.p.id });
      if (n.p.title) wrap.append(h("h3", { class: "su-t" }, n.p.title, n.p.data && ["table", "list"].includes(n.c) ? h("span", { class: "su-count", style: { marginLeft: "8px" } }, rowsFor(n.p).length) : null));
      wrap.append(body);
      fn(n.p, body, n, path);
      const note = noteEl(n); if (note) wrap.append(note);
      return wrap;
    } catch (e) {
      const msg = `${path} (${n.c}): ${e && e.message || e}`;
      ST.errors.push(msg);
      return h("div", { class: "su-err" }, msg);
    }
  }

  // ---- page -----------------------------------------------------------------------
  const root = document.getElementById("su-root");
  if (PLAN.accent) document.documentElement.style.setProperty("--accent", PLAN.accent);
  const head = h("header", { class: "su-head" }, h("h1", null, PLAN.title), PLAN.subtitle ? h("p", { class: "su-sub", html: inline(PLAN.subtitle) }) : null,
    PLAN.meta && PLAN.meta.length ? h("div", { class: "su-meta" }, PLAN.meta.map((m) => badge(String(m)))) : null);
  const flow = h("main", { class: "su-flow" });
  PLAN.layout.forEach((n, i) => flow.append(node(n, `layout[${i}]`)));
  root.append(head, flow);

  const rerenderLive = () => { mermaidReady = false; LIVE.forEach((fn) => { try { fn(); } catch (e) { /* drawn again later */ } }); flushPending(); };
  matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", rerenderLive);
  new MutationObserver(rerenderLive).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  const finish = () => { flushPending(); Promise.allSettled(WAIT).then(() => Promise.allSettled(WAIT)).then(() => { ST.done = true; document.documentElement.dataset.suDone = "1"; }); };
  if (document.readyState === "complete") finish(); else window.addEventListener("load", finish);
})();
