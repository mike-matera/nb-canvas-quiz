"""
Execute the checker on a test question from STDIN.
"""

import logging
import subprocess
import sys
import tempfile
from importlib.resources import files
from pathlib import Path

import nbformat

from nbquiz.testbank import bank

logging.basicConfig(level=logging.INFO)


def add_args(parser):
    pass


def cell_for_tag(nb, tag):
    return [
        cell
        for cell in nb.cells
        if "metadata" in cell and "tags" in cell["metadata"] and tag in cell["metadata"]["tags"]
    ][0]


def has_error(cell):
    return cell["outputs"] and any(["ename" in output for output in cell["outputs"]])


def get_error(cell):
    for output in cell["outputs"]:
        if "ename" in output:
            return output["ename"], output["evalue"]
    raise ValueError("No error in get_error():", cell)


def get_html(cell):
    for output in cell["outputs"]:
        if "data" in output and "text/html" in output["data"]:
            return output["data"]["text/html"]
    raise ValueError(f"No html in get_html(): {cell}")


def main(args):
    # Slurp stdin until EOF
    student_code = sys.stdin.read()

    # Load the notebook template.
    template_file = files("nbquiz.resources").joinpath("test-notebook-template.ipynb").read_text()
    nb = nbformat.reads(template_file, as_version=nbformat.NO_CONVERT)

    student_cell = cell_for_tag(nb, "student")
    student_cell["source"] = student_code

    testbank_cell = cell_for_tag(nb, "testbank")
    for path in bank.paths:
        testbank_cell["source"] += f"""\nbank.add_path("{path}")"""
    testbank_cell["source"] += """\nbank.load()"""

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
        student_cell = cell_for_tag(nb, "student")
        testbank_cell = cell_for_tag(nb, "testbank")
        runner_cell = cell_for_tag(nb, "runner")
        checker_cell = cell_for_tag(nb, "checker")

        if has_error(student_cell):
            # Error executing student code.
            rval = 10
            ename, evalue = get_error(student_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(testbank_cell):
            # Inernal test error (should this ever happen?)
            rval = 11
            ename, evalue = get_error(testbank_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(runner_cell):
            # Internal test error (should this ever happen?)
            rval = 12
            ename, evalue = get_error(runner_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(checker_cell):
            # Test failure
            rval = 13
            print(get_html(runner_cell))

        else:
            print(get_html(runner_cell))

        return rval
