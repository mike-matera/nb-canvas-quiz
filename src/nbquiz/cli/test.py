"""
Execute the checker on a test question from STDIN.
"""

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

import nbformat

logging.basicConfig(level=logging.INFO)


def add_args(parser):
    parser.add_argument(
        "-c", "--celltag", required=True, help="The cell tag belonging to the test."
    )


def main(args, tb):
    # Slurp stdin until EOF
    student_code = sys.stdin.read()

    # Construct a notebook:
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("%load_ext nbtest"))
    nb.cells.append(nbformat.v4.new_code_cell(student_code))
    bank = tb._questions[args.celltag]
    nb.cells.append(nbformat.v4.new_code_cell(bank["source"]))
    nb.cells.append(
        nbformat.v4.new_code_cell(f"""%%testing {args.celltag[1:]}
nbtest_cases = [{args.celltag[1:]}]
""")
    )
    nb.cells.append(
        nbformat.v4.new_code_cell("""import nbtest
nbtest.assert_ok()""")
    )

    # Execute the notebook
    with tempfile.TemporaryDirectory() as td:
        with open(Path(td) / "output.ipynb", "w") as fh:
            nbformat.write(nb, fh)

        result = subprocess.run(
            """jupyter execute --inplace --allow-errors --timeout 2 --startup_timeout 4 output.ipynb""",
            shell=True,
            capture_output=True,
            cwd=td,
            encoding="utf-8",
        )

        logging.info(result.stderr)

        # Read the notebook
        with open(Path(td) / "output.ipynb") as fh:
            nb = nbformat.read(fh, nbformat.NO_CONVERT)

        # Check for errors
        rval = 0
        if nb.cells[1]["outputs"] and "ename" in nb.cells[1]["outputs"][0]:
            # Error executing student code.
            rval = 1
            print(
                f"""{nb.cells[1]["outputs"][0]["ename"]}: {nb.cells[1]["outputs"][0]["evalue"]}"""
            )

        elif nb.cells[4]["outputs"] and "ename" in nb.cells[4]["outputs"][0]:
            # Test failure
            rval = 2
            print(nb.cells[3]["outputs"][0]["data"]["text/html"])

        elif "ename" in nb.cells[3]["outputs"][0]:
            # Test error (should this ever happen?)
            rval = 3
            print(
                f"""{nb.cells[3]["outputs"][0]["ename"]}: {nb.cells[3]["outputs"][0]["evalue"]}"""
            )
        else:
            print(nb.cells[3]["outputs"][0]["data"]["text/html"])

        return rval
