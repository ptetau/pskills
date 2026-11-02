#!/usr/bin/env python3
"""Write the structured outputs of pdlc: commits, handoffs, header fields, and specs.

Usage: python3 pdlc/bin/pdlc.py <subcommand> [options]

Subcommands: commit, message, handoff, stop, set, intent, change.

Exit codes, for every subcommand:
  0  done
  1  a contract problem (one line for each problem, and nothing written)
  2  a usage error
  3  a git error
  4  not a pdlc project

Each subcommand is registered here and answers "not implemented" until its code is added
to HANDLERS.
"""
import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # do not leave a __pycache__ in pdlc/bin of the project
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pdlclib  # noqa: E402,F401  (the handlers use it)

EXIT_DONE, EXIT_CONTRACT, EXIT_USAGE, EXIT_GIT, EXIT_NOT_PROJECT = 0, 1, 2, 3, 4

SUBCOMMANDS = {
    "commit": "make a pdlc commit with its subject and one trailer block",
    "message": "print the message of a pdlc commit, and make no commit",
    "handoff": "write the handoff of a stage",
    "stop": "write a stop record and commit it",
    "set": "set header fields and statuses of an intent or a change",
    "intent": "make a new intent, or change the lists of an intent",
    "change": "make the spec of a new change",
}


def not_implemented(name):
    def handler(args, extra):
        print("pdlc.py %s: not implemented" % name)
        return EXIT_USAGE
    return handler


# One handler for each subcommand: handler(args, extra) -> exit code. `args` is the parsed
# namespace, and `extra` is the list of arguments that the subcommand parser did not know.
HANDLERS = {name: not_implemented(name) for name in SUBCOMMANDS}


def build_parser():
    parser = argparse.ArgumentParser(prog="pdlc.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True, metavar="subcommand")
    for name, text in SUBCOMMANDS.items():
        sub.add_parser(name, help=text, description=text)
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args, extra = build_parser().parse_known_args(argv)
    return HANDLERS[args.command](args, extra)


if __name__ == "__main__":
    sys.exit(main())
