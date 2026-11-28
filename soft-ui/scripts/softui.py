#!/usr/bin/env python3
"""soft-ui: turn a short YAML spec into one checked, self-contained HTML page.

Usage:
  softui.py catalog                       list each component, one line each
  softui.py explain NAME [NAME ...]       props and an example for each component
  softui.py render SPEC [-o OUT] [--artifact] [--fast] [--shot PNG]

SPEC is a .yaml/.yml/.json file, or "-" to read the spec from stdin. Data file paths in the
spec resolve from the folder of the spec (from the current folder for stdin).

render fixes small mistakes itself and prints one "fixed" line for each, with the right
form to use next time. It writes nothing when it finds an error that it cannot fix.
--artifact writes the page in the form that the Artifact tool publishes (no html/head/body).
After it writes the page, render loads it in headless Chromium (about 2 s) and reports render
errors, for example a Mermaid syntax error, and sideways scroll at phone width. --fast skips this.
"""

import argparse
import csv
import difflib
import hashlib
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registry as R  # noqa: E402

ASSETS = HERE.parent / "assets"
LIBS = {
    "chart": "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js",
    "mermaid": "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js",
    "hljs": "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js",
}
FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&"
         "family=IBM+Plex+Sans:wght@400;500;600;700&display=swap")
MAX_INLINE_KB = 1500


class SpecError(Exception):
    pass


# ---- name lookup ----------------------------------------------------------------------

ALIAS_TO_COMP = {}
for _name, _c in R.C.items():
    ALIAS_TO_COMP[_name] = _name
    for _a in _c["aliases"]:
        ALIAS_TO_COMP.setdefault(_a.lower(), _name)
for _k in R.CHART_KINDS:
    ALIAS_TO_COMP.setdefault(_k, "chart")


def close(word, options, cutoff=0.72):
    m = difflib.get_close_matches(word, list(options), n=1, cutoff=cutoff)
    return m[0] if m else None


def lookup_comp(key):
    """Return (component, how) for a key, or (None, None). how is '' for an exact match."""
    if not isinstance(key, str):
        return None, None
    k = key.strip()
    if k in R.C:
        return k, ""
    kl = k.lower().replace("_", "-")
    if kl in R.C:
        return kl, "case"
    if kl in ALIAS_TO_COMP:
        return ALIAS_TO_COMP[kl], "alias"
    kl2 = kl.replace("-", "")
    if kl2 in ALIAS_TO_COMP:
        return ALIAS_TO_COMP[kl2], "alias"
    m = close(kl, ALIAS_TO_COMP.keys(), 0.8)
    if m:
        return ALIAS_TO_COMP[m], "typo"
    return None, None


# ---- data loading ---------------------------------------------------------------------

TOON_HEAD = re.compile(r"^\s*(?:[\w-]+)?\[(\d+)\]\{([^}]*)\}:\s*$")


def scalar(v):
    """Turn a CSV cell into a number, bool, None, or str."""
    if not isinstance(v, str):
        return v
    s = v.strip()
    if s == "":
        return None
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    if s.lower() in ("null", "none", "-"):
        return None
    if re.fullmatch(r"[+-]?\d+", s):
        try:
            return int(s)
        except ValueError:
            return s
    if re.fullmatch(r"[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?", s):
        return float(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_csv(text, delim=None):
    text = text.strip("\n")
    if delim is None:
        first = text.split("\n", 1)[0]
        delim = "\t" if "\t" in first else ("|" if first.count("|") > first.count(",") else ",")
    lines = [ln for ln in text.split("\n") if ln.strip() and not re.fullmatch(r"[\s|:-]+", ln)]
    if delim == "|":
        lines = [ln.strip().strip("|") for ln in lines]
    rd = csv.reader(io.StringIO("\n".join(lines)), delimiter=delim, skipinitialspace=True)
    rows = list(rd)
    if not rows:
        return []
    head = [h.strip() for h in rows[0]]
    return [{h: scalar(c) for h, c in zip(head, r)} for r in rows[1:]]


def parse_toon(text):
    lines = text.strip("\n").split("\n")
    m = TOON_HEAD.match(lines[0])
    head = [h.strip() for h in m.group(2).split(",")]
    body = "\n".join(ln.strip() for ln in lines[1:] if ln.strip())
    rd = csv.reader(io.StringIO(body), skipinitialspace=True)
    return [{h: scalar(c) for h, c in zip(head, r)} for r in rd]


def looks_like_path(s):
    return (isinstance(s, str) and "\n" not in s and len(s) < 300
            and re.search(r"\.(json|jsonl|ndjson|csv|tsv|ya?ml|toon|txt|diff|patch|[a-z]{1,5})$", s.strip())
            is not None and " " not in s.strip())


class Ctx:
    def __init__(self, base):
        self.base = base
        self.fixes = []
        self.errors = []
        self.data = {}  # name -> {"rows": [...], "cols": [...]}
        self.libs = set()
        self.count = 0
        self.anon = 0
        self.told = set()

    def fix(self, path, what, hint):
        # Give a long props list only the first time.
        m = re.search(r" \((\w+) props: [^)]*\)$| \((\w+) props are .*\)$", hint)
        if m:
            name = m.group(1) or m.group(2)
            if name in self.told:
                hint = hint[:m.start()]
            self.told.add(name)
        self.fixes.append(f"fixed {path}: {what}. Next time: {hint}")

    def err(self, path, msg):
        self.errors.append(f"error {path}: {msg}")

    def file(self, s):
        p = Path(s).expanduser()
        if not p.is_absolute():
            p = self.base / p
        return p


def dig(obj, dotted):
    for part in dotted.split("."):
        if isinstance(obj, dict):
            obj = obj.get(part)
        elif isinstance(obj, list) and part.isdigit():
            obj = obj[int(part)]
        else:
            return None
    return obj


import ast
import operator as op

BINOPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Mod: op.mod,
          ast.Pow: op.pow, ast.FloorDiv: op.floordiv}
CMPOPS = {ast.Eq: op.eq, ast.NotEq: op.ne, ast.Lt: op.lt, ast.LtE: op.le, ast.Gt: op.gt, ast.GtE: op.ge}
FUNCS = {"round": round, "abs": abs, "min": min, "max": max, "len": len, "str": str, "int": int, "float": float}


def safe_eval(node, row):
    """Evaluate a small expression over one row: arithmetic, comparisons, if/else, and FUNCS."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body, row)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in row:
            raise KeyError(node.id)
        return row[node.id]
    if isinstance(node, ast.BinOp) and type(node.op) in BINOPS:
        a, b = safe_eval(node.left, row), safe_eval(node.right, row)
        if a is None or b is None:
            return None
        if isinstance(node.op, ast.Div) and b == 0:
            return None
        return BINOPS[type(node.op)](a, b)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = safe_eval(node.operand, row)
        return None if v is None else -v
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in CMPOPS:
        return CMPOPS[type(node.ops[0])](safe_eval(node.left, row), safe_eval(node.comparators[0], row))
    if isinstance(node, ast.BoolOp):
        vals = [safe_eval(v, row) for v in node.values]
        return all(vals) if isinstance(node.op, ast.And) else any(vals)
    if isinstance(node, ast.IfExp):
        return safe_eval(node.body, row) if safe_eval(node.test, row) else safe_eval(node.orelse, row)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS:
        args = [safe_eval(a, row) for a in node.args]
        return None if any(a is None for a in args) else FUNCS[node.func.id](*args)
    raise ValueError(f"not allowed in an expression: {ast.dump(node)[:40]}")


def add_columns(ctx, rows, adds, path):
    """Add computed columns: add: {name: "expression over columns"}."""
    if not isinstance(adds, dict):
        ctx.err(path, 'add must be a map, e.g. add: {delta: "after - before"}')
        return rows
    cols = list(rows[0].keys()) if rows else []
    for name, expr in adds.items():
        try:
            tree = ast.parse(str(expr), mode="eval")
        except SyntaxError:
            ctx.err(path, f'add.{name}: "{expr}" is not a valid expression')
            continue
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - set(FUNCS)
        for nm in sorted(names - set(cols)):
            m = close(nm, cols, 0.6)
            ctx.err(path, f'add.{name}: no column "{nm}"' + (f' (did you mean "{m}"?)' if m else f". Columns: {', '.join(cols)}"))
        if names - set(cols):
            continue
        try:
            for r in rows:
                v = safe_eval(tree, r)
                r[name] = round(v, 4) if isinstance(v, float) else v
        except (ValueError, TypeError, KeyError) as e:
            ctx.err(path, f'add.{name}: {e}. Allowed: + - * / % **, comparisons, x if c else y, {", ".join(FUNCS)}')
            continue
        cols.append(name)
    return rows


def to_rows(val, ctx, path, base_key=None):
    """Turn any data form into a list of dict rows. Return None on error."""
    if isinstance(val, dict) and "add" in val and any(k in val for k in ("file", "path", "src", "rows", "csv")):
        val = dict(val)
        adds = val.pop("add")
        inner = val.pop("rows", None) or val.pop("csv", None)
        rows = to_rows(inner if inner is not None else val, ctx, path)
        return None if rows is None else add_columns(ctx, [dict(r) for r in rows], adds, path)
    if isinstance(val, dict) and ("file" in val or "path" in val or "src" in val):
        f = val.get("file") or val.get("src") or val.get("path")
        rows = to_rows(f, ctx, path)
        key = val.get("key") or val.get("at") or val.get("select")
        if rows is not None and key:
            raw = load_file_raw(ctx.file(f))
            sub = dig(raw, str(key))
            if sub is None:
                keys = ", ".join(k for k, v in raw.items() if isinstance(v, (list, dict))) if isinstance(raw, dict) else ""
                ctx.err(path, f'no key "{key}" in {f}. Keys that hold data: {keys or "none"}')
                return None
            rows = to_rows(sub, ctx, path)
        return rows
    if isinstance(val, str) and "#" in val and looks_like_path(val.split("#", 1)[0]):
        f, key = val.strip().split("#", 1)
        return to_rows({"file": f, "key": key}, ctx, path)
    if isinstance(val, str):
        s = val.strip()
        if looks_like_path(s):
            p = ctx.file(s)
            if not p.exists():
                ctx.err(path, f'data file "{s}" not found (looked in {p.parent})')
                return None
            return to_rows(load_file_raw(p), ctx, path)
        if TOON_HEAD.match(s.split("\n", 1)[0]):
            return parse_toon(s)
        if "\n" in s:
            return parse_csv(s)
        ctx.err(path, f'data "{s}" is not a dataset name, a file, or CSV text')
        return None
    if isinstance(val, list):
        if not val:
            return []
        if all(isinstance(r, dict) for r in val):
            return val
        if all(isinstance(r, list) for r in val):
            head = [str(h) for h in val[0]]
            ctx.fix(path, "converted a list of lists (first row = header) to rows",
                    "a list of lists is fine; a list of maps or CSV text also works")
            return [dict(zip(head, r)) for r in val[1:]]
        if all(not isinstance(r, (dict, list)) for r in val):
            return [{"value": r} for r in val]
    if isinstance(val, dict):
        # {key: value} map -> rows of key/value; {key: {..}} map -> rows with an id column.
        if all(isinstance(v, dict) for v in val.values()):
            return [{"id": k, **v} for k, v in val.items()]
        if all(isinstance(v, list) for v in val.values()):
            n = max(len(v) for v in val.values())
            ctx.fix(path, "converted a map of columns to rows", "a list of rows or CSV text")
            return [{k: (v[i] if i < len(v) else None) for k, v in val.items()} for i in range(n)]
        return [{"key": k, "value": v} for k, v in val.items()]
    ctx.err(path, "data must be rows (a list of maps), CSV text, TOON text, or a file path")
    return None


def diffstat(text):
    rows = []
    for f in parse_patch(text):
        status = "added" if not f["old"] else "deleted" if not f["new"] else "renamed" if f["old"] != f["new"] else "modified"
        rows.append({"file": f["new"] or f["old"], "status": status, "added": f["add"], "removed": f["del"]})
    return rows


def load_file_raw(p):
    text = p.read_text(encoding="utf-8", errors="replace")
    ext = p.suffix.lower()
    if ext in (".diff", ".patch"):
        return diffstat(text)
    if ext == ".json":
        return json.loads(text)
    if ext in (".jsonl", ".ndjson"):
        return [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    if ext in (".yaml", ".yml"):
        return load_yaml(text)
    if ext == ".tsv":
        return parse_csv(text, "\t")
    if ext == ".toon":
        return parse_toon(text)
    return parse_csv(text)


def col_type(vals):
    vals = [v for v in vals if v is not None][:300]
    if not vals:
        return "str"
    if all(isinstance(v, bool) for v in vals):
        return "bool"
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return "num"
    if all(isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}([T ][\d:.]+Z?([+-]\d{2}:?\d{2})?)?$", v) for v in vals):
        return "date"
    return "str"


def register_parts(ctx, name, val):
    """A JSON object file also gives one dataset per array inside it: name.key."""
    if not (isinstance(val, str) and looks_like_path(val) and "#" not in val):
        return
    p = ctx.file(val.strip())
    if p.suffix.lower() not in (".json", ".yaml", ".yml") or not p.exists():
        return
    raw = load_file_raw(p)
    if not isinstance(raw, dict):
        return
    for k, v in raw.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            register(ctx, f"{name}.{k}", v)
        elif isinstance(v, dict) and v and all(isinstance(x, (list, dict)) for x in v.values()):
            for k2, v2 in v.items():
                if isinstance(v2, list) and v2 and all(isinstance(x, dict) for x in v2):
                    register(ctx, f"{name}.{k}.{k2}", v2)


def register(ctx, name, rows):
    cols = []
    for r in rows[:500]:
        for k in r:
            if k not in cols:
                cols.append(k)
    rows = [{k: jsonable(v) for k, v in r.items()} for r in rows]
    types = {c: col_type([r.get(c) for r in rows]) for c in cols}
    ctx.data[name] = {"rows": rows, "cols": cols, "types": types}


def jsonable(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, (list, dict)):
        return v
    return str(v)


# ---- YAML -----------------------------------------------------------------------------

def load_yaml(text):
    try:
        import yaml  # PyYAML
    except ImportError:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise SpecError("PyYAML is not installed. Run: pip install pyyaml (or write the spec as JSON)")

    class Loader(yaml.SafeLoader):
        pass
    # Keep dates as strings: the page formats them.
    for ch, resolvers in list(Loader.yaml_implicit_resolvers.items()):
        Loader.yaml_implicit_resolvers[ch] = [(t, r) for t, r in resolvers if t != "tag:yaml.org,2002:timestamp"]
    try:
        return yaml.load(text, Loader=Loader)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        prob = getattr(e, "problem", None) or str(e).split("\n")[0]
        hint = ""
        if "mapping values are not allowed" in str(e):
            hint = ' Hint: quote a value that has ": " in it, e.g. text: "a: b".'
        elif "found character '\\t'" in str(e):
            hint = " Hint: indent with spaces, not tabs."
        raise SpecError(f"YAML syntax error{where}: {prob}.{hint}")


# ---- spec normalisation -----------------------------------------------------------------

def coerce(ctx, path, comp, key, val, spec):
    """Coerce one prop value to its type. Return (ok, value)."""
    t = spec["t"]
    if t == "str":
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return True, str(val)
        if isinstance(val, str):
            return True, val
        if isinstance(val, list) and key in ("sort",):
            return True, str(val[0])
        return True, json.dumps(val) if not isinstance(val, str) else val
    if t in ("int", "num"):
        if isinstance(val, bool):
            ctx.err(path, f"{key} must be a number, not {val}")
            return False, None
        if isinstance(val, (int, float)):
            return True, int(val) if t == "int" else val
        if isinstance(val, str):
            m = re.fullmatch(r"\s*([+-]?\d+(?:\.\d+)?)\s*(px|%)?\s*", val)
            if m:
                ctx.fix(path, f'{key} "{val}" read as a number', f"{key}: {m.group(1)}")
                n = float(m.group(1))
                return True, int(n) if t == "int" else n
        ctx.err(path, f"{key} must be a number, got {val!r}")
        return False, None
    if t == "bool":
        if isinstance(val, bool):
            return True, val
        if isinstance(val, str) and val.lower() in ("yes", "no", "on", "off", "true", "false", "1", "0"):
            return True, val.lower() in ("yes", "on", "true", "1")
        if isinstance(val, (int, float)):
            return True, bool(val)
        ctx.err(path, f"{key} must be true or false")
        return False, None
    if t == "enum":
        opts = spec["enum"]
        if isinstance(val, str):
            v = val.strip()
            if v in opts:
                return True, v
            vl = v.lower()
            if key == "kind" and vl in R.CHART_KINDS:
                nv = R.CHART_KINDS[vl]
                if nv != v:
                    ctx.fix(path, f'kind "{v}" → "{nv}"', f"kind: {nv}")
                return True, nv
            for o in opts:
                if o.lower() == vl:
                    return True, o
            syn = {"vertical": "TD", "horizontal": "LR", "down": "TD", "right": "LR", "tb": "TD",
                   "bottom-right": "br", "bottom-left": "bl", "top-right": "tr", "top-left": "tl",
                   "warning": "warn", "danger": "bad", "error": "bad", "critical": "bad", "success": "good",
                   "ok": "good", "pass": "good", "fail": "bad", "average": "mean", "avg": "mean",
                   "total": "sum", "side-by-side": "split", "inline": "unified", "small": "s",
                   "medium": "m", "large": "l", "percent": "pct", "integer": "int", "number": "num"}
            if vl in syn and syn[vl] in opts:
                ctx.fix(path, f'{key} "{v}" → "{syn[vl]}"', f"{key}: {syn[vl]} (one of {', '.join(opts)})")
                return True, syn[vl]
            m = close(vl, opts, 0.6)
            if m:
                ctx.fix(path, f'{key} "{v}" → "{m}"', f"{key}: {m} (one of {', '.join(opts)})")
                return True, m
        if val is True and "count" in opts:
            return True, "count"
        if spec.get("default") is not None:
            ctx.fix(path, f"{key} {val!r} is not one of {', '.join(opts)}; used {spec['default']}",
                    f"{key}: one of {', '.join(opts)}")
            return True, spec["default"]
        ctx.err(path, f"{key} must be one of {', '.join(opts)}, got {val!r}")
        return False, None
    if t == "list":
        if isinstance(val, list):
            return True, val
        if isinstance(val, str) and "," in val:
            return True, [scalar(x) for x in val.split(",")]
        return True, [val]
    if t == "map":
        if isinstance(val, dict):
            return True, val
        if isinstance(val, list) and all(isinstance(x, dict) and len(x) == 1 for x in val):
            out = {}
            for x in val:
                out.update(x)
            return True, out
        ctx.err(path, f"{key} must be a map (key: value)")
        return False, None
    if t == "text":
        if isinstance(val, (int, float)):
            return True, str(val)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            return True, "\n".join(val)
        if not isinstance(val, str):
            ctx.err(path, f"{key} must be text")
            return False, None
        return True, val
    return True, val  # any, col, cols, data, nodes: checked elsewhere


def node_label(name, path):
    return f"{path}.{name}" if path else name


def norm_nodes(ctx, val, path):
    """Normalise a list of nodes."""
    if val is None:
        return []
    if isinstance(val, dict):
        comp, _ = find_comp_key(val)
        if comp or "type" in val or "component" in val:
            val = [val]
        else:
            # {label: node} map, e.g. tabs given as a map.
            out = []
            for k, v in val.items():
                kids = norm_nodes(ctx, v if isinstance(v, list) else [v], f"{path}[{k}]")
                if len(kids) == 1:
                    kids[0]["p"].setdefault("title", str(k))
                    out.append(kids[0])
                elif kids:
                    out.append({"c": "col", "p": {"title": str(k)}, "kids": kids})
            return out
    if not isinstance(val, list):
        val = [val]
    out = []
    for i, n in enumerate(val):
        nn = norm_node(ctx, n, f"{path}[{i}]")
        if nn is not None:
            out.append(nn)
    return out


def find_comp_key(d):
    hits = []
    for k in d:
        c, how = lookup_comp(k)
        if c and how != "typo":
            hits.append((k, c, how))
    if not hits:
        for k in d:
            if k in R.COMMON:
                continue
            c, how = lookup_comp(k)
            if c:
                hits.append((k, c, how))
    if not hits:
        return None, None
    # Prefer the key whose value is a map or list (the props), then the first key.
    hits.sort(key=lambda h: (not isinstance(d[h[0]], (dict, list)), list(d).index(h[0])))
    return hits[0][1], hits[0][0]


def norm_node(ctx, n, path):
    ctx.count += 1
    if isinstance(n, str):
        return {"c": "text", "p": {"md": n}, "kids": []}
    if isinstance(n, list):
        ctx.fix(path, "a nested list became a col", "- col: [...]")
        return {"c": "col", "p": {}, "kids": norm_nodes(ctx, n, path)}
    if not isinstance(n, dict):
        return {"c": "text", "p": {"md": str(n)}, "kids": []}
    d = dict(n)
    comp, key = None, None
    if not any(lookup_comp(k)[1] in ("", "case") for k in d):
        for tk in ("type", "component", "c"):
            if isinstance(d.get(tk), str) and lookup_comp(d[tk])[0]:
                orig = d.pop(tk)
                comp = lookup_comp(orig)[0]
                if comp == "chart" and orig.lower() in R.CHART_KINDS:
                    d.setdefault("kind", R.CHART_KINDS[orig.lower()])
                ctx.fix(path, f"{tk}: {orig} read as the component name", f"- {comp}: {{...props}}")
                return build(ctx, comp, d, node_label(comp, path))
    if comp is None:
        comp, key = find_comp_key(d)
        if comp is None:
            ctx.err(path, f"no component in {sorted(d)}. Run `softui.py catalog` for the names")
            return None
        _, how = lookup_comp(key)
        val = d.pop(key)
        props_in = {}
        cdef = R.C[comp]
        if isinstance(val, dict) and not (comp in ("kv",) and not any(k in cdef["props"] for k in val)):
            props_in.update(val)
        elif val is not None:
            if cdef["short"]:
                props_in[cdef["short"]] = val
            elif "data" in cdef["props"]:
                props_in["data"] = val
            elif "src" in cdef["props"]:
                props_in["src"] = val
            else:
                ctx.err(path, f"{comp} needs a map of props, e.g. {comp}: {{...}}")
                return None
        for k, v in d.items():  # sibling keys are props too
            props_in.setdefault(k, v)
        kl = key.lower()
        if comp == "chart" and kl in R.CHART_KINDS:
            props_in.setdefault("kind", R.CHART_KINDS[kl])
        elif comp == "callout" and kl in R.CALLOUT_TONES:
            props_in.setdefault("tone", R.CALLOUT_TONES[kl])
        elif comp == "diagram" and kl in R.MERMAID_HEADERS:
            props_in["_hint"] = R.MERMAID_HEADERS[kl]
        elif how in ("typo",):
            ctx.fix(path, f'"{key}" → {comp}', f"- {comp}: ...")
        elif how == "alias" and kl not in R.CHART_KINDS and kl not in R.CALLOUT_TONES and kl not in R.MERMAID_HEADERS:
            ctx.fix(path, f'"{key}" read as {comp}', f"- {comp}: ...")
    return build(ctx, comp, props_in, node_label(comp, path))


def norm_props(ctx, comp, props_in, path):
    cdef = R.C[comp]
    allp = {**R.COMMON, **cdef["props"]}
    out = {}
    hint = props_in.pop("_hint", None)
    for k, v in props_in.items():
        k2 = k
        if k not in allp:
            cand = R.PROP_ALIASES.get(k) or R.PROP_ALIASES.get(str(k).lower())
            if cand not in allp:
                cand = close(str(k).lower(), allp.keys(), 0.7)
            if cand and cand not in props_in:
                ctx.fix(path, f'prop "{k}" → "{cand}"', f"{cand}: ... ({comp} props: {', '.join(cdef['props'])})")
                k2 = cand
            elif v is None:
                ctx.fix(path, f'dropped "{k}" with no value; a comma inside {{...}} splits the text there',
                        'quote text that has a comma, e.g. sub: "a, b, c"')
                continue
            else:
                ctx.fix(path, f'dropped unknown prop "{k}"', f"use only known props ({comp} props: {', '.join(cdef['props'])})")
                continue
        out[k2] = v
    if hint:
        out["_hint"] = hint
    return out


def build(ctx, comp, props_in, path):
    cdef = R.C[comp]
    p = norm_props(ctx, comp, props_in, path)
    allp = {**R.COMMON, **cdef["props"]}
    node = {"c": comp, "p": {}, "kids": []}

    # Children first.
    errs_before = len(ctx.errors)
    for ck in ("items", "side", "main"):
        if ck in allp and allp[ck]["t"] == "nodes" and ck in p:
            kids = norm_nodes(ctx, p.pop(ck), f"{path}.{ck}" if ck != "items" else path)
            if ck == "items":
                node["kids"] = kids
            else:
                node["p"][ck] = kids

    # Data next, so columns can be checked.
    ds = None
    if "data" in cdef["props"] and "data" in p:
        ds = resolve_data(ctx, p.pop("data"), path)
        if ds is None:
            return None
        node["p"]["data"] = ds

    for k, v in p.items():
        if k == "_hint":
            node["p"][k] = v
            continue
        spec = allp[k]
        ok, v2 = coerce(ctx, path, comp, k, v, spec)
        if not ok:
            continue
        node["p"][k] = v2

    # Required props.
    for k, spec in cdef["props"].items():
        if spec["req"] and k not in node["p"] and not (k == "items" and node["kids"]) \
                and not (spec["t"] == "nodes" and len(ctx.errors) > errs_before):
            if not default_required(ctx, comp, k, node, path):
                ctx.err(path, f"{comp} needs `{k}` ({spec['doc'] or spec['t']})."
                        + (f" Columns: {', '.join(ctx.data[ds]['cols'])}" if ds and spec["t"] == "col" else ""))
    check_cols(ctx, comp, node, ds, path)
    finish(ctx, comp, node, path)
    return node


def default_required(ctx, comp, k, node, path):
    p = node["p"]
    ds = p.get("data")
    cols = ctx.data[ds]["cols"] if ds in ctx.data else []
    types = ctx.data[ds]["types"] if ds in ctx.data else {}

    def pick(names, want=None):
        for n in names:
            for c in cols:
                if c.lower() == n:
                    return c
        if want:
            for c in cols:
                if types.get(c) == want:
                    return c
        return None
    guess = None
    if comp == "chart" and k == "x":
        guess = pick(["x", "date", "day", "week", "month", "time", "name", "label", "category"], "date") or (cols[0] if cols else None)
    elif comp in ("list", "board") and k == "head":
        guess = pick(["title", "name", "summary", "head", "label", "id"], "str")
    elif comp == "timeline" and k == "at":
        guess = pick(["at", "date", "when", "time", "ts"], "date")
    elif comp == "timeline" and k == "text":
        guess = pick(["text", "what", "event", "title", "message", "summary"], "str")
    elif comp == "gantt" and k == "task":
        guess = pick(["task", "name", "title", "step"], "str")
    elif comp == "gantt" and k == "start":
        guess = pick(["start", "from", "begin"], "date")
    elif comp == "graph" and k == "from":
        guess = pick(["from", "src", "source", "a"])
    elif comp == "graph" and k == "to":
        guess = pick(["to", "dst", "target", "b"])
    elif comp == "heatmap" and k in ("x", "y"):
        guess = None
    elif (comp == "kv" and k == "pairs" and "data" in p) or (comp == "stat" and k == "value" and "data" in p):
        return True
    elif comp == "stat" and k == "label":
        p["label"] = p.get("title", "")
        return True
    if guess:
        p[k] = guess
        ctx.fix(path, f"{comp} had no `{k}`; used column \"{guess}\"", f"{k}: {guess}")
        return True
    return False


def resolve_data(ctx, val, path):
    if isinstance(val, str) and val in ctx.data:
        return val
    if isinstance(val, str) and "\n" not in val and not looks_like_path(val):
        m = close(val, ctx.data.keys(), 0.6) or next((k for k in ctx.data if k.lower() == val.lower()), None)
        if m:
            ctx.fix(path, f'data "{val}" → "{m}"', f"data: {m}")
            return m
        ctx.err(path, f'no dataset "{val}". Datasets: {", ".join(ctx.data) or "none (add a top-level data: map)"}')
        return None
    rows = to_rows(val, ctx, path)
    if rows is None:
        return None
    key = val if isinstance(val, str) and looks_like_path(val) else None
    if key and key in ctx.data:
        return key
    ctx.anon += 1
    name = key or f"_d{ctx.anon}"
    register(ctx, name, rows)
    return name


def col_fix(ctx, ds, c, path, key):
    """Return the right column name for c in ds, or None."""
    cols = ctx.data[ds]["cols"]
    if not isinstance(c, str):
        c = str(c)
    if c in cols:
        return c
    for x in cols:
        if x.lower() == c.lower() or x.lower().replace("_", "") == c.lower().replace("_", "").replace(" ", ""):
            ctx.fix(path, f'{key} column "{c}" → "{x}"', f"{key}: {x}")
            return x
    m = close(c, cols, 0.6)
    if m:
        ctx.fix(path, f'{key} column "{c}" → "{m}"', f"{key}: {m}")
        return m
    ctx.err(path, f'{key}: no column "{c}" in "{ds}". Columns: {", ".join(cols)}')
    return None


def check_cols(ctx, comp, node, ds, path):
    p = node["p"]
    cdef = R.C[comp]
    if ds is None or ds not in ctx.data:
        for k, spec in cdef["props"].items():
            if spec["t"] in ("col", "cols") and k in p and comp not in ("checklist", "tree", "stats") and k != "filter":
                pass
        return
    for k, spec in cdef["props"].items():
        if k not in p or spec["t"] not in ("col", "cols"):
            continue
        v = p[k]
        if spec["t"] == "col":
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            r = col_fix(ctx, ds, v, path, k)
            if r is None:
                p.pop(k)
            else:
                p[k] = r
        else:
            if v is True:
                continue
            if v is False:
                p.pop(k)
                continue
            if isinstance(v, str):
                v = [x.strip() for x in v.split(",")] if "," in v else [v]
            if not isinstance(v, list):
                v = [v]
            out = []
            for c in v:
                if isinstance(c, dict):
                    key = c.get("key") or c.get("col") or c.get("name") or c.get("field")
                    if key is None and len(c) == 1:
                        (key, lab), = c.items()
                        c = {"key": key, "label": lab}
                    r = col_fix(ctx, ds, key, path, k)
                    if r:
                        out.append({**{kk: vv for kk, vv in c.items() if kk not in ("col", "name", "field")}, "key": r})
                else:
                    r = col_fix(ctx, ds, c, path, k)
                    if r:
                        out.append(r)
            p[k] = out
    if comp == "graph":
        return
    tm = p.get("tone")
    if isinstance(tm, dict) and tm and all(not isinstance(v, dict) for v in tm.values()) and comp != "callout":
        # {high: bad} with no column: find the column that holds those values.
        keys = {str(k).lower() for k in tm}
        rows = ctx.data[ds]["rows"]
        best = max(ctx.data[ds]["cols"], key=lambda c: len(keys & {str(r.get(c)).lower() for r in rows}))
        if keys & {str(r.get(best)).lower() for r in rows}:
            p["tone"] = {best: tm}
            ctx.fix(path, f"tone map had no column; used \"{best}\"", f"tone: {{{best}: {{value: tone}}}}")
        else:
            ctx.fix(path, "dropped tone: no column holds its values", "tone: {column: {value: tone}}")
            p.pop("tone")
    for mk in ("tone", "fmt"):
        if isinstance(p.get(mk), dict):
            fixed = {}
            for c, v in p[mk].items():
                r = col_fix(ctx, ds, c, path, mk)
                if r:
                    fixed[r] = v
            p[mk] = fixed
    if isinstance(p.get("sort"), str) and comp == "table":
        s = p["sort"]
        neg = s.startswith("-")
        r = col_fix(ctx, ds, s.lstrip("-+").split()[0], path, "sort")
        if r:
            p["sort"] = ("-" if neg or s.lower().endswith(" desc") else "") + r
        else:
            p.pop("sort")
    if isinstance(p.get("where"), dict):
        w = {}
        for c, v in p["where"].items():
            r = col_fix(ctx, ds, c, path, "where")
            if r:
                w[r] = v
        p["where"] = w


def text_or_file(ctx, s, path, key):
    if isinstance(s, str) and looks_like_path(s):
        f = ctx.file(s.strip())
        if f.exists():
            return f.read_text(encoding="utf-8", errors="replace"), f.name
        if key in ("patch", "before", "after") or "/" in s or s.endswith((".py", ".js", ".ts", ".go", ".rs")):
            ctx.err(path, f'{key}: file "{s}" not found (looked in {f.parent})')
            return None, None
    return s, None


EXT_LANG = {".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript", ".jsx": "javascript",
            ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby", ".sh": "bash", ".yml": "yaml",
            ".yaml": "yaml", ".json": "json", ".sql": "sql", ".md": "markdown", ".css": "css", ".html": "xml",
            ".kt": "kotlin", ".cs": "csharp", ".c": "c", ".h": "c", ".cpp": "cpp", ".php": "php", ".swift": "swift",
            ".toml": "ini", ".diff": "diff"}


NOTE_COLS = {"id": ["id", "ref", "key"], "file": ["file", "path", "filename"], "line": ["line", "lineno", "line_no", "ln"],
             "head": ["title", "head", "summary", "name"], "text": ["text", "comment", "body", "message", "note", "detail"],
             "sev": ["severity", "sev", "level", "priority", "tone"]}


def resolve_notes(ctx, val, path):
    ds = resolve_data(ctx, val, path + ".notes")
    if ds is None:
        return None
    cols = ctx.data[ds]["cols"]
    pick = {k: next((c for c in cols if c.lower() in names), None) for k, names in NOTE_COLS.items()}
    if not pick["line"] or not (pick["text"] or pick["head"]):
        ctx.err(path, f"notes need a line column and a text column. Columns: {', '.join(cols)}")
        return None
    out = []
    for r in ctx.data[ds]["rows"]:
        out.append({k: r.get(c) for k, c in pick.items() if c})
    return out


def finish(ctx, comp, node, path):
    """Component-specific work: read files, compute diffs, build Mermaid text."""
    p = node["p"]
    if comp in ("diff", "code") and "notes" in p:
        notes = resolve_notes(ctx, p.pop("notes"), path)
        if notes:
            p["notes"] = notes
    if comp == "code" and "src" in p:
        src, fname = text_or_file(ctx, p["src"], path, "src")
        if src is None:
            p.pop("src")
            return
        if fname:
            p.setdefault("title", fname)
            p.setdefault("lang", EXT_LANG.get(Path(fname).suffix.lower()))
        lines = src.rstrip("\n").split("\n")
        if p.get("lines"):
            m = re.fullmatch(r"\s*(\d+)\s*[-:–]\s*(\d+)\s*", str(p["lines"]))
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                lines = lines[a - 1:b]
                p["start"] = a
            else:
                ctx.fix(path, f'lines "{p["lines"]}" ignored', "lines: 10-40")
        p["src"] = "\n".join(lines)
        if p.get("lang"):
            ctx.libs.add("hljs")
    elif comp == "diff":
        files = None
        if "patch" in p:
            txt, _ = text_or_file(ctx, p["patch"], path, "patch")
            if txt is None:
                return
            files = parse_patch(txt)
            if not files:
                ctx.err(path, "patch has no unified diff hunks (lines that start with @@)")
                return
        elif "before" in p or "after" in p:
            a, an = text_or_file(ctx, p.get("before", ""), path, "before")
            b, bn = text_or_file(ctx, p.get("after", ""), path, "after")
            if a is None or b is None:
                return
            ud = difflib.unified_diff(a.splitlines(), b.splitlines(), an or "before", bn or "after",
                                      lineterm="", n=p.get("context", 3))
            files = parse_patch("\n".join(ud)) or [{"old": an or "before", "new": bn or "after", "hunks": [], "add": 0, "del": 0}]
            if bn:
                p.setdefault("lang", EXT_LANG.get(Path(bn).suffix.lower()))
        else:
            ctx.err(path, "diff needs `patch`, or `before` and `after`")
            return
        if p.get("files"):
            want = [str(f) for f in p["files"]]
            files = [f for f in files if any(w in (f["new"] or f["old"]) for w in want)]
        for f in files:
            if not p.get("lang"):
                f["lang"] = EXT_LANG.get(Path(f["new"] or f["old"] or "").suffix.lower())
        p.pop("patch", None), p.pop("before", None), p.pop("after", None)
        p["files"] = files
        ctx.libs.add("hljs")
    elif comp == "diagram" and "src" in p:
        src = p["src"].strip("\n")
        first = src.lstrip().split("\n", 1)[0].strip()
        known = ("graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram", "gantt",
                 "pie", "mindmap", "timeline", "journey", "gitGraph", "quadrantChart", "C4", "block", "xychart",
                 "sankey", "requirementDiagram", "%%", "---")
        if not first.startswith(known):
            head = p.get("_hint") or guess_mermaid(src)
            src = head + "\n" + src
            ctx.fix(path, f"diagram had no Mermaid header; added `{head}`", f"start the source with `{head}`")
        src = re.sub(r"^```(?:mermaid)?\s*\n|\n```\s*$", "", src)
        p["src"] = src
        p.pop("_hint", None)
        ctx.libs.add("mermaid")
    elif comp == "graph" and p.get("data") in ctx.data and "from" in p and "to" in p:
        nodes = None
        if p.get("nodes"):
            nd = resolve_data(ctx, p.pop("nodes"), path + ".nodes")
            nodes = ctx.data.get(nd)
            if nodes and p.get("by") and p["by"] not in nodes["cols"]:
                p["by"] = col_fix(ctx, nd, p["by"], path, "by") or None
            if nodes and isinstance(p.get("tone"), dict):
                tm = {}
                for c, v in p["tone"].items():
                    r = col_fix(ctx, nd, c, path, "tone")
                    if r:
                        tm[r] = v
                p["tone"] = tm
        p["src"] = edges_to_mermaid(ctx.data[p["data"]]["rows"], p, nodes)
        ctx.libs.add("mermaid")
    elif comp == "chart":
        ctx.libs.add("chart")
        if not p.get("y") and p.get("agg", "none") == "none":
            p["agg"] = "count"
            ctx.fix(path, "chart had no `y`; counted rows per x", "y: <column>, or agg: count")
        if isinstance(p.get("y"), list) and len(p["y"]) > 1 and p.get("series"):
            ctx.fix(path, "chart has several y columns and a series; used the first y", "one y with series, or several y without")
            p["y"] = p["y"][:1]
    elif comp == "list" and p.get("code"):
        ctx.libs.add("hljs")
    elif comp == "kv" and isinstance(p.get("pairs"), list):
        pairs = {}
        for item in p["pairs"]:
            if isinstance(item, dict):
                pairs.update(item)
        p["pairs"] = pairs
    elif comp == "stats" and "data" not in p and isinstance(p.get("items"), dict):
        p["items"] = [{"label": k, "value": v} for k, v in p["items"].items()]
    if comp == "stats" and isinstance(p.get("items"), list):
        items = []
        for i, it in enumerate(p["items"]):
            if isinstance(it, dict):
                items.append(norm_props(ctx, "stat", dict(it), f"{path}.items[{i}]"))
            else:
                items.append(it)
        p["items"] = items
    elif comp == "checklist" and isinstance(p.get("items"), dict):
        p["items"] = [("[x] " if v else "[ ] ") + str(k) for k, v in p["items"].items()]


def guess_mermaid(src):
    if re.search(r"->>|-->>|participant |actor ", src):
        return "sequenceDiagram"
    if re.search(r"^\s*class \w+|<\|--|\*--|o--", src, re.M):
        return "classDiagram"
    if "[*]" in src:
        return "stateDiagram-v2"
    if re.search(r"\|\|--|\}o--", src):
        return "erDiagram"
    return "flowchart TD"


def mid(name, ids):
    if name not in ids:
        ids[name] = f"n{len(ids)}"
    return ids[name]


def mlabel(s):
    return '"' + str(s).replace('"', "#quot;") + '"'


TONE_FILL = {"bad": ("#fdecec", "#dc3c3d"), "warn": ("#fff4dc", "#d08f00"), "good": ("#e6f6ea", "#0aac23"),
             "info": ("#e6f0fc", "#257de0"), "neutral": ("#eef1f5", "#8a93a3")}
AUTO_TONE = {"critical": "bad", "high": "bad", "fail": "bad", "failed": "bad", "medium": "warn", "warn": "warn",
             "low": "info", "info": "info", "pass": "good", "ok": "good", "done": "good"}


def edges_to_mermaid(rows, p, nodes=None):
    ids = {}
    out = [f"flowchart {p.get('dir', 'LR')}"]
    groups = {}
    edges = []
    attrs = {}
    if nodes:
        key = p.get("key") or next((c for c in nodes["cols"] if c.lower() in ("name", "id", "node", "key")), nodes["cols"][0])
        for r in nodes["rows"]:
            attrs[r.get(key)] = r
            mid(r.get(key), ids)
            if p.get("by"):
                groups.setdefault(str(r.get(p["by"])), set()).add(r.get(key))
    for r in rows:
        a, b = r.get(p["from"]), r.get(p["to"])
        if a is None:
            continue
        ia = mid(a, ids)
        if p.get("group"):
            groups.setdefault(str(r.get(p["group"])), set()).add(a)
        if b is None:
            continue
        ib = mid(b, ids)
        lab = r.get(p["label"]) if p.get("label") else None
        edges.append(f"  {ia} -->|{mlabel(lab)}| {ib}" if lab not in (None, "") else f"  {ia} --> {ib}")
    grouped = set()
    for gi, (g, members) in enumerate(groups.items()):
        out.append(f"  subgraph g{gi}[{mlabel(g)}]")
        for m in members:
            out.append(f"    {ids[m]}[{mlabel(m)}]")
            grouped.add(m)
        out.append("  end")
    for name, i in ids.items():
        if name not in grouped:
            out.append(f"  {i}[{mlabel(name)}]")
    tone = p.get("tone")
    if tone and attrs:
        col, tmap = next(iter(tone.items())) if isinstance(tone, dict) and tone else (None, None)
        used = set()
        for name, r in attrs.items():
            v = r.get(col) if col else None
            t = (tmap or {}).get(v) if isinstance(tmap, dict) else None
            t = t or AUTO_TONE.get(str(v).lower())
            if t in TONE_FILL:
                out.append(f"  class {ids[name]} t_{t}")
                used.add(t)
        for t in sorted(used):
            fill, stroke = TONE_FILL[t]
            out.append(f"  classDef t_{t} fill:{fill},stroke:{stroke},color:#1b2029,stroke-width:1.5px")
    return "\n".join(out + edges)


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)")


def parse_patch(text):
    files, cur, hunk = [], None, None
    o = n = 0
    for ln in text.splitlines():
        if ln.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)", ln)
            cur = {"old": m.group(1) if m else "", "new": m.group(2) if m else "", "hunks": [], "add": 0, "del": 0}
            files.append(cur)
            hunk = None
            continue
        if ln.startswith("--- "):
            if cur is None or cur["hunks"]:
                cur = {"old": "", "new": "", "hunks": [], "add": 0, "del": 0}
                files.append(cur)
            cur["old"] = re.sub(r"^a/", "", ln[4:].split("\t")[0].strip())
            continue
        if ln.startswith("+++ ") and cur is not None and not cur["hunks"]:
            cur["new"] = re.sub(r"^b/", "", ln[4:].split("\t")[0].strip())
            continue
        m = HUNK.match(ln)
        if m:
            if cur is None:
                cur = {"old": "", "new": "", "hunks": [], "add": 0, "del": 0}
                files.append(cur)
            o, n = int(m.group(1)), int(m.group(3))
            hunk = {"head": m.group(5), "lines": []}
            cur["hunks"].append(hunk)
            continue
        if hunk is None:
            continue
        if ln.startswith("+"):
            hunk["lines"].append(["a", None, n, ln[1:]])
            n += 1
            cur["add"] += 1
        elif ln.startswith("-"):
            hunk["lines"].append(["d", o, None, ln[1:]])
            o += 1
            cur["del"] += 1
        elif ln.startswith("\\"):
            continue
        else:
            hunk["lines"].append(["c", o, n, ln[1:] if ln.startswith(" ") else ln])
            o += 1
            n += 1
    for f in files:
        if f["new"] == "/dev/null":
            f["new"] = None
        if f["old"] == "/dev/null":
            f["old"] = None
    return [f for f in files if f["hunks"]]


# ---- page -------------------------------------------------------------------------------

def normalise_page(ctx, spec):
    if isinstance(spec, list):
        ctx.fix("page", "the spec was a list; used it as the layout", "title: ...\\nlayout: [...]")
        spec = {"layout": spec}
    if not isinstance(spec, dict):
        raise SpecError("the spec must be a YAML map with title and layout")
    page = {}
    stray = []
    for k, v in spec.items():
        if k in R.PAGE_KEYS:
            page[k] = v
            continue
        m = {"name": "title", "heading": "title", "description": "subtitle", "summary": "subtitle",
             "datasets": "data", "sources": "data", "body": "layout", "content": "layout", "blocks": "layout",
             "items": "layout", "nodes": "layout", "children": "layout", "components": "layout",
             "sections": "layout", "badges": "meta", "tags": "meta"}.get(k) or close(str(k), R.PAGE_KEYS, 0.75)
        if m and m not in spec and m not in page:
            ctx.fix("page", f'"{k}" → "{m}"', f"{m}: ...")
            page[m] = v
        elif lookup_comp(k)[0]:
            stray.append({k: v})
        else:
            ctx.fix("page", f'dropped unknown key "{k}"', f"page keys are {', '.join(R.PAGE_KEYS)}")
    if stray:
        ctx.fix("page", f"{len(stray)} component(s) at the top level moved into layout", "put each node under layout:")
        page.setdefault("layout", [])
        if not isinstance(page["layout"], list):
            page["layout"] = [page["layout"]]
        page["layout"] = page["layout"] + stray
    if "title" not in page:
        page["title"] = "Report"
        ctx.fix("page", "no title; used \"Report\"", "title: <2-5 words>")
    if not page.get("layout"):
        raise SpecError("the spec has no layout. Add layout: [ ...nodes ]. Run `softui.py catalog`")
    return page


def compile_spec(spec, base):
    ctx = Ctx(base)
    page = normalise_page(ctx, spec)
    data = page.get("data") or {}
    if not isinstance(data, dict):
        ctx.err("data", "data must be a map of name: rows|csv|file")
        data = {}
    for name, val in data.items():
        rows = to_rows(val, ctx, f"data.{name}")
        if rows is not None:
            register(ctx, str(name), rows)
            register_parts(ctx, str(name), val)
    layout = norm_nodes(ctx, page["layout"], "layout")
    width = page.get("width", "normal")
    if width not in R.PAGE_KEYS["width"]["enum"]:
        width = "normal"
    meta = page.get("meta")
    if isinstance(meta, dict):
        meta = [f"{k}: {v}" for k, v in meta.items()]
    elif isinstance(meta, str):
        meta = [meta]
    plan = {"title": str(page["title"]), "subtitle": page.get("subtitle"), "meta": meta or [], "width": width,
            "accent": page.get("accent"), "layout": layout,
            "data": {k: {"rows": v["rows"], "cols": v["cols"], "types": v["types"]} for k, v in ctx.data.items()}}
    return ctx, plan


def scan_libs(nodes, libs):
    for n in nodes:
        if n["c"] in ("chart",):
            libs.add("chart")
        if n["c"] in ("diagram", "graph"):
            libs.add("mermaid")
        scan_libs(n["kids"], libs)
        for k in ("side", "main"):
            if k in n["p"]:
                scan_libs(n["p"][k], libs)


def emit(plan, libs, artifact):
    css = (ASSETS / "style.css").read_text()
    js = (ASSETS / "runtime.js").read_text()
    data = json.dumps(plan, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = html.escape(plan["title"])
    scripts = "".join(f'<script src="{LIBS[k]}"></script>\n' for k in ("chart", "hljs", "mermaid") if k in libs)
    body = (f'<title>{title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            f'<link rel="stylesheet" href="{FONTS}">\n<style>\n{css}\n</style>\n'
            f'<div id="su-root" class="su-page su-w-{plan["width"]}"></div>\n'
            f'<script type="application/json" id="su-plan">{data}</script>\n{scripts}<script>\n{js}\n</script>\n')
    if artifact:
        return body
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + body.replace(f'<div id="su-root"', '</head>\n<body>\n<div id="su-root"', 1) + "</body>\n</html>\n")


def read_spec(arg):
    if arg == "-":
        return sys.stdin.read(), Path.cwd()
    p = Path(arg)
    if not p.exists():
        raise SpecError(f'spec file "{arg}" not found')
    return p.read_text(encoding="utf-8"), p.resolve().parent


def render(args):
    text, base = read_spec(args.spec)
    spec = load_yaml(text)
    ctx, plan = compile_spec(spec, base)
    for f in ctx.fixes:
        print(f)
    if ctx.errors:
        for e in ctx.errors:
            print(e)
        print(f"FAILED: {len(ctx.errors)} error(s); nothing written. Fix them and run again. "
              f"`softui.py explain NAME` shows the props of a component.")
        return 1
    libs = set(ctx.libs)
    scan_libs(plan["layout"], libs)
    out = Path(args.out) if args.out else (
        Path(args.spec).with_suffix(".html") if args.spec != "-" else Path("soft-ui.html"))
    page = emit(plan, libs, args.artifact)
    kb = len(page.encode()) // 1024
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} · {ctx.count} nodes · {len(plan['data'])} datasets · {kb} KB"
          + (f" · {len(ctx.fixes)} fixed" if ctx.fixes else ""))
    if kb > MAX_INLINE_KB:
        print(f"warning: the page is {kb} KB. Use `where`, fewer columns, or a smaller file.")
    if not args.fast or args.shot:
        return browser_check(out, args.shot, args.artifact)
    return 0


def browser_check(path, shot=None, artifact=False):
    target = path
    if artifact:
        tmp = Path(tempfile.mkdtemp()) / "page.html"
        body = path.read_text()
        tmp.write_text('<!doctype html><html><head><meta charset="utf-8">'
                       '<meta name="viewport" content="width=device-width, initial-scale=1"></head><body>'
                       + body + "</body></html>")
        target = tmp
    cmd = ["node", str(HERE / "verify.js"), str(Path(target).resolve())] + ([str(Path(shot).resolve())] if shot else [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"check skipped: {e}")
        return 0
    out = (r.stdout or "").strip()
    if r.returncode not in (0, 1) and not out:
        print("check skipped: " + (r.stderr.strip().splitlines() or ["node or playwright is missing"])[-1])
        return 0
    print(out)
    return r.returncode


# ---- catalog / explain ------------------------------------------------------------------

GROUPS = [("layout", "LAYOUT (hold other nodes)"), ("summary", "SUMMARY"), ("data", "DATA (data: name|rows|csv|file)"),
          ("code", "CODE"), ("diagram", "DIAGRAM")]


DATA_HELP = """data — named datasets under the page key `data:`. Each node names one with `data: NAME`.
  rows:        d: [{a: 1, b: x}, {a: 2, b: y}]
  CSV text:    d: |            (first line = header; quote cells that hold commas)
                 a,b
                 1,x
  TOON text:   d: |
                 [2]{a,b}:
                 1,x
                 2,y
  file:        d: results.json | .jsonl | .csv | .tsv | .yaml | .diff/.patch (one row per file)
  inner array: d: design.json#components      or  d: {file: design.json, key: components}
  all arrays:  d: design.json   → also registers d.components, d.calls, ... for each array inside
  computed:    d: {file: eps.json, add: {delta: "after - before", pct: "round((after/before-1)*100, 1)"}}
  single object (e.g. run.json): show it with kv: {data: d, keys: [app, commit]}
  per node:    where: {sev: [high, critical]}  or  where: {ms: ">500"} keeps matching rows
Paths resolve from the folder of the spec."""

EXAMPLE = """
title: Test run 4120
data: {runs: results.json}          # rows; columns suite, test, status, ms
layout:
- stats: [{label: Passed, value: 412, tone: good}, {label: Failed, value: 3, tone: bad}]
- row:
  - chart: {data: runs, x: suite, y: ms, agg: sum}
    title: Time by suite
  - table: {data: runs, cols: [test, status, ms], group: status, fmt: {ms: ms}}
    w: 2
"""


def sig(name):
    c = R.C[name]
    parts = []
    for k, s in c["props"].items():
        parts.append(k + ("*" if s["req"] else ""))
    return f"{name}: {' '.join(parts)}"


def catalog():
    print("soft-ui — write a YAML spec, run `softui.py render spec.yaml` → one checked HTML page.")
    print("page: title* subtitle meta data{name: rows|csv-text|toon-text|file.json|file.csv} layout*[nodes] width")
    print("an array inside a JSON file: data: {comps: design.json#components}; also data: {d: design.json} gives d.components, d.calls, ...")
    print("a .diff/.patch file as data gives one row per file: file, status, added, removed")
    print('computed columns: data: {d: {file: x.json, add: {delta: "after - before", pct: "round((after/before-1)*100, 1)"}}}')
    print("node: - NAME: {props}  or  - NAME: shorthand  (a bare string = markdown text)")
    print("every node also takes: title note span w h where   (* = required)")
    for g, label in GROUPS:
        print(label)
        for name, c in R.C.items():
            if c["group"] == g:
                short = f" (short: {c['short']})" if c["short"] else ""
                print(f"  {sig(name)}{short} — {c['doc']}")
    print("fmt values: " + " ".join(R.FMTS) + " · tone values: " + " ".join(R.TONES))
    print("Values such as high/medium/low and pass/fail/done get tone colours without a tone map.")
    print("example:")
    for ln in EXAMPLE.strip("\n").split("\n"):
        print("  " + ln)
    print("`softui.py explain table chart` for prop details and examples; `explain data` for every data form.")


def explain(names):
    rc = 0
    for name in names:
        comp, how = lookup_comp(name)
        if name == "data":
            print(DATA_HELP)
            continue
        if name == "page":
            print("page")
            for k, s in R.PAGE_KEYS.items():
                print(f"  {k}{'*' if s['req'] else ''}: {s['t']}" + (f" — {s['doc']}" if s["doc"] else ""))
            continue
        if not comp:
            print(f"unknown component {name!r}. Run `softui.py catalog`.")
            rc = 1
            continue
        c = R.C[comp]
        alias = f" (you wrote {name!r})" if how else ""
        print(f"{comp}{alias} — {c['doc']}")
        if c["short"]:
            print(f"  shorthand: `{comp}: <{c['short']}>`")
        for k, s in c["props"].items():
            t = s["t"] if s["t"] != "enum" else "|".join(s["enum"])
            dflt = f" = {s['default']}" if s["default"] not in (None, False) else ""
            print(f"  {k}{'*' if s['req'] else ''}: {t}{dflt}" + (f" — {s['doc']}" if s["doc"] else ""))
        if c["aliases"]:
            print(f"  also accepted as: {', '.join(c['aliases'][:6])}")
        print("  example:")
        for ln in c["example"].split("\n"):
            print("    " + ln)
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(prog="softui.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("catalog")
    e = sub.add_parser("explain")
    e.add_argument("names", nargs="+")
    for name in ("render",):
        r = sub.add_parser(name)
        r.add_argument("spec")
        r.add_argument("-o", "--out")
        r.add_argument("--artifact", action="store_true")
        r.add_argument("--fast", action="store_true", help="skip the browser check")
        r.add_argument("--shot", help="also save a screenshot (PNG) of the page")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "catalog":
            catalog()
            return 0
        if a.cmd == "explain":
            return explain(a.names)
        if a.cmd == "render":
            return render(a)
        ap.print_help()
        return 2
    except SpecError as ex:
        print(f"error: {ex}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
