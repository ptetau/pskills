#!/usr/bin/env python3
"""Tests for check_writing.py. Run: python test_check_writing.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_writing  # noqa: E402

# (text, rule that must be found, or None when no finding is permitted)
CASES = [
    ("Run the tests and then read every line of the log, and after that write a summary of the failures for the team.", "length"),
    ("The checker reads the design file and compares each part of the design with the parts that the blueprint gives in section five of the text.", "length"),
    ("Run the tests. Read the log.", None),
    ("The first part reads the file; the second part writes it.", "semicolon"),
    ("Don't run the tests.", "contraction"),
    ("The user's file is open.", None),
    ("Use short words, e.g. 'use'.", "latin"),
    ("The agent has merged the branch.", "tense"),
    ("The agent is running the tests.", "tense"),
    ("The file is missing.", None),
    ("When running the tests, read the log.", "tense"),
    ("The file should have been updated.", "tense"),
    ("The log is read by the checker.", "passive"),
    ("The file must be updated.", "passive"),
    ("Set up the project.", "phrasal"),
    ("Make sure the tests pass.", "that"),
    ("Make sure that the tests pass.", None),
    ("Utilize the cache.", "word"),
    ("The tests failed.\n\nIt is now fixed.", "reference"),
    ("Do you want B1 or B3?", "id"),
    ("Do you want B1 (keep the cache) or B3 (remove the cache)?", None),
    ("The rubric has items R1, R2, … in order.", None),
    ("R3 Exactly one option is marked.", None),
    ('The rubric has R3 "one option marked".', None),
    ('Do not write "Don\'t do it, e.g. now". Write "Do it now".', None),
    ("The C4 model has four levels.", None),
    ("- **Verify:** `npm test` runs the suite.", None),
    ("The skill keeps the behavior of the old version.", "spelling"),
    ("Organize the files.", "spelling"),
    ("The file size is small.", None),
    ("The `color` field holds the colour.", None),
    ("Each paragraph has a topic. A paragraph has one topic. Write short text. The text is clear. "
     "The words are short. The reader is happy. The end is near.", "paragraph"),
]


def main():
    failed = 0
    for text, rule in CASES:
        _, stats = check_writing.check(text, max_grade=None)
        rules = {f["rule"] for f in stats["findings"]}
        ok = (rule in rules) if rule else not rules
        if not ok:
            failed += 1
            print("FAIL  expected %s, got %s: %s" % (rule or "no finding", sorted(rules) or "none", text[:70]))
    print("%d of %d cases pass" % (len(CASES) - failed, len(CASES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
