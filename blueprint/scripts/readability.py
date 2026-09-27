#!/usr/bin/env python3
"""Check that a design document or blueprint reads in plain English.

The target reader is a bright 10-year-old: short sentences, common words, and every
technical word explained. Only prose is measured. Code blocks, `inline code`, tables,
headings, and diagrams are skipped, because names and code must stay exact.

Reports:
  - average words per sentence (aim for 15 or fewer)
  - sentences over 25 words (aim for none), with the longest ones to rewrite
  - Flesch-Kincaid grade level of the prose (aim for 7 or lower)
  - technical words used in the prose but not explained in a "Words used here" list

Everything here is advice: it prints WARN lines and never fails a build on its own.
The same file ships with /decompose and /blueprint.

Usage:
  python readability.py notifications.design.md
  python readability.py notifications.blueprint.md --json
"""

import argparse
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

FENCE = re.compile(r"^```.*?^```", re.M | re.S)


def prose_of(text):
    text = FENCE.sub("\n", text)
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith(("#", "|", ">", "<!--")) or re.match(r"^[-=*_]{3,}$", s):
            lines.append("")          # keep paragraph breaks
            continue
        if re.match(r"^([-*+]|\d+\.)\s+", s):
            lines.append("")          # each list item is its own sentence
        s = re.sub(r"^[-*+]\s+|^\d+\.\s+", "", s)              # list markers
        s = re.sub(r"`[^`]*`", "X", s)                           # names count as one short word
        s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)            # links keep their text
        s = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", s)       # emphasis
        lines.append(s)
    return "\n".join(lines)


def sentences_of(prose):
    out = []
    for para in re.split(r"\n\s*\n", prose):
        para = " ".join(para.split())
        if not para:
            continue
        for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", para):
            words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", sent)
            if len(words) >= 3:
                out.append((sent, words))
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
    prose = prose_of(text)
    sents = sentences_of(prose)
    words = [w for _, ws in sents for w in ws]
    stats = {"sentences": len(sents), "words": len(words)}
    warnings = []
    if not sents:
        return warnings, stats
    avg = len(words) / len(sents)
    syl = sum(syllables(w) for w in words) / len(words)
    grade = 0.39 * avg + 11.8 * syl - 15.59
    long = sorted(((len(ws), s) for s, ws in sents if len(ws) > 25), reverse=True)
    stats.update({"avg_words_per_sentence": round(avg, 1), "grade": round(grade, 1),
                  "long_sentences": len(long)})
    if avg > 15:
        warnings.append("average sentence is %.1f words; aim for 15 or fewer" % avg)
    if grade > 7:
        warnings.append("reading grade is %.1f; aim for 7 or lower (shorter sentences, shorter words)" % grade)
    for n, s in long[:5]:
        warnings.append("long sentence (%d words): %s" % (n, s[:140] + ("…" if len(s) > 140 else "")))
    if len(long) > 5:
        warnings.append("%d more sentences over 25 words" % (len(long) - 5))

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
