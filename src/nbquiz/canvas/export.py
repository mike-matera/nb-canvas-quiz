"""
The ability to construct a Canvas quiz export.
"""

import uuid
import zipfile
from abc import ABC
from dataclasses import dataclass, field
from typing import Union

from jinja2 import Environment, PackageLoader, Template

jinja = Environment(
    loader=PackageLoader("nbquiz", package_path="resources/canvas"),
)


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
        return EssayItem.template.render(id=self.id, title=self.title, html=self.html)


@dataclass
class FileItem(_Item):
    """A file upload question"""

    template = jinja.get_template("assessment/item_file.xml")

    def render(self):
        return FileItem.template.render(id=self.id, title=self.title, html=self.html)


@dataclass
class Section(_Chunk):
    """A group of questions"""

    template = jinja.get_template("assessment/section.xml")

    id: str = field(default_factory=_Chunk._id)
    title: str = ""
    items: list[_Item] = field(default_factory=list)

    def render(self):
        return Section.template.render(
            id=self.id, title=self.title, items="\n".join([i.render() for i in self.items])
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
            id=self.id, title=self.title, questions="\n".join([i.render() for i in self.questions])
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
            title=self.title,
            description=self.description,
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
        return FileResource.template.render(id=self.id, filename=self.filename)


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


q1 = EssayItem(title="question1", html="instructions1")
q2 = EssayItem(title="question2", html="instructions2")
group = Section(title="Question Group", items=[q1, q2])
q3 = FileItem(title="Upload", html="Submit Here")
quiz = Assessment(title="My Test Assessment", questions=[group, q3])
meta = AssessmentMeta(assessment_id=quiz.id, title="This is the final", description="Do it now!")
asmr = AssessmentResource(assessment_id=quiz.id)
file = FileResource(filename="temp_test_stdin.txt")
manifest = Manifest(resources=[asmr, file])


with zipfile.ZipFile("output.zip", "w") as zf:
    zf.writestr("imsmanifest.xml", manifest.render())
    zf.writestr(f"{quiz.id}/{quiz.id}.xml", quiz.render())
    zf.writestr(f"{quiz.id}/assessment_meta.xml", meta.render())
    zf.writestr("non_cc_assessments/", "")
    zf.write(arcname=f"web_resources/Uploaded Media/{file.filename}", filename=file.filename)
