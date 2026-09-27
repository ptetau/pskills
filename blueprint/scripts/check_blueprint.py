#!/usr/bin/env python3
"""Check that a blueprint (Agent System Design Document) is complete, traceable, and
congruent with its design.

Structural and traceability checks only; it cannot judge whether the design is good.

Errors (exit code 1):
  - the six sections are missing or out of order
  - section 1 lacks an in-scope or out-of-scope list, or uses "(assumed)" inline
    without a "Decisions added by this spec" list
  - more than 3 [NEEDS CLARIFICATION] markers, or any at all without --draft
  - section 2 has no invariants, or an invariant lacks an error code or an enforcement
    point ("Enforced by `Component.method`"), or names a component or method that
    section 5 doesn't have
  - section 3 has no typed code block or no error catalog table, or the catalog and the
    quoted codes in the contracts disagree
  - a code used anywhere (invariants, section 5 prose, comments, and strings, scenarios)
    is missing from the error catalog
  - a Status/State type from section 3 has no '### Type' state machine with a diagram
  - a component in section 5 lacks a purpose, a signature block, or failure and retry
    semantics
  - section 6 has fewer than 3 scenarios, a scenario lacks Given/When/Then, an
    invariant's code is never asserted (in a Then step or an Examples row), or there is
    no "Done when" / "Verify" line
    with a command
  - design IDs (V1, F2, UC3, FR-1, SC-1, INV-1) remain outside code blocks
  - a flow calls a component its kind may not call (walls.md call rules), or one its
    "May call" line doesn't list
  - section 5 has no C4 component diagram, or it leaves out a component, shows one section 5
    doesn't define, or draws a call the call rules forbid; section 1 has neither a C4
    container diagram placing every component nor a line saying there is one container
  - with --render: a Mermaid diagram does not render (needs mmdc)
  - with --design: a Client, Manager, Engine, or ResourceAccess in the design's walls has
    no section 5 subsection; section 5 has a component the design doesn't; a design API
    verb has no matching method, or a method isn't in the design's API; a design brick
    isn't in its component's subsection; a shared contract has no type of that name

Not checked: whether a contract's fields or variants match the design's.

Warnings: plain-English problems (see readability.py: long sentences, a reading grade
above 7, technical words missing from the "Words used here" list), more than 7 invariants,
more than 5
scenarios, more than 5 steps in a scenario, a Background over 4 steps, a Then step that
asserts storage, money typed as a bare number, `any` in TypeScript, a component without
"May call", a design utility not mentioned in section 5, filler phrasing.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import readability  # ships alongside this script
except ImportError:  # pragma: no cover
    readability = None

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
CRYPTIC_ID = re.compile(r"\b(?:(?:V|F|UC)\d{1,3}|(?:FR|NFR|SC|INV)-\d+)\b")
FENCE = re.compile(r"^```(\w*)[^\n]*\n(.*?)^```", re.M | re.S)
MONEY_AS_NUMBER = re.compile(
    r"\b\w*(amount|price|total|cost|balance|fee)\w*\??\s*[:]\s*(number|float|double|f32|f64|float32|float64)\b", re.I)
STATE_TYPE = re.compile(r"\b(?:type|enum)\s+(\w*(?:Status|State))\b")
COMPONENT = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Manager|Engine|Access))\b")
DESIGN_CALL = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Manager|Engine|Access))\.([A-Z][A-Za-z0-9]*)\b")
NOT_COMPONENTS = {"ResourceAccess"}
DB_ASSERTION = re.compile(r"\b(database|db|sql|rows?|columns?)\b", re.I)
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


COMPONENT_TYPES = {"client", "manager", "engine", "resourceaccess", "utility"}
ALLOWED_CALLS = {  # walls.md call matrix; Utilities, storage, and vendors are always allowed
    "client": {"manager"},
    "manager": {"engine", "resourceaccess", "manager"},   # Manager to Manager only through a queue
    "engine": {"resourceaccess"},
    "resourceaccess": set(),
    "utility": set(),
}

KIND_NAMES = {"client": "Client", "manager": "Manager", "engine": "Engine",
              "resourceaccess": "ResourceAccess", "resource": "Resource", "utility": "Utility"}


def a_kind(kind):
    name = KIND_NAMES.get(kind, kind)
    return ("an " if name[:1] in "AEIOU" else "a ") + name


def section5_components(s5):
    """[(name, kind or None, body)] from '### Group (Kind)' and '#### Name' headings."""
    out, kind = [], None
    for block in re.split(r"^(?=#{3,4}\s)", s5, flags=re.M):
        head = block.split("\n", 1)[0]
        if head.startswith("#### "):
            name = head[5:].strip().strip("`")
            out.append((name, kind, block))
        elif head.startswith("### "):
            g = head.lower()
            kind = ("client" if "client" in g else "manager" if "manager" in g else "engine" if "engine" in g
                    else "resourceaccess" if "resourceaccess" in g or "resource access" in g
                    else "utility" if "utilit" in g else None)
    return out


def methods_of(body):
    names = set()
    for _, block in code_blocks(body, TYPED_LANGS):
        names.update(re.findall(r"^\s*(?:func\s+(?:\([^)]*\)\s*)?)?(?:async\s+)?([a-zA-Z_]\w*)\s*\(", block, re.M))
    return names - {"if", "for", "while", "switch", "return", "function"}


def flow_calls(body):
    """(callee, method) pairs named in a component's Flow bullets."""
    calls = []
    for m in re.finditer(r"\*\*Flows?\b.*?(?=\n- \*\*(?!Flow)|\n####|\Z)", body, re.S):
        calls += re.findall(r"`([A-Z][A-Za-z0-9]*)\.([a-zA-Z_]\w*)", m.group(0))
    return calls


def design_components(design_text):
    """{name: type} from the design's walls: a table with a Type column, else the layer listing."""
    sections, _ = split_sections(design_text)
    walls = next((body for title, body in sections.values() if re.search(r"wall", title, re.I)), design_text)
    comps = {}
    lines = strip_code(walls).split("\n")
    type_col = None
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            type_col = None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if i + 1 < len(lines) and re.match(r"^\s*\|[-| :]+\|\s*$", lines[i + 1]):
            type_col = next((k for k, c in enumerate(cells) if c.lower() == "type"), None)
            continue
        if type_col is not None and type_col < len(cells) and cells[0] and not set(cells[0]) <= set("-: "):
            kind = re.sub(r"[^a-z]", "", cells[type_col].lower())
            if kind in COMPONENT_TYPES:
                comps[cells[0].strip("`").strip()] = kind
    if comps:
        return comps
    # no typed table: a layer listing ("Clients  A  B") plus suffixed names in the walls text
    for _, block in code_blocks(walls):
        for line in block.split("\n"):
            m = re.match(r"^\s*(Clients|Utilities)\s+(.*)$", line)
            if m:
                kind = "client" if m.group(1) == "Clients" else "utility"
                for name in re.split(r"\s{2,}|\s*·\s*", m.group(2).strip()):
                    if name:
                        comps[name] = kind
    for name in set(COMPONENT.findall(walls)) - NOT_COMPONENTS:
        comps.setdefault(name, re.sub(r".*(Manager|Engine|Access)$", lambda m: {"Access": "resourceaccess"}
                                      .get(m.group(1), m.group(1).lower()), name))
    return comps


C4_ELEMENT = re.compile(r"^\s*(Person|Person_Ext|System|System_Ext|SystemDb|SystemDb_Ext|SystemQueue|SystemQueue_Ext|"
                        r"Container|Container_Ext|ContainerDb|ContainerDb_Ext|ContainerQueue|ContainerQueue_Ext|"
                        r"Component|Component_Ext|ComponentDb|ComponentDb_Ext|ComponentQueue|ComponentQueue_Ext)"
                        r"\(\s*(\w+)\s*,\s*\"([^\"]*)\"(.*)\)\s*$", re.M)
C4_REL = re.compile(r"^\s*(?:Rel|BiRel|Rel_[UDLR]|Rel_Up|Rel_Down|Rel_Left|Rel_Right|Rel_Back)\(\s*(\w+)\s*,\s*(\w+)",
                    re.M)


FLOW_NODE = re.compile(r"^\s*(\w+)\s*(?:\[\(|\(\[|\[\[|\(\(|\[|\(|\{)\s*\"(.*?)\"", re.M)
FLOW_EDGE = re.compile(r"^\s*(\w+)\s*(?:-->|-\.->|==>)\s*(?:\|[^|]*\|\s*)?(\w+)", re.M)


def c4_blocks(body, kind):
    """Mermaid blocks of one C4 diagram kind (C4Context, C4Container, C4Component, ...).

    A component diagram may also be a C4-styled flowchart whose boxes say "[Component: Kind]"."""
    out = []
    for lang, b in code_blocks(body, {"mermaid"}):
        head = re.sub(r"^\s*---.*?---\s*", "", b, flags=re.S)
        if re.match(r"\s*%s\b" % kind, head):
            out.append(b)
        elif kind == "C4Component" and re.match(r"\s*(flowchart|graph)\b", head) and "[Component:" in b:
            out.append(b)
    return out


def diagram_parts(b):
    """({alias: (name, element kind)}, [(from alias, to alias)]) from a C4 macro or C4-styled flowchart."""
    elements, rels = {}, []
    for m in C4_ELEMENT.finditer(b):
        elements[m.group(2)] = (m.group(3).strip("`"), m.group(1))
    rels += C4_REL.findall(b)
    for m in FLOW_NODE.finditer(b):
        label = m.group(2)
        bold = re.search(r"<b>(.*?)</b>", label)
        name = (bold.group(1) if bold else re.split(r"<br\s*/?>", label)[0]).strip().strip("`")
        kind = re.search(r"\[(Component|Container|External system|Person)[^\]]*\]", label)
        elements.setdefault(m.group(1), (name, "Component" if kind and kind.group(1) == "Component"
                                          else (kind.group(1) if kind else "other")))
    rels += FLOW_EDGE.findall(b)
    return elements, rels


def check_c4(s1, s5, components, kinds, errors, warnings):
    """Diagrams must name the same components as the text, and arrows must follow the call rules."""
    names = {c.split("\n", 1)[0].strip().strip("`") for c in components}
    built = {n for n in names if kinds.get(n) != "utility"}
    for where, body in (("section 1", s1), ("section 5", s5)):
        for m in re.finditer(r"^```mermaid\n(.*?)^```\n?((?:\s*\n)*[^\n]*)", body, re.M | re.S):
            b, after = m.group(1), m.group(2)
            if not (re.match(r"\s*C4\w+", b) or "[Component:" in b):
                continue
            title = re.search(r"^\s*title:?\s*\"?([^\n\"]+)", b, re.M)
            if not title:
                warnings.append("%s: a C4 diagram has no title (c4model.com: title every diagram with its type "
                                "and scope)" % where)
            elif not re.search(r"context|container|component|dynamic|deployment", title.group(1), re.I):
                warnings.append("%s: diagram title '%s' doesn't say its type (e.g. 'Component diagram for …')"
                                % (where, title.group(1).strip()))
            if not re.match(r"\s*key\b", after.strip(), re.I):
                warnings.append("%s: no 'Key:' line under a C4 diagram (c4model.com: every diagram needs a key)"
                                % where)
    comp = c4_blocks(s5, "C4Component")
    if not comp and len(built) > 3:
        errors.append("section 5: no C4 component diagram of the parts and their calls (```mermaid C4Component, or a "
                      "flowchart whose boxes say [Component: Kind]); C4 makes it optional only for 3 parts or fewer")
    for b in comp:
        elements, rels = diagram_parts(b)
        labels = {name for name, kind in elements.values() if kind.startswith("Component")}
        for n in sorted(built - labels):
            errors.append("section 5: `%s` is missing from the C4 component diagram" % n)
        for l in sorted(labels - names):
            if not re.search(r"storage|store|database|db|queue|vendor|resource", l, re.I):
                errors.append("section 5: the C4 component diagram shows `%s`, which section 5 doesn't define" % l)
        alias = {a: name for a, (name, kind) in elements.items()}
        for a, b2 in rels:
            src, dst = alias.get(a), alias.get(b2)
            ks, kd = kinds.get(src), kinds.get(dst)
            if ks and kd and kd not in ALLOWED_CALLS.get(ks, set()):
                errors.append("section 5: the C4 diagram draws `%s` calling `%s`, but %s may not call %s"
                              % (src, dst, a_kind(ks), a_kind(kd)))
    cont = c4_blocks(s1, "C4Container")
    if cont:
        text = "\n".join(cont)
        for n in sorted(built):
            if not re.search(r"\b%s\b" % re.escape(n), text):
                errors.append("section 1: `%s` is not placed in any container of the C4 container diagram" % n)
    elif not re.search(r"one container|single container", s1, re.I):
        errors.append("section 1: no C4 container diagram (```mermaid C4Container), and no line saying "
                      "everything runs in one container")


def check_design(design_text, s5, components, s3_code=""):
    """Congruence with the source design: same components, same verbs."""
    errors, warnings = [], []
    comps = design_components(design_text)
    heads = {c.split("\n", 1)[0].strip().strip("`") for c in components}
    for name, kind in sorted(comps.items()):
        if name in heads:
            continue
        if kind == "utility":
            if not re.search(r"\b%s\b" % re.escape(name), s5, re.I):
                warnings.append("--design: utility `%s` from the design is not mentioned in section 5" % name)
        else:
            errors.append("--design: %s `%s` is in the design but has no section 5 subsection" % (kind, name))
    for h in sorted(heads - set(comps)):
        errors.append("--design: `%s` is in section 5 but not in the design (a blueprint never adds components)" % h)
    bodies = {c.split("\n", 1)[0].strip().strip("`"): c for c in components}
    verbs = {(c, v) for c, v in DESIGN_CALL.findall(design_text) if c in comps}
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
        name = cells[0].strip("`").strip() if cells else ""
        if name not in comps:
            continue
        for col, into in ((api_col, verbs), (brick_col, bricks)):
            if col is not None and col < len(cells):
                for v in re.findall(r"`([A-Z][A-Za-z0-9]*)", cells[col]):
                    if v not in comps and not v.isupper():   # skip HTTP methods and codes
                        into.add((name, v))
    dsections, _ = split_sections(design_text)
    brick_section = next((b for t, b in dsections.values() if re.search(r"brick", t, re.I)), "")
    for block in re.split(r"^(?=###\s)", brick_section, flags=re.M):
        head = block.split("\n", 1)[0]
        name = head[4:].strip().strip("`") if head.startswith("### ") else ""
        if name in comps:
            for line in strip_code(block).split("\n"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
                if cells and not set(cells[0]) <= set("-: "):
                    for b in re.findall(r"`([A-Z][A-Za-z0-9]*)", cells[0]):
                        bricks.add((name, b))
    for comp, brick in sorted(bricks):
        body = bodies.get(comp)
        if body is not None and not re.search(r"\b%s\b" % re.escape(brick), body, re.I):
            errors.append("--design: brick `%s` of `%s` is not in its section 5 subsection (list it under "
                          "Internals)" % (brick, comp))
    # contracts keep their names
    contracts = set(re.findall(r"`([A-Z][A-Za-z0-9]*)`\s+used by", design_text))
    contracts |= set(re.findall(r"`([A-Z][A-Za-z0-9]*)\s*\{", design_text))
    for line in strip_code(design_text).split("\n"):
        if re.search(r"shared contract", line, re.I):
            contracts |= set(re.findall(r"`([A-Z][A-Za-z0-9]*)(?:`|\s*\{)", line))
    for c in sorted(contracts - set(comps)):
        if not re.search(r"\b(?:interface|type|struct|enum)\s+%s\b" % re.escape(c), s3_code):
            errors.append("--design: shared contract `%s` from the design has no type of that name in section 3" % c)
    # no methods the design doesn't have, where the design lists an API
    design_verbs = {}
    for c, v in verbs:
        design_verbs.setdefault(c, set()).add(v.lower())
    for c, body in bodies.items():
        if c in design_verbs:
            for m in sorted(methods_of(body)):
                if m.lower() not in design_verbs[c]:
                    errors.append("--design: `%s.%s` is not in the design's API for `%s` (a blueprint never adds "
                                  "verbs; add it to the design first)" % (c, m, c))
    for comp, verb in sorted(verbs):
        body = bodies.get(comp)
        if body is None:
            continue
        if not re.search(r"\b%s\s*\(" % re.escape(verb[0].lower() + verb[1:]), body) and \
           not re.search(r"\b%s\s*\(" % re.escape(verb), body):
            errors.append("--design: `%s.%s` from the design has no matching method in section 5" % (comp, verb))
    return errors, warnings, len(comps)


def check(text, compile_ts=False, draft=False, design_text=None, render=False):
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
    decisions = carried = 0
    for listed in re.finditer(r"#+\s*(decisions (?:added|carried)[^\n]*|assumptions)\n(.*?)(?=\n#+\s|\Z)",
                              s1, re.I | re.S):
        n = len(re.findall(r"^\s*[-*]\s+", listed.group(2), re.M))
        if re.search(r"carried", listed.group(1), re.I):
            carried += n
        else:
            decisions += n
    if assumed > decisions + carried:
        warnings.append("%d inline '(assumed)' tags but only %d decisions listed; list every one"
                        % (assumed, decisions + carried))
    if assumed and not re.search(r"decisions (added|carried)|assumptions", s1, re.I):
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
    if not items:
        errors.append("section 2: no numbered invariants")
    elif len(items) > 7:
        warnings.append("section 2: %d invariants; the format asks for at most 7" % len(items))
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
    machines = re.split(r"^###\s+", s4, flags=re.M)[1:]
    for t in state_types:
        base = re.sub(r"(Status|State)$", "", t)
        home = [m for m in machines if re.search(r"\b(%s|%s)\b" % (re.escape(t), re.escape(base)),
                                                  m.split("\n", 1)[0], re.I)]
        if not home:
            errors.append("section 4: state type `%s` from section 3 has no '### %s' state machine" % (t, t))
        elif not any(re.search(r"stateDiagram|──\[|──►|-->|->", m) for m in home):
            errors.append("section 4: '### %s' has no diagram" % t)
        else:
            decl = re.search(r"\b(?:type|enum)\s+%s\b[^;{]*?=\s*([^;]+);" % re.escape(t), contract_code)
            states = re.findall(r"\"([A-Za-z_][\w-]*)\"", decl.group(1)) if decl else []
            diagram = "\n".join(home)
            for st in states:
                if not re.search(r"\b%s\b" % re.escape(st), diagram):
                    errors.append("section 4: state `%s` of `%s` is missing from its diagram" % (st, t))

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

    bodies = {c.split("\n", 1)[0].strip().strip("`"): c for c in components}
    kinds = {name: kind for name, kind, _ in section5_components(s5)}
    for name, kind, body in section5_components(s5):
        may = re.search(r"may call[^\n]*(?:\n(?!- \*\*)[^\n]*)*", body, re.I)
        may_text = may.group(0) if may else ""
        for callee, method in flow_calls(body):
            if callee == name or callee not in kinds:
                continue
            ck = kinds.get(callee)
            if kind and ck and ck not in ALLOWED_CALLS.get(kind, set()):
                errors.append("section 5, %s: its flow calls `%s.%s`, but %s may not call %s (walls.md call "
                              "rules)" % (name, callee, method, a_kind(kind), a_kind(ck)))
            elif may and not re.search(r"\b%s\b" % re.escape(callee), may_text):
                errors.append("section 5, %s: its flow calls `%s.%s`, which its 'May call' line doesn't allow"
                              % (name, callee, method))
            elif kind == "manager" and ck == "manager":
                warnings.append("section 5, %s: calls Manager `%s`; that is allowed only through a queue" % (name, callee))
    check_c4(s1, s5, components, kinds, errors, warnings)
    for n, item in enumerate(items, 1):
        enforced = re.split(r"enforced (?:by|in|at)", item, flags=re.I)
        if len(enforced) < 2:
            continue
        clause = enforced[1]
        named = [(c, m) for c, m in re.findall(r"`([A-Z][A-Za-z0-9]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?", clause)
                 if not c.isupper() and (m or c in bodies or COMPONENT.fullmatch(c))]
        for comp, method in named:
            if comp not in bodies:
                errors.append("section 2, invariant %d: enforced by `%s`, which has no section 5 subsection" % (n, comp))
            elif method and not re.search(r"\b%s\s*\(" % re.escape(method), bodies[comp]):
                errors.append("section 2, invariant %d: `%s.%s` is not a method in section 5" % (n, comp, method))

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
        for m in re.finditer(r"^\s*Then\b.*(?:\n\s*(?:And|But)\b.*)*", body, re.M):
            if DB_ASSERTION.search(m.group(0)):
                warnings.append("section 6, scenario %d (%s): a Then step asserts storage; assert what a caller "
                                "can observe" % (n, title))
        steps = len(STEP.findall(body))
        if steps > 5:
            warnings.append("section 6, scenario %d (%s): %d steps; Cucumber recommends 3-5" % (n, title, steps))
    asserted = []
    for sc in scenarios:
        parts = re.split(r"^\s*Examples:", sc, flags=re.M)
        thens = re.findall(r"^\s*Then\b.*(?:\n\s*(?:And|But)\b.*)*", parts[0], re.M)
        asserted += thens + parts[1:]
    exercised = set(BARE_CODE.findall("\n".join(asserted)))
    mentioned = set(BARE_CODE.findall(gherkin))
    for code in sorted(invariant_codes - exercised):
        errors.append("section 6: invariant error code `%s` is never asserted by a scenario (in a Then step or "
                      "an Examples row)" % code)
    if not re.search(r"(done when|verify)[^\n]*`[^`]+`", strip_code(s6), re.I):
        errors.append("section 6: no 'Done when' / 'Verify' line with the command that runs the suite")

    # --- every code used is catalogued
    if catalog:
        s5_codes = set(ERROR_CODE.findall(strip_code(s5)))
        for _, block in code_blocks(s5, TYPED_LANGS):
            for comment in re.findall(r"//[^\n]*|/\*.*?\*/|#[^\n]*", block, re.S):
                s5_codes.update(BARE_CODE.findall(comment))
            s5_codes.update(QUOTED_CODE.findall(block))
        used = {"section 2": invariant_codes, "section 5": s5_codes, "section 6": mentioned}
        for where, codes in used.items():
            for c in sorted(codes - catalog):
                errors.append("%s: `%s` is not in the error catalog" % (where, c))

    # --- global
    for i, line in enumerate(prose.split("\n"), 1):
        for m in CRYPTIC_ID.finditer(line):
            errors.append("line %d: cryptic design ID '%s'; use the domain term" % (i, m.group(0)))
    if FILLER.search(prose):
        warnings.append("filler phrasing found; lead with substance")
    if readability is not None:
        rw, rs = readability.check(text)
        warnings += ["plain English: " + w for w in rw]
        plain = rs

    stats = {"reading_grade": plain.get("grade") if readability is not None else None,
             "invariants": len(items), "error_codes": sorted(catalog), "state_types": state_types,
             "components": len(components), "scenarios": len(scenarios), "assumed": assumed,
             "decisions": decisions, "carried": carried,
             "open_questions": open_questions}

    if design_text is not None:
        e, w, n = check_design(design_text, s5, components, contract_code)
        errors += e
        warnings += w
        stats["design_components"] = n

    if render:
        mmdc = shutil.which("mmdc")
        blocks = [b for _, b in code_blocks(text, {"mermaid"})]
        if not mmdc:
            warnings.append("--render: mmdc (Mermaid CLI) not found on PATH; skipped")
        else:
            cfg = os.environ.get("MMDC_PUPPETEER_CONFIG")
            with tempfile.TemporaryDirectory() as d:
                for i, b in enumerate(blocks, 1):
                    src, out = os.path.join(d, "d%d.mmd" % i), os.path.join(d, "d%d.svg" % i)
                    with open(src, "w", encoding="utf-8") as f:
                        f.write(b)
                    cmd = [mmdc, "-i", src, "-o", out] + (["-p", cfg] if cfg else [])
                    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
                    if r.returncode != 0 or not os.path.exists(out):
                        title = re.search(r"^\s*title:?\s*\"?([^\"\n]+)", b, re.M)
                        name = title.group(1).strip() if title else b.strip().split("\n", 1)[0]
                        log = r.stdout.decode("utf-8", "replace")
                        err = re.search(r"^Error:.*?(?=^\S*\.parseError|^\s+at |\Z)", log, re.M | re.S)
                        errors.append("--render: diagram %d (%s) does not render:\n    %s"
                                      % (i, name, (err.group(0) if err else log[-600:]).strip().replace("\n", "\n    ")))
            stats["rendered"] = len(blocks)

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
    p.add_argument("--render", action="store_true",
                   help="render every Mermaid diagram with mmdc, if installed (MMDC_PUPPETEER_CONFIG for a browser config)")
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
    errors, warnings, stats = check(text, opts.compile, opts.draft, design, opts.render)
    status = "FAIL" if errors else ("DRAFT" if stats.get("open_questions") else "PASS")
    if opts.json:
        json.dump({"status": status, "errors": errors, "warnings": warnings, "stats": stats}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if stats:
            print("blueprint: %(invariants)d invariants · %(components)d components · %(scenarios)d scenarios · "
                  "%(decisions)d decisions added (%(assumed)d marked inline) + %(carried)d carried · "
                  "%(open_questions)d open questions"
                  % stats)
        for e in errors:
            print("ERROR   " + e)
        for w in warnings:
            print("WARN    " + w)
        print(status if not errors else "FAIL (%d errors)" % len(errors))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
