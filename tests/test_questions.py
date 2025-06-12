"""
Test cases for ubquiz.question classes.
"""

from unittest import TestCase

from nbquiz.question import FunctionQuestion, Parameter, TestQuestion


class T1(TestCase):
    """Test the TestQuestion base class."""

    def test_simple(self):
        """Verify the question has the docstring"""

        class te(TestQuestion):
            """simple"""

        self.assertIn("simple", te.question())

        self.assertIsInstance(te.cellid(), str)
        self.assertIsInstance(te.celltag(), str)

    def test_celltags(self):
        """Test cell tag generation."""

        class MyTestFoo(TestQuestion):
            pass

        self.assertEqual("@mtf-", MyTestFoo.celltag()[0:5])

        class _MyTestFoo(TestQuestion):
            pass

        self.assertEqual("@_mtf-", _MyTestFoo.celltag()[0:6])

        class __MyTestFoo(TestQuestion):
            pass

        self.assertEqual("@__mtf-", __MyTestFoo.celltag()[0:7])

        class _(TestQuestion):
            pass

        self.assertEqual("@_-", _.celltag()[0:3])

        class __(TestQuestion):
            pass

        self.assertEqual("@__-", __.celltag()[0:4])

        class mytest(TestQuestion):
            pass

        self.assertEqual("@m-", mytest.celltag()[0:3])

        class mytestFoo(TestQuestion):
            pass

        self.assertEqual("@mf-", mytestFoo.celltag()[0:4])

        class mytestFoo234(TestQuestion):
            pass

        self.assertEqual("@mf234-", mytestFoo234.celltag()[0:7])

    def test_rendering(self):
        """Check docstring rendering"""

        # Should be able to have an empty docstring
        class te(TestQuestion):
            pass

        self.assertIsNotNone(te.question())
        self.assertNotEqual(te.question(), "")

        class te(TestQuestion):
            """{{thing}}"""

            thing: str = "foo"

        # Class access is the parameter
        self.assertIsInstance(te.thing, Parameter)
        # Look for parameter value
        self.assertIn("`foo`", te.question())
        # ValueError on missing parameter in question
        with self.assertRaises(ValueError):

            class te(TestQuestion):
                """{{thing}}"""

                bad_thing: str = "foo"

    def test_params(self):
        """Test using parameters"""

        # Test literal expansion
        class te(TestQuestion):
            """{{param}}"""

            param: str = Parameter("foo", "literal")

        self.assertIn("`foo`", te.question())

        # Test span expansion
        class te(TestQuestion):
            """{{param}}"""

            param: str = Parameter("foo", "span")

        self.assertIn("[foo]", te.question())

        # Test attribute expansion
        class te(TestQuestion):
            """{{param}}"""

            param: str = Parameter("foo", "span", "bar")

        self.assertIn("[foo]{bar}", te.question())

        class te(TestQuestion):
            """{{param}}"""

            param: str = Parameter("foo", "literal", "bar")

        self.assertIn("`foo`{bar}", te.question())

    def test_filters(self):
        """Test my custom filters."""

        class te(TestQuestion):
            """{{param|plain}}"""

            param: str = "foo"

        self.assertNotIn("`foo`", te.question())

        class te(TestQuestion):
            """`{{param|literal}}`"""

            param: str = "foo"

        self.assertIn("``foo``", te.question())

    def test_subclassing(self):
        """Test the subclassing behavior."""

        # This causes an error.
        with self.assertRaises(ValueError):

            class te(TestQuestion):
                """{{thing}}"""

        # Validation disabled by abstract_bases
        class te(TestQuestion):
            """{{thing}}"""

            abstract_bases = TestQuestion.abstract_bases + ["te"]

        # Validation disabled by leading underscore
        class _te(TestQuestion):
            """{{thing}}"""

    def test_template_values(self):
        """Test the return from template_values"""

        class te(TestQuestion):
            foo: str = "bar"

        self.assertIn("celltag", te.template_values())
        self.assertIn("cellid", te.template_values())
        self.assertIn("foo", te.template_values())
        self.assertIsInstance(te.foo, Parameter)
        self.assertIn(te.foo, te.template_values().values())

    def test_variants(self):
        """Test making variants"""

        class te(TestQuestion):
            base: str = "bb"

        # Can't be empty
        with self.assertRaises(ValueError):
            te.variant()

        var = te.variant(classname="blah")
        self.assertEqual("blah", var.__name__)

        var = te.variant(param="baram")
        self.assertEqual(var.param, "baram")

        var = te.variant(param="baram", shmaram=10)
        self.assertEqual(var.param, "baram")
        self.assertEqual(var.shmaram, 10)

        self.assertEqual(var.__name__, "te_param:baram_shmaram:10")


class T2(TestCase):
    """Test FunctionQuestion"""

    def test_basic(self):
        with self.assertRaises(AttributeError):

            class te(FunctionQuestion):
                pass

        with self.assertRaises(AttributeError):

            class te(FunctionQuestion):
                name = "foo"

        with self.assertRaises(ValueError):

            class te(FunctionQuestion):
                name = "foo"
                annotations = {}

    def test_annotations(self):
        """Test the annotations dictionary"""

        class te(FunctionQuestion):
            name = "foo"
            annotations = {
                "bar": str,
                "{name}": str,
                "return": str,
            }

        self.assertIn("bar", te.resolve_annotations())
        self.assertNotIn("name", te.resolve_annotations())
        self.assertIn(te.name, te.resolve_annotations())

        # Currently failing if it suspects you've missed the curlys.
        # Is this really right?
        with self.assertRaises(AssertionError):

            class te(FunctionQuestion):
                name = "foo"
                annotations = {
                    "name": str,
                    "return": str,
                }

    def test_template_values(self):
        class te(FunctionQuestion):
            name = "foo"
            annotations = {
                "bar": str,
                "{name}": str,
                "return": str,
            }

        self.assertIn("annotations", te.template_values())
        self.assertIsInstance(te.template_values(), dict)
