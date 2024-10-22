"""
Export a test bank to canvas.
"""

from ..canvas_html import md_to_canvas_html


def add_args(parser):
    pass


def main(args, tb):
    for q in tb._questions:
        print(md_to_canvas_html(tb._questions[q]["class"].question()))
