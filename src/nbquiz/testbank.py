"""
Interface for a group of test banks.
"""

import io
import logging
import os
import zipfile
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse, urlunparse

import nbformat
import requests

from nbquiz.question import QuestionGroup, TestQuestion

logging.basicConfig(level=logging.INFO)


class _TestBank:
    """A group of test loaded from multiple files."""

    def __init__(self):
        self._questions = {}
        self._sources = ""
        self._paths = []

    def add_path(self, path: str) -> None:
        logging.info(f"Adding notebook search path: {path}")
        self._paths.append(str(path))

    def load(self) -> None:
        """Load the test banks from the collected paths."""
        for p in self._paths:
            url = urlparse(p)
            if url.scheme.startswith("http"):
                self._load_url(url)
            else:
                p = Path(p)
                if not p.exists():
                    raise ValueError("The test bank path doesn't exist:", p)
                if p.suffix == ".zip":
                    self._load_zip(p)
                elif p.suffix == ".ipynb":
                    logging.info(f"Loading test bank file: {p}")
                    with open(p) as fh:
                        self._loads(fh.read())
                else:
                    for nb in p.glob("*.ipynb"):
                        logging.info(f"Loading test bank file: {nb}")
                        with open(nb) as fh:
                            self._loads(fh.read())
        logging.info(f"""Loaded {self.stats()["questions"]} questions.""")

    def _load_url(self, url):
        """Load test questions from a test bank notebook."""
        logging.info(f"Fetching URL: {urlunparse(url)}")
        response = requests.get(urlunparse(url))
        if response.status_code != 200:
            raise ValueError(
                f"Error fetching url: {urlunparse(url)}: {response.status_code}"
            )
        if response.headers["content-type"] == "application/zip":
            self._load_zip(io.BytesIO(response.content))
        elif response.headers["content-type"] == "application/octet-stream":
            self._loads(response.content)
        else:
            raise ValueError(
                f"The url {urlunparse(url)} points to something I don't understand."
            )

    def _load_zip(self, p):
        """Load test banks from a zip file."""
        with zipfile.ZipFile(p, "r") as zip:
            for file in zip.namelist():
                with zip.open(file) as file:
                    logging.info(f"Loading zipped test bank file: {file.name}")
                    self._loads(file.read())

    def _loads(self, data):
        """Load test questions from a test bank notebook."""
        nb = nbformat.reads(data, nbformat.NO_CONVERT)
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
                and instance.__name__ not in instance.abstract_bases
            ):
                logging.info(
                    f"Found question: {instance.cellid()} tag: {instance.celltag()}"
                )
                instance.validate()
                self._questions[instance.celltag()] = instance
                self._questions[instance.cellid()] = instance

            if isinstance(instance, QuestionGroup):
                logging.info(f"Found question group: @{attr}")
                self._questions[f"@{attr}"] = instance
                for question in instance:
                    logging.info(
                        f"  Group question: {question.cellid()} tag: {question.celltag()}"
                    )
                    question.validate()
                    self._questions[question.celltag()] = question
                    self._questions[question.cellid()] = question

    def stats(self):
        return {
            "questions": len(set([id(v) for v in self._questions.values()])),
        }

    def source(self):
        """Return a source code blob of the entire test bank."""
        return self._sources

    def match(self, tags: Iterable[str]) -> TestQuestion:
        """Match a list of tags to the testbank, return a list of all matching tests."""
        questions = [
            self._questions[tag] for tag in tags if tag in self._questions
        ]
        if not questions:
            raise ValueError(
                f"""I can't find a test for any of the tags: {", ".join(tags)}. Did you add the tag from the question?"""
            )
        return questions

    def find(self, tag: str) -> TestQuestion:
        """Find a test question by tag."""
        found = self.match([tag])
        if len(found) == 0:
            raise ValueError(f"Cannot find tag: {tag}")
        return found[0]

    @property
    def questions(self):
        return self._questions

    @property
    def paths(self):
        return self._paths


# Global singleton
bank = _TestBank()

if "NBQUIZ_TESTBANKS" in os.environ:
    for path in os.environ.get("NBQUIZ_TESTBANKS").split(","):
        bank.add_path(path)
