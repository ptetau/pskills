#!/usr/bin/env python3
"""Check that a design document or blueprint reads in plain English.

The target reader is a bright 10-year-old: short sentences, common words, and every
technical word explained. Only prose is measured. Code blocks, `inline code`, tables,
headings, and diagrams are skipped, because names and code must stay exact.

Reports:
  - average words per sentence (aim for 15 or fewer)
  - every sentence over 25 words (aim for none), with its line number
  - Flesch-Kincaid grade level of the prose (aim for 7 or lower)
  - technical words used in the prose but not explained in a "Words used here" list

Everything here is advice: it prints WARN lines and never fails a build on its own.
The same file ships with /decompose and /blueprint.

Usage:
  python readability.py notifications.design.md
  python readability.py notifications.blueprint.md --json
"""

import argparse
import bisect
import json
import re
import sys

# Words a 10-year-old won't know. Each must be explained in the document's
# "Words used here" list if the prose uses it.
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

FENCE = re.compile(r"^(`{3,})[^\n]*\n.*?^\1`*[ \t]*$", re.M | re.S)   # a ```` fence may hold ``` lines


def prose_map(text):
    """(prose, line_of): the prose, and a function from a prose offset to its source line."""
    text = FENCE.sub(lambda m: "\n" * m.group(0).count("\n"), text)   # keep line numbers
    lines, starts, offset = [], [], 0

    def emit(s, lineno):
        nonlocal offset
        starts.append((offset, lineno))
        lines.append(s)
        offset += len(s) + 1

    for lineno, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if not s or s.startswith(("#", "|", ">", "<!--")) or re.match(r"^[-=*_]{3,}$", s):
            emit("", lineno)          # keep paragraph breaks
            continue
        if re.match(r"^([-*+]|\d+\.)\s+", s):
            emit("", lineno)          # each list item is its own sentence
        s = re.sub(r"^[-*+]\s+|^\d+\.\s+", "", s)              # list markers
        s = re.sub(r"`[^`]*`", "X", s)                           # names count as one short word
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)            # links keep their text
        s = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", s)       # emphasis
        emit(s, lineno)
    keys = [o for o, _ in starts]

    def line_of(off):
        return starts[max(0, bisect.bisect_right(keys, off) - 1)][1] if starts else None
    return "\n".join(lines), line_of


def prose_of(text):
    return prose_map(text)[0]


def sentences_of(prose, line_of=None):
    """[(sentence, words, source line or None)] for sentences of 3 words or more."""
    out, start = [], 0
    for brk in list(re.finditer(r"\n\s*\n", prose)) + [None]:
        end = brk.start() if brk else len(prose)
        para, base = prose[start:end], start
        start = brk.end() if brk else end
        s0 = 0
        for cut in [c.end() for c in re.finditer(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", para)] + [len(para)]:
            raw, at = para[s0:cut], base + s0
            s0 = cut
            sent = " ".join(raw.split())
            words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", sent)
            if len(words) >= 3:
                at += len(raw) - len(raw.lstrip())
                out.append((sent, words, line_of(at) if line_of else None))
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


def check(text):
    prose, line_of = prose_map(text)
    sents = sentences_of(prose, line_of)
    words = [w for _, ws, _ in sents for w in ws]
    stats = {"sentences": len(sents), "words": len(words)}
    warnings = []
    if not sents:
        return warnings, stats
    avg = len(words) / len(sents)
    syl = sum(syllables(w) for w in words) / len(words)
    grade = 0.39 * avg + 11.8 * syl - 15.59
    long = [(line, len(ws), s) for s, ws, line in sents if len(ws) > 25]
    stats.update({"avg_words_per_sentence": round(avg, 1), "grade": round(grade, 1),
                  "long_sentences": len(long),
                  "long": [{"line": line, "words": n, "text": s} for line, n, s in long]})
    if avg > 15:
        warnings.append("average sentence is %.1f words; aim for 15 or fewer" % avg)
    if grade > 7:
        warnings.append("reading grade is %.1f; aim for 7 or lower (shorter sentences, shorter words)" % grade)
    for line, n, s in long:
        warnings.append("line %s: long sentence (%d words): %s" % (line, n, s[:140] + ("…" if len(s) > 140 else "")))

    terms, has_list = glossary_terms(text)
    used = sorted({j for j in JARGON if re.search(r"\b%s\b" % re.escape(j), prose, re.I)})
    unexplained = [j for j in used
                   if not any(j == t or j.startswith(t) or t.startswith(j[:6]) or j in t.split() for t in terms)]
    stats["jargon_unexplained"] = unexplained
    if unexplained:
        where = "its 'Words used here' list" if has_list else "a 'Words used here' list (none found)"
        warnings.append("technical words not explained in %s: %s" % (where, ", ".join(unexplained)))
    return warnings, stats


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    opts = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    with open(opts.file, encoding="utf-8") as f:
        text = f.read()
    warnings, stats = check(text)
    if opts.json:
        json.dump({"warnings": warnings, "stats": stats}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    if stats.get("sentences"):
        print("plain English: %(sentences)d sentences · %(avg_words_per_sentence)s words each on average · "
              "grade %(grade)s · %(long_sentences)d over 25 words" % stats)
    for w in warnings:
        print("WARN    " + w)
    print("READS PLAINLY" if not warnings else "REWRITE THE FLAGGED PARTS")


if __name__ == "__main__":
    main()
