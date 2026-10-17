"""Count the words of a text."""
import re

WORD = re.compile(r"[a-z']+")


def count_words(text):
    """Return (word, count) pairs, most common first. Equal counts sort by word."""
    counts = {}
    for word in WORD.findall(text.lower()):
        counts[word] = counts.get(word, 0) + 1
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
