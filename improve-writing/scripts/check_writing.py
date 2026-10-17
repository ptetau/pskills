#!/usr/bin/env python3
"""Examine a Markdown file against the writing guidelines (WRITING-GUIDELINES.md).

The guidelines are the ASD-STE100 Simplified Technical English (STE) rules, plus two more
rules: the local-references rule and the described-IDs rule. This script finds the
problems that a script can measure. A person or an agent must still read the text for the
other rules, for example one topic in each sentence.

Only prose is examined. Code blocks, inline code, tables, headings, HTML, and block
quotes are not prose. Inline code counts as one word, and so does text in parentheses
or in quotes (STE rules 8.5 and 8.6).

Each finding has a rule tag:
  length        an instruction has more than 20 words (5.1), or a descriptive sentence
                has more than 25 words (6.3)
  paragraph     a paragraph has more than six sentences (6.6). The description in the
                frontmatter of a skill is metadata, so this rule does not apply to it
  semicolon     a semicolon in prose (8.1)
  contraction   "don't", "it's", and other contractions (4.2)
  latin         "e.g.", "i.e.", "etc.", and other Latin abbreviations (GR-6)
  tense         a verb form that STE does not use: perfect, progressive, or a complex
                construction with an auxiliary verb (3.2, 3.4, 3.5)
  passive       a passive with a known agent ("is read by"), or a passive instruction
                ("must be updated") (3.6, 5.3)
  phrasal       a phrasal verb, for example "set up" (9.3)
  that          "make sure" without "that" (GR-1)
  word          a word from the built-in list of words to replace (1.1 to 1.4)
  ste-word      with --dictionary only: a word that the STE dictionary does not approve.
                Review each one. Keep a technical noun or verb of your subject (1.5, 1.12)
  reference     a paragraph, list item, or reply that starts with a pronoun such as "It"
                or "This", or the words "the former" or "the latter" (local references)
  id            an ID such as "B2" or "#6" with no description in the same sentence
                (described IDs)
  spelling      an American spelling; the guidelines use New Zealand English (1.14)
  glossary      a technical word that the "Words used here" list does not give. This
                applies when the file has such a list, or with --require-glossary (use the
                option for a design or a spec; a guide or a skill needs no list)
  grade         the reading grade is more than --max-grade (Flesch-Kincaid)

Usage:
  python check_writing.py FILE.md
  python check_writing.py FILE.md --dictionary ASD-STE100.pdf   # or a text file of it
  python check_writing.py FILE.md --json
  python check_writing.py FILE.md --strict                       # exit 1 on findings
  python check_writing.py DESIGN.md --require-glossary --max-grade 7   # a design or a spec

The STE dictionary is free from https://www.asd-ste100.org. ASD does not let other
persons distribute the dictionary, so this script does not contain it. You can also set
the STE100_DICTIONARY environment variable to the path of your copy.
"""

import argparse
import bisect
import json
import os
import re
import sys

# --- word lists (our own lists; not taken from the STE dictionary) -------------------

# Technical words that a reader possibly does not know. A document that uses one in its
# prose must give it in a "Words used here" list.
JARGON = [
    "abstraction", "asynchronous", "atomic", "atomically", "backoff", "cardinality",
    "compare-and-set", "composable", "composition", "concurrency", "decomposition",
    "deterministic", "encapsulate", "encapsulates", "idempotency", "idempotent",
    "immutable", "immutability", "invariant", "invariants", "jitter", "latency",
    "mutation", "orchestration", "orchestrate", "orthogonal", "orthogonality",
    "payload", "polymorphism", "postcondition", "precondition", "primitive",
    "primitives", "semantics", "serialization", "synchronous", "throughput",
    "topology", "transactional", "volatile", "volatility",
]

# Words and phrases to replace, with a plainer alternative. Lower case. A phrase is
# matched as a whole phrase.
REPLACE = {
    "utilize": "use", "utilise": "use", "in order to": "to", "prior to": "before",
    "ensure": "make sure that", "however": "but", "therefore": "thus",
    "approximately": "about", "additional": "more", "assist": "help",
    "commence": "start", "demonstrate": "show", "facilitate": "help",
    "indicate": "show", "initiate": "start", "obtain": "get", "terminate": "stop",
    "transmit": "send", "via": "through", "whilst": "while", "regarding": "about",
    "subsequently": "then", "numerous": "many", "in the event that": "if",
    "due to the fact that": "because", "a number of": "some", "is able to": "can",
    "are able to": "can", "has the ability to": "can", "make use of": "use",
    "with regard to": "about", "in addition": "also", "should": "'must' for a rule, or 'try to' / 'usually' for advice (keep the strength)",
    "may": "'is permitted to' for a permission, or 'can' for an ability", "might": "can", "never": "do not", "avoid": "do not, or prevent",
    "allow": "let", "allows": "lets", "provide": "give", "provides": "gives",
    "perform": "do", "need to": "must", "needs to": "must", "have to": "must",
    "has to": "must", "a lot of": "many", "lots of": "many", "describe": "give, or tell",
    "describes": "gives, or tells", "explain": "tell", "explains": "tells",
    "mention": "give, or write", "mentions": "gives", "verify": "make sure that",
    "verifies": "makes sure that", "require": "necessary, or must",
    "requires": "must have", "required": "necessary", "whole": "full, or all",
    "within": "in", "difficult": "not easy", "impossible": "not possible",
}

# Phrasal verbs (STE 9.3) and a one-word alternative.
PHRASAL = {
    "set up": "prepare, or configure", "sets up": "prepares", "find out": "find",
    "carry out": "do", "carries out": "does", "point out": "show, or tell",
    "points out": "shows", "figure out": "find", "fill in": "complete, or write",
    "fill out": "complete", "go over": "examine", "look into": "examine",
    "look up": "find", "pick up": "get", "sort out": "correct", "give up": "stop",
    "come up with": "make", "end up": "become, or stay", "clean up": "remove, or clean",
    "break down": "divide", "write down": "write", "write up": "write",
"hand over": "give", "spin up": "start", "kick off": "start",
    "wrap up": "complete", "turn on": "start", "turn off": "stop", "back up": "copy",
    "go through": "examine", "work out": "calculate, or find", "put together": "make",
    "leave out": "omit", "left out": "omitted", "rule out": "eliminate",
    "show up": "appear", "shows up": "appears", "bring up": "show", "fall back": "use instead",
    "falls back": "uses instead", "boil down": "become", "lay out": "arrange",
}

# Technical nouns and verbs of software (STE 1.5, 1.12). The dictionary check does not
# flag these words.
TECHNICAL = set("""
file files branch branches prompt prompts article articles commit commits merge merges
deploy deploys parse parses render renders click clicks schema schemas field fields
record records query queries request requests release releases issue issues build builds
run runs test tests check checks log logs push pushes pull pulls fetch fetches
clone clones script scripts stage stages patch patches tag tags flag flags hook hooks
skill skills agent agents spec specs token tokens cache caches queue queues
template templates checker linter suite suites rubric rubrics eval evals workflow
workflows worktree worktrees frontmatter repo repository repositories markdown
""".split())

# American spellings and their New Zealand English form (STE 1.14, as the guidelines set it).
NZ_SPELLING = {
    "behavior": "behaviour", "behaviors": "behaviours", "behavioral": "behavioural",
    "color": "colour", "colors": "colours", "colored": "coloured", "favor": "favour",
    "favorite": "favourite", "honor": "honour", "labor": "labour", "neighbor": "neighbour",
    "center": "centre", "centered": "centred", "catalog": "catalogue", "catalogs": "catalogues",
    "dialog": "dialogue", "defense": "defence", "offense": "offence", "gray": "grey",
    "judgment": "judgement", "judgments": "judgements", "fulfill": "fulfil", "enroll": "enrol",
    "canceled": "cancelled", "canceling": "cancelling", "labeled": "labelled",
    "labeling": "labelling", "modeled": "modelled", "modeling": "modelling",
    "traveled": "travelled", "signaled": "signalled", "totaled": "totalled",
    "analyze": "analyse", "analyzed": "analysed", "analyzes": "analyses", "analyzing": "analysing",
    "license": "licence (noun) or license (verb)", "practice": "practice (noun) or practise (verb)",
}
IZE_EXCEPT = {"size", "sizes", "sized", "seize", "seized", "prize", "prizes", "capsize", "resize",
              "resized", "resizes", "downsize", "oversize", "oversized", "baize", "maize"}
IZE = re.compile(r"\b([a-z]{3,}?)(iz)(e|es|ed|ing|ation|ations|er|ers)\b", re.I)
LATIN = re.compile(r"\b(e\.\s?g\.|i\.\s?e\.|etc\.|cf\.|viz\.|et al\.|vs\.|n\.\s?b\.)", re.I)
CONTRACTION = re.compile(r"\b(\w+n['’]t|\w+['’](?:re|ve|ll|d|m)|(?:it|that|there|what|here|let|who|where|he|she)['’]s)\b", re.I)
ING_ADJECTIVES = set("""missing existing remaining pending following outstanding interesting misleading
matching corresponding leading trailing surrounding ongoing upcoming incoming outgoing during string
thing nothing something anything everything morning evening ceiling building setting""".split())
IRREGULAR = set("""been done made given taken written read run seen found kept put set shown told
built sent spent held left lost meant paid said sold stood understood begun broken chosen
drawn driven eaten fallen forgotten frozen gotten hidden known proven shaken spoken stolen
sworn thrown woken worn hung brought bought caught fought sought taught thought""".split())
AUX_PERFECT = re.compile(r"\b(has|have|had|'ve)\s+(?:not\s+|already\s+|just\s+|now\s+)?(\w+ed|%s)\b" % "|".join(IRREGULAR), re.I)
PROGRESSIVE = re.compile(r"\b(am|is|are|was|were|be|been)\s+(?:not\s+|still\s+|now\s+)?(\w{3,}ing)\b", re.I)
COMPLEX_AUX = re.compile(r"\b(would|could|should|might|must|may|will)\s+have\s+(?:been\s+)?\w+\b", re.I)
GERUND_CLAUSE = re.compile(r"\b(when|while|before|after|by|on|without)\s+(\w{3,}ing)\b", re.I)
PASSIVE_BY = re.compile(r"\b(is|are|was|were|be|been|being)\s+(?:not\s+)?(\w+ed|%s)\s+by\b" % "|".join(IRREGULAR), re.I)
PASSIVE_MODAL = re.compile(r"\b(must|should|can|will|may|needs to|has to|have to)\s+(?:not\s+)?be\s+(\w+ed|%s)\b" % "|".join(IRREGULAR), re.I)
NO_THAT = re.compile(r"\b(make sure|makes sure)\s+(?!that\b|of\b|to\b)(the|a|an|it|you|we|they|this|these|all|each|every|no|nothing|your|its|their|[A-Z]|X\b)", re.I)
START_PRONOUN = re.compile(r"^(?:It|Its|They|Them|Their|He|She|His|Her)\b|^(?:This|That|These|Those)\b(?=\s*(?:[.,;:)!?]|$|\s+(?:is|are|was|were|will|can|must|means|makes|gives|shows|lets|keeps|also|does|did|has|had|happens|works|needs|way)\b))")
FORMER_LATTER = re.compile(r"\bthe (former|latter)\b", re.I)
ID_TOKEN = re.compile(r"(?<![\w#/.-])((?:[A-Z]{1,4}-?\d{1,3}[a-z]?)|#\d+)(?![\w-])")
ID_EXEMPT = set("""C4 Z3 H1 H2 H3 H4 H5 H6 S3 EC2 ES5 ES6 ES2020 IPV4 IPV6 IPv4 IPv6 SHA1 SHA256 MD5
UTF8 UTF-8 HTTP2 OAUTH2 OAuth2 X509 B2B B2C P2P MP3 MP4 A4 A3 L1 L2 L3 CO2 G7 G20 Q1 Q2 Q3 Q4
W3C K8S ISO8601 PEP8 GPT4 MS1 HS256 RS256 ES256 AES256 ARM64 X64 X86 RFC9110 RFC9457""".split())
IMPERATIVE = set("""add apply ask avoid build call change check choose close commit compare confirm copy count
create cut decide delete do draw drop edit end ensure examine exclude find fix follow get give go
include install keep leave let list load look make mark merge move name note obey open pick
prefer prepare print push put read record remove rename replace reply report request return
rewrite run save say select send set show skip sort split start stop take tell test try turn
update use wait write""".split())
CONDITION_START = re.compile(r"^(if|when|before|after|unless|once|while|for each|for every|until)\b", re.I)

FENCE = re.compile(r"^(`{3,})[^\n]*\n.*?^\1`*[ \t]*$", re.M | re.S)   # a ```` fence may hold ``` lines


def frontmatter_description(text):
    """(text without the frontmatter, the description value or '', its first line number)."""
    if not text.startswith("---\n"):
        return text, "", 0
    end = text.find("\n---", 4)
    if end < 0:
        return text, "", 0
    head = text[4:end]
    body_lines = text.count("\n", 0, end + 4)
    m = re.search(r"^description:\s*(?:[>|][-+]?\s*\n)?(.*?)(?=^\w[\w-]*:|\Z)", head, re.M | re.S)
    desc = " ".join(m.group(1).split()) if m else ""
    line = head.count("\n", 0, m.start()) + 2 if m else 0
    # keep the line count, so that line numbers stay correct
    return "\n" * body_lines + text[end + 4:], desc, line


def prose_map(text):
    """(prose, line_of, raw_of): the prose, a map from offset to source line, and the raw lines.

    Each list item and each paragraph is its own paragraph in the prose."""
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    text = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    lines, starts, offset = [], [], 0

    def emit(s, lineno):
        nonlocal offset
        starts.append((offset, lineno))
        lines.append(s)
        offset += len(s) + 1

    for lineno, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if not s or s.startswith(("#", "|", ">", "<")) or re.match(r"^[-=*_]{3,}$", s):
            emit("", lineno)
            continue
        if re.fullmatch(r"(\*\*|__)[^*_\n]{1,80}(\1:?|:\1)", s):     # a bold label alone on a line is a heading
            emit("", lineno)
            continue
        if re.match(r"^([-*+]|\d+\.|[A-Za-z]\.)\s+", s):
            emit("", lineno)
        s = re.sub(r"^[-*+]\s+(\[[ xX]\]\s+)?|^\d+\.\s+|^[A-Za-z]\.\s+", "", s)
        # a bold label at the start ("**Verify:**") is a label, one word (STE 8.6): keep only a marker
        s = re.sub(r"^(\*\*|__)[^*_\n]{1,40}?(?::\1|\1:)\s+(?=\S)", "LABEL: ", s)
        s = re.sub(r"<[^>]+>", "", s)
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
        s = re.sub(r"(\*\*|__)(.+?)\1", r"\2", s)
        s = re.sub(r"(?<![\w*])[*_]([^*_]+)[*_](?![\w*])", r"\1", s)
        emit(s, lineno)
    keys = [o for o, _ in starts]

    def line_of(off):
        return starts[max(0, bisect.bisect_right(keys, off) - 1)][1] if starts else None
    return "\n".join(lines), line_of


def prose_of(text):
    return prose_map(frontmatter_description(text)[0])[0]


def for_count(sent):
    """The sentence with inline code, quoted text, and parentheses reduced to one word each."""
    s = re.sub(r"`[^`]*`", "X", sent)
    s = re.sub(r"\"[^\"]*\"|“[^”]*”", "Q", s)
    for _ in range(3):
        s = re.sub(r"\([^()]*\)", "P", s)
    return s


def words_of(s):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", s)


def paragraphs_of(prose, line_of):
    """[[(sentence, line)]] for each paragraph."""
    out, start = [], 0
    for brk in list(re.finditer(r"\n\s*\n", prose)) + [None]:
        end = brk.start() if brk else len(prose)
        para, base = prose[start:end], start
        start = brk.end() if brk else end
        sents, s0 = [], 0
        safe = re.sub(r"`[^`]*`|\"[^\"]{0,300}\"|“[^”]{0,300}”", lambda m: re.sub(r"\S", "X", m.group(0)), para)   # no splits in code or quotes
        safe = re.sub(r"\b(e\.g|i\.e|etc|vs|cf)\.", lambda m: m.group(0).replace(".", "_"), safe, flags=re.I)
        for cut in [c.end() for c in re.finditer(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(`*“])", safe)] + [len(para)]:
            raw, at = para[s0:cut], base + s0
            s0 = cut
            sent = " ".join(raw.split())
            if sent:
                at += len(raw) - len(raw.lstrip())
                sents.append((sent, line_of(at) if line_of else None))
        if sents:
            out.append(sents)
    return out


def sentences_of(prose, line_of=None):
    """[(sentence, words, line)] for sentences of three words or more (readability.py interface)."""
    out = []
    for para in paragraphs_of(prose, line_of):
        for sent, line in para:
            ws = words_of(for_count(sent))
            if len(ws) >= 3:
                out.append((sent, ws, line))
    return out


def syllables(word):
    w = word.lower().strip("'’-")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def glossary_terms(text):
    terms, found = set(), False
    for m in re.finditer(r"^(?:#+\s*|\*\*)words used here(?:\*\*)?\s*$(.*?)(?=^#+\s|^\*\*[^*\n]+\*\*\s*$|\Z)",
                         text, re.I | re.M | re.S):
        found = True
        for line in m.group(1).split("\n"):
            t = re.match(r"^\s*[-*]\s+\*{0,2}([^*:—–]+?)\*{0,2}\s*(?:[:—–]|\s-\s)", line)
            if t:
                for part in re.split(r"[,/]| or ", t.group(1)):
                    terms.add(part.strip().lower())
    return terms, found


def is_instruction(sent):
    s = re.sub(r"^\W+", "", sent)
    s = re.sub(r"^(?:(?:[A-Z]{0,4}-?\d+(?:\.\d+)?[a-z]?|and|to)[,\s]+)+", "", s)   # labels: "3.1, 3.2", "R3"
    if CONDITION_START.match(s) and "," in s:
        s = s.split(",", 1)[1].strip()
    first = (re.match(r"[A-Za-z]+", s) or [""])[0].lower()
    return first in IMPERATIVE or s.lower().startswith(("do not ", "don't ", "never ", "always "))


def lemma_candidates(w):
    w = w.lower()
    out = [w]
    for suf, rep in (("ies", "y"), ("ied", "y"), ("es", ""), ("s", ""), ("ed", ""), ("ed", "e"),
                     ("d", ""), ("ing", ""), ("ing", "e"), ("er", ""), ("est", ""), ("ly", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            out.append(w[: len(w) - len(suf)] + rep)
    return out


def load_dictionary(path):
    """{word: approved alternative} for words that the STE dictionary lists as not approved
    and does not also approve as a different part of speech."""
    if path.lower().endswith(".pdf"):
        try:
            import pypdf
        except ImportError:
            sys.exit("--dictionary: reading a PDF needs pypdf (pip install pypdf), or give a text file")
        text = "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(path).pages)
    else:
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
    pos = r"(?:v|n|adj|adv|prep|conj|pron|art|TN|TV)"
    entry = re.compile(r"^\s*([A-Za-z][A-Za-z'’.-]*(?: [A-Za-z][A-Za-z'’.-]*){0,3})\s+\((%s)\)(.*)$" % pos)
    approved, banned = set(), {}
    for line in text.split("\n"):
        m = entry.match(line)
        if not m:
            continue
        word, rest = m.group(1), m.group(3)
        if word.upper() == word:
            approved.add(word.lower())
        elif word.islower():
            alt = re.match(r"\s*((?:[A-Z][A-Z'’-]*\s*)+\(%s\)(?:,\s*(?:[A-Z][A-Z'’-]*\s*)+\(%s\))*)" % (pos, pos), rest)
            if alt:                       # entries in the revision log have no alternative
                banned.setdefault(word, re.sub(r"\s+", " ", alt.group(1).lower()))
    banned = {w: a for w, a in banned.items() if w not in approved and " " not in w}
    return {"banned": banned, "approved": approved}


def described(sent, m):
    """True if the ID at match m has a description in the same sentence."""
    after = sent[m.end():]
    before = sent[: m.start()]
    if re.match(r"\s*(\(|:|—|–|-\s|=|\"|“|Q\b|,\s*(the|a|an)\b)", after):     # Q is a masked quote
        return True
    if re.match(r"(\s*,\s*(?:[A-Z]{1,4}-?\d{1,3}[a-z]?|#\d+))*\s*,?\s*(…|\.\.\.)", after):   # a scheme: "R1, R2, …"
        return True
    if before.rstrip().endswith("(") or re.search(r"\([^)]*$", before):    # "the question order (R5)"
        return True
    if re.fullmatch(r"(?:\s*(?:[A-Z]{1,4}-?\d{1,3}[a-z]?|#\d+|and|to|,))*\s*", before) and \
            re.match(r"\s*(and|,|to)?\s*[A-Za-z]", after):        # a label: "R3 Exactly one …", "GR-3, GR-4 If …"
        return True
    return False


def check(text, dictionary=None, max_grade=9.0, require_glossary=False):
    """(warnings, stats). warnings are strings; stats['findings'] holds the full records."""
    body, desc, desc_line = frontmatter_description(text)
    prose, line_of = prose_map(body)
    paras = paragraphs_of(prose, line_of)
    desc_para = None
    if desc:
        desc_para = [(s, desc_line) for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", desc)]
        paras.insert(0, desc_para)
    findings = []

    def add(rule, line, msg, sent=""):
        findings.append({"rule": rule, "line": line, "message": msg,
                         "text": sent[:140] + ("…" if len(sent) > 140 else "")})

    sents_all = []
    for para in paras:
        counted = [(s, l) for s, l in para if len(words_of(for_count(s))) >= 3]
        if len(counted) > 6 and para is not desc_para:   # a skill description is metadata, not a paragraph
            add("paragraph", para[0][1], "%d sentences in one paragraph; write six or fewer (6.6)" % len(counted),
                para[0][0])
        for i, (sent, line) in enumerate(para):
            raw = re.sub(r"^LABEL: ", "", sent)
            nocode = re.sub(r"`[^`]*`", "X", raw)
            nocode = re.sub(r"\"[^\"]*\"|“[^”]*”", "Q", nocode)          # quoted text is exempt
            n = len(words_of(for_count(raw)))
            if n >= 3:
                sents_all.append((raw, line, n))
                limit, kind, rule = (20, "instruction", "5.1") if is_instruction(nocode) else (25, "descriptive sentence", "6.3")
                if n > limit:
                    add("length", line, "%s of %d words; write %d or fewer (%s)" % (kind, n, limit, rule), raw)
            if ";" in re.sub(r"\([^)]*\)", "", nocode):
                add("semicolon", line, "semicolon; write two sentences (8.1)", raw)
            for m in CONTRACTION.finditer(nocode):
                add("contraction", line, "contraction '%s'; write it in full (4.2)" % m.group(0), raw)
            for m in LATIN.finditer(nocode):
                add("latin", line, "Latin abbreviation '%s'; write 'for example', 'that is', or a list (GR-6)" % m.group(0), raw)
            for rx, why in ((AUX_PERFECT, "perfect tense; use the simple past or present (3.2)"),
                            (PROGRESSIVE, "progressive '-ing' form; use a simple tense (3.2, 3.5)"),
                            (COMPLEX_AUX, "complex verb construction; use a simple tense (3.4)"),
                            (GERUND_CLAUSE, "'-ing' clause; write 'when you …' or a new sentence (3.5)")):
                for m in rx.finditer(nocode):
                    if rx is AUX_PERFECT and m.group(2).lower() in ("need", "used", "based"):
                        continue
                    if rx in (PROGRESSIVE, GERUND_CLAUSE) and m.group(2).lower() in ING_ADJECTIVES:
                        continue
                    add("tense", line, "'%s': %s" % (m.group(0), why), raw)
            for w in words_of(nocode):
                lw = w.lower()
                if lw in NZ_SPELLING and lw not in ("license", "practice"):
                    add("spelling", line, "'%s'; write '%s' (1.14, New Zealand English)" % (w, NZ_SPELLING[lw]), raw)
                elif lw not in IZE_EXCEPT:
                    z = IZE.fullmatch(lw)
                    if z:
                        add("spelling", line, "'%s'; write '%s' (1.14, New Zealand English)"
                            % (w, z.group(1) + "is" + z.group(3)), raw)
            for m in PASSIVE_BY.finditer(nocode):
                add("passive", line, "'%s': passive with a known agent; make the agent the subject (3.6)" % m.group(0), raw)
            for m in PASSIVE_MODAL.finditer(nocode):
                add("passive", line, "'%s': passive instruction; use the imperative (5.3)" % m.group(0), raw)
            low = nocode.lower()
            for phrase, alt in PHRASAL.items():
                if re.search(r"\b%s\b" % re.escape(phrase), low):
                    add("phrasal", line, "phrasal verb '%s'; write '%s' (9.3)" % (phrase, alt), raw)
            for m in NO_THAT.finditer(nocode):
                add("that", line, "'%s' without 'that'; write '%s that' (GR-1)" % (m.group(0), m.group(1)), raw)
            for phrase, alt in REPLACE.items():
                if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(phrase), low):
                    add("word", line, "'%s'; write '%s' (1.1)" % (phrase, alt), raw)
            if dictionary:
                seen = set()
                for k, w in enumerate(words_of(nocode)):
                    lw = w.lower().strip("'’")
                    if lw in seen or lw in TECHNICAL or (k > 0 and w[:1].isupper()):
                        continue
                    cands = lemma_candidates(lw)
                    if any(c in dictionary["approved"] for c in cands):
                        continue
                    for cand in cands:
                        if cand in dictionary["banned"] and cand not in REPLACE:
                            add("ste-word", line, "'%s' is not an approved STE word; consider '%s', or keep it if it "
                                "is a technical noun or verb of the subject (1.1, 1.5, 1.12)" % (w, dictionary["banned"][cand]), raw)
                            seen.add(lw)
                            break
            if i == 0 and START_PRONOUN.match(re.sub(r"^\W+", "", raw)):
                add("reference", line, "starts with a pronoun that refers back; write the full noun (local references)", raw)
            for m in FORMER_LATTER.finditer(nocode):
                add("reference", line, "'%s' makes the reader look back; write the noun (local references)" % m.group(0), raw)
            unwrap = lambda m: "X" if (m.group(1).startswith("-") or " " in m.group(1)) else m.group(1)   # a command example
            plain = re.sub(r"\"[^\"]*\"|“[^”]*”", "Q", re.sub(r"`([^`]*)`", unwrap, raw))
            for m in ID_TOKEN.finditer(plain):
                tok = m.group(1)
                if tok in ID_EXEMPT or tok.upper() in ID_EXEMPT:
                    continue
                if not described(plain, m):
                    add("id", line, "ID '%s' has no description in the same sentence; write '%s (short description)' "
                        "(described IDs)" % (tok, tok), raw)

    stats = {"sentences": len(sents_all), "words": sum(n for _, _, n in sents_all)}
    if sents_all:
        words = [w for s, _, _ in sents_all for w in words_of(for_count(s))]
        avg = len(words) / len(sents_all)
        syl = sum(syllables(w) for w in words) / max(1, len(words))
        grade = 0.39 * avg + 11.8 * syl - 15.59
        long_ = [(l, n, s) for s, l, n in sents_all if n > 25]
        stats.update({"avg_words_per_sentence": round(avg, 1), "grade": round(grade, 1),
                      "long_sentences": len(long_),
                      "long": [{"line": l, "words": n, "text": s} for l, n, s in long_]})
        if max_grade is not None and grade > max_grade:
            add("grade", None, "reading grade %.1f; aim for %.0f or lower (shorter sentences, shorter words)" % (grade, max_grade))

    terms, has_list = glossary_terms(text)
    plain_prose = re.sub(r"`[^`]*`", "X", prose)          # a word in inline code is a name, not prose
    used = sorted({j for j in JARGON if re.search(r"\b%s\b" % re.escape(j), plain_prose, re.I)})
    unexplained = [j for j in used
                   if not any(j == t or j.startswith(t) or t.startswith(j[:6]) or j in t.split() for t in terms)]
    stats["jargon_unexplained"] = unexplained
    if unexplained and (has_list or require_glossary):
        where = "its 'Words used here' list" if has_list else "a 'Words used here' list (none found)"
        add("glossary", None, "technical words not explained in %s: %s" % (where, ", ".join(unexplained)))

    findings.sort(key=lambda f: (f["line"] or 0, f["rule"]))
    stats["findings"] = findings
    stats["by_rule"] = {}
    for f in findings:
        stats["by_rule"][f["rule"]] = stats["by_rule"].get(f["rule"], 0) + 1
    warnings = ["%s%s: %s%s" % ("line %s " % f["line"] if f["line"] else "", f["rule"], f["message"],
                               (" | " + f["text"]) if f["text"] else "") for f in findings]
    return warnings, stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("files", nargs="+")
    p.add_argument("--dictionary", default=os.environ.get("STE100_DICTIONARY"),
                   help="your copy of the ASD-STE100 standard (PDF, or a text file of the PDF)")
    p.add_argument("--max-grade", type=float, default=9.0, help="warn above this reading grade (default 9)")
    p.add_argument("--only", help="comma-separated rule tags to report, for example length,id")
    p.add_argument("--require-glossary", action="store_true",
                   help="also warn when the file has no 'Words used here' list (for a design or a spec)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="exit 1 if there are findings")
    opts = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    dictionary = load_dictionary(opts.dictionary) if opts.dictionary else None
    only = set(opts.only.split(",")) if opts.only else None
    total, results = 0, {}
    for path in opts.files:
        with open(path, encoding="utf-8") as f:
            warnings, stats = check(f.read(), dictionary, opts.max_grade, opts.require_glossary)
        if only:
            stats["findings"] = [x for x in stats["findings"] if x["rule"] in only]
        results[path] = stats
        total += len(stats["findings"])
        if opts.json:
            continue
        if len(opts.files) > 1:
            print("== %s" % path)
        if stats.get("sentences"):
            print("writing: %(sentences)d sentences · %(avg_words_per_sentence)s words each on average · grade %(grade)s"
                  % stats + (" · STE dictionary on" if dictionary else " · STE dictionary off"))
        for f in stats["findings"]:
            print("WARN    %s%s: %s%s" % ("line %s " % f["line"] if f["line"] else "", f["rule"], f["message"],
                                         ("\n        | " + f["text"]) if f["text"] else ""))
        counts = " · ".join("%s %d" % kv for kv in sorted(stats["by_rule"].items()))
        print(("OBEYS THE GUIDELINES" if not stats["findings"] else "REWRITE THE FLAGGED PARTS (%s)" % counts))
    if opts.json:
        json.dump(results if len(opts.files) > 1 else results[opts.files[0]], sys.stdout, indent=2)
        sys.stdout.write("\n")
    if opts.strict and total:
        sys.exit(1)


if __name__ == "__main__":
    main()
