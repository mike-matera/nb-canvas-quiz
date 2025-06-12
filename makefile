protos:
	cd src/ && uv run python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. nbquiz/runtime/checker.proto

test:
	uv run python -m unittest tests/test_questions.py

.PHONY: test all
