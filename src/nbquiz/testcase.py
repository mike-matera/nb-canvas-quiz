"""
Support for Notebook test banks.
"""

## TODO: Tighten up validation. Is it possible to get out of band failures on internal errors?
## TODO: Consider correctness and overrides for validation errors.
## TODO: Pretty print class names
## TODO: Document the question format.

import ast
import hashlib
import re
import textwrap
from collections.abc import Iterable
from typing import Callable
from unittest import TestCase

import nbtest


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
    # The attribute named will be put in `self.solution`
    # If None, `self.solution` will contain a CellCacheEntry
    name = None

    def __init__(self, tests=()):
        """
        Create the test instance. Failures here will be reported as exceptions in the notebook,
        not student-facing failures. Validation checks should be done here so that the stack
        traces have meaning for test developers.
        """
        super().__init__(tests)
        self.validate()
        try:
            self.solution_cell = nbtest.get(self._celltag)
        except KeyError:
            self.fail(f"I can't find a cell with the tag {self._celltag} in the docstring.")

    def setUp(self) -> None:
        """
        Validate the existence of the attribute `self.name` in the solution cell in
        `self.solution_cell`. Check for required and forbidden syntax. Guarantees
        that `self.solution` contains the attribute in `self.name`. If `self.name`
        is `None` then `self.solution` contains the same as `self.solution_cell`.
        """

        alltokens = set((t.__class__ for t in ast.walk(self.solution_cell.tree)))

        assert all(
            {token in alltokens for token in self.tokens_required}
        ), """The solution is missing required syntax."""

        if self.tokens_forbidden:
            assert not any(
                {token in alltokens for token in self.tokens_forbidden}
            ), """The solution uses forbidden syntax."""

        if self.name is not None:
            assert (
                self.name.startswith("_")
                or self.name in self.solution_cell.assignments
                or self.name in self.solution_cell.functions
                or self.name in self.solution_cell.classes
            ), f"""The name {self.name} has not been defined."""
            assert self.name in self.solution_cell.ns, f"""{self.name} is not defined."""
            self.solution = self.solution_cell.ns[self.name]
        else:
            self.solution = self.solution_cell

        return super().setUp()

    @classmethod
    def validate(cls):
        """
        The validate() method should check any an all class variables for correctness.
        Failures in validate() will be reported with stack traces in test cells.
        """
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

        error = None
        try:
            cls.__doc__.format(**{item: getattr(cls, item) for item in dir(cls)})
        except KeyError as e:
            error = e
        assert not error, f"""The question text references a variable {error} that is not present in the class definition."""

    @classmethod
    def question(cls):
        """Return the Markdown of a test question."""
        cls.validate()
        return textwrap.dedent("""
        {}

        Add the tag `{}` to the docstring in your solution cell.
        """).format(
            textwrap.dedent(cls.__doc__).format(
                **{item: f"""`{getattr(cls, item)}`""" for item in dir(cls)}
            ),
            cls._celltag,
        )

    @classmethod
    def variant(cls, classname=None, extra_bases=None, **params):
        """Create a variant of a test question."""
        cls.validate()
        m = hashlib.sha1()
        m.update(cls.__name__.encode("utf-8"))
        for name, value in params.items():
            m.update(f"""{name}:{value}""".encode("utf-8"))

        if not classname:
            classname = f"""{cls.__name__}_{m.hexdigest()[0:4]}"""

        class_locals = dict(**cls.__dict__)
        class_locals.update(params)

        bases = cls.__bases__
        if extra_bases:
            bases = bases + tuple(extra_bases)

        newtype = type(classname, bases, class_locals)
        newtype.validate()
        return newtype


class FunctionQuestion(TestQuestion):
    """
    A class that validates that functions behave as expected.

    The following are checked:

        1. The name has been defined as a function.
        2. The arguments have the right names and are in the right order.
        3. Returns a wrapper so that calls can be checked for return type.

    """

    # Required: A dictionary of type annotations similar to the ones
    # returned by `inspect.get_annotations()`
    annotations = None

    def setUp(self):
        super().setUp()
        assert isinstance(
            self.solution, Callable
        ), f"""{self.name} is not a function (did you redefine it?)."""
        assert self.annotations is not None, """annotations cannot be none in a FunctionQuestion."""

        if not self.name.startswith("_"):
            # Ignore my internal functions.
            assert self.name in self.solution_cell.functions, f"""{self.name} is not a function."""
            assert (
                self.solution_cell.functions[self.name].docstring is not None
            ), f"""The function {self.name} has no docstring."""

            argnames = [arg for arg in self._resolve_annotations() if arg != "return"]
            assert len(argnames) == len(
                self.solution_cell.functions[self.name].arguments
            ), f"""The function {self.name} has the wrong number of arguments."""
            for i, arg in enumerate(argnames):
                assert (
                    arg == self.solution_cell.functions[self.name].arguments[i]
                ), f"""The argument "{self.solution_cell.functions[self.name].arguments[i]}" is misspelled or in the wrong place."""

        inner_function = self.solution

        def _wrapper(*args, **kwargs):
            rval = inner_function(*args, **kwargs)
            assert isinstance(
                rval, self.annotations["return"]
            ), f"""The function {self.name} returned {rval} not a {self.annotations["return"]}"""
            return rval

        # Wrap the solution function.
        self.solution = _wrapper

    @classmethod
    def _resolve_annotations(cls):
        formatted = {}
        for an, typ in cls.annotations.items():
            if (m := re.match(r"^\s*{\s*(\S+)\s*}\s*$", an)) is not None:
                assert hasattr(
                    cls, m.group(1)
                ), f"""The annotation dictionary references "{m.group(1)}" but the class does not have a matching variable."""
                formatted[getattr(cls, m.group(1))] = typ
            else:
                formatted[an] = typ
        return formatted

    @classmethod
    def validate(cls):
        assert cls.name is not None, """The `name` attribute is required in a FunctionQuestion."""
        cls._resolve_annotations()
        return super().validate()


class CellQuestion(FunctionQuestion):
    """
    Create a cell-based variant of a function question.
    """

    def setUp(self):
        # Validate that the cell defines the required variables.
        argnames = [arg for arg in self._resolve_annotations() if arg != "return"]
        for name in argnames:
            assert (
                name in self.solution_cell.assignments
            ), f"""The variable "{name}" was never assigned."""

        # Create a wrapper function in the user's namespace.
        def _cell_wrapper(*args, **kwargs):
            updates = {name: args[i] for i, name in enumerate(argnames)}
            updates.update(kwargs)
            result = self.solution_cell.run(updates)
            return result.result

        self.solution_cell.ns["_cell_wrapper"] = _cell_wrapper
        super().setUp()

    @classmethod
    def validate(cls):
        # Override the symbol name to use the cell-based wrapper.
        cls.name = "_cell_wrapper"
        return super().validate()
