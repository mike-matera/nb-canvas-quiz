all:
	cd src/ && python -m grpc_tools.protoc -I. --python_out=. --pyi_out=. --grpc_python_out=. nbquiz/runtime/checker.proto
