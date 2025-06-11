"""
The ability to construct a Canvas quiz export.
"""

import logging
import uuid
import zipfile
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union
from xml.sax.saxutils import escape

import nbformat
from jinja2 import Environment, PackageLoader, Template

from nbquiz.question import TestQuestion
from nbquiz.quiz import Quiz

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
    pick: int = 1
    items: list[_Item] = field(default_factory=list)

    def render(self):
        return Section.template.render(
            id=self.id,
            title=escape(self.title),
            pick=self.pick,
            items="\n".join([i.render() for i in self.items]),
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
        return AssessmentResource.template.render(
            id=self.id, assessment_id=self.assessment_id
        )


@dataclass
class FileResource(_Chunk):
    """A reference to a saved file."""

    template = jinja.get_template("resource_file.xml")

    id: str = field(default_factory=_Chunk._id)
    filename: str = None  # assumed to b in "web_resources/Uploaded Media/"

    def render(self):
        return FileResource.template.render(
            id=self.id, filename=escape(self.filename)
        )


@dataclass
class Manifest(_Chunk):
    """The top-level manifest."""

    template = jinja.get_template("imsmanifest.xml")

    id: str = field(default_factory=_Chunk._id)
    resources: list[Union[FileResource | AssessmentResource]] = field(
        default_factory=list
    )

    def render(self):
        return Manifest.template.render(
            id=self.id,
            resources="\n".join([i.render() for i in self.resources]),
        )


class CanvasExport(Quiz):
    """
    An API to construct an export package containing one quiz and arbitrary
    files.
    """

    def __init__(self):
        """Create a Canvas quiz export with the given title and description."""

        self._quiz = Assessment(title="Quiz", questions=[])
        self._quiz_meta = AssessmentMeta(
            assessment_id=self._quiz.id,
            title="Quiz",
            description="Description",
        )
        self._quiz_res = AssessmentResource(assessment_id=self._quiz.id)
        self._manifest = Manifest(resources=[self._quiz_res])
        self._files = []

    def set_title(self, title):
        """Set the title in Canvas. Visible to students."""
        self._quiz.title = title
        self._quiz_meta.title = title

    def set_description(self, description):
        """Set the quiz instructions. Visible before students open the test."""
        self._quiz_meta.description = md_to_canvas_html(description)

    def add_file(self, name: str):
        """Add a file path to the uploaded media."""

        p = Path(name)
        if not p.exits():
            raise ValueError(f"File {p} does not exist.")
        self._files.append(p.absolute())

    def add_question(self, question: TestQuestion):
        """Add a test question to the assessment."""

        logging.info(f"Adding question: {question}")
        self._quiz.questions.append(
            EssayItem(
                title=question.__name__,
                html=md_to_canvas_html(question.question()),
            )
        )

    def add_group(self, group):
        """Add a question group to the assessment."""

        logging.info(f"Adding group: {group}")
        self._quiz.questions.append(
            Section(
                title=group.__name__,
                pick=group.pick,
                items=[
                    EssayItem(
                        title=question.__name__,
                        html=md_to_canvas_html(question.question()),
                    )
                    for question in group
                ],
            )
        )

    def write(self, filename):
        """Write the assessment export ZIP file to disk."""

        nb = nbformat.v4.new_notebook()
        nb.cells.append(
            nbformat.v4.new_code_cell(
                """%load_ext nb_unittest""",
                metadata={"editable": False, "deletable": False},
            ),
        )
        nb.cells.append(
            nbformat.v4.new_markdown_cell(
                f"""# {self._quiz_meta.title}
{self._quiz_meta.description}
""",
                metadata={"editable": False, "deletable": False},
            )
        )
        for i, question in enumerate(self._quiz.questions):
            nb.cells.append(
                nbformat.v4.new_markdown_cell(
                    f"""# Question {i + 1}
Please answer question #{i + 1} in the next cell.
""",
                    metadata={"editable": False, "deletable": False},
                )
            )
            nb.cells.append(
                nbformat.v4.new_code_cell(
                    f"""\"""
@answer{i + 1}
Add the checker tag here: 
\"""
""",
                    metadata={"editable": True, "deletable": False},
                )
            )
            nb.cells.append(
                nbformat.v4.new_code_cell(
                    f"""%%testing @answer{i + 1} 
import nbquiz.runtime.client
nbtest_cases = [nbquiz.runtime.client.proxy_test(answer{i + 1})]
""",
                    metadata={"editable": False, "deletable": False},
                )
            )

        def file_link(filename):
            return f"""<a class="instructure_file_link inline_disabled" title="{filename}" href="$IMS-CC-FILEBASE$/Uploaded%20Media/{filename}?canvas_=1&amp;canvas_qs_wrap=1" target="_blank" data-canvas-previewable="false">{filename}</a>"""

        with zipfile.ZipFile(filename, "w") as zf:
            # Add a section to the description with a list of files:
            self._quiz_meta.description += """<p>Attached files:<ul>"""

            # Finalize and write any additional file resources.
            for file in self._files:
                self._manifest.resources.append(
                    FileResource(filename=file.name)
                )
                zf.write(
                    arcname=f"web_resources/Uploaded Media/{file.name}",
                    file=file,
                )
                self._quiz_meta.description += (
                    f"<li>{file_link(file.name)}</li>"
                )

            # Add the test file to the manifest.
            nbfilename = f"{self._quiz_meta.title}.ipynb"
            self._manifest.resources.append(FileResource(filename=nbfilename))
            zf.writestr(
                f"web_resources/Uploaded Media/{nbfilename}",
                data=nbformat.writes(nb),
            )
            self._quiz_meta.description += (
                f"<li>{file_link(nbfilename)}</li></ul></p>"
            )

            # Finalize the test with the file upload question
            self._quiz.questions.append(
                FileItem(
                    title="Upload", html="""Upload your Jupyter notebook"""
                )
            )

            # Write out the rest of the resources.
            zf.writestr("imsmanifest.xml", self._manifest.render())
            zf.writestr(
                f"{self._quiz.id}/{self._quiz.id}.xml", self._quiz.render()
            )
            zf.writestr(
                f"{self._quiz.id}/assessment_meta.xml",
                self._quiz_meta.render(),
            )
            zf.writestr("non_cc_assessments/", "")
