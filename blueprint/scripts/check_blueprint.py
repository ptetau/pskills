#!/usr/bin/env python3
"""Check that a blueprint (Agent System Design Document) is complete, traceable, and
congruent with its design.

Structural and traceability checks only; it cannot judge whether the design is good.

Errors (exit code 1):
  - the six sections are missing or out of order
  - section 1 lacks an in-scope or out-of-scope list, or uses "(assumed)" inline
    without a "Decisions added by this spec" list
  - more than 3 [NEEDS CLARIFICATION] markers, or any at all without --draft
  - section 2 does not have 4-7 invariants, or an invariant lacks an error code or an
    enforcement point ("Enforced by")
  - section 3 has no typed code block, or no error catalog table; the catalog and the
    quoted codes in the contracts disagree
  - a code used anywhere is missing from the error catalog
  - a Status/State type from section 3 has no state machine in section 4
  - a component in section 5 lacks a purpose, a signature block, or failure and retry
    semantics
  - section 6 has fewer than 3 scenarios, a scenario lacks Given/When/Then, an
    invariant's code is never exercised, or there is no "Done when" / "Verify" line
    with a command
  - cryptic design IDs (V1, F2, UC3) remain outside code blocks
  - with --design: a component in the design is missing from section 5, or section 5
    has a Manager, Engine, or Access component the design doesn't

Warnings: more than 5 scenarios, more than 5 steps in a scenario, a Background over 4
lines, money typed as a bare number, `any` in TypeScript, a component without
"May call", a design verb with no matching method, filler phrasing.

Usage:
  python check_blueprint.py notifications.blueprint.md
  python check_blueprint.py notifications.blueprint.md --design notifications.design.md
  python check_blueprint.py notifications.blueprint.md --compile   # also run tsc if installed
  python check_blueprint.py notifications.blueprint.md --draft     # open questions allowed
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SECTIONS = [
    (1, r"boundary|scope"),
    (2, r"invariant"),
    (3, r"contract|data"),
    (4, r"state"),
    (5, r"module|interface|signature"),
    (6, r"verification|test|bdd|gherkin"),
]
TYPED_LANGS = {"ts", "typescript", "go", "golang", "rust", "rs"}
CODE = r"[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+"
ERROR_CODE = re.compile(r"`(%s)`" % CODE)
BARE_CODE = re.compile(r"\b(%s)\b" % CODE)
QUOTED_CODE = re.compile(r"\"(%s)\"" % CODE)
CRYPTIC_ID = re.compile(r"\b(?:V|F|UC)\d{1,2}\b")
FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)
MONEY_AS_NUMBER = re.compile(
    r"\b\w*(amount|price|total|cost|balance|fee)\w*\??\s*[:]\s*(number|float|double|f32|f64|float32|float64)\b", re.I)
STATE_TYPE = re.compile(r"\b(?:type|enum)\s+(\w*(?:Status|State))\b")
COMPONENT = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Manager|Engine|Access))\b")
DESIGN_CALL = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Manager|Engine|Access))\.([A-Z][A-Za-z0-9]*)\b")
NOT_COMPONENTS = {"ResourceAccess"}
STEP = re.compile(r"^\s*(Given|When|Then|And|But|\*)\b", re.M)
FILLER = re.compile(r"^(in this document|this document (will|describes)|let's|here is|here's|i will|we will now)\b",
                    re.I | re.M)


def strip_code(text):
    return FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def split_sections(text):
    """Return ({number: (title, body)}, [numbers in order]) for '## N. Title' headings."""
    lines = text.split("\n")
    heads = [(i, int(m.group(1)), m.group(2).strip())
             for i, line in enumerate(lines) for m in [re.match(r"^##\s+(\d+)\.\s+(.*)$", line)] if m]
    found, order = {}, []
    for k, (i, num, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        found[num] = (title, "\n".join(lines[i + 1:end]))
        order.append(num)
    return found, order


def code_blocks(body, langs=None):
    return [(m.group(1).lower(), m.group(2)) for m in FENCE.finditer(body)
            if langs is None or m.group(1).lower() in langs]


def check_design(design_text, s5, components):
    """Congruence with the source design: same components, same verbs."""
    errors, warnings = [], []
    design_comps = set(COMPONENT.findall(design_text)) - NOT_COMPONENTS
    heads = {c.split("\n", 1)[0].strip().strip("`") for c in components}
    bp_comps = {h for h in heads if COMPONENT.fullmatch(h)} - NOT_COMPONENTS
    for c in sorted(design_comps - heads):
        errors.append("--design: `%s` is in the design but has no section 5 subsection" % c)
    for c in sorted(bp_comps - design_comps):
        errors.append("--design: `%s` is in section 5 but not in the design (a blueprint never adds components)" % c)
    bodies = {c.split("\n", 1)[0].strip().strip("`"): c for c in components}
    verbs = set(DESIGN_CALL.findall(design_text))
    bricks = set()
    lines = strip_code(design_text).split("\n")
    api_col = brick_col = None
    for i, line in enumerate(lines):       # read tables by header: "API ..." and "Bricks" columns
        if not line.lstrip().startswith("|"):
            api_col = brick_col = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if i + 1 < len(lines) and re.match(r"^\s*\|[-| :]+\|\s*$", lines[i + 1]):
            api_col = next((k for k, c in enumerate(cells) if re.match(r"api\b", c, re.I)), None)
            brick_col = next((k for k, c in enumerate(cells) if re.match(r"bricks?\b", c, re.I)), None)
            continue
        comp = COMPONENT.fullmatch(cells[0].strip("`")) if cells else None
        if not comp:
            continue
        for col, into in ((api_col, verbs), (brick_col, bricks)):
            if col is not None and col < len(cells):
                for v in re.findall(r"`([A-Z][A-Za-z0-9]*)", cells[col]):
                    if not COMPONENT.fullmatch(v):
                        into.add((comp.group(1), v))
    for comp, brick in sorted(bricks):
        body = bodies.get(comp)
        if body is not None and not re.search(r"\b%s\b" % re.escape(brick), body, re.I):
            warnings.append("--design: brick `%s` of `%s` is not mentioned in its section 5 subsection "
                            "(list it under Internals)" % (brick, comp))
    for comp, verb in sorted(verbs):
        body = bodies.get(comp)
        if body is None:
            continue
        if not re.search(r"\b%s\s*\(" % re.escape(verb[0].lower() + verb[1:]), body) and \
           not re.search(r"\b%s\s*\(" % re.escape(verb), body):
            warnings.append("--design: `%s.%s` from the design has no matching method in section 5" % (comp, verb))
    return errors, warnings, len(design_comps)


def check(text, compile_ts=False, draft=False, design_text=None):
    errors, warnings = [], []
    sections, order = split_sections(text)

    # --- structure
    for num, pattern in SECTIONS:
        if num not in sections:
            errors.append("section %d is missing (expected a '## %d. ...' heading)" % (num, num))
        elif not re.search(pattern, sections[num][0], re.I):
            errors.append("section %d is titled '%s'; expected something matching /%s/"
                          % (num, sections[num][0], pattern))
    core = [n for n in order if 1 <= n <= 6]
    if core != sorted(core):
        errors.append("sections are out of order: %s" % order)
    if errors:
        return errors, warnings, {}
    s1, s2, s3, s4, s5, s6 = (sections[n][1] for n in range(1, 7))
    prose = strip_code(text)

    # --- 1. scope, decisions, open questions
    if not re.search(r"in[- ]scope", s1, re.I):
        errors.append("section 1: no in-scope list")
    if not re.search(r"out[- ]of[- ]scope|non-goals", s1, re.I):
        errors.append("section 1: no out-of-scope (non-goals) list")
    assumed = len(re.findall(r"\(assumed\)", prose, re.I))
    if assumed and not re.search(r"decisions added|assumptions", s1, re.I):
        errors.append("%d '(assumed)' tags but section 1 has no 'Decisions added by this spec' list" % assumed)
    open_questions = len(re.findall(r"\[NEEDS CLARIFICATION", prose))
    if open_questions > 3:
        errors.append("%d [NEEDS CLARIFICATION] markers; at most 3 (decide the rest and mark them assumed)"
                      % open_questions)
    elif open_questions and not draft:
        errors.append("%d open [NEEDS CLARIFICATION] question(s): not agent-ready (use --draft while they are "
                      "out)" % open_questions)
    elif open_questions:
        warnings.append("%d open [NEEDS CLARIFICATION] question(s): draft only" % open_questions)

    # --- 2. invariants
    items = [i for i in re.findall(r"^\s*\d+\.\s+(.*(?:\n(?!\s*\d+\.\s).*)*)", strip_code(s2), re.M) if i.strip()]
    if not 4 <= len(items) <= 7:
        errors.append("section 2: %d invariants; expected 4-7" % len(items))
    invariant_codes = set()
    for n, item in enumerate(items, 1):
        codes = ERROR_CODE.findall(item)
        if not codes:
            errors.append("section 2, invariant %d: no error code in backticks (e.g. `PERIOD_LOCKED`)" % n)
        if not re.search(r"enforced (by|in|at)", item, re.I):
            errors.append("section 2, invariant %d: no enforcement point ('Enforced by `Component.method`')" % n)
        invariant_codes.update(codes)

    # --- 3. contracts and error catalog
    typed = code_blocks(s3, TYPED_LANGS)
    if not typed:
        errors.append("section 3: no typed code block (```ts, ```go, or ```rust)")
    contract_code = "\n".join(b for _, b in typed)
    for m in MONEY_AS_NUMBER.finditer(contract_code):
        warnings.append("section 3: '%s' looks like money typed as a bare number; use a Money type in minor units"
                        % m.group(0).strip())
    if re.search(r":\s*any\b", contract_code):
        warnings.append("section 3: `any` in a contract; give it a real type")
    state_types = sorted(set(STATE_TYPE.findall(contract_code)))
    catalog = set()
    for line in strip_code(s3).split("\n"):
        if line.lstrip().startswith("|"):
            first = line.strip().strip("|").split("|")[0]
            catalog.update(ERROR_CODE.findall(first))
    if not catalog:
        errors.append("section 3: no error catalog (a table with one `CODE` per row: meaning, fault, "
                      "HTTP status, retryable)")
    typed_codes = set(QUOTED_CODE.findall(contract_code))
    if catalog and typed_codes:
        for c in sorted(typed_codes - catalog):
            errors.append("section 3: `%s` is in the contract types but not in the error catalog" % c)
        for c in sorted(catalog - typed_codes):
            errors.append("section 3: `%s` is in the error catalog but not in the contract types" % c)

    # --- 4. state machines
    if not (re.search(r"stateDiagram", s4) or re.search(r"──\[|──►|-->|->", s4)):
        errors.append("section 4: no state diagram (mermaid stateDiagram-v2 or ASCII arrows)")
    for t in state_types:
        base = re.sub(r"(Status|State)$", "", t)
        if t not in s4 and not re.search(r"\b%s\b" % re.escape(base), s4):
            errors.append("section 4: state type `%s` from section 3 has no state machine" % t)

    # --- 5. modules
    components = re.split(r"^####\s+", s5, flags=re.M)[1:]
    if not components:
        errors.append("section 5: no components (expected '#### ComponentName' subsections)")
    for comp in components:
        name = comp.split("\n", 1)[0].strip().strip("`")
        if not re.search(r"purpose", comp, re.I):
            errors.append("section 5, %s: no purpose" % name)
        if not code_blocks(comp, TYPED_LANGS):
            errors.append("section 5, %s: no typed signature block" % name)
        if not re.search(r"failure|retr", comp, re.I):
            errors.append("section 5, %s: no failure and retry semantics" % name)
        if not re.search(r"may call", comp, re.I):
            warnings.append("section 5, %s: no 'May call' line" % name)

    # --- 6. verification
    gherkin = "\n".join(b for _, b in code_blocks(s6, {"gherkin", "feature", "cucumber"}))
    if not gherkin:
        errors.append("section 6: no ```gherkin block")
    background = re.search(r"^\s*Background:.*?\n((?:(?!\s*(?:Scenario|Example|Rule)).*\n)*)", gherkin, re.M)
    if background and len(STEP.findall(background.group(1))) > 4:
        warnings.append("section 6: Background has more than 4 steps (Cucumber: move detail into higher-level steps)")
    scenarios = re.split(r"^\s*(?:Scenario Outline|Scenario Template|Scenario|Example):", gherkin, flags=re.M)[1:]
    if len(scenarios) < 3:
        errors.append("section 6: %d scenarios; expected at least 3" % len(scenarios))
    elif len(scenarios) > 5:
        warnings.append("section 6: %d scenarios; the format asks for 3-5 (use Scenario Outlines)" % len(scenarios))
    for n, sc in enumerate(scenarios, 1):
        title = sc.split("\n", 1)[0].strip()
        body = re.split(r"^\s*Examples:", sc, flags=re.M)[0]
        for kw in ("Given", "When", "Then"):
            if not re.search(r"^\s*%s\b" % kw, body, re.M):
                errors.append("section 6, scenario %d (%s): no %s step" % (n, title, kw))
        steps = len(STEP.findall(body))
        if steps > 5:
            warnings.append("section 6, scenario %d (%s): %d steps; Cucumber recommends 3-5" % (n, title, steps))
    exercised = set(BARE_CODE.findall(gherkin))
    for code in sorted(invariant_codes - exercised):
        errors.append("section 6: invariant error code `%s` is never exercised by a scenario" % code)
    if not re.search(r"(done when|verify)[^\n]*`[^`]+`", strip_code(s6), re.I):
        errors.append("section 6: no 'Done when' / 'Verify' line with the command that runs the suite")

    # --- every code used is catalogued
    if catalog:
        used = {"section 2": invariant_codes, "section 5": set(ERROR_CODE.findall(strip_code(s5))),
                "section 6": exercised}
        for where, codes in used.items():
            for c in sorted(codes - catalog):
                errors.append("%s: `%s` is not in the error catalog" % (where, c))

    # --- global
    for i, line in enumerate(prose.split("\n"), 1):
        for m in CRYPTIC_ID.finditer(line):
            errors.append("line %d: cryptic design ID '%s'; use the domain term" % (i, m.group(0)))
    if FILLER.search(prose):
        warnings.append("filler phrasing found; lead with substance")

    stats = {"invariants": len(items), "error_codes": sorted(catalog), "state_types": state_types,
             "components": len(components), "scenarios": len(scenarios), "assumed": assumed,
             "open_questions": open_questions}

    if design_text is not None:
        e, w, n = check_design(design_text, s5, components)
        errors += e
        warnings += w
        stats["design_components"] = n

    if compile_ts:
        ts = [b for _, b in code_blocks(text, {"ts", "typescript"})]
        tsc = shutil.which("tsc")
        if not ts:
            warnings.append("--compile: no TypeScript blocks to compile")
        elif not tsc:
            warnings.append("--compile: tsc not found on PATH; skipped")
        else:
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "blueprint.ts")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(ts))
                r = subprocess.run([tsc, "--noEmit", "--strict", "--target", "es2020", path],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                if r.returncode != 0:
                    errors.append("--compile: TypeScript does not type-check:\n" +
                                  r.stdout.decode("utf-8", "replace").replace(path, "blueprint.ts"))
                stats["compiled"] = r.returncode == 0

    return errors, warnings, stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("file", help="the blueprint markdown file")
    p.add_argument("--design", help="the source design document, to check the two are congruent")
    p.add_argument("--draft", action="store_true", help="allow open [NEEDS CLARIFICATION] questions")
    p.add_argument("--compile", action="store_true", help="type-check TypeScript blocks with tsc, if installed")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    opts = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    with open(opts.file, encoding="utf-8") as f:
        text = f.read()
    design = None
    if opts.design:
        with open(opts.design, encoding="utf-8") as f:
            design = f.read()
    errors, warnings, stats = check(text, opts.compile, opts.draft, design)
    status = "FAIL" if errors else ("DRAFT" if stats.get("open_questions") else "PASS")
    if opts.json:
        json.dump({"status": status, "errors": errors, "warnings": warnings, "stats": stats}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if stats:
            print("blueprint: %(invariants)d invariants · %(components)d components · %(scenarios)d scenarios · "
                  "%(assumed)d assumed decisions · %(open_questions)d open questions" % stats)
        for e in errors:
            print("ERROR   " + e)
        for w in warnings:
            print("WARN    " + w)
        print(status if not errors else "FAIL (%d errors)" % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
