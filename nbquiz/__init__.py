"""
Support for Notebook test banks.
"""

import textwrap
import typing
from unittest import TestCase

import nbtest

TypeHints = typing.Mapping[str, typing.Any]
FunctionInfo = typing.NamedTuple("FunctionInfo", [("name", str), ("annotations", TypeHints)])


class TestQuestion(TestCase):
    """Base class for test questions."""

    # These lists are advisory. They can be used for
    # selection and they can optionally used to validate
    # solutions.
    tokens_required = []
    tokens_forbidden = []

    # String tags that can be used to select questions for a test.
    tags = []


class FunctionTestCase(TestQuestion):
    """
    A base class that has helpers for function based test questions.
    """

    func_info: FunctionInfo

    @classmethod
    def validate(cls):
        assert hasattr(cls, "func_info"), """Function tests must have the "func_info" attribute."""
        assert isinstance(
            cls.func_info, FunctionInfo
        ), """The func_info attribute must be a FunctionInfo"""
        # assert isinstance(cls.func_info.annotations, TypeHints), """The "annotations" attribute of func_info must be TypeHints"""

    def setUp(self) -> None:
        """Checks for the function."""
        self.validate()
        cell_tag = "@" + type(self).__name__
        solution = nbtest.get(cell_tag)
        if solution is None:
            self.fail(f"I can't find a cell with the tag {cell_tag}")

        if self.func_info.name not in solution.functions:
            self.fail(f"""I can't find a function named "{self.func_info.name}" """)

        # Copy the function into this namespace. This is the equivalent of importing the function.
        globals()[self.func_info.name] = solution.ns[self.func_info.name]

        return super().setUp()

    @staticmethod
    def format_type(t):
        tstr = str(t)
        tstr = tstr.replace("typing.", "")
        return tstr

    @classmethod
    def question(cls):
        cls.validate()
        doc = textwrap.dedent(cls.__doc__)
        doc += f"""\nFunction name: `{cls.func_info.name}`:\n\n"""
        doc += """Arguments:\n\n"""
        for arg in list(cls.func_info.annotations)[:-1]:
            doc += f"""  - `{arg}`: `{cls.format_type(cls.func_info.annotations[arg])}`\n"""
        doc += f"""\nReturns: `{cls.format_type(cls.func_info.annotations["return"])}`\n\n"""
        return doc


class CellTestCase(FunctionTestCase):
    """
    Make a function test case into a cell test case by having the user create variables
    with the same names as arguments and have the cell result in the return value.
    """

    def setUp(self) -> None:
        self.validate()
        cell_tag = "@" + type(self).__name__
        solution = nbtest.get(cell_tag)
        if solution is None:
            self.fail(f"I can't find a cell with the tag {cell_tag}")

        # FIXME: This should also support kwargs
        def wrapper(*args):
            args = {
                name: args[n]
                for n, name in enumerate(self.func_info.annotations)
                if name != "return"
            }
            result = solution.run(args)
            return result.result

        solution.ns[self.func_info.name] = wrapper

        # Copy the function into this namespace. This is the equivalent of importing the function.
        globals()[self.func_info.name] = solution.ns[self.func_info.name]

        # return super(TestCase).setUp()

    @classmethod
    def question(cls):
        # Avoid printing the function definition.
        return textwrap.dedent(cls.__doc__)
