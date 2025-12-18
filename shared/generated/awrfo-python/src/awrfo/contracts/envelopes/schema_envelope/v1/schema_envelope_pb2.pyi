import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SchemaEnvelope(_message.Message):
    __slots__ = ()
    TIME_S_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    PRODUCER_FIELD_NUMBER: _ClassVar[int]
    ENVELOPE_VERSION_FIELD_NUMBER: _ClassVar[int]
    time_s: float
    occurred_at: _timestamp_pb2.Timestamp
    producer: str
    envelope_version: int
    def __init__(self, time_s: _Optional[float] = ..., occurred_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., producer: _Optional[str] = ..., envelope_version: _Optional[int] = ...) -> None: ...
