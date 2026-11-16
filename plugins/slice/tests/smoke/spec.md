# Spec: wordfreq

Status: ratified

## Purpose

A small Python module, `wordfreq`, that counts the words of a text and lists the most common ones.

## Decisions

- D1 (case): words are compared in lower case.
- D2 (words): a word is a run of letters and apostrophes. Everything else separates words.
- D3 (ties): words with the same count are listed in alphabetical order.
- D4 (stack): Python 3 and unittest, a module `wordfreq` in `src/wordfreq.py`.

## Requirements

- R1 (count): `count(text)` returns a dict from each word to its count. For "The cat, the hat." it returns {"the": 2, "cat": 1, "hat": 1}.
- R2 (top): `top(text, n)` returns the n most common words as a list of (word, count) pairs, by count from high to low, ties in alphabetical order (D3).
- R3 (bad n): `top(text, n)` raises ValueError with the message "n must be at least 1" when n is below 1.

## Out of scope

- A command line, files, and other languages.
