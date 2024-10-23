"""
The checker server.
"""

import asyncio
import logging

import grpc

from . import checker_pb2, checker_pb2_grpc

logging.basicConfig(level=logging.INFO)


class Checker(checker_pb2_grpc.CheckerServicer):
    def __init__(self, tb):
        self._tbpath = tb

    async def run_tests(
        self,
        request: checker_pb2.TestRequest,
        context: grpc.aio.ServicerContext,
    ) -> checker_pb2.TestReply:
        proc = await asyncio.create_subprocess_shell(
            f"""nbquiz -t {self._tbpath} test""",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(input=request.source.encode("utf-8"))
        if stderr != "":
            logging.warning(stderr)

        await proc.wait()
        return checker_pb2.TestReply(response=stdout, status=proc.returncode)
