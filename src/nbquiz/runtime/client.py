"""The checker client."""

import logging

import checker_pb2
import checker_pb2_grpc
import grpc


def run():
    print("I'm gonna send your code.")
    with grpc.insecure_channel("localhost:") as channel:
        print("I'm connected to the Checker!")
        stub = checker_pb2_grpc.CheckerStub(channel)

        response = stub.run_tests(checker_pb2.TestRequest(id="@fuck", source="you"))

    print("Greeter client received: " + response.response)


if __name__ == "__main__":
    logging.basicConfig()
    run()
