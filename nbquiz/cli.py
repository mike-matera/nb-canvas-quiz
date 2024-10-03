"""
Command line tools for nbquiz.
"""

import sys

from nbquiz.testbank import TestBank


def main():
    tb = TestBank()
    tb._load(sys.argv[1])


if __name__ == "__main__":
    exit(main())
