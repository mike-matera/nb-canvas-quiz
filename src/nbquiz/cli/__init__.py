"""
Command line tools for nbquiz.
"""

import argparse
import importlib
import logging
import pathlib
from pathlib import Path

from .. import testbank

subcommands = {
    file.stem: importlib.import_module(f".{file.stem}", package=__package__)
    for file in pathlib.Path(__file__).parent.glob("*.py")
    if str(file) != __file__
}

parser = argparse.ArgumentParser(
    prog="nbquiz",
    description="Do various things with nbtest.",
    epilog="See help on subcommands.",
)

parser.add_argument(
    "-t",
    "--testbank",
    required=True,
    help="A path that will be recursively searched for testbank files.",
)

subparsers = parser.add_subparsers(help="subcommand help", required=True)
for command in subcommands:
    subparser = subparsers.add_parser(command, help=subcommands[command].__doc__)
    subcommands[command].add_args(subparser)
    subparser.set_defaults(func=subcommands[command].main)


def main():
    global parser, args
    args = parser.parse_args()

    # Load the tesbanks for subcommands.
    tb = testbank.TestBank()
    tb.load(*Path(args.testbank).glob("**/*.ipynb"))
    logging.info(f"""Loaded {tb.stats()["questions"]} questions.""")

    # Call the subcommand.
    return args.func(args, tb)


if __name__ == "__main__":
    exit(main())
