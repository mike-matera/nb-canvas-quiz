"""
Launch the server.
"""

import asyncio
import logging

import grpc

from nbquiz.testbank import bank

from ..runtime.server import Checker, checker_pb2_grpc


def add_args(parser):
    pass


async def run_server() -> None:
    server = grpc.aio.server()
    checker = Checker()
    checker_pb2_grpc.add_CheckerServicer_to_server(checker, server)
    listen_addr = "[::]:32453"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


def main(args):
    # Validate paths so that errors happen sooner rather than later.
    bank.load()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server())
