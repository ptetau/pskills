"""The wordfreq command: print how often each word appears in a file."""
import sys

from wordfreq.counter import count_words


def main(argv=None, stdout=None, stderr=None):
    argv = sys.argv[1:] if argv is None else argv
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    if len(argv) != 1:
        print("usage: wordfreq FILE", file=stderr)
        return 2
    path = argv[0]
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        print("error: cannot read " + path, file=stderr)
        return 2
    for word, count in count_words(text):
        print(word + " " + str(count), file=stdout)
    return 0
