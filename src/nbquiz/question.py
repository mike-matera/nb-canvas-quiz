"""
Support for Notebook test banks.
"""

## NB: Canvas cannot have question groups inside of groups. This system,
##     similarly need only support a single level of hierarchy.
## TODO: Document the question format.

import ast
import hashlib
import re
import textwrap
import typing
from collections import UserList
from collections.abc import Iterable
from typing import Callable
from unittest import TestCase

from jinja2 import Environment, PackageLoader, select_autoescape

import nbtest

_template_env = Environment(
    loader=PackageLoader("nbquiz", package_path="resources"),
    autoescape=select_autoescape(),
    trim_blocks=True,
)


class TestQuestion(TestCase):
    """Base class for test questions."""

    # These lists are advisory. They can be used for
    # selection and they can optionally used to validate
    # solutions.
    tokens_required = []
    tokens_forbidden = []

    # Docstring must be present.
    __doc__: str

    def __init__(self, tests=()):
        """
        Create the test instance. Failures here will be reported as exceptions in the notebook,
        not student-facing failures. Validation checks should be done here so that the stack
        traces have meaning for test developers.
        """
        super().__init__(tests)
        self.validate()
        self.solution_cell = None

        doctags = nbtest.tags()
        celltag = self.celltag()
        nametag = self.cellid()

        if celltag in doctags:
            self.solution_cell = nbtest.get(celltag)
        elif nametag in doctags:
            self.solution_cell = nbtest.get(nametag)
        else:
            self.fail(f"I can't find a solution with the tag {self.celltag()}.")

    def setUp(self) -> None:
        """
        Check for required and forbidden syntax. Guarantees that `self.solution_cell`
        contains the TagCacheEntry with the solution inside.
        """

        alltokens = set((t.__class__ for t in ast.walk(self.solution_cell.tree)))

        assert all(
            {token in alltokens for token in self.tokens_required}
        ), """The solution is missing required syntax."""

        if self.tokens_forbidden:
            assert not any(
                {token in alltokens for token in self.tokens_forbidden}
            ), """The solution uses forbidden syntax."""

        return super().setUp()

    @classmethod
    def cellid(cls):
        """
        Return the class name in tag format.
        """
        return f"@{cls.__name__}"

    @classmethod
    def celltag(cls):
        """Produce a unique, opaque identifier for this test question."""
        m = hashlib.sha1()
        prefix = cls.__name__[0].lower() + "".join(
            [ll.lower() for ll in cls.__name__[1:] if ll.isupper()]
        )
        m.update(cls.__name__.encode("utf-8"))
        return f"@{prefix}-{m.hexdigest()[:4]}"

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
        error = None
        try:
            cls.__doc__.format(**{item: getattr(cls, item) for item in dir(cls)})
        except KeyError as e:
            error = e
        assert not error, f"""The question text references a variable {error} that is not present in the class definition."""

    @classmethod
    def _template_values(cls):
        values = {item: str(getattr(cls, item)) for item in dir(cls)}
        values.update(
            {
                "celltag": cls.celltag(),
                "cellid": cls.cellid(),
            }
        )
        values["question"] = textwrap.dedent(cls.__doc__).strip().format(**values)
        return values

    @classmethod
    def question(cls):
        """Return the Markdown of a test question."""
        cls.validate()
        return _template_env.get_template("question_template.md").render(**cls._template_values())

    @classmethod
    def variant(cls, classname=None, extra_bases=None, **params):
        """Create a variant of a test question."""
        cls.validate()
        m = hashlib.sha1()
        m.update(cls.__name__.encode("utf-8"))
        for name, value in params.items():
            m.update(f"""{name}:{value}""".encode("utf-8"))

        if classname is None:
            classname = f"""{cls.__name__}_{m.hexdigest()[0:4]}"""

        class_locals = dict(**cls.__dict__)
        class_locals.update(params)

        bases = cls.__bases__
        if extra_bases:
            bases = bases + tuple(extra_bases)

        newtype = type(classname, bases, class_locals)
        newtype.validate()
        return newtype


class QuestionGroup(UserList):
    """
    A collection of questions that are grouped together for the purpose
    of test randomization. During a quiz students will receive one of
    the questions in the group at random. A QuestionGroup is a good way
    to support multiple variations of a test question.
    """

    def __init__(self, init):
        super().__init__(init)

    ## TODO: What are the functions of this class?
    ## should the be a union or intersection of components?

    def validate(self):
        for q in self.data:
            q.validate()


class FunctionQuestion(TestQuestion):
    """
    A class that validates that functions behave as expected.

    The following are checked:

        1. The name has been defined as a function.
        2. The arguments have the right names and are in the right order.
        3. Returns a wrapper so that calls can be checked for return type.

    """

    # Required: The name of the solution function. The function will
    # be put in `self.solution` by the framework code.
    name: str

    # Required: A dictionary of type annotations similar to the ones
    # returned by `inspect.get_annotations()`
    annotations = None

    def __init__(self, tests=()):
        super().__init__(tests)
        self.solution_cell: nbtest.tagcache.TagCacheEntry

    def setUp(self):
        super().setUp()

        assert self.name in self.solution_cell.ns, f"""{self.name} is not defined."""
        self.solution = self.solution_cell.ns[self.name]

        assert isinstance(
            self.solution, Callable
        ), f"""{self.name} is not a function (did you redefine it?)."""

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
            if self.annotations["return"] is None:
                assert rval is None, f"""The function {self.name} returned {rval} instead of None"""
            elif self.annotations["return"] is typing.Any:
                pass
            else:
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
        assert hasattr(
            cls, "annotations"
        ), """The attribute `annotations` is required in a FunctionQuestion"""
        assert isinstance(
            cls.annotations, dict
        ), """The `annotations` attribute must be a dictionary"""
        assert (
            "return" in cls.annotations
        ), """The `annotations` dictionary must contain the "return" key."""
        cls._resolve_annotations()
        return super().validate()

    @classmethod
    def _template_values(cls):
        values = super()._template_values()
        values["annotations"] = cls._resolve_annotations()
        return values

    @classmethod
    def question(cls):
        cls.validate()
        values = cls._template_values()
        return _template_env.get_template("function_question_template.md").render(**values)


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
            # Make sure this wrapper produces the same STDOUT that the cell would.
            print(result.stdout)
            return result.result

        self.solution_cell.ns["_cell_wrapper"] = _cell_wrapper
        super().setUp()

    @classmethod
    def validate(cls):
        # Override the symbol name to use the cell-based wrapper.
        cls.name = "_cell_wrapper"
        return super().validate()

    @classmethod
    def question(cls):
        cls.validate()
        values = cls._template_values()
        return _template_env.get_template("cell_question_template.md").render(**values)


class ClassQuestion(TestQuestion):
    """
    A class that validates solution classes.

    The following are checked:

        1. The name has been defined as a class.
    """

    def setUp(self):
        # Validate that the cell defines the required class.
        assert self.name in self.solution_cell.ns, f"""{self.name} is not defined."""
        self.solution = self.solution_cell.ns[self.name]

        assert isinstance(
            self.solution, type
        ), f"""{self.name} is not a class (did you redefine it?)."""

        if not self.name.startswith("_"):
            # Ignore my internal classes.
            assert self.name in self.solution_cell.classes, f"""{self.name} is not a class."""
            assert (
                self.solution_cell.classes[self.name].docstring is not None
            ), f"""The class {self.name} has no docstring."""

        super().setUp()
