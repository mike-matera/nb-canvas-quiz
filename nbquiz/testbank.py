"""
Interface for a group of test banks.
"""

import nbformat
from nbtest.analysis import AnalysisNode

from nbquiz import TestQuestion


class TestBank:
    """A group of test loaded from multiple files."""

    def __init__(self):
        self._tags = {}
        self._questions = []

    def _load(self, filename: str):
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
        self._questions += (
            test_ns[cls]
            for cls in AnalysisNode(source).classes
            if issubclass(test_ns[cls], TestQuestion)
        )

        # Rebuild the caches
        self._tags = {}
        self._required = {}
        self._forbidden = {}
        for q in self._questions:
            for t in q.tags:
                if t not in self._tags:
                    self._tags[t] = [q]
                else:
                    self._tags[t].append(q)

            for r in q.tokens_required:
                if r not in self._required:
                    self._required[r] = [q]
                else:
                    self._required[r].append(q)

            for f in q.tokens_forbidden:
                if f not in self._forbidden:
                    self._forbidden[f] = [q]
                else:
                    self._forbidden[f].append(q)

        print(self._tags)
        print(self._required)
        print(self._forbidden)
