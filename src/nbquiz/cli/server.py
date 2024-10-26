"""
Launch the server.
"""

import asyncio
import logging
from argparse import ArgumentParser

import grpc

from nbquiz.testbank import bank

from ..runtime.server import Checker, checker_pb2_grpc


def add_args(parser: ArgumentParser):
    parser.add_argument(
        "-p", "--port", type=int, default=32222, help="Run the service on this port number"
    )
    parser.add_argument(
        "-n",
        "--concurrent",
        type=int,
        default=None,
        help="Number of concurrent RPCs allowed. Default is no limit.",
    )


async def run_server(args: ArgumentParser) -> None:
    server = grpc.aio.server(maximum_concurrent_rpcs=args.concurrent)
    checker = Checker()
    checker_pb2_grpc.add_CheckerServicer_to_server(checker, server)
    listen_addr = f"[::]:{args.port}"
    server.add_insecure_port(listen_addr)
    if args.concurrent is not None:
        logging.info(f"Set concurrency limit of {args.concurrent} RPCs.")
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


def main(args: ArgumentParser):
    # Validate paths so that errors happen sooner rather than later.
    bank.load()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server(args))
