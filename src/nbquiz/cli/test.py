"""
Execute the checker on a test question from STDIN. The basic process is:

1. Read a code snippet from STDIN
2. Construct a notebook containing the code snippet
3. Execute the notebook with jupyter
4. Parse the notebook for result values
5. Write results to STDOUT

Security notes:

Student code runs in the jupyter process. The use of STDIN/STDOUT and
return values reduces the attack surface between this utility an the
server that executes it. Any non-zero exit of this utility will be interpreted
as a test failure.

TODO: Use unshare() if possible to limit access to the file system
TODO: Enable auditing in the interpreter running jupyter
TODO: Parse and validate student code.

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

# gRPC limits messages to 4MB. That's small enough to prevent the server
# from crashing but student code should never be that big. Set a reasonable
# limit.
QUESTION_SIZE_MAX: int = 4096


def add_args(parser):
    pass


def cell_for_tag(nb, tag):
    return [
        cell
        for cell in nb.cells
        if "metadata" in cell
        and "tags" in cell["metadata"]
        and tag in cell["metadata"]["tags"]
    ][0]


def has_error(cell):
    return cell["outputs"] and any(
        ["ename" in output for output in cell["outputs"]]
    )


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

    if len(student_code) > QUESTION_SIZE_MAX:
        raise ValueError("Student code exceeds the maximum.")

    # Load the notebook template.
    template_file = (
        files("nbquiz.resources")
        .joinpath("test-notebook-template.ipynb")
        .read_text()
    )
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
            # Error is in the student code cell. (Normal error.)
            rval = 10
            ename, evalue = get_error(student_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(testbank_cell):
            # The error is in the testbank. This errors should be logged
            # on the server but not passed back to the user.
            rval = 100
            ename, evalue = get_error(testbank_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(runner_cell):
            # The runner cell has an error. This this might have feedback for
            # the test developer and it might have feedback for the student
            # (Normal error.)
            rval = 11
            ename, evalue = get_error(runner_cell)
            print(f"""{ename}: {evalue}""")

        elif has_error(checker_cell):
            # A test has failed. (Normal error.)
            rval = 12
            print(get_html(runner_cell))

        else:
            print(get_html(runner_cell))

        return rval
