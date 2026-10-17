#!/usr/bin/env python3
"""Check a /quiz-visual spec, and the page that was rendered from it.

Usage:
  python3 check_quiz.py SPEC.json [PAGE.html]

It checks these things:
  1. The spec is valid. (The rules are in render_quiz.py and references/spec.md.)
  2. The words that the agent wrote follow the writing guidelines. These are the intro, each
     question, each option sentence, each piece of evidence, and each caption. A finding is a
     WARN. Fix each WARN. The words inside a sample, a mockup, or a demo are not checked,
     because they show the words that the user will see in the real work.
  3. A question where each option has the preview kind "none" is a WARN. It must be a choice
     that has no visual difference. If the options differ in how they look, sound, or work,
     show the difference.
  4. The page (when you give it) holds the same questions as the spec, has an input and a
     label for each option, has no duplicate ID, has a sandbox on each frame, and loads
     nothing from the network except the fonts.

Output: one line for each ERROR or WARN, then PASS or FAIL. An ERROR gives FAIL.
The exit code is 1 for FAIL and 0 for PASS. Standard library only.
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_writing  # noqa: E402
import render_quiz  # noqa: E402

FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
MAX_PAGE = 4_000_000


def prose_fields(spec):
    """Yield (where, text) for each text that the agent wrote as prose."""
    yield "intro", spec.get("intro", "")
    for q in spec.get("questions", []):
        qid = q.get("id", "?")
        yield "question '%s'" % qid, q.get("question", "")
        if q.get("evidence"):
            yield "question '%s' evidence" % qid, q["evidence"]
        for o in q.get("options", []):
            yield "option '%s/%s'" % (qid, o.get("id", "?")), o.get("text", "")
            cap = (o.get("preview") or {}).get("caption")
            if cap:
                yield "option '%s/%s' caption" % (qid, o.get("id", "?")), cap


def check_spec(spec):
    errors = ["ERROR %s" % e for e in render_quiz.validate(spec)]
    warns = []
    if errors:
        return errors, warns
    for where, text in prose_fields(spec):
        if not text.strip():
            continue
        _, stats = check_writing.check(text, max_grade=None)
        for f in stats["findings"]:
            if f["rule"] == "glossary":
                continue
            warns.append("WARN %s: %s (%s)" % (where, f["message"], f["rule"]))
    for q in spec["questions"]:
        if all(o["preview"]["kind"] == "none" for o in q["options"]):
            warns.append("WARN question '%s': no option has a preview. Show the difference, or confirm that the options do not differ in how they look, sound, or work." % q["id"])
    return errors, warns


def check_page(spec, page):
    errors = []
    if len(page.encode("utf-8")) > MAX_PAGE:
        errors.append("ERROR page: larger than %d bytes." % MAX_PAGE)
    m = re.search(r'<script type="application/json" id="quiz-spec">(.*?)</script>', page, re.S)
    if not m:
        return errors + ["ERROR page: the embedded spec is missing."]
    try:
        embedded = json.loads(m.group(1))
    except ValueError:
        return errors + ["ERROR page: the embedded spec is not valid JSON."]
    want = [(q["id"], [o["id"] for o in q["options"]]) for q in spec["questions"]]
    have = [(q["id"], [o["id"] for o in q["options"]]) for q in embedded.get("questions", [])]
    if want != have:
        errors.append("ERROR page: the questions in the page are different from the spec.")
    ids = re.findall(r'\bid="([^"]+)"', page)
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append("ERROR page: the id '%s' is used two times." % dup)
    for q in spec["questions"]:
        for o in q["options"]:
            iid = "%s--%s" % (q["id"], o["id"])
            if 'id="%s"' % iid not in page or 'for="%s"' % iid not in page:
                errors.append("ERROR page: option '%s' has no input and label." % iid)
    for tag in re.findall(r"<iframe\b[^>]*>", page):
        if "sandbox=" not in tag:
            errors.append("ERROR page: a frame has no sandbox.")
    outer = re.sub(r'srcdoc="[^"]*"', "", page)
    outer = re.sub(r'<script type="application/json".*?</script>', "", outer, flags=re.S)
    outer = re.sub(r'xmlns(?::\w+)?="[^"]*"', "", outer)
    for url in sorted(set(re.findall(r"(?:src|href)=\"(https?://[^\"]+)\"", outer))):
        if not any(h in url for h in FONT_HOSTS):
            errors.append("ERROR page: it loads %s. Only the fonts may load from the network." % url)
    if re.search(r"<script[^>]+src=", outer):
        errors.append("ERROR page: a script loads from a file or the network.")
    return errors


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    try:
        spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("Cannot read the spec: %s" % e)
        return 2
    errors, warns = check_spec(spec)
    if not errors and len(args) > 1:
        errors += check_page(spec, Path(args[1]).read_text(encoding="utf-8"))
    for line in errors + warns:
        print(line)
    if not errors:
        n = len(spec["questions"])
        kinds = sorted({o["preview"]["kind"] for q in spec["questions"] for o in q["options"]} - {"none"})
        print("quiz-visual: %d questions · previews: %s · %d writing warnings" % (n, ", ".join(kinds) or "none", len(warns)))
    print("FAIL" if errors else "PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
