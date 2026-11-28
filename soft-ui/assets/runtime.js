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
      else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
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
    if (ra >= 0 && rb >= 0) return ra - rb;
    if (isNum(a) && isNum(b)) return a - b;
    return String(a).localeCompare(String(b), undefined, { numeric: true });
  }
  function autoTone(ds, col) {
    const d = DS[ds]; if (!d || !col) return false;
    const vals = new Set(d.rows.map((r) => r[col]).filter((v) => v != null).map((v) => String(v).toLowerCase()));
    return vals.size > 0 && vals.size <= 12 && [...vals].every((v) => v in AUTO);
  }
  function toneOf(p, row, ds, cols) {
    if (p.tone && typeof p.tone === "object") for (const c in p.tone) {
      const m = p.tone[c], v = row[c];
      if (m && typeof m === "object" && v != null) {
        const t = m[v] ?? m[String(v)] ?? m[String(v).toLowerCase()];
        if (t) return normTone(t);
      }
    }
    for (const c of arr(cols)) if (autoTone(ds, c)) return normTone(AUTO[String(row[c]).toLowerCase()]);
    return null;
  }
  function cellTone(p, ds, col, v) {
    if (v == null) return null;
    const m = p.tone && p.tone[col];
    if (m) return normTone(m[v] ?? m[String(v)] ?? m[String(v).toLowerCase()]);
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
      case "ms": return isNaN(n) ? String(v) : n >= 1000 ? (n / 1000).toLocaleString("en", { maximumFractionDigits: 2 }) + " s" : Math.round(n * 10) / 10 + " ms";
      case "s": return isNaN(n) ? String(v) : n >= 120 ? (n / 60).toFixed(1) + " min" : n.toLocaleString("en", { maximumFractionDigits: 2 }) + " s";
      case "bytes": { if (isNaN(n)) return String(v); const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0, x = n; while (x >= 1024 && i < 4) { x /= 1024; i++; } return x.toLocaleString("en", { maximumFractionDigits: 1 }) + " " + u[i]; }
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
  function fmtCell(v, f, t) {
    if (f === "md") return h("span", { class: "su-md", html: inline(v ?? "") });
    if (f === "code") return v == null ? "" : h("code", { class: "su-code-inline" }, String(v));
    if (f === "delta") {
      const s = fmt(v, f, t); const n = parseFloat(String(v));
      return h("span", { style: { color: n > 0 ? "var(--bad-ink)" : n < 0 ? "var(--good-ink)" : "" } }, s);
    }
    return fmt(v, f, t);
  }

  // ---- data -----------------------------------------------------------------------
  function matchWhere(row, where) {
    for (const k in where) {
      const want = where[k], v = row[k];
      if (Array.isArray(want)) { if (!want.map(String).includes(String(v))) return false; }
      else if (typeof want === "string" && /^(>=|<=|>|<|!=)/.test(want)) {
        const m = want.match(/^(>=|<=|>|<|!=)\s*(.*)$/), x = isNum(v) ? +m[2] : m[2];
        if (!({ ">=": v >= x, "<=": v <= x, ">": v > x, "<": v < x, "!=": String(v) !== String(m[2]) })[m[1]]) return false;
      } else if (String(v) !== String(want)) return false;
    }
    return true;
  }
  function rowsFor(p) {
    const d = DS[p.data]; if (!d) return [];
    let rows = d.rows;
    if (p.where) rows = rows.filter((r) => matchWhere(r, p.where));
    const f = FILT[p.data];
    if (f) {
      for (const c in f.f) if (f.f[c].size) rows = rows.filter((r) => f.f[c].has(String(r[c])));
      if (f.q) { const q = f.q.toLowerCase(); rows = rows.filter((r) => Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(q))); }
    }
    return rows;
  }
  const typeOf = (ds, c) => (DS[ds] && DS[ds].types[c]) || "str";
  const uniq = (rows, c) => { const s = new Map(); for (const r of rows) { const v = r[c]; if (v != null && !s.has(String(v))) s.set(String(v), v); } return [...s.values()]; };
  function subscribe(ds, fn) { (SUBS[ds] = SUBS[ds] || []).push(fn); }
  function notify(ds) { for (const fn of SUBS[ds] || []) fn(); }
  function groupBy(rows, col) {
    const m = new Map();
    for (const r of rows) { const k = r[col] == null ? "—" : String(r[col]); if (!m.has(k)) m.set(k, []); m.get(k).push(r); }
    const keys = [...m.keys()];
    if (keys.every((k) => sevRank(k) >= 0 || k === "—")) keys.sort(cmp);
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
      const vals = uniq(DS[ds].rows, c).sort(cmp);
      const sel = h("select", { "aria-label": c, id: "su-f" + ++uid, onchange: (e) => { st.f[c] = e.target.value; onChange(); } },
        h("option", { value: "" }, `${c}: all`), vals.map((v) => h("option", { value: String(v) }, String(v))));
      bar.append(sel);
    }
    return { el: bar, apply: (rows) => rows.filter((r) => Object.entries(st.f).every(([c, v]) => !v || String(r[c]) === v) && (!st.q || Object.values(r).some((v) => v != null && String(v).toLowerCase().includes(st.q)))) };
  }

  // ---- components -----------------------------------------------------------------
  const C = {};
  const BOXED = new Set(["chart", "heatmap", "gantt", "tree", "kv", "checklist", "timeline", "meter", "diagram", "graph", "filter"]);

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
    const v = h("div", { class: "su-stat-v" }, typeof p.value === "number" ? fmt(p.value, p.fmt) : String(p.value ?? "—"));
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
  function aggValue(p) {
    const rows = rowsFor(p), agg = p.agg || "count";
    if (agg === "count") return rows.length;
    const v = rows.map((r) => +r[p.col]).filter(isFinite);
    if (!v.length) return null;
    return agg === "sum" ? v.reduce((a, b) => a + b, 0) : agg === "mean" ? v.reduce((a, b) => a + b, 0) / v.length : agg === "min" ? Math.min(...v) : Math.max(...v);
  }
  C.stat = (p, el) => {
    if (!p.data) { el.append(statEl(p)); return; }
    const draw = () => el.replaceChildren(statEl({ ...p, value: aggValue(p) }));
    draw(); subscribe(p.data, draw);
  };
  C.stats = (p, el) => {
    const grid = h("div", { class: "su-stats" });
    const draw = () => {
      grid.innerHTML = "";
      let items = arr(p.items);
      if (p.data && p.by) {
        const rows = rowsFor(p), groups = groupBy(rows, p.by);
        const order = p.order ? arr(p.order).map(String) : groups.map((g) => g[0]);
        const m = new Map(groups);
        items = (p.total ? [{ label: p.total === true ? "Total" : p.total, value: rows.length }] : [])
          .concat(order.map((k) => ({ label: k, value: (m.get(k) || []).length, tone: cellTone(p, p.data, p.by, k) || undefined })));
      } else if (p.data) {
        const rows = rowsFor(p), d = DS[p.data];
        const lc = p.label || d.cols.find((c) => typeOf(p.data, c) === "str") || d.cols[0];
        const vc = p.value || d.cols.find((c) => typeOf(p.data, c) === "num") || d.cols[1];
        items = rows.map((r) => ({ label: r[lc], value: r[vc], tone: p.tone ? r[p.tone] : null, delta: r.delta, unit: r.unit, sub: r.sub, good: r.good }));
      }
      for (const it of items) grid.append(statEl(typeof it === "object" ? it : { label: "", value: it }));
    };
    draw(); if (p.data) subscribe(p.data, draw);
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
    const cols = (p.cols && p.cols.length ? p.cols : d.cols.filter((c) => c !== p.group)).map((c) => (typeof c === "object" ? c : { key: c }));
    const sort = { k: null, d: 1 };
    if (p.sort) { sort.k = p.sort.replace(/^-/, ""); sort.d = p.sort.startsWith("-") ? -1 : 1; }
    const shut = new Set();
    let page = 0;
    const wrap = h("div", { class: "su-tw" + (p.h ? " su-scroll" : ""), style: p.h ? { maxHeight: p.h + "px" } : null });
    const ctl = localControls(p, ds, () => { page = 0; draw(); });
    if (ctl.el) el.append(ctl.el);
    el.append(wrap);
    const bars = new Set(arr(p.bar).map(colKey));
    function draw() {
      let rows = ctl.apply(rowsFor(p)).slice();
      if (sort.k) rows.sort((a, b) => sort.d * cmp(a[sort.k], b[sort.k]) || 0);
      const max = {}; for (const b of bars) max[b] = Math.max(1e-9, ...rows.map((r) => Math.abs(+r[b] || 0)));
      const total = rows.length;
      const lim = p.limit && !p.group ? p.limit : 0;
      if (lim) rows = rows.slice(page * lim, page * lim + lim);
      const t = h("table", { class: "su-table" + (p.dense ? " su-dense" : "") });
      const tr = h("tr"); for (const c of cols) tr.append(headCell(c, ds, p, sort, draw));
      t.append(h("thead", null, tr));
      const tb = h("tbody");
      const rowEl = (r) => {
        const row = h("tr");
        for (const c of cols) {
          const k = c.key, ty = typeOf(ds, k), f = c.fmt || (p.fmt && p.fmt[k]), v = r[k];
          const td = h("td", { class: (ty === "num" ? "su-num" : "") + (ty === "date" ? " su-mono" : "") });
          const tone = cellTone(p, ds, k, v);
          if (bars.has(k) && isNum(+v)) td.append(h("div", { class: "su-cellbar" }, h("i", { style: { width: Math.round((Math.abs(+v) / max[k]) * 80) + "px" } }), h("span", null, fmt(v, f, ty))));
          else if (tone) td.append(badge(fmt(v, f, ty), tone));
          else { const x = fmtCell(v, f, ty); td.append(x); }
          row.append(td);
        }
        return row;
      };
      if (p.group) {
        for (const [k, rs] of groupBy(rows, p.group)) {
          const tone = cellTone(p, ds, p.group, k);
          const g = h("tr", { class: "su-grp" + (shut.has(k) ? " su-shut" : ""), onclick: () => { shut.has(k) ? shut.delete(k) : shut.add(k); draw(); } },
            h("td", { colspan: cols.length }, tone ? badge(k, tone) : k, " ", h("span", { class: "su-count" }, rs.length)));
          tb.append(g);
          if (!shut.has(k)) rs.forEach((r) => tb.append(rowEl(r)));
        }
      } else rows.forEach((r) => tb.append(rowEl(r)));
      if (!total) tb.append(h("tr", null, h("td", { colspan: cols.length, class: "su-empty" }, "No rows match.")));
      t.append(tb);
      wrap.replaceChildren(t);
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
      const days = span / DAY, step = [1, 2, 7, 14, 30, 61, 91, 182, 365].find((s) => days / s <= 7) || 365;
      const ticks = h("div", { class: "su-g-ticks" });
      for (let t = lo; t <= hi; t += step * DAY) ticks.append(h("span", { style: { left: pos(t) + "%" } }, new Date(t).toISOString().slice(5, 10)));
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
  };
  C.tree = (p, el) => {
    const ds = p.data;
    const draw = () => {
      const root = { kids: new Map(), row: null };
      const items = p.data ? rowsFor(p).map((r) => [String(r[p.path || "path"] ?? ""), r]) : arr(p.paths).map((s) => [String(s), null]);
      for (const [path, r] of items) {
        let n = root;
        for (const part of path.split("/").filter(Boolean)) { if (!n.kids.has(part)) n.kids.set(part, { kids: new Map(), row: null }); n = n.kids.get(part); }
        n.row = r || n.row;
      }
      const ul = (n, depth) => {
        const list = h("ul");
        const entries = [...n.kids.entries()].sort((a, b) => (b[1].kids.size > 0) - (a[1].kids.size > 0) || a[0].localeCompare(b[0]));
        for (let [name, k] of entries) {
          while (k.kids.size === 1 && !k.row && [...k.kids.values()][0].kids.size) { const [n2, k2] = [...k.kids.entries()][0]; name += "/" + n2; k = k2; }
          if (k.kids.size) list.append(h("li", null, h("details", { open: depth < (p.open ?? 2) }, h("summary", null, name + "/", h("span", { class: "su-count" }, " " + countLeaves(k))), ul(k, depth + 1))));
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
    const ds = p.data, f = (FILT[ds] = FILT[ds] || { f: {}, q: "" });
    const box = h("div", { class: "su-filter" });
    const count = h("span", { class: "su-count" });
    const upd = () => { count.textContent = `${rowsFor(p).length} of ${DS[ds].rows.length} rows`; };
    if (p.search !== false) box.append(h("div", { class: "su-ctl", style: { marginBottom: 0 } }, h("input", { type: "search", placeholder: "Search…", "aria-label": "Search", id: "su-s" + ++uid, oninput: (e) => { f.q = e.target.value; notify(ds); } }), count));
    for (const c0 of arr(p.fields)) {
      const c = colKey(c0); f.f[c] = f.f[c] || new Set();
      const row = h("div", { class: "su-filter-row" }, h("b", null, c));
      const chips = h("div", { class: "su-chips" });
      for (const v of uniq(DS[ds].rows, c).sort(cmp)) {
        const t = cellTone(p, ds, c, v);
        const b = h("button", { class: "su-chip", "aria-pressed": "false", type: "button" }, t ? h("span", { class: "su-dot su-t-" + t, style: { marginRight: "5px" } }) : null, String(v));
        b.addEventListener("click", () => { const s = f.f[c], k = String(v); s.has(k) ? s.delete(k) : s.add(k); b.setAttribute("aria-pressed", s.has(k)); notify(ds); });
        chips.append(b);
      }
      row.append(chips); box.append(row);
    }
    el.append(box); upd(); subscribe(ds, upd);
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
  function chartModel(p) {
    const ds = p.data, rows = rowsFor(p), x = p.x, ys = arr(p.y).map(colKey), agg = p.agg && p.agg !== "none" ? p.agg : null;
    const xt = typeOf(ds, x);
    let keys = uniq(rows, x);
    if (xt === "date" || xt === "num" || p.sort === "x") keys.sort(cmp);
    const sdom = p.series ? uniq(DS[ds].rows, p.series).map(String) : null; // full data: colours stay put when filtered
    if (sdom && sdom.every((s) => sevRank(s) >= 0)) sdom.sort(cmp);
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
    return { labels: keys.map((k) => fmt(k, null, xt)), sets, xt };
  }
  const refLines = {
    id: "suRef",
    afterDatasetsDraw(chart, _a, opts) {
      const marks = opts.marks || []; if (!marks.length) return;
      const { ctx, chartArea: a } = chart, horiz = chart.options.indexAxis === "y";
      const sc = horiz ? chart.scales.x : chart.scales.y;
      ctx.save(); ctx.setLineDash([4, 4]); ctx.lineWidth = 1.5; ctx.strokeStyle = css("--bad"); ctx.fillStyle = css("--muted"); ctx.font = "11px " + css("--mono");
      for (const m of marks) {
        const v = m.y ?? m.x ?? m.value; if (v == null) continue;
        const px = sc.getPixelForValue(+v);
        ctx.beginPath();
        if (horiz) { ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); } else { ctx.moveTo(a.left, px); ctx.lineTo(a.right, px); }
        ctx.stroke();
        if (m.label) { ctx.textAlign = horiz ? "left" : "right"; ctx.fillText(m.label, horiz ? px + 4 : a.right - 4, horiz ? a.top + 10 : px - 4); }
      }
      ctx.restore();
    },
  };
  C.chart = (p, el) => {
    const box = h("div", { class: "su-chart", style: { height: (p.height || 260) + "px" } });
    const cv = h("canvas", { role: "img", "aria-label": (p.title || "chart") + ": " + p.kind + " of " + arr(p.y).map(colKey).join(", ") + " by " + p.x });
    box.append(cv); el.append(box);
    let chart = null;
    const draw = () => {
      if (!window.Chart) { el.replaceChildren(h("div", { class: "su-err" }, "Chart.js did not load (no network?).")); return; }
      if (chart) chart.destroy();
      const m = chartModel(p), kind = p.kind || "bar";
      const ser = seriesColors(p, kind === "donut" ? m.labels : m.sets.map((x) => x.label));
      const fg = css("--muted"), grid = css("--line"), font = css("--font");
      const single = m.sets.length === 1;
      const datasets = m.sets.map((s) => {
        const c = ser[s.idx] || ser[s.idx % 8];
        const base = { label: s.label, data: s.data, borderColor: c, backgroundColor: c };
        if (kind === "line" || kind === "area") return { ...base, borderWidth: 2, pointRadius: m.labels.length > 40 ? 0 : 2.5, pointHoverRadius: 5, tension: 0.25, fill: kind === "area" ? (p.stack ? "stack" : "origin") : false, backgroundColor: kind === "area" ? c + (p.stack ? "cc" : "33") : c, spanGaps: true };
        if (kind === "scatter") return { ...base, data: s.data.map((v, i) => ({ x: +m.labels[i].replace(/,/g, ""), y: v })), pointRadius: 4, pointHoverRadius: 6 };
        if (kind === "donut") return { ...base, backgroundColor: ser, borderColor: css("--surface"), borderWidth: 2 };
        return { ...base, borderRadius: 4, borderSkipped: "start", maxBarThickness: 38, borderWidth: 0 };
      });
      const tick = (v) => fmt(v, p.fmt);
      const vAxis = { beginAtZero: p.zero !== false, stacked: !!p.stack, grid: { color: grid, drawTicks: false }, border: { display: false }, ticks: { color: fg, padding: 6, callback: tick, maxTicksLimit: 6, precision: m.sets.every((s) => s.data.every((v) => v == null || Number.isInteger(v))) ? 0 : undefined } };
      const cAxis = { stacked: !!p.stack, grid: { display: false }, border: { color: css("--line-2") }, ticks: { color: fg, autoSkip: true, maxRotation: 0, maxTicksLimit: 12 } };
      const horiz = !!p.horizontal && kind === "bar";
      const cfg = {
        type: kind === "area" ? "line" : kind === "donut" ? "doughnut" : kind,
        data: { labels: m.labels, datasets },
        options: {
          responsive: true, maintainAspectRatio: false, animation: false, indexAxis: horiz ? "y" : "x",
          interaction: { mode: kind === "scatter" || kind === "donut" ? "nearest" : "index", intersect: kind === "scatter" || kind === "donut" },
          plugins: {
            legend: { display: !single || kind === "donut", position: "top", align: "start", labels: { color: fg, boxWidth: 10, boxHeight: 10, font: { family: font, size: 12 }, padding: 12 } },
            tooltip: { callbacks: { label: (c) => ` ${c.dataset.label}: ${fmt(c.parsed && typeof c.parsed === "object" ? (horiz ? c.parsed.x : c.parsed.y) : c.parsed, p.fmt)}` } },
            suRef: { marks: arr(p.mark) },
          },
          scales: kind === "donut" ? {} : horiz ? { x: vAxis, y: cAxis } : { x: kind === "scatter" ? { ...vAxis, beginAtZero: false } : cAxis, y: vAxis },
          cutout: kind === "donut" ? "62%" : undefined,
        },
        plugins: [refLines],
      };
      Chart.defaults.font.family = font; Chart.defaults.color = fg;
      chart = new Chart(cv, cfg);
    };
    draw(); subscribe(p.data, draw); LIVE.push(draw);
  };

  C.heatmap = (p, el) => {
    const ds = p.data, box = h("div", { class: "su-heat" }); el.append(box);
    const draw = () => {
      const rows = rowsFor(p), xt = typeOf(ds, p.x);
      const xs = uniq(rows, p.x); if (xt === "date" || xt === "num") xs.sort(cmp);
      const cell = new Map(), tot = new Map();
      for (const r of rows) {
        const k = r[p.y] + "\u0001" + r[p.x]; if (!cell.has(k)) cell.set(k, []);
        cell.get(k).push(p.v ? +r[p.v] : 1);
      }
      const val = (a) => !a ? null : p.agg === "mean" ? a.reduce((s, b) => s + b, 0) / a.length : p.agg === "max" ? Math.max(...a) : p.agg === "count" ? a.length : a.reduce((s, b) => s + b, 0);
      const ys = uniq(rows, p.y);
      for (const y of ys) tot.set(y, xs.reduce((s, x) => s + (val(cell.get(y + "\u0001" + x)) || 0), 0));
      if (typeOf(ds, p.y) !== "date") ys.sort((a, b) => tot.get(b) - tot.get(a)); else ys.sort(cmp);
      const all = [...cell.values()].map(val).filter(isNum);
      const lo = Math.min(0, ...all), hi = Math.max(...all, 0), amax = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
      const color = (v) => {
        if (v == null) return "var(--sunk)";
        if (p.scale === "div") { const t = Math.abs(v) / amax; return `color-mix(in oklab, var(${v < 0 ? "--div-lo" : "--div-hi"}) ${Math.round(8 + 82 * t)}%, var(--surface))`; }
        const t = hi === lo ? 1 : (v - lo) / (hi - lo); return `color-mix(in oklab, var(--seq-hi) ${Math.round(6 + 90 * t)}%, var(--surface))`;
      };
      const t = h("table", { role: "grid" });
      t.append(h("thead", null, h("tr", null, h("th"), xs.map((x) => h("th", null, fmt(x, null, xt))))));
      const tb = h("tbody");
      for (const y of ys) {
        const tr = h("tr", null, h("th", { class: "su-y", title: y }, y));
        for (const x of xs) {
          const v = val(cell.get(y + "\u0001" + x)), tt = v == null ? 0 : p.scale === "div" ? Math.abs(v) / amax : (v - lo) / (hi - lo || 1);
          tr.append(h("td", { style: { background: color(v) }, class: tt > 0.55 && p.scale !== "div" ? "su-hi" : "", title: `${y} · ${fmt(x, null, xt)}: ${v == null ? "—" : fmt(v, p.fmt)}` }, p.labels && v != null ? fmt(v, p.fmt) : ""));
        }
        tb.append(tr);
      }
      t.append(tb);
      const scale = h("div", { class: "su-scale" }, h("span", null, fmt(p.scale === "div" ? -amax : lo, p.fmt)),
        h("i", { style: { background: p.scale === "div" ? "linear-gradient(90deg, var(--div-lo), var(--surface), var(--div-hi))" : "linear-gradient(90deg, color-mix(in oklab, var(--seq-hi) 6%, var(--surface)), var(--seq-hi))" } }),
        h("span", null, fmt(p.scale === "div" ? amax : hi, p.fmt)), p.v ? h("span", null, `${p.agg || "sum"} of ${p.v}`) : h("span", null, "rows"));
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
      h("div", { class: "su-cnote-h" }, n.sev ? badge(String(n.sev), t) : null, n.head ? h("b", { html: inline(n.head) }) : null),
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
    const split = (p.mode || "split") === "split";
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
      flowchart: { htmlLabels: true, curve: "basis" }, sequence: { useMaxWidth: true }, themeCSS: ".node rect, .node polygon { rx: 6; ry: 6; }",
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
    const job = { el: box, src: p.src, path };
    PENDING.push(job);
    LIVE.push(() => { if (!PENDING.includes(job)) { mermaidReady = false; PENDING.push(job); } });
  };
  C.graph = C.diagram;

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
