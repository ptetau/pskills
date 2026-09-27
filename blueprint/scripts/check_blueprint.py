#!/usr/bin/env python3
"""Check that a blueprint (Agent System Design Document) is complete and traceable.

Structural and traceability checks only; it cannot judge whether the design is good.

Errors (exit code 1):
  - the six sections are missing or out of order
  - section 1 lacks an in-scope or out-of-scope list, or uses "(assumed)" inline
    without listing the decisions it added
  - section 2 does not have 4-7 numbered invariants, or an invariant lacks an error
    code or an enforcement point ("Enforced by")
  - section 3 has no typed code block (TypeScript, Go, or Rust)
  - a Status/State type from section 3 has no state machine in section 4
  - a component in section 5 lacks a purpose, a signature code block, or failure and
    retry semantics
  - section 6 has fewer than 3 scenarios, a scenario lacks Given/When/Then, an
    invariant's error code is never exercised, or a scenario uses an undefined code
  - cryptic design IDs (V1, F2, UC3) remain outside code blocks

Warnings (reported, exit code unaffected): more than 5 scenarios, money typed as a
bare number, `any` in TypeScript, a component without "May call", filler phrasing.

Usage:
  python check_blueprint.py notifications.blueprint.md
  python check_blueprint.py notifications.blueprint.md --json
  python check_blueprint.py notifications.blueprint.md --compile   # also run tsc if available
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
ERROR_CODE = re.compile(r"`([A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+)`")
BARE_CODE = re.compile(r"\b([A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+)\b")
CRYPTIC_ID = re.compile(r"\b(?:V|F|UC)\d{1,2}\b")
FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)
MONEY_AS_NUMBER = re.compile(
    r"\b\w*(amount|price|total|cost|balance|fee)\w*\??\s*[:]\s*(number|float|double|f32|f64|float32|float64)\b", re.I)
STATE_TYPE = re.compile(r"\b(?:type|enum)\s+(\w*(?:Status|State))\b")
FILLER = re.compile(r"^(in this document|this document (will|describes)|let's|here is|here's|i will|we will now)\b", re.I | re.M)


def strip_code(text):
    return FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def split_sections(text):
    """Return {number: (title, body, first_line)} for '## N. Title' headings."""
    found = {}
    order = []
    lines = text.split("\n")
    heads = []
    for i, line in enumerate(lines):
        m = re.match(r"^##\s+(\d+)\.\s+(.*)$", line)
        if m:
            heads.append((i, int(m.group(1)), m.group(2).strip()))
    for k, (i, num, title) in enumerate(heads):
        end = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
        found[num] = (title, "\n".join(lines[i + 1:end]), i + 1)
        order.append(num)
    return found, order


def code_blocks(body, langs=None):
    blocks = []
    for m in FENCE.finditer(body):
        lang = m.group(1).lower()
        if langs is None or lang in langs:
            blocks.append((lang, m.group(2)))
    return blocks


def check(text, compile_ts=False):
    errors, warnings = [], []
    sections, order = split_sections(text)

    # --- structure
    for num, pattern in SECTIONS:
        if num not in sections:
            errors.append("section %d is missing (expected a '## %d. ...' heading)" % (num, num))
        elif not re.search(pattern, sections[num][0], re.I):
            errors.append("section %d is titled '%s'; expected something matching /%s/"
                          % (num, sections[num][0], pattern))
    if [n for n in order if 1 <= n <= 6] != sorted(n for n in order if 1 <= n <= 6):
        errors.append("sections are out of order: %s" % order)
    if errors:
        return errors, warnings, {}

    s1, s2, s3, s4, s5, s6 = (sections[n][1] for n in range(1, 7))

    # --- 1. scope
    if not re.search(r"in[- ]scope", s1, re.I):
        errors.append("section 1: no in-scope list")
    if not re.search(r"out[- ]of[- ]scope|non-goals", s1, re.I):
        errors.append("section 1: no out-of-scope (non-goals) list")
    assumed = len(re.findall(r"\(assumed\)", strip_code(text), re.I))
    if assumed and not re.search(r"decisions added|assumptions", s1, re.I):
        errors.append("%d '(assumed)' tags but section 1 has no 'Decisions added by this spec' list" % assumed)

    # --- 2. invariants
    items = re.findall(r"^\s*\d+\.\s+(.*(?:\n(?!\s*\d+\.\s).*)*)", strip_code(s2), re.M)
    items = [i for i in items if i.strip()]
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

    # --- 3. contracts
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
    defined_codes = invariant_codes | set(ERROR_CODE.findall(s5)) | set(BARE_CODE.findall(contract_code))

    # --- 6. verification
    gherkin = "\n".join(b for _, b in code_blocks(s6, {"gherkin", "feature", "cucumber"}))
    if not gherkin:
        errors.append("section 6: no ```gherkin block")
    scenarios = re.split(r"^\s*(?:Scenario Outline|Scenario Template|Scenario|Example):", gherkin, flags=re.M)[1:]
    if len(scenarios) < 3:
        errors.append("section 6: %d scenarios; expected at least 3" % len(scenarios))
    elif len(scenarios) > 5:
        warnings.append("section 6: %d scenarios; the format asks for 3-5 (use Scenario Outlines)" % len(scenarios))
    for n, sc in enumerate(scenarios, 1):
        title = sc.split("\n", 1)[0].strip()
        for kw in ("Given", "When", "Then"):
            if not re.search(r"^\s*%s\b" % kw, sc, re.M):
                errors.append("section 6, scenario %d (%s): no %s step" % (n, title, kw))
    exercised = set(BARE_CODE.findall(gherkin))
    for code in sorted(invariant_codes - exercised):
        errors.append("section 6: invariant error code `%s` is never exercised by a scenario" % code)
    for code in sorted(exercised - defined_codes):
        errors.append("section 6: scenario uses `%s`, which no invariant, contract, or component defines" % code)

    # --- global
    for i, line in enumerate(strip_code(text).split("\n"), 1):
        for m in CRYPTIC_ID.finditer(line):
            errors.append("line %d: cryptic design ID '%s'; use the domain term" % (i, m.group(0)))
    if FILLER.search(strip_code(text)):
        warnings.append("filler phrasing found; lead with substance")

    stats = {"invariants": len(items), "error_codes": sorted(invariant_codes), "state_types": state_types,
             "components": len(components), "scenarios": len(scenarios), "assumed": assumed}

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
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--compile", action="store_true", help="type-check TypeScript blocks with tsc, if installed")
    opts = p.parse_args(argv)
    with open(opts.file, encoding="utf-8") as f:
        text = f.read()
    errors, warnings, stats = check(text, opts.compile)
    if opts.json:
        json.dump({"ok": not errors, "errors": errors, "warnings": warnings, "stats": stats}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if stats:
            print("blueprint: %(invariants)d invariants · %(components)d components · %(scenarios)d scenarios · "
                  "%(assumed)d assumed decisions" % stats)
        for e in errors:
            print("ERROR   " + e)
        for w in warnings:
            print("WARN    " + w)
        print("PASS" if not errors else "FAIL (%d errors)" % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
