"""
Support for Notebook test banks.
"""

## NB: Canvas cannot have question groups inside of groups. This system,
##     similarly need only support a single level of hierarchy.
## TODO: Document the question format.

## FIXME: When accessing a parameter with `ClassName.param` you seem to get
## the Parameter instance. When accessing with `self.param` you seem to get
## the value as expected. Figure this out.

import ast
import hashlib
import os
import re
import textwrap
import typing
from collections import UserList
from collections.abc import Iterable
from typing import Callable, get_type_hints
from unittest import TestCase

import nb_unittest
from jinja2 import (
    Environment,
    PackageLoader,
    StrictUndefined,
    UndefinedError,
    select_autoescape,
)

_template_env = Environment(
    loader=PackageLoader("nbquiz", package_path="resources"),
    autoescape=select_autoescape(),
    trim_blocks=True,
    undefined=StrictUndefined,
)


def plain_filter(input):
    """
    A Jinja filter that enables the selection of parameter representations.
    """
    if not isinstance(input, Parameter):
        return input
    return input.value()


def literal_filter(input):
    """
    A Jinja filter that enables the selection of parameter representations.
    """
    if not isinstance(input, Parameter):
        return f"`{input}`"
    assert input._type == "literal", """Non literal can't be converted."""
    return str(input)


_template_env.filters["plain"] = plain_filter
_template_env.filters["literal"] = literal_filter


class Parameter(property):
    """A parameter is a read-only property with representation information."""

    def __init__(self, value, typ="literal", attrs=None):
        super().__init__(lambda self: value)
        self._value = value
        self._type = typ
        self._attrs = attrs

    def value(self):
        return self._value

    def __str__(self):
        """The default representation is a literal."""
        attr_str = ""
        if self._attrs is not None:
            attr_str = f"{{{self._attrs}}}"

        if self._type == "literal":
            return f"`{self._value}`{attr_str}"
        elif self._type == "span":
            return f"[{self._value}]{attr_str}"
        else:
            raise ValueError(
                f"""type must be "literal" or "span" not {self._type}"""
            )


class _QuestionValidator(type):
    """Metaclass for questions to make validation happen during a test definition."""

    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)
        if (
            cls.__name__ not in cls.abstract_bases
            and not cls.__name__.startswith("_")
        ):
            # Only validate if this is not an ABC
            cls.validate()


class TestQuestion(TestCase, metaclass=_QuestionValidator):
    """Base class for test questions."""

    # These lists are advisory. They can be used for
    # selection and they can optionally used to validate
    # solutions.
    tokens_required = []
    tokens_forbidden = []

    # Docstring must be present.
    __doc__: str

    # Subclasses should add their name to avoid having the base class validated.
    abstract_bases: list[str] = ["TestQuestion"]

    def __init__(self, tests=()):
        """
        Create the test instance. Failures here will be reported as exceptions in the notebook,
        not student-facing failures. Validation checks should be done here so that the stack
        traces have meaning for test developers.
        """
        super().__init__(tests)
        self.solution_cell = None

        doctags = nb_unittest.tags()
        celltag = self.celltag()
        nametag = self.cellid()

        if celltag in doctags:
            self.solution_cell = nb_unittest.get(celltag)
        elif nametag in doctags:
            self.solution_cell = nb_unittest.get(nametag)
        else:
            self.fail(
                f"I can't find a solution with the tag {self.celltag()}."
            )

    def setUp(self) -> None:
        """
        Check for required and forbidden syntax. Guarantees that `self.solution_cell`
        contains the TagCacheEntry with the solution inside.
        """

        alltokens = set(
            (t.__class__ for t in ast.walk(self.solution_cell.tree))
        )

        assert all({token in alltokens for token in self.tokens_required}), (
            """The solution is missing required syntax."""
        )

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
        """
        Produce a unique, opaque identifier for this test question.
        """
        m = hashlib.sha1()
        prefix = cls.__name__[0].lower() + "".join(
            [
                ll.lower()
                for ll in cls.__name__[1:]
                if ll.isupper() or ll.isdigit() or ll == "_"
            ]
        )
        m.update(cls.__name__.encode("utf-8"))
        return f"@{prefix}-{m.hexdigest()[:4]}"

    @classmethod
    def validate(cls):
        """
        The validate() method should check any an all class variables for correctness.
        Failures in validate() will be reported in the cell where a test class is
        defined.
        """
        assert isinstance(cls.tokens_required, Iterable), (
            f"""`tokens_required` must be iterable, not a {cls.tokens_required.__class__}"""
        )
        assert isinstance(cls.tokens_forbidden, Iterable), (
            f"""`tokens_forbidden` must be iterable, not a {cls.tokens_forbidden.__class__}"""
        )

        # Generate the _params dictionary
        cls._params = {}
        for attr in get_type_hints(cls):
            if not attr.startswith("_") and attr != "abstract_bases":
                value = getattr(cls, attr)
                if not isinstance(value, Parameter):
                    # Wrap plain-value parameters
                    p = Parameter(value)
                    setattr(cls, attr, p)
                    cls._params[attr] = p
                else:
                    cls._params[attr] = value

        # Test-render the question to make sure all template values are present
        try:
            cls.question()
        except UndefinedError as e:
            raise ValueError(f"The template value {e}. Check your parameters.")

    @classmethod
    def template_values(cls):
        """
        Generate a dictionary of values to be passed in to the question rendering template.
        The following key/value pairs will be present:

            - param: value -- All parameters named by the question and their values
            - "celltag": value -- The result of celltag()
            - "cellid": value -- The result of cellid()
            - "question": value -- The rendered question text

        Subclasses should override this to add or change parameters as needed.
        """
        values = {
            "celltag": cls.celltag(),
            "cellid": cls.cellid(),
        }
        values.update(cls._params)
        if cls.__doc__ is not None:
            temp = _template_env.from_string(
                textwrap.dedent(cls.__doc__).strip()
            )
            values["question"] = temp.render(**values)
        else:
            values["question"] = ""

        return values

    @classmethod
    def question(cls):
        """Return the Markdown of a test question."""
        return _template_env.get_template("question_template.md").render(
            **cls.template_values()
        )

    @classmethod
    def variant(cls, classname=None, **params):
        """Create a variant of a test question."""

        # Generate a derived class name.
        if classname is None:
            if not params:
                raise ValueError(
                    "The variant parameters can not be empty when no classname is specified."
                )
            classname = (
                cls.__name__
                + "_"
                + "_".join([f"{k}:{v}" for k, v in params.items()])
            )

        m = hashlib.sha1()
        m.update(classname.encode("utf-8"))

        class_locals = dict(**cls.__dict__)
        class_locals.update(params)

        newtype = type(classname, cls.__bases__, class_locals)
        return newtype


class QuestionGroup(UserList):
    """
    A collection of questions that are grouped together for the purpose
    of test randomization. During a quiz students will receive one of
    the questions in the group at random. A QuestionGroup is a good way
    to support multiple variations of a test question.
    """

    def __init__(self, name="QuestionGroup", pick=1, init=None):
        self.__name__ = name
        self.pick = pick
        super().__init__(init)


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

    # I'm abstract
    abstract_bases = TestQuestion.abstract_bases + ["FunctionQuestion"]

    def __init__(self, tests=()):
        super().__init__(tests)
        self.solution_cell: nb_unittest.tagcache.TagCacheEntry

    def setUp(self):
        super().setUp()

        assert self.name in self.solution_cell.ns, (
            f"""{self.name} is not defined."""
        )
        self.solution = self.solution_cell.ns[self.name]

        assert isinstance(self.solution, Callable), (
            f"""{self.name} is not a function (did you redefine it?)."""
        )

        if not self.name.startswith("_"):
            # Subclasses can disable arg name checks of wrappers.
            assert self.name in self.solution_cell.functions, (
                f"""{self.name} is not a function."""
            )
            assert (
                self.solution_cell.functions[self.name].docstring is not None
            ), f"""The function {self.name} has no docstring."""

            argnames = [
                arg.value() if isinstance(arg, Parameter) else arg
                for arg in self.resolve_annotations()
                if arg != "return"
            ]
            assert len(argnames) == len(
                self.solution_cell.functions[self.name].arguments
            ), (
                f"""The function {self.name} has the wrong number of arguments."""
            )
            for i, arg in enumerate(argnames):
                funcarg = self.solution_cell.functions[self.name].arguments[i]
                if os.environ.get("NBQUIZ_STRICT") is not None or (
                    not funcarg.startswith("_") and not funcarg.endswith("_")
                ):
                    assert arg == funcarg, (
                        f"""The argument "{funcarg}" is misspelled or in the wrong place."""
                    )

        inner_function = self.solution

        def _wrapper(*args, **kwargs):
            rval = inner_function(*args, **kwargs)
            if self.annotations["return"] is None:
                assert rval is None, (
                    f"""The function {self.name} returned {rval} instead of None"""
                )
            elif self.annotations["return"] is typing.Any:
                pass
            else:
                assert isinstance(rval, self.annotations["return"]), (
                    f"""The function {self.name} returned {rval} not a {self.annotations["return"]}"""
                )

            return rval

        # Wrap the solution function.
        self.solution = _wrapper

    @classmethod
    def resolve_annotations(cls):
        """
        Generate the true annotations dictionary by resolving keys that have
        the "{parameter}" syntax. This enables the ability to have variations
        with different parameter names.
        """
        formatted = {}
        for an, typ in cls.annotations.items():
            if (m := re.match(r"^\s*{\s*(\S+)\s*}\s*$", an)) is not None:
                pname = m.group(1)
                pvalue = cls._params[pname]
                assert isinstance(pvalue.value(), str), (
                    f"""Parameters that name function arguments must be strings but "{pname}" is an {pvalue.value().__class__}"""
                )
                assert pname in cls._params, (
                    f"""The annotation dictionary references "{pname}" but the class does not have a matching variable."""
                )
                formatted[pvalue] = typ
            else:
                # Check for a missed template value.
                assert an not in cls._params, (
                    f"""Annotation argument "{an}" matches a class attribute {an} == "{getattr(cls, an)}". Did you mean "{{{an}}}"?"""
                )
                formatted[an] = typ

        return formatted

    @classmethod
    def template_values(cls):
        values = super().template_values()
        values["annotations"] = cls.resolve_annotations()
        return values

    @classmethod
    def validate(cls):
        super().validate()
        assert cls.name is not None, (
            """The `name` attribute is required in a FunctionQuestion."""
        )
        assert hasattr(cls, "annotations"), (
            """The attribute `annotations` is required in a FunctionQuestion"""
        )
        assert isinstance(cls.annotations, dict), (
            """The `annotations` attribute must be a dictionary"""
        )
        assert "return" in cls.annotations, (
            """The `annotations` dictionary must contain the "return" key."""
        )
        cls.resolve_annotations()

    @classmethod
    def question(cls):
        values = cls.template_values()
        return _template_env.get_template(
            "function_question_template.md"
        ).render(**values)


class CellQuestion(FunctionQuestion):
    """
    Create a cell-based variant of a function question.
    """

    # I'm abstract
    abstract_bases = FunctionQuestion.abstract_bases + ["CellQuestion"]

    def setUp(self):
        # Validate that the cell defines the required variables.
        argnames = [
            arg.value() if isinstance(arg, Parameter) else arg
            for arg in self.resolve_annotations()
            if arg != "return"
        ]
        for name in argnames:
            assert name in self.solution_cell.assignments, (
                f"""The variable "{name}" was never assigned."""
            )

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
        cls.name = "_cell_wrapper"
        return super().validate()

    @classmethod
    def question(cls):
        values = cls.template_values()
        return _template_env.get_template("cell_question_template.md").render(
            **values
        )


class ClassQuestion(TestQuestion):
    """
    A class that validates solution classes.

    The following are checked:

        1. The name has been defined as a class.
    """

    # I'm abstract
    abstract_bases = TestQuestion.abstract_bases + ["ClassQuestion"]

    def setUp(self):
        super().setUp()

        # Validate that the cell defines the required class.
        assert self.name in self.solution_cell.ns, (
            f"""{self.name} is not defined."""
        )
        self.solution = self.solution_cell.ns[self.name]

        assert isinstance(self.solution, type), (
            f"""{self.name} is not a class (did you redefine it?)."""
        )

        if not self.name.startswith("_"):
            # Ignore my internal classes.
            assert self.name in self.solution_cell.classes, (
                f"""{self.name} is not a class."""
            )
            assert (
                self.solution_cell.classes[self.name].docstring is not None
            ), f"""The class {self.name} has no docstring."""
            # Ignore my internal classes.
            assert self.name in self.solution_cell.classes, (
                f"""{self.name} is not a class."""
            )
            assert (
                self.solution_cell.classes[self.name].docstring is not None
            ), f"""The class {self.name} has no docstring."""
