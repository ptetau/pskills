# wordfreq

wordfreq counts the words in a text file and prints each word with its count. The most
common word comes first.

## Use

```
python3 -m wordfreq notes.txt
```

Each line has a word, a space, and the count. Words that appear the same number of times
are in alphabetical order. wordfreq ignores case. A word has letters and apostrophes.

If wordfreq cannot read the file, it prints `error: cannot read <path>` to standard error
and exits with code 2.

## Test

```
python3 -m unittest discover -s tests
```
