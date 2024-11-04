"""
Make an HTML document preview of a quiz.
"""

import logging

from docutils.core import publish_string
from myst_parser.docutils_ import Parser

from nbquiz.canvas.html import MYST_EXTENSIONS, md_to_canvas_html
from nbquiz.quiz import Quiz

logging.basicConfig(level=logging.INFO)


class Preview(Quiz):
    def __init__(self):
        super().__init__()
        self._title = ""
        self._desc = ""
        self._content = []
        self._count = 1

    def set_title(self, title):
        self._title = title

    def set_description(self, description):
        self._description = description

    def add_file(self, filename):
        pass

    def add_question(self, question):
        self._content.append(
            f"## {self._count}. Question `{question.cellid()}`\n{question.question()}\n"
        )
        self._count += 1

    def add_group(self, group):
        items = {question.cellid(): question.question() for question in group}
        grouptext = f"## {self._count}. Group `{group.__name__}` with {len(items)} Items (pick {group.pick})\n"
        for n, item in enumerate(items):
            grouptext += f"\n\n### Option {n+1} `{item}`\n{items[item]}"
        self._content.append(grouptext)
        self._count += 1

    def write(self, html, pretty):
        content = "\n\n".join([c for c in self._content])
        source = f"""# {self._title}
{self._description}
{content}
"""
        if pretty:
            output = publish_string(
                source=source,
                writer_name="html5",
                settings_overrides={
                    "myst_enable_extensions": MYST_EXTENSIONS,
                    "embed_stylesheet": True,
                },
                parser=Parser(),
            )
            with open(html, "wb") as fh:
                fh.write(output)
        else:
            with open(html, "w") as fh:
                fh.write(md_to_canvas_html(source))


def add_args(parser):
    parser.add_argument(
        "testyaml", help="A YAML file containing a description of a test."
    )
    parser.add_argument(
        "output",
        help="An html file that will have a formatted preview of the quiz.",
    )
    parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        default=False,
        help="""Enable pretty HTML5 output. Defaults to Canvas compatible output.""",
    )


def main(args):
    logging.info(f"Loading test file: {args.testyaml}")
    c = Preview()
    c.load_file(args.testyaml)
    logging.info(f"Writing {args.output}")
    c.write(args.output, args.pretty)
