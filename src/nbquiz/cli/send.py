"""
Send a code message to the server and view the response.
"""

import logging
import sys

from nbquiz.runtime.client import check

logging.basicConfig(level=logging.INFO)


def add_args(parser):
    pass


def main(args):
    status, response = check(sys.stdin.read())
    print(response)
    sys.exit(status)
