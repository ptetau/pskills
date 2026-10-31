#!/usr/bin/env python3
"""pdlc stdin check. Claude Code runs this before every Bash call.

A Bash call that runs `cat > FILE` with no heredoc waits for input. The input does not come,
so the call hangs until the Bash tool stops it. This hook finds such a command and blocks the
call before it starts. Exit 2 shows the reason to Claude, with the way to write the file.

The hook knows five command words:
  - `cat` reads standard input when it has no file operand, or when an operand is `-`.
  - `tee` always reads it.
  - `python`, `python3`, `python3.N` and `node` read it when they have no argument, or when
    an argument `-` comes before the script.
A command has input when a pipe feeds it, or when it has an input redirect (`<`, `<<`,
`<<<`). The body of a heredoc is not part of the command, so its text does not count. A
reader inside a group that gets a pipe or a redirect also has input. The hook cannot see
where a group ends, so it lets the call run.

When in doubt, the hook lets the call run. A hang that it misses costs time. A call that it
blocks by mistake costs one turn. So the call runs when the hook cannot parse the command,
when a word is in quotes, and outside a pdlc project (a folder that holds pdlc/config.md).
"""
import json
import os
import re
import sys

ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
# Words that come before the command word, or wrap it. The hook looks past them.
SKIP = {"!", "{", "}", "if", "then", "else", "elif", "do", "while", "until", "time", "exec",
        "command", "nohup", "env"}
# A command that starts with one of these runs a group of commands. A command that is one of
# the ENDS closes a group.
GROUPS = {"{", "while", "until", "for", "if", "case"}
ENDS = {"done", "}", "fi", "esac"}
INTERPRETER = re.compile(r"^(?:python(?:3(?:\.\d+)?)?|node)$")
CANDIDATE = re.compile(r"\b(?:cat|tee|python[\d.]*|node)\b")
SUBSTITUTION = "$()"  # the word that stands for the output of $(...) or <(...)
# The longest operator first.
REDIRECTS = ("<<<", "<<-", "<<", "<>", "<&", "<", ">>", ">&", ">|", ">")
MESSAGE = ("pdlc: `%s` reads standard input, but this Bash call gives it no input. The call "
           "waits until the Bash tool stops it. Write the file with the Write tool, or put the "
           "text in a heredoc: `cat > FILE <<'EOF'`, then the lines, then `EOF`.")


def project_root(path):
    """The nearest folder at or above path that holds pdlc/config.md, or None."""
    path = os.path.realpath(path)
    while True:
        if os.path.isfile(os.path.join(path, "pdlc", "config.md")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def tokenize(text):
    """The tokens of a shell command. ValueError when a quote or a bracket stays open.

    A token is one of:
      ("word", text)   a word, with its quotes removed
      ("redir", op)    a redirect operator: the next word is its target
      ("sep",)         ; && || & or a newline: the next command starts
      ("pipe",)        | or |&: the next command gets the output of this one
      ("open", sub)    ( or $( or <( or a backtick. sub is True when its output is a word
      ("close",)       the close of an open
    The body of each heredoc is skipped. Text in quotes is part of a word, except $( ... )
    inside double quotes: that gives open and close tokens."""
    toks, word, started = [], [], False
    stack = []        # what is open: '"', ')' for ( or $( or <(, and '`' for a backtick
    heredocs = []     # (end word, strip tabs) of each heredoc whose body starts at the next newline
    delimiter = None  # after << or <<-: the next word is the end word (True for <<-)
    i, n = 0, len(text)

    def flush():
        nonlocal started, delimiter
        if not started:
            return
        value = "".join(word)
        del word[:]
        started = False
        if delimiter is not None:
            heredocs.append((value, delimiter))
            delimiter = None
        toks.append(("word", value))

    while i < n:
        c = text[i]
        if stack and stack[-1] == '"':  # inside double quotes
            if c == '"':
                stack.pop()
                i += 1
            elif c == "\\" and text[i + 1:i + 2] in ("$", "`", '"', "\\", "\n"):
                if text[i + 1] != "\n":
                    word.append(text[i + 1])
                    started = True
                i += 2
            elif text.startswith("$(", i):
                if word:
                    flush()
                started = False
                toks.append(("open", True))
                stack.append(")")
                i += 2
            else:
                word.append(c)
                started = True
                i += 1
        elif c in " \t":
            flush()
            i += 1
        elif c == "\n":
            flush()
            toks.append(("sep",))
            delimiter = None
            i += 1
            for end, dash in heredocs:  # skip the body of each heredoc
                while i < n:
                    j = text.find("\n", i)
                    line = text[i:] if j < 0 else text[i:j]
                    i = n if j < 0 else j + 1
                    if (line.lstrip("\t") if dash else line) == end:
                        break
            del heredocs[:]
        elif c == "\\":
            if text[i + 1:i + 2] != "\n":
                word.append(text[i + 1:i + 2])
                started = True
            i += 2
        elif c == "'":
            j = text.find("'", i + 1)
            if j < 0:
                raise ValueError("a single quote stays open")
            word.append(text[i + 1:j])
            started = True
            i = j + 1
        elif c == '"':
            stack.append('"')
            started = True
            i += 1
        elif text.startswith("$'", i):
            j = i + 2
            while j < n and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                raise ValueError("a $' quote stays open")
            word.append(text[i + 2:j])
            started = True
            i = j + 1
        elif text.startswith(("$(", "<(", ">("), i):
            flush()
            toks.append(("open", True))
            stack.append(")")
            i += 2
        elif c == "`":
            flush()
            if stack and stack[-1] == "`":
                stack.pop()
                toks.append(("close",))
            else:
                stack.append("`")
                toks.append(("open", True))
            i += 1
        elif c == "(":
            flush()
            toks.append(("open", False))
            stack.append(")")
            i += 1
        elif c == ")":
            flush()
            if stack and stack[-1] == ")":
                stack.pop()
            toks.append(("close",))
            i += 1
        elif c == "#" and not started:  # a comment runs to the end of the line
            while i < n and text[i] != "\n":
                i += 1
        elif c == ";":
            flush()
            toks.append(("sep",))
            delimiter = None
            i += 1
        elif c == "|":
            flush()
            if text.startswith("||", i):
                toks.append(("sep",))
                i += 2
            else:
                toks.append(("pipe",))
                i += 2 if text.startswith("|&", i) else 1
        elif c == "&" and not text.startswith("&>", i):
            flush()
            toks.append(("sep",))
            i += 2 if text.startswith("&&", i) else 1
        elif c in "<>&":  # a redirect: < or > or &>
            if c == "&":
                flush()
                op = "&>>" if text.startswith("&>>", i) else "&>"
            else:
                if started and "".join(word).isdigit():
                    del word[:]  # the number of a file descriptor, as in 2>&1
                    started = False
                else:
                    flush()
                op = next(o for o in REDIRECTS if text.startswith(o, i))
            toks.append(("redir", op))
            if op in ("<<", "<<-"):
                delimiter = op == "<<-"
            i += len(op)
        else:
            word.append(c)
            started = True
            i += 1
    flush()
    if stack:
        raise ValueError("a quote or a bracket stays open")
    return toks


class Simple:
    """One simple command: its words, and whether it has input."""

    def __init__(self, piped=False):
        self.words = []
        self.piped = piped
        self.input = piped
        self.target = False  # the next word is the target of a redirect
        self.ends_group = False  # it is done, }, fi, esac, or a ( ... ) that closed


def parse(toks):
    """(simple commands, grouped). grouped is True when a group of commands gets a pipe or an
    input redirect, as in `cmd | { ...; }` or `while ...; done < list`. The hook cannot tell
    which commands are in that group."""
    done, waiting, cur = [], [], Simple()
    grouped = False

    def finish():
        nonlocal grouped
        done.append(cur)
        if cur.piped and cur.words and cur.words[0] in GROUPS:
            grouped = True

    for tok in toks:
        kind = tok[0]
        if kind == "word":
            if cur.target:
                cur.target = False
            else:
                cur.ends_group = cur.ends_group or (not cur.words and tok[1] in ENDS)
                cur.words.append(tok[1])
        elif kind == "redir":
            cur.target = True
            if tok[1].startswith("<"):
                cur.input = True
                grouped = grouped or cur.ends_group
        elif kind in ("sep", "pipe"):
            if kind == "sep" and cur.piped and not cur.words:
                continue  # a newline after | goes on with the pipe
            finish()
            cur = Simple(piped=kind == "pipe")
        elif kind == "open":
            grouped = grouped or (cur.piped and not cur.words and not tok[1])
            waiting.append((cur, tok[1]))
            cur = Simple()
        else:  # close
            finish()
            if waiting:
                cur, sub = waiting.pop()
                if not sub:
                    cur.ends_group = not cur.words
                elif cur.target:
                    cur.target = False
                else:
                    cur.words.append(SUBSTITUTION)
            else:
                cur = Simple()
    finish()
    done.extend(outer for outer, _ in waiting)
    return done, grouped


def command_of(words):
    """The words from the command word on, after the assignments and the wrapper words."""
    i = 0
    while i < len(words):
        if words[i] in SKIP or ASSIGNMENT.match(words[i]):
            i += 1
        elif words[i] == "timeout":
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 2 if words[i] in ("-k", "-s") else 1  # these two options take a value
            i += 1  # the time limit
        else:
            break
    return words[i:]


def reads_input(words):
    """True when a command with these words reads standard input."""
    if not words:
        return False
    name, args = os.path.basename(words[0]), words[1:]
    if name == "tee":
        return True
    if name == "cat":
        end = args.index("--") if "--" in args else len(args)  # after -- every word is a file
        files = [a for a in args[:end] if not a.startswith("-")] + args[end + 1:]
        return "-" in args or not files
    if INTERPRETER.match(name):
        for arg in args:
            if arg == "-":
                return True
            if not arg.startswith("-"):
                return False  # a script, or the code of -c, or a module
        return not args
    return False


def waiting_command(command):
    """The text of the first command that waits for input that it does not get, or None."""
    if not CANDIDATE.search(command):
        return None
    commands, grouped = parse(tokenize(command.replace("\r\n", "\n")))
    if grouped:
        return None
    for simple in commands:
        words = command_of(simple.words)
        if not simple.input and reads_input(words):
            return " ".join(words)[:60]
    return None


def main():
    try:
        call = json.load(sys.stdin)
        command = call["tool_input"]["command"]
    except (ValueError, KeyError, TypeError):
        return 0
    if call.get("tool_name") != "Bash" or not isinstance(command, str):
        return 0
    root = project_root(call.get("cwd") or os.getcwd())
    if not root:
        return 0
    try:
        found = waiting_command(command)
    except Exception:  # a command that the hook cannot parse goes through
        return 0
    if not found:
        return 0
    print(MESSAGE % found, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
