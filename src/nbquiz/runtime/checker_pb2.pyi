from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TestRequest(_message.Message):
    __slots__ = ("id", "source")
    ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    source: str
    def __init__(self, id: _Optional[str] = ..., source: _Optional[str] = ...) -> None: ...

class TestReply(_message.Message):
    __slots__ = ("response", "error")
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    response: str
    error: str
    def __init__(self, response: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...
