"""The checker client."""

import unittest

import grpc

from . import checker_pb2, checker_pb2_grpc

HOST = "localhost"
PORT = 32222


def check(code):
    with grpc.insecure_channel(f"{HOST}:{PORT}") as channel:
        stub = checker_pb2_grpc.CheckerStub(channel)
        response = stub.run_tests(checker_pb2.TestRequest(source=code))
    return response.status, response.response


def proxy_test(cell):
    class TestProxy(unittest.TestCase):
        def test_server(self):
            " "
            status, response = check(cell.source)
            if status != 0:
                self.fail(response)

    return TestProxy
