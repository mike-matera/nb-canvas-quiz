"""
Export a test bank to canvas.
"""

from nbquiz.testbank import bank

from ..canvas_html import md_to_canvas_html


def add_args(parser):
    pass


def main(args):
    bank.load()
    for q in bank._questions:
        print(md_to_canvas_html(bank._questions[q].question()))
