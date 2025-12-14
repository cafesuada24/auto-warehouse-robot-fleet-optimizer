from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EventEnvelope(_message.Message):
    __slots__ = ["attributes", "causation_id", "content_type", "correlation_id", "envelope_version", "event_id", "event_type", "idempotency_key", "occurred_at", "partition_key", "producer", "tenant_id", "traceparent"]
    class AttributesEntry(_message.Message):
        __slots__ = ["key", "value"]
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    CAUSATION_ID_FIELD_NUMBER: _ClassVar[int]
    CONTENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    ENVELOPE_VERSION_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    OCCURRED_AT_FIELD_NUMBER: _ClassVar[int]
    PARTITION_KEY_FIELD_NUMBER: _ClassVar[int]
    PRODUCER_FIELD_NUMBER: _ClassVar[int]
    TENANT_ID_FIELD_NUMBER: _ClassVar[int]
    TRACEPARENT_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.ScalarMap[str, str]
    causation_id: str
    content_type: str
    correlation_id: str
    envelope_version: int
    event_id: str
    event_type: str
    idempotency_key: str
    occurred_at: _timestamp_pb2.Timestamp
    partition_key: str
    producer: str
    tenant_id: str
    traceparent: str
    def __init__(self, event_id: _Optional[str] = ..., event_type: _Optional[str] = ..., occurred_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., producer: _Optional[str] = ..., tenant_id: _Optional[str] = ..., partition_key: _Optional[str] = ..., idempotency_key: _Optional[str] = ..., correlation_id: _Optional[str] = ..., causation_id: _Optional[str] = ..., traceparent: _Optional[str] = ..., attributes: _Optional[_Mapping[str, str]] = ..., content_type: _Optional[str] = ..., envelope_version: _Optional[int] = ...) -> None: ...
