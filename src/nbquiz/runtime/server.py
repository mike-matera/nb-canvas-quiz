"""
The checker server.
"""

import asyncio
import logging

import checker_pb2
import checker_pb2_grpc
import grpc


# Service implementation
class Checker(checker_pb2_grpc.CheckerServicer):
    def __init__(self):
        print("Loading some fucking tests...")

    async def run_tests(
        self,
        request: checker_pb2.TestRequest,
        context: grpc.aio.ServicerContext,
    ) -> checker_pb2.TestReply:
        # Test run is something like
        # Create test notebook file.
        # subprocess.run("jupyter execute --output output.ipynb input.ipynb")
        # Parse the resulting notebook for errors.
        return checker_pb2.TestReply(response="You pretty much fucked it.")


# main()
async def serve() -> None:
    server = grpc.aio.server()
    checker = Checker()
    checker_pb2_grpc.add_CheckerServicer_to_server(checker, server)
    listen_addr = "[::]:32453"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
