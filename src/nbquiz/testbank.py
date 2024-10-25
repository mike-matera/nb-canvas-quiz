"""
Interface for a group of test banks.
"""

import logging
from pathlib import Path
from typing import Iterable, Union

import nbformat

from nbquiz.question import CellQuestion, FunctionQuestion, QuestionGroup, TestQuestion

logging.basicConfig(level=logging.INFO)


class _TestBank:
    """A group of test loaded from multiple files."""

    def __init__(self):
        self._questions = {}
        self._sources = ""
        self._paths = []

    def add_path(self, path: Union[str, Path]) -> None:
        path = Path(path).absolute()
        if not path.exists():
            raise ValueError(f"""Path "{path} does not exist.""")
        logging.info(f"Adding notebook search path: {path}")
        self._paths.append(path)

    def load(self) -> None:
        for p in self._paths:
            for nb in p.glob("*.ipynb"):
                logging.info(f"Loaded testbank file: {nb}")
                self._load(nb)

        logging.info(f"""Loaded {self.stats()["questions"]} questions.""")

    def stats(self):
        return {
            "questions": len(set([id(v) for v in self._questions.values()])),
        }

    def source(self):
        """Return a source code blob of the entire test bank."""
        return self._sources

    def match(self, tags: Iterable[str]) -> TestQuestion:
        """Match a list of tags to the testbank, return a list of all matching tests."""
        questions = [self._questions[tag] for tag in tags if tag in self._questions]
        if not questions:
            raise ValueError("""No question tag found. Did you add the tag from the question?""")
        return questions

    def find(self, tag: str) -> TestQuestion:
        """Find a test question by tag."""
        found = self.match([tag])
        if len(found) == 0:
            raise ValueError(f"Cannot find tag: {tag}")
        return found[0]

    def _load(self, filename: Union[str, Path]):
        nb = nbformat.read(filename, nbformat.NO_CONVERT)
        source = "\n\n".join(
            [
                cell["source"]
                for cell in nb["cells"]
                if cell["cell_type"] == "code"
                and "tags" in cell["metadata"]
                and "question" in cell["metadata"]["tags"]
            ]
        )
        test_ns = {}
        exec(source, test_ns)
        self._sources += "\n\n" + source

        for attr in test_ns:
            instance = test_ns[attr]
            if (
                not attr.startswith("_")
                and isinstance(instance, type)
                and issubclass(instance, TestQuestion)
                and instance not in [TestQuestion, FunctionQuestion, CellQuestion]
            ):
                logging.info(f"Found question: {instance.cellid()} tag: {instance.celltag()}")
                instance.validate()
                self._questions[instance.celltag()] = instance
                self._questions[instance.cellid()] = instance

            if isinstance(instance, QuestionGroup):
                logging.info(f"Found question group: @{attr}")
                self._questions[f"@{attr}"] = instance
                for question in instance:
                    logging.info(f"  Group question: {question.cellid()} tag: {question.celltag()}")
                    question.validate()
                    self._questions[question.celltag()] = question
                    self._questions[question.cellid()] = question

    @property
    def questions(self):
        return self._questions

    @property
    def paths(self):
        return self._paths


# Global singleton
bank = _TestBank()
