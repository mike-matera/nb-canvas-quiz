"""
Command line tools for nbquiz.
"""

import argparse
import importlib
import pathlib

from nbquiz.testbank import bank

subcommands = {
    file.stem: importlib.import_module(f".{file.stem}", package=__package__)
    for file in pathlib.Path(__file__).parent.glob("*.py")
    if str(file) != __file__
}

parser = argparse.ArgumentParser(
    prog="nbquiz",
    description="Do various things with nb_unittest.",
    epilog="See help on subcommands.",
)

parser.add_argument(
    "-t",
    "--testbank",
    required=False,
    help="A comma separated list of paths that will be searched for test bank files.",
)

subparsers = parser.add_subparsers(help="subcommand help", required=True)
for command in subcommands:
    subparser = subparsers.add_parser(
        command, help=subcommands[command].__doc__
    )
    subcommands[command].add_args(subparser)
    subparser.set_defaults(func=subcommands[command].main)


def main():
    global parser, args
    args = parser.parse_args()

    # Load the tesbanks for subcommands.
    if args.testbank is not None:
        for b in args.testbank.split(","):
            bank.add_path(b)

    # Call the subcommand.
    return args.func(args)


if __name__ == "__main__":
    exit(main())
