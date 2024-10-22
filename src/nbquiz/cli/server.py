"""
Launch the server.
"""

import asyncio
import logging

import grpc

from ..runtime.server import Checker, checker_pb2_grpc


def add_args(parser):
    pass


async def run_server(tb) -> None:
    server = grpc.aio.server()
    checker = Checker(tb)
    checker_pb2_grpc.add_CheckerServicer_to_server(checker, server)
    listen_addr = "[::]:32453"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


def main(args, tb):
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server(args.testbank))
