"""
Command line tools for nbquiz.
"""

import sys

from canvas_html import md_to_canvas_html

from nbquiz.testbank import TestBank


def main():
    tb = TestBank()
    tb._load(sys.argv[1])
    for q in tb.questions:
        print("Question:")
        print(md_to_canvas_html(q.question()))


if __name__ == "__main__":
    exit(main())
