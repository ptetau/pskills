#!/usr/bin/env python3
"""Render a /quiz-visual spec (JSON) as one self-contained HTML page.

Usage:
  python3 render_quiz.py SPEC.json [-o OUT.html] [--artifact]

  --artifact  write the page in the form that the Artifact tool publishes: no <html>, <head>,
              or <body> tags, and no charset or viewport meta (the tool adds them).

The spec format is in references/spec.md. The preview kinds are in references/preview-kinds.md.
The script checks the spec first. If the spec has an error, it prints each error and writes
nothing. Standard library only.
"""

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "references" / "page-template.html"

KINDS = {
    "sample": "SAMPLE", "wireframe": "WIREFRAME", "swatch": "PALETTE", "flow": "FLOW",
    "code": "CODE", "svg": "GRAPHIC", "html": "MOCKUP", "demo": "DEMO · CLICK IT", "none": "",
}
BLOCKS = {"header", "nav", "hero", "image", "text", "button", "list", "input", "footer", "chart",
          "card", "tabs", "avatar", "map"}
FRAMES = {"phone", "browser", "email", "none"}
SAMPLE_FRAMES = {"email", "message", "card", "page", "plain"}
WHO = {"user", "system", "staff"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
MAX_SNIPPET = 20000
SANDBOX_CSP = ("default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
               "img-src data:; font-src data:")


def words(text):
    return len(re.findall(r"\S+", text or ""))


def is_str(v, nonempty=True):
    return isinstance(v, str) and (v.strip() != "" or not nonempty)


# ── Validation ───────────────────────────────────────────────────────────────

def validate(spec):
    """Return a list of error strings. An empty list means the spec is valid."""
    errs = []
    if not isinstance(spec, dict):
        return ["The spec must be a JSON object."]
    if not is_str(spec.get("title")) or not 2 <= words(spec["title"]) <= 5:
        errs.append("title: write a name of 2 to 5 words.")
    if not is_str(spec.get("intro")) or words(spec["intro"]) > 25:
        errs.append("intro: write one sentence of 25 words or fewer.")
    qs = spec.get("questions")
    if not isinstance(qs, list) or not 1 <= len(qs) <= 10:
        errs.append("questions: give 1 to 10 questions.")
        return errs
    seen = set()
    for i, q in enumerate(qs, 1):
        where = "question %d" % i
        if not isinstance(q, dict):
            errs.append("%s: must be an object." % where)
            continue
        qid = q.get("id")
        if not is_str(qid) or not ID_RE.match(qid):
            errs.append("%s: id must be lower-case words joined by hyphens." % where)
        elif qid in seen:
            errs.append("%s: the id '%s' is used two times." % (where, qid))
        else:
            seen.add(qid)
        where = "question '%s'" % (qid if is_str(qid) else i)
        if not is_str(q.get("label")) or len(q["label"]) > 12:
            errs.append("%s: label must have 12 characters or fewer." % where)
        if not is_str(q.get("question")) or not q["question"].strip().endswith("?") or words(q["question"]) > 25:
            errs.append("%s: question must be one sentence of 25 words or fewer that ends with '?'." % where)
        opts = q.get("options")
        if not isinstance(opts, list) or not 2 <= len(opts) <= 5:
            errs.append("%s: give 2 to 5 options." % where)
            continue
        oseen, recs = set(), 0
        for j, o in enumerate(opts, 1):
            ow = "%s, option %d" % (where, j)
            if not isinstance(o, dict):
                errs.append("%s: must be an object." % ow)
                continue
            oid = o.get("id")
            if not is_str(oid) or not ID_RE.match(oid):
                errs.append("%s: id must be lower-case words joined by hyphens." % ow)
            elif oid in oseen:
                errs.append("%s: the id '%s' is used two times." % (ow, oid))
            else:
                oseen.add(oid)
            if not is_str(o.get("label")) or words(o["label"]) > 5:
                errs.append("%s: label must have 1 to 5 words." % ow)
            if not is_str(o.get("text")) or words(o["text"]) > 25:
                errs.append("%s: text must be one sentence of 25 words or fewer." % ow)
            if o.get("recommended"):
                recs += 1
            errs.extend(validate_preview(o.get("preview"), ow))
        if recs > 1:
            errs.append("%s: mark at most one option as recommended." % where)
        if recs == 1 and not is_str(q.get("evidence")):
            errs.append("%s: a recommended option needs 'evidence', the words of the user that point to it." % where)
        if recs == 0 and q.get("evidence"):
            errs.append("%s: 'evidence' is set, but no option is recommended." % where)
    return errs


def validate_preview(p, where):
    if not isinstance(p, dict) or p.get("kind") not in KINDS:
        return ["%s: preview.kind must be one of %s." % (where, ", ".join(sorted(KINDS)))]
    k, errs = p["kind"], []
    w = "%s, %s preview" % (where, k)
    if k == "sample":
        if p.get("frame", "card") not in SAMPLE_FRAMES:
            errs.append("%s: frame must be one of %s." % (w, ", ".join(sorted(SAMPLE_FRAMES))))
        body = p.get("body")
        if not isinstance(body, list) or not body or not all(is_str(b) for b in body) or len(body) > 4:
            errs.append("%s: body must list 1 to 4 paragraphs." % w)
    elif k == "wireframe":
        if p.get("frame", "browser") not in FRAMES:
            errs.append("%s: frame must be one of %s." % (w, ", ".join(sorted(FRAMES))))
        rows = p.get("rows")
        if not isinstance(rows, list) or not rows or len(rows) > 10:
            errs.append("%s: rows must list 1 to 10 rows." % w)
        else:
            for r in rows:
                errs.extend(check_row(r, w))
    elif k == "swatch":
        cs = p.get("colors")
        if not isinstance(cs, list) or not 2 <= len(cs) <= 6:
            errs.append("%s: colors must list 2 to 6 colours." % w)
        else:
            for c in cs:
                if not isinstance(c, dict) or not is_str(c.get("name")) or not COLOR_RE.match(str(c.get("value", ""))):
                    errs.append("%s: each colour needs a name and a value such as #1a2b3c." % w)
                elif c.get("role", "accent") not in ("bg", "ink", "accent", "extra"):
                    errs.append("%s: role must be bg, ink, accent, or extra." % w)
    elif k == "flow":
        st = p.get("steps")
        if not isinstance(st, list) or not 2 <= len(st) <= 7 or not all(isinstance(s, dict) and is_str(s.get("label")) for s in st):
            errs.append("%s: steps must list 2 to 7 steps, each with a label." % w)
        elif any(s.get("who", "user") not in WHO for s in st):
            errs.append("%s: who must be user, system, or staff." % w)
    elif k == "code":
        code = p.get("code")
        if not is_str(code) or code.count("\n") > 14:
            errs.append("%s: code must have 15 lines or fewer." % w)
    elif k in ("svg", "html", "demo"):
        if not is_str(p.get("alt")):
            errs.append("%s: alt must say in one sentence what the preview shows." % w)
        field = "svg" if k == "svg" else "html"
        body = p.get(field)
        if not is_str(body):
            errs.append("%s: %s is required." % (w, field))
        elif len(body) > MAX_SNIPPET:
            errs.append("%s: %s is longer than %d characters." % (w, field, MAX_SNIPPET))
        elif k == "svg" and not body.lstrip().startswith("<svg"):
            errs.append("%s: svg must start with '<svg'." % w)
        for f in ("css", "js"):
            v = p.get(f)
            if v is not None and (not isinstance(v, str) or len(v) > MAX_SNIPPET):
                errs.append("%s: %s must be text of %d characters or fewer." % (w, f, MAX_SNIPPET))
        if k != "demo" and p.get("js"):
            errs.append("%s: js is only for the demo kind." % w)
        blob = " ".join(str(p.get(f) or "") for f in (field, "css", "js"))
        blob = re.sub(r'xmlns(?::\w+)?="[^"]*"', "", blob)      # a namespace is not a request
        if re.search(r"(?i)(?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}", blob):
            errs.append("%s: no web address. The preview cannot load anything from the network." % w)
        h = p.get("height", 220)
        if k != "svg" and (not isinstance(h, int) or not 120 <= h <= 420):
            errs.append("%s: height must be a whole number from 120 to 420." % w)
    return errs


def check_row(r, w):
    if isinstance(r, str):
        return [] if r in BLOCKS else ["%s: unknown block '%s'." % (w, r)]
    if not isinstance(r, dict):
        return ["%s: a row must be a block name or an object." % w]
    if "cols" in r:
        cols = r["cols"]
        if not isinstance(cols, list) or not 2 <= len(cols) <= 4:
            return ["%s: cols must list 2 to 4 blocks." % w]
        out = []
        for c in cols:
            out.extend(check_row(c, w))
        return out
    if "grid" in r:
        n = r["grid"]
        if not isinstance(n, int) or not 2 <= n <= 4 or r.get("item", "card") not in BLOCKS:
            return ["%s: grid must be 2 to 4 with a known item." % w]
        return []
    if r.get("type") in BLOCKS:
        return []
    return ["%s: a row object needs 'type', 'cols', or 'grid'." % w]


# ── Previews ─────────────────────────────────────────────────────────────────

def esc(s):
    return html.escape(str(s), quote=True)


def wire_block(b):
    if isinstance(b, str):
        b = {"type": b}
    if "cols" in b:
        ratio = b.get("ratio") or [1] * len(b["cols"])
        tpl = " ".join("%sfr" % esc(x) for x in ratio)
        return '<div class="r" style="grid-template-columns:%s">%s</div>' % (tpl, "".join(wire_block(c) for c in b["cols"]))
    if "grid" in b:
        n, item = b["grid"], b.get("item", "card")
        count = b.get("count", n)
        cells = "".join(wire_block({"type": item, "label": b.get("label")}) for _ in range(count))
        return '<div class="r" style="grid-template-columns:repeat(%d,1fr)">%s</div>' % (n, cells)
    label = esc(b.get("label", "")) if b.get("label") else ""
    return '<div class="wb %s">%s</div>' % (esc(b["type"]), label)


def preview_label(p):
    k = p["kind"]
    if k == "wireframe":
        names = []
        for r in p["rows"]:
            if isinstance(r, str):
                names.append(r)
            elif "cols" in r:
                names.append("%d columns" % len(r["cols"]))
            elif "grid" in r:
                names.append("%d-column grid" % r["grid"])
            else:
                names.append(r["type"])
        return "Wireframe: " + ", ".join(names)
    if k == "swatch":
        return "Palette: " + ", ".join("%s %s" % (c["name"], c["value"]) for c in p["colors"])
    if k == "flow":
        return "Flow: " + " then ".join(s["label"] for s in p["steps"])
    return p.get("alt") or p.get("caption") or k


def sandbox_doc(p, scripts):
    css = ("html,body{margin:0;height:100%}body{font:14px/1.4 system-ui,sans-serif;color:#1b2030;"
           "background:#f7f7f4;display:flex;align-items:center;justify-content:center;padding:14px;box-sizing:border-box}"
           "button{font:inherit}")
    parts = ['<!doctype html><meta charset="utf-8">',
             '<meta http-equiv="Content-Security-Policy" content="%s">' % SANDBOX_CSP,
             "<style>%s%s</style>" % (css, p.get("css", "")), p["html"]]
    if scripts and p.get("js"):
        parts.append("<script>%s</script>" % p["js"].replace("</script", "<\\/script"))
    return "".join(parts)


def render_preview(p):
    """Return (inner HTML, is_framed)."""
    k = p["kind"]
    cap = '<div class="cap">%s</div>' % esc(p["caption"]) if p.get("caption") else ""
    if k == "sample":
        fr = p.get("frame", "card")
        bar = ""
        if fr == "email":
            bar = '<div class="bar">%s<b>%s</b></div>' % (esc(p.get("from", "")), esc(p.get("title", ""))) if (p.get("from") or p.get("title")) else ""
        head = '<h4>%s</h4>' % esc(p["title"]) if p.get("title") and fr in ("card", "page") else ""
        paras = "".join("<p>%s</p>" % esc(t) for t in p["body"])
        go = '<span class="go">%s</span>' % esc(p["action"]) if p.get("action") else ""
        return ('<div class="pv pv-sample f-%s">%s<div class="in">%s%s%s</div></div>%s' % (fr, bar, head, paras, go, cap)), False
    if k == "wireframe":
        fr = p.get("frame", "browser")
        rows = "".join(wire_block(r) for r in p["rows"])
        return ('<div class="pv"><div class="wf f-%s" role="img" aria-label="%s">%s</div></div>%s'
                % (fr, esc(preview_label(p)), rows, cap)), False
    if k == "swatch":
        cs = p["colors"]
        roles = {}
        for c in cs:
            roles.setdefault(c.get("role", "accent"), c["value"])
        bg = roles.get("bg", cs[0]["value"])
        ink = roles.get("ink", cs[1]["value"] if len(cs) > 1 else "#111")
        ac = roles.get("accent", cs[-1]["value"])
        chips = "".join('<div class="chip" style="background:%s;color:%s">%s</div>'
                        % (esc(c["value"]), "#fff" if lum(c["value"]) < 0.5 else "#111", esc(c["name"])) for c in cs)
        sample = ('<div class="demo" style="background:%s;color:%s"><b>%s</b><span class="go" style="background:%s;color:%s">%s</span></div>'
                  % (esc(bg), esc(ink), esc(p.get("sample", "Sample heading")), esc(ac),
                     "#fff" if lum(ac) < 0.5 else "#111", esc(p.get("action", "Button"))))
        return ('<div class="pv pv-swatch" role="img" aria-label="%s"><div class="chips">%s</div>%s</div>%s'
                % (esc(preview_label(p)), chips, sample, cap)), False
    if k == "flow":
        orient = p.get("orientation") or ("column" if len(p["steps"]) > 3 else "row")
        col = " col" if orient == "column" else ""
        out = []
        for i, s in enumerate(p["steps"]):
            if i:
                out.append('<span class="arr" aria-hidden="true">→</span>')
            note = "<small>%s</small>" % esc(s["note"]) if s.get("note") else ""
            out.append('<div class="step%s" data-who="%s">%s%s</div>' % (" em" if s.get("emphasis") else "", esc(s.get("who", "user")), esc(s["label"]), note))
        return ('<div class="pv pv-flow%s" role="img" aria-label="%s">%s</div>%s' % (col, esc(preview_label(p)), "".join(out), cap)), False
    if k == "code":
        return '<div class="pv"><pre class="pv-code"><code>%s</code></pre></div>%s' % (esc(p["code"]), cap), False
    if k == "svg":
        data = base64.b64encode(p["svg"].encode("utf-8")).decode("ascii")
        return '<img class="pv-img" src="data:image/svg+xml;base64,%s" alt="%s">%s' % (data, esc(p["alt"]), cap), False
    if k in ("html", "demo"):
        doc = sandbox_doc(p, k == "demo")
        sb = "allow-scripts" if k == "demo" else ""
        return ('<iframe class="pv-frame" sandbox="%s" srcdoc="%s" title="%s" style="height:%dpx"></iframe>'
                % (sb, esc(doc), esc(p["alt"]), p.get("height", 220))), True
    return '<div class="pv-none">Words only</div>', False


def lum(hexv):
    h = hexv.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ── Page ─────────────────────────────────────────────────────────────────────

TICK = ('<span class="tick" aria-hidden="true"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8.5l3.2 3.2L13 4.8"/></svg></span>')


def render_option(q, o):
    kind = o["preview"]["kind"]
    inner, framed = render_preview(o["preview"])
    tag = KINDS[kind]
    kind_chip = '<span class="kind">%s</span>' % esc(tag) if tag else ""
    typ = "checkbox" if q.get("multi") else "radio"
    iid = "%s--%s" % (q["id"], o["id"])
    badge = '<span class="badge">Suggested</span>' if o.get("recommended") else ""
    ev = '<span class="ev">%s</span>' % esc(q["evidence"].strip().rstrip(".") + ".") if o.get("recommended") else ""
    return (
        '<div class="opt" data-opt="%s">'
        '<div class="mat%s">%s%s%s</div>'
        '<label class="body" for="%s"><input type="%s" id="%s" name="%s" value="%s" data-q="%s">'
        '<span class="name-row"><span class="name">%s</span>%s</span><span class="text">%s</span>%s</label></div>'
        % (esc(o["id"]), " has-frame" if framed else "", kind_chip, TICK, inner, esc(iid), typ, esc(iid),
           esc(q["id"]), esc(o["id"]), esc(q["id"]), esc(o["label"]), badge, esc(o["text"]), ev)
    )


def render_question(i, total, q):
    hint = '<p class="hint">Pick as many as you like.</p>' if q.get("multi") else ""
    opts = "".join(render_option(q, o) for o in q["options"])
    return (
        '<section class="q" id="q-%(id)s" data-deferred="0" aria-labelledby="h-%(id)s">\n'
        '<div class="q-top"><span class="q-no">%(no)02d / %(total)02d</span><span class="q-label">%(label)s</span>'
        '<span class="q-state" data-s="open">Not answered</span></div>\n'
        '<h2 id="h-%(id)s">%(question)s</h2>%(hint)s\n'
        '<fieldset class="opts" data-n="%(n)d" style="margin-top:24px"><legend class="sr">%(question)s</legend>%(opts)s</fieldset>\n'
        '<div class="tools"><div class="note"><label for="note-%(id)s">Note (optional)</label>'
        '<textarea id="note-%(id)s" data-q="%(id)s" rows="1" placeholder="Anything the options miss"></textarea></div>'
        '<button class="btn small defer" type="button" data-defer="%(id)s">You decide</button></div>\n'
        '</section>'
        % {"id": esc(q["id"]), "no": i, "total": total, "label": esc(q["label"]), "question": esc(q["question"]),
           "hint": hint, "n": len(q["options"]), "opts": opts}
    )


def public_spec(spec):
    return {
        "title": spec["title"], "task": spec.get("task"),
        "questions": [{
            "id": q["id"], "label": q["label"], "question": q["question"], "multi": bool(q.get("multi")),
            "options": [{"id": o["id"], "label": o["label"], "recommended": bool(o.get("recommended"))} for o in q["options"]],
        } for q in spec["questions"]],
    }


def render(spec, artifact=False):
    errs = validate(spec)
    if errs:
        raise ValueError("\n".join(errs))
    qs = spec["questions"]
    rail = "".join('<li id="r-%s"><a href="#q-%s"><span class="n">%02d</span><span>%s</span><span class="st"></span></a></li>'
                   % (esc(q["id"]), esc(q["id"]), i, esc(q["label"])) for i, q in enumerate(qs, 1))
    questions = "\n".join(render_question(i, len(qs), q) for i, q in enumerate(qs, 1))
    data = json.dumps(public_spec(spec), ensure_ascii=False).replace("</", "<\\/")
    eyebrow = esc(spec["task"]) if spec.get("task") else "%d questions" % len(qs)
    page = TEMPLATE.read_text(encoding="utf-8")
    for key, val in (("{{TITLE}}", esc(spec["title"])), ("{{INTRO}}", esc(spec["intro"])), ("{{EYEBROW}}", eyebrow),
                     ("{{TOTAL}}", str(len(qs))), ("{{RAIL}}", rail), ("{{QUESTIONS}}", questions)):
        page = page.replace(key, val)
    page = page.replace("{{SPEC_JSON}}", data)
    if artifact:
        head = re.search(r"<head>(.*?)</head>", page, re.S).group(1)
        head = re.sub(r'<meta charset[^>]*>\s*|<meta name="viewport"[^>]*>\s*', "", head)
        body = re.search(r"<body>(.*?)</body>", page, re.S).group(1)
        page = head.strip() + "\n" + body.strip() + "\n"
    return page


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("spec")
    p.add_argument("-o", "--out")
    p.add_argument("--artifact", action="store_true", help="write the Artifact form of the page")
    a = p.parse_args(argv)
    try:
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("Cannot read the spec: %s" % e, file=sys.stderr)
        return 2
    try:
        page = render(spec, a.artifact)
    except ValueError as e:
        print("The spec has errors:\n" + str(e), file=sys.stderr)
        return 1
    out = Path(a.out) if a.out else Path(a.spec).with_suffix("").with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    print("wrote %s (%d bytes)" % (out, len(page.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
