"""
Test a question from STDIN
"""

import argparse
import logging
import sys
from pathlib import Path

import nbformat

from .. import testbank

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(
    prog="nbquiz test",
    description="Execute the checker on a test question.",
    epilog="Parts of the nbquiz cli.",
)

parser.add_argument(
    "-t",
    "--testbank",
    required=True,
    help="A path that will be recursively searched for testbank files.",
)
parser.add_argument("-c", "--celltag", required=True, help="The cell tag belonging to the test.")
args = parser.parse_args()


def main():
    global args
    tb = testbank.TestBank()
    tb.load(*Path(args.testbank).glob("**/*.ipynb"))

    logging.info(f"Loaded {tb.stats()["questions"]} questions.")

    # Slurp stdin until EOF
    student_code = sys.stdin.read()

    # Construct a notebook:
    nb = nbformat.v4.new_notebook()

    nb.cells.append(nbformat.v4.new_code_cell("%load_ext nbtest"))

    nb.cells.append(nbformat.v4.new_code_cell(student_code))

    bank = tb._questions[args.celltag]
    nb.cells.append(nbformat.v4.new_code_cell(bank["source"]))

    nb.cells.append(
        nbformat.v4.new_code_cell(f"""
%%testing {args.celltag}
nbtest_cases = [{args.celltag}]
""")
    )

    with open("output.ipynb", "w") as fh:
        nbformat.write(nb, fh)


if __name__ == "__main__":
    exit(main())
