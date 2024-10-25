"""
The ability to construct a Canvas quiz export.
"""

import logging
import uuid
import zipfile
from abc import ABC
from dataclasses import dataclass, field
from io import TextIOWrapper
from pathlib import Path
from typing import Union
from xml.sax.saxutils import escape

import yaml
from jinja2 import Environment, PackageLoader, Template

from nbquiz.question import QuestionGroup, TestQuestion

from ..testbank import bank
from .html import md_to_canvas_html

jinja = Environment(
    loader=PackageLoader("nbquiz", package_path="resources/canvas"),
)

logging.basicConfig(level=logging.INFO)


@dataclass
class _Chunk(ABC):
    template: Template = None

    @staticmethod
    def _id():
        return "g" + str(uuid.uuid4()).replace("-", "")


@dataclass
class _Item(_Chunk):
    """Base class for questions."""

    id: str = field(default_factory=_Chunk._id)
    title: str = ""
    html: str = ""


@dataclass
class EssayItem(_Item):
    """An essay question"""

    template = jinja.get_template("assessment/item_essay.xml")

    def render(self):
        return EssayItem.template.render(
            id=self.id, title=escape(self.title), html=escape(self.html)
        )


@dataclass
class FileItem(_Item):
    """A file upload question"""

    template = jinja.get_template("assessment/item_file.xml")

    def render(self):
        return FileItem.template.render(
            id=self.id, title=escape(self.title), html=escape(self.html)
        )


@dataclass
class Section(_Chunk):
    """A group of questions"""

    template = jinja.get_template("assessment/section.xml")

    id: str = field(default_factory=_Chunk._id)
    title: str = ""
    items: list[_Item] = field(default_factory=list)

    def render(self):
        return Section.template.render(
            id=self.id, title=escape(self.title), items="\n".join([i.render() for i in self.items])
        )


@dataclass
class Assessment(_Chunk):
    """A quiz."""

    template = jinja.get_template("assessment/assessment.xml")

    id: str = field(default_factory=_Chunk._id)
    title: str = ""
    questions: list[Union[_Item, Section]] = field(default_factory=list)

    def render(self):
        return Assessment.template.render(
            id=self.id,
            title=escape(self.title),
            questions="\n".join([i.render() for i in self.questions]),
        )


@dataclass
class AssessmentMeta(_Chunk):
    """Metadata for an assessment"""

    template = jinja.get_template("assessment/assessment_meta.xml")

    id: str = field(default_factory=_Chunk._id)
    assessment_id: str = None  # Joins with id in Assessment
    title: str = ""
    description: str = ""

    def render(self):
        return AssessmentMeta.template.render(
            id=self.id,
            assessment_id=self.assessment_id,
            title=escape(self.title),
            description=escape(self.description),
        )


@dataclass
class AssessmentResource(_Chunk):
    """A resource reference to an assessment."""

    template = jinja.get_template("resource_assessment.xml")

    id: str = field(default_factory=_Chunk._id)
    assessment_id: str = None  # Joins with id in Assessment

    def render(self):
        return AssessmentResource.template.render(id=self.id, assessment_id=self.assessment_id)


@dataclass
class FileResource(_Chunk):
    """A reference to a saved file."""

    template = jinja.get_template("resource_file.xml")

    id: str = field(default_factory=_Chunk._id)
    filename: str = None  # assumed to b in "web_resources/Uploaded Media/"

    def render(self):
        return FileResource.template.render(id=self.id, filename=escape(self.filename))


@dataclass
class Manifest(_Chunk):
    """The top-level manifest."""

    template = jinja.get_template("imsmanifest.xml")

    id: str = field(default_factory=_Chunk._id)
    resources: list[Union[FileResource | AssessmentResource]] = field(default_factory=list)

    def render(self):
        return Manifest.template.render(
            id=self.id, resources="\n".join([i.render() for i in self.resources])
        )


class CanvasExport:
    """
    An API to construct an export package containing one quiz and arbitrary files.
    """

    def __init__(self, title, description):
        self._quiz = Assessment(title=title, questions=[])
        self._quiz_meta = AssessmentMeta(
            assessment_id=self._quiz.id, title=title, description=md_to_canvas_html(description)
        )
        self._quiz_res = AssessmentResource(assessment_id=self._quiz.id)
        self._manifest = Manifest(resources=[self._quiz_res])
        self._files = []

    @classmethod
    def from_yaml(cls, stream: TextIOWrapper):
        """Factory method to create a test from a YAML description."""

        test = yaml.load(stream, Loader=yaml.Loader)

        # TODO: validate YAML
        export = CanvasExport(title=test["title"], description=test["description"])

        def elaborate_group(questions_data):
            for question_data in questions_data:
                match question_data:
                    case {"group": _, "questions": _}:
                        raise ValueError("Canvas does not allow groups in groups.")
                    case {"name": name, "params": params}:
                        question = bank.find(f"@{name}")
                        variant = question.variant(**params)
                        yield variant
                    case str() as name:
                        question = bank.find(f"@{name}")
                        if isinstance(question, QuestionGroup):
                            raise ValueError("Canvas does not allow groups in groups.")
                        yield bank.find(f"@{name}")

        for question_data in test["questions"]:
            match question_data:
                case {"group": group, "questions": questions}:
                    export.add_group(QuestionGroup(group, list(elaborate_group(questions))))

                case {"name": name, "params": params}:
                    question = bank.find(f"@{name}")
                    variant = question.variant(**params)
                    export.add_question(variant)

                case str() as name:
                    question = bank.find(f"@{name}")
                    if isinstance(question, type) and issubclass(question, TestQuestion):
                        export.add_question(question)
                    elif isinstance(question, QuestionGroup):
                        export.add_group(question)

                case _:
                    raise ValueError(f"I don't understand this: {question_data}")

        return export

    def add_file(self, name):
        p = Path(name)
        if not p.exits():
            raise ValueError(f"File {p} does not exist.")
        self._files.append(p.absolute())

    def add_question(self, question):
        logging.info(f"Adding question: {question}")
        self._quiz.questions.append(
            EssayItem(title=question.__name__, html=md_to_canvas_html(question.question()))
        )

    def add_group(self, group):
        logging.info(f"Adding question: {group}")
        self._quiz.questions.append(
            Section(
                title="Group",
                items=[
                    EssayItem(title=question.__name__, html=md_to_canvas_html(question.question()))
                    for question in group
                ],
            )
        )

    def write(self, filename):
        with zipfile.ZipFile(filename, "w") as zf:
            # Finalize and write the file resources.
            for file in self._files:
                self._manifest.resources.append(FileResource(filename=file.name))
                zf.write(arcname=f"web_resources/Uploaded Media/{file.name}", filename=file)

            # Finalize the test with the file upload question
            self._quiz.questions.append(
                FileItem(title="Upload", html="""Upload your Jupyter notebook""")
            )

            # Write out the rest of the resources.
            zf.writestr("imsmanifest.xml", self._manifest.render())
            zf.writestr(f"{self._quiz.id}/{self._quiz.id}.xml", self._quiz.render())
            zf.writestr(f"{self._quiz.id}/assessment_meta.xml", self._quiz_meta.render())
            zf.writestr("non_cc_assessments/", "")
