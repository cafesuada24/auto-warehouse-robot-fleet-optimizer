import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EventEnvelope(_message.Message):
    __slots__ = ()
    class AttributesEntry(_message.Message):
        __slots__ = ()
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    PRODUCER_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    PARTITION_KEY_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    TRACEPARENT_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENVELOPE_VERSION_FIELD_NUMBER: _ClassVar[int]
    event_id: str
    event_type: str
    ts_ms: int
    occurred_at: _timestamp_pb2.Timestamp
    producer: str
    tenant_id: str
    partition_key: str
    idempotency_key: str
    correlation_id: str
    causation_id: str
    traceparent: str
    attributes: _containers.ScalarMap[str, str]
    content_type: str
    envelope_version: int
    def __init__(self, event_id: _Optional[str] = ..., event_type: _Optional[str] = ..., ts_ms: _Optional[int] = ..., occurred_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., producer: _Optional[str] = ..., tenant_id: _Optional[str] = ..., partition_key: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., traceparent: _Optional[str] = ..., attributes: _Optional[_Mapping[str, str]] = ..., content_type: _Optional[str] = ..., envelope_version: _Optional[int] = ...) -> None: ...
