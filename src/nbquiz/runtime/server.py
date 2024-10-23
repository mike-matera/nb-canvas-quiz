"""
The checker server.
"""

import asyncio
import logging
import time

import grpc

from nbquiz.testbank import bank

from . import checker_pb2, checker_pb2_grpc

logging.basicConfig(level=logging.INFO)


class Checker(checker_pb2_grpc.CheckerServicer):
    async def run_tests(
        self,
        request: checker_pb2.TestRequest,
        context: grpc.aio.ServicerContext,
    ) -> checker_pb2.TestReply:
        start = time.monotonic()
        proc = await asyncio.create_subprocess_shell(
            f"""nbquiz {" ".join([f"-t {p}" for p in bank.paths])} test""",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=request.source.encode("utf-8"))
        if stderr != "":
            logging.info(stderr)

        await proc.wait()
        end = time.monotonic()
        logging.info(f"Request completed in {end-start} seconds.")
        return checker_pb2.TestReply(response=stdout.decode("utf-8"), status=proc.returncode)
