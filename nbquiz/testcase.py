"""
Support for Notebook test banks.
"""

import ast
import hashlib
import textwrap
from collections.abc import Iterable
from typing import Callable
from unittest import TestCase

import nbtest
from nbtest.tagcache import TagCacheEntry


class TestQuestion(TestCase):
    """Base class for test questions."""

    # These lists are advisory. They can be used for
    # selection and they can optionally used to validate
    # solutions.
    tokens_required = []
    tokens_forbidden = []

    # String tags that can be used to select questions for a test.
    tags = []

    # Define what tag selects this question, defaults to the class name.
    celltag = None

    # The name of an attribute in the notebook namespace to test.
    # This name will be valid in the test as if it had been imported.
    # None skips any import.
    name = None

    def setUp(self) -> None:
        """Checks for the function."""
        self.validate_class()
        try:
            self.solution = nbtest.get(self._celltag)
        except KeyError:
            self.fail(f"I can't find a cell with the tag {self._celltag} in the docstring.")

        alltokens = set((t.__class__ for t in ast.walk(self.solution.tree)))

        assert all(
            {token in alltokens for token in self.tokens_required}
        ), """The solution is missing required syntax."""

        if self.tokens_forbidden:
            assert not any(
                {token in alltokens for token in self.tokens_forbidden}
            ), """The solution uses forbidden syntax."""

        self.solution = self.validate_instance(self.solution)

        return super().setUp()

    def validate_instance(self, solution: TagCacheEntry) -> any:
        """Validate the existence of a symbol (or do nothing if it's None)"""
        if self.name is not None:
            # Find a symbol and return it.
            assert (
                self.name.startswith("_")
                or self.name in solution.assignments
                or self.name in solution.functions
                or self.name in solution.classes
            ), f"""The name {self.name} has not been defined."""
            assert self.name in solution.ns, f"""{self.name} is not defined."""
            return solution.ns[self.name]
        else:
            # Return the TagCacheEntry
            return solution

    @classmethod
    def validate_class(cls):
        assert isinstance(
            cls.tokens_required, Iterable
        ), f"""`tokens_required` must be iterable, not a {cls.tokens_required.__class__}"""
        assert isinstance(
            cls.tokens_forbidden, Iterable
        ), f"""`tokens_forbidden` must be iterable, not a {cls.tokens_forbidden.__class__}"""
        assert isinstance(
            cls.tags, Iterable
        ), f"""`tags` must be iterable, not a {cls.tags.__class__}"""
        if cls.celltag is None:
            cls._celltag = f"@{cls.__name__}"
        else:
            cls._celltag = cls.celltag

    @classmethod
    def question(cls):
        cls.validate_class()
        return textwrap.dedent("""
        {}

        Add the tag `{}` to the docstring in your solution cell.
        """).format(
            textwrap.dedent(cls.__doc__).format(
                **{item: getattr(cls, item) for item in dir(cls) if not item.startswith("__")}
            ),
            cls._celltag,
        )

    @classmethod
    def variant(cls, **params):
        m = hashlib.sha1()
        m.update(cls.__name__.encode("utf-8"))
        for name, value in params.items():
            m.update(f"""{name}:{value}""".encode("utf-8"))

        if "classname" not in params:
            classname = f"""{cls.__name__}{m.hexdigest()[0:4]}"""
        else:
            classname = params["classname"]

        if "celltag" not in params:
            params["celltag"] = f"@{classname}"

        class_locals = dict(**cls.__dict__)
        class_locals.update(params)
        return type(classname, cls.__bases__, class_locals)


class FunctionQuestion(TestQuestion):
    """
    A class that validates that functions behave as expected.

    The following are checked:

        1. The name has been defined as a function.
        2. The arguments have the right names and are in the right order.
        3. Returns a wrapper so that calls can be checked for return values.

    """

    annotations = None

    @classmethod
    def validate_class(cls):
        assert cls.name is not None, """The `name` attribute is required in a FunctionQuestion."""
        for attr in cls.annotations:
            if attr != "return" and attr.strip().startswith("{"):
                assert hasattr(
                    cls, attr[1:-1].strip()
                ), f"""Annotations expect the parameter {attr} but it's not defined in {cls}"""

        return super().validate_class()

    def validate_instance(self, solution: TagCacheEntry):
        attr = super().validate_instance(solution)
        assert isinstance(
            attr, Callable
        ), f"""{self.name} is not a function (did you redefine it?)."""
        assert self.annotations is not None, """annotations cannot be none in a FunctionQuestion."""

        if not self.name.startswith("_"):
            # Ignore my internal functions.
            assert self.name in solution.functions, f"""{self.name} is not a function."""
            assert (
                solution.functions[self.name].docstring is not None
            ), f"""The function {self.name} has no docstring."""
            args = self.annotations.copy()
            del args["return"]
            assert len(args) == len(
                solution.functions[self.name].arguments
            ), f"""The function {self.name} has the wrong number of arguments."""
            for i, arg in enumerate(args):
                if arg.strip().startswith("{"):
                    arg = getattr(self, arg[1:-1].strip())
                assert (
                    arg == solution.functions[self.name].arguments[i]
                ), f"""The argument "{solution.functions[self.name].arguments[i]}" is misspelled or in the wrong place."""

        def _wrapper(*args, **kwargs):
            rval = attr(*args, **kwargs)
            assert isinstance(
                rval, self.annotations["return"]
            ), f"""The function {self.name} returned {rval} not a {self.annotations["return"]}"""
            return rval

        return _wrapper

    # @staticmethod
    # def format_type(t):
    #    tstr = str(t)
    #    tstr = tstr.replace("typing.", "")
    #    return tstr

    # @classmethod
    # def question(cls):
    #    cls.validate()
    #    doc = textwrap.dedent(cls.__doc__).format(**cls._params())
    #    doc += f"""\nFunction name: `{cls.func_info.name}`:\n\n"""
    #    doc += """Arguments:\n\n"""
    #    for arg in list(cls.func_info.annotations)[:-1]:
    #        doc += f"""- `{arg}`: `{cls.format_type(cls.func_info.annotations[arg])}`\n"""
    #    doc += f"""\nReturns: `{cls.format_type(cls.func_info.annotations["return"])}`\n\n"""
    #    return doc


class CellQuestion(FunctionQuestion):
    """
    Create a cell-based variant of a function question.
    """

    @classmethod
    def validate_class(cls):
        cls.name = "_cell_wrapper"
        return super().validate_class()

    def validate_instance(self, solution):
        # Create a wrapper function in the user's namespace.
        def _cell_wrapper(*args, **kwargs):
            updates = {}
            for i, arg in enumerate(self.annotations):
                if arg != "return":
                    if arg.strip().startswith("{"):
                        updates[getattr(self, arg[1:-1].strip())] = args[i]
                    else:
                        updates[arg] = args[i]

            updates.update(kwargs)
            result = solution.run(updates)
            return result.result

        solution.ns["_cell_wrapper"] = _cell_wrapper
        return super().validate_instance(solution)
